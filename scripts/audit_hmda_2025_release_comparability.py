"""Audit same-year HMDA 2025 Snapshot versus captured Dynamic aggregates.

Raw HMDA rows remain in the private data root. This script reads only the
receipt-bound aggregate views and acquisition receipts, emits a small public
summary JSON, and stores hashes/paths in a private audit receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


SOURCES = {
    "snapshot": {
        "source_id": "hmda-national-snapshot-2025-9a5e89600e3c",
        "status": "VERIFIED_HMDA_NATIONAL_SNAPSHOT_2025",
        "receipt": Path("data/private/hmda/hmda-national-snapshot-2025-9a5e89600e3c/acquisition-complete.json"),
        "release": "2025 Static Snapshot",
        "source_as_of": "2026-06-02",
    },
    "dynamic": {
        "source_id": "hmda-national-dynamic-2025-20261011",
        "status": "VERIFIED_HMDA_2025_DYNAMIC_AS_OF_2026_10_11",
        "receipt": Path("data/private/hmda/hmda-national-dynamic-2025-20261011/acquisition-complete.json"),
        "release": "2025 Dynamic weekly capture",
        "source_as_of": "2026-10-11T12:00:30Z",
    },
}

ACTION_LABELS = {
    "1": "originated",
    "2": "approved_not_accepted",
    "3": "denied",
    "4": "withdrawn",
    "5": "closed_incomplete",
    "6": "purchased",
    "7": "preapproval_denied",
    "8": "preapproval_approved_not_accepted",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_action_profile(items: list[dict]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        code = str(item.get("code", item.get("value", "")))
        if code not in ACTION_LABELS or code in result:
            raise ValueError(f"Unexpected or duplicate action code in receipt: {code!r}")
        result[code] = int(item["records"])
    if set(result) != set(ACTION_LABELS):
        raise ValueError(f"Expected action codes 1-8, found {sorted(result)}")
    return result


def latest_aggregate(data_root: Path, source_id: str) -> tuple[Path, Path, dict, dict]:
    matches = []
    for folder in (data_root / "artifacts/private").glob("hmda-national-view-*"):
        view_path = folder / "view-complete.json"
        aggregate_path = folder / "aggregates.json"
        if not view_path.is_file() or not aggregate_path.is_file():
            continue
        view = read_json(view_path)
        if (view.get("source_id") == source_id
                and view.get("status") == "VERIFIED_HMDA_NATIONAL_AGGREGATE_VIEW"):
            matches.append((str(view.get("completed_at", "")), view_path, aggregate_path, view))
    if not matches:
        raise FileNotFoundError(f"No verified aggregate view found for {source_id}")
    _, view_path, aggregate_path, view = max(matches, key=lambda row: row[0])
    return view_path, aggregate_path, view, read_json(aggregate_path)


def validate_aggregate(name: str, receipt: dict, aggregate: dict) -> tuple[dict, dict[str, int]]:
    profile = receipt["datasets"]["lar"]["profile"]
    summary = aggregate["summary"]
    action_counts = normalize_action_profile(profile["actions"])
    aggregate_actions = {str(row["code"]): int(row["records"]) for row in aggregate["actions"]}
    if aggregate_actions != action_counts:
        raise ValueError(f"{name}: aggregate action counts do not match the acquisition receipt")
    records = int(summary["records"])
    reporters = int(summary["reporters"])
    decision_denominator = sum(action_counts[code] for code in ("1", "2", "3"))
    denied_numerator = action_counts["3"]
    if sum(action_counts.values()) != records:
        raise ValueError(f"{name}: action counts do not sum to all records")
    if int(summary["decision_denominator"]) != decision_denominator:
        raise ValueError(f"{name}: denominator does not equal action 1+2+3")
    if int(summary["denied_numerator"]) != denied_numerator:
        raise ValueError(f"{name}: denied numerator does not equal action 3")
    observed_rate = Decimal(str(summary["descriptive_denial_rate"]))
    expected_rate = Decimal(denied_numerator) / Decimal(decision_denominator)
    if abs(observed_rate - expected_rate) > Decimal("1e-15"):
        raise ValueError(f"{name}: denial share does not recompute from exact counts")
    source_summary = profile["summary"]
    if int(source_summary["records"]) != records:
        raise ValueError(f"{name}: aggregate row count does not match source receipt")
    source_reporters = source_summary.get("distinct_reporting_LEIs", source_summary.get("distinct_LEIs"))
    if int(source_reporters) != reporters:
        raise ValueError(f"{name}: aggregate reporter count does not match source receipt")
    if receipt.get("public_release_approved") is not False:
        raise ValueError(f"{name}: private acquisition receipt must keep public_release_approved=false")
    return {
        "release": SOURCES[name]["release"],
        "source_as_of": SOURCES[name]["source_as_of"],
        "lar_records": records,
        "reporters": reporters,
        "decision_denominator_actions_1_2_3": decision_denominator,
        "denied_numerator_action_3": denied_numerator,
        "descriptive_denied_share": str(expected_rate),
    }, action_counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    parser.add_argument("--output", type=Path, required=True, help="Sanitized public JSON output path")
    args = parser.parse_args()
    data_root = args.data_root.resolve()
    if data_root.drive.upper() != "D:":
        raise ValueError("Private data and receipts must remain on D:")

    private_inputs = {}
    summaries = {}
    action_counts = {}
    for name, spec in SOURCES.items():
        receipt_path = data_root / spec["receipt"]
        receipt = read_json(receipt_path)
        if receipt.get("source_id") != spec["source_id"] or receipt.get("status") != spec["status"]:
            raise ValueError(f"{name}: unexpected acquisition receipt identity/status")
        observed_as_of = receipt.get("snapshot_freeze_date") or receipt.get("release_as_of_utc")
        if isinstance(observed_as_of, dict):
            observed_as_of = observed_as_of.get("lar")
        if isinstance(observed_as_of, str) and observed_as_of.endswith(" GMT"):
            observed_as_of = datetime.strptime(
                observed_as_of, "%a, %d %b %Y %H:%M:%S GMT"
            ).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        if observed_as_of != spec["source_as_of"]:
            raise ValueError(f"{name}: release date in acquisition receipt changed: {observed_as_of!r}")
        view_path, aggregate_path, view, aggregate = latest_aggregate(data_root, spec["source_id"])
        summary, actions = validate_aggregate(name, receipt, aggregate)
        summaries[name] = summary
        action_counts[name] = actions
        lar = receipt["datasets"]["lar"]
        archive_sha = (lar.get("archive") or {}).get("sha256") or lar.get("archive_sha256")
        csv_sha = (lar.get("csv") or {}).get("sha256")
        private_inputs[name] = {
            "source_id": spec["source_id"],
            "acquisition_receipt_path": str(receipt_path),
            "acquisition_receipt_sha256": sha256(receipt_path),
            "lar_archive_sha256": archive_sha,
            "lar_csv_sha256": csv_sha,
            "view_receipt_path": str(view_path),
            "view_receipt_sha256": sha256(view_path),
            "aggregate_path": str(aggregate_path),
            "aggregate_sha256": sha256(aggregate_path),
            "view_completed_at": view.get("completed_at"),
        }

    snapshot = summaries["snapshot"]
    dynamic = summaries["dynamic"]
    denied_share_delta_pp = (
        (Decimal(dynamic["descriptive_denied_share"])
         - Decimal(snapshot["descriptive_denied_share"]))
        * Decimal(100)
    ).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    delta = {
        "lar_records": dynamic["lar_records"] - snapshot["lar_records"],
        "reporters": dynamic["reporters"] - snapshot["reporters"],
        "decision_denominator_actions_1_2_3": (
            dynamic["decision_denominator_actions_1_2_3"]
            - snapshot["decision_denominator_actions_1_2_3"]
        ),
        "denied_numerator_action_3": (
            dynamic["denied_numerator_action_3"] - snapshot["denied_numerator_action_3"]
        ),
        "denied_share_percentage_points": str(denied_share_delta_pp),
    }
    action_deltas = [
        {
            "action_taken": code,
            "label": ACTION_LABELS[code],
            "snapshot_records": action_counts["snapshot"][code],
            "dynamic_records": action_counts["dynamic"][code],
            "dynamic_minus_snapshot": action_counts["dynamic"][code] - action_counts["snapshot"][code],
        }
        for code in ACTION_LABELS
    ]
    if sum(row["dynamic_minus_snapshot"] for row in action_deltas) != delta["lar_records"]:
        raise ValueError("Action-count deltas do not reconcile to the all-record delta")
    if sum(row["dynamic_minus_snapshot"] for row in action_deltas[:3]) != delta["decision_denominator_actions_1_2_3"]:
        raise ValueError("Action 1-3 deltas do not reconcile to the decision-denominator delta")
    if action_deltas[2]["dynamic_minus_snapshot"] != delta["denied_numerator_action_3"]:
        raise ValueError("Action-3 delta does not reconcile to the denied-numerator delta")

    public = {
        "evidence_type": "hmda_2025_same_year_release_comparison",
        "status": "PASS",
        "activity_year": 2025,
        "comparison_basis": {
            "snapshot": snapshot,
            "dynamic": dynamic,
            "delta_dynamic_minus_snapshot": delta,
            "action_count_deltas": action_deltas,
            "denominator_contract": "action_taken 1+2+3",
            "denied_share_formula": "count(action_taken=3) / count(action_taken in 1,2,3)",
        },
        "interpretation": [
            "The comparison holds activity year constant and changes only the publisher release state captured here.",
            "The Dynamic capture includes late submissions/resubmissions after the Snapshot freeze; these are aggregate record-count differences, not borrower transitions.",
            "HMDA records application and underwriting actions, not repayment, delinquency, default, loss, or probability of default.",
        ],
        "limitations": [
            "No row-level matching or unique borrower/application transition is claimed.",
            "The Dynamic file is a dated weekly capture, not a final annual vintage.",
            "This calculation uses receipt-bound source-verified aggregates and acquisition action profiles; it does not perform a second parse of raw LAR rows.",
            "Detailed receipts, raw data and source hashes remain private.",
        ],
        "official_sources": [
            "https://ffiec.cfpb.gov/data-publication/snapshot-national-loan-level-dataset/2025",
            "https://ffiec.cfpb.gov/data-publication/dynamic-national-loan-level-dataset/2025",
            "https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq",
            "https://ffiec.cfpb.gov/documentation/api/data-browser/",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(public, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    args.output.write_bytes(encoded)

    receipt_id = uuid.uuid4().hex[:12]
    private_dir = data_root / "artifacts/private" / f"hmda-release-comparability-audit-{receipt_id}"
    private_dir.mkdir(parents=True, exist_ok=False)
    private_receipt = {
        "status": "PASS_HMDA_2025_SAME_YEAR_RELEASE_COMPARISON",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "visibility": "private",
        "public_release_approved": False,
        "public_output": str(args.output.resolve()),
        "public_output_sha256": hashlib.sha256(encoded).hexdigest(),
        "generator_sha256": sha256(Path(__file__).resolve()),
        "private_inputs": private_inputs,
        "validation": {
            "acquisition_receipt_status_and_source_id": "PASS",
            "acquisition_action_profiles_match_aggregate_action_counts": "PASS",
            "action_codes_1_through_8_sum_to_release_records": "PASS",
            "action_1_plus_2_plus_3_equals_decision_denominator": "PASS",
            "action_3_equals_denied_numerator": "PASS",
            "snapshot_and_dynamic_capture_dates_are_distinct": "PASS",
            "no_raw_lar_rows_written_to_public_output": True,
            "no_forecast_or_imputation": True,
        },
        "result": public["comparison_basis"],
    }
    receipt_path = private_dir / "receipt.json"
    receipt_path.write_text(json.dumps(private_receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "public_output": str(args.output),
        "private_receipt": str(receipt_path),
        "record_delta": delta["lar_records"],
        "decision_denominator_delta": delta["decision_denominator_actions_1_2_3"],
        "denied_share_delta_pp": delta["denied_share_percentage_points"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
