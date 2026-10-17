"""Audit action counts for the HMDA release selected by the official Data Browser.

The API response is an aggregate of actions 1–8 only. Exact local receipt
profiles are used to distinguish the Browser-selected release from the
different One-Year archive currently shown by CreditAtlas for 2019–2022.
Raw LAR files are never read or copied by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


API_BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/aggregations"
API_DOCS = "https://ffiec.cfpb.gov/documentation/api/data-browser/"
FAQ = "https://ffiec.cfpb.gov/documentation/tools/data-browser/data-browser-faq"
ACTION_FILTER = "1,2,3,4,5,6,7,8"
FREEZES = {
    2018: ("Three-Year", "2021-12-31"),
    2019: ("Three-Year", "2022-12-31"),
    2020: ("Three-Year", "2023-12-31"),
    2021: ("Three-Year", "2024-12-31"),
    2022: ("Three-Year", "2025-12-31"),
    2023: ("One-Year", "2025-05-19"),
    2024: ("One-Year", "2026-06-02"),
    2025: ("Snapshot", "2026-06-02"),
}
ACTIONS = tuple(str(code) for code in range(1, 9))


class AuditError(ValueError):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rate(denied: int, decisions: int) -> str:
    if decisions <= 0:
        return ""
    return format(Decimal(denied) / Decimal(decisions), ".12f")


def pp_delta(browser_rate: str, local_rate: str) -> str | None:
    if not browser_rate or not local_rate:
        return None
    return format((Decimal(browser_rate) - Decimal(local_rate)) * Decimal(100), ".8f")


def totals(actions: dict[str, int]) -> dict:
    records = sum(actions.values())
    decisions = sum(actions[code] for code in ("1", "2", "3"))
    denied = actions["3"]
    return {
        "action_1_to_8_records": records,
        "decision_denominator_actions_1_2_3": decisions,
        "denied_numerator_action_3": denied,
        "descriptive_denied_share": rate(denied, decisions),
    }


def parse_actions(profile: dict) -> dict[str, int]:
    if isinstance(profile.get("recognized_action_counts"), dict):
        raw = profile["recognized_action_counts"]
        actions = {str(key): int(value) for key, value in raw.items() if str(key) in ACTIONS}
    else:
        raw = profile.get("actions")
        if isinstance(raw, dict):
            actions = {str(key): int(value) for key, value in raw.items() if str(key) in ACTIONS}
        elif isinstance(raw, list):
            actions = {}
            for row in raw:
                if not isinstance(row, dict):
                    continue
                code = str(row.get("value", row.get("code", "")))
                if code in ACTIONS:
                    if code in actions:
                        raise AuditError(f"Duplicate local action code {code}")
                    actions[code] = int(row["records"])
        else:
            raise AuditError("Local source receipt has no recognizable action profile")
    if set(actions) != set(ACTIONS) or any(value < 0 for value in actions.values()):
        raise AuditError("Local receipt must contain nonnegative counts for action codes 1–8")
    return actions


def _receipt_source(source_dir: Path, receipt_name: str, vintage: str,
                    freeze_date: str, profile: dict, source_id: str | None = None) -> dict:
    actions = parse_actions(profile)
    summary = profile.get("summary", {})
    receipt_total = summary.get("records")
    action_total = sum(actions.values())
    quarantined = int(profile.get("quarantined_out_of_domain_rows", {}).get("rows", 0) or 0)
    if receipt_total is not None and int(receipt_total) != action_total + quarantined:
        raise AuditError(f"{source_dir.name}: action profile does not reconcile to receipt rows")
    return {
        "source_id": source_id or source_dir.name,
        "receipt_file": receipt_name,
        "release_vintage": vintage,
        "freeze_date": freeze_date,
        "actions": actions,
        "summary": totals(actions),
        "action_domain_plus_quarantine_reconciles_to_receipt":
            receipt_total is None or int(receipt_total) == action_total + quarantined,
    }


def local_release_for_year(data_root: Path, year: int) -> dict:
    hmda_root = data_root / "data/private/hmda"
    if year == 2018:
        source_dir = hmda_root / "hmda-browser-three-year-2018"
        acquisition_path = source_dir / "acquisition-receipt.json"
        audit_path = source_dir / "audit-receipt.json"
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        if (acquisition.get("status") != "DOWNLOADED_PENDING_ROW_AUDIT"
                or acquisition.get("freeze_date") != "2021-12-31"
                or audit.get("status") != "PASS_WITH_QUARANTINED_SOURCE_ROWS"
                or audit.get("freeze_date") != "2021-12-31"
                or audit.get("sha256") != acquisition.get("sha256")
                or audit.get("profile", {}).get("official_aggregation_reconciliation")
                != "PASS_FOR_ACTION_CODES_1_TO_8"):
            raise AuditError("2018 Three-Year acquisition/audit receipt contract failed")
        quarantine = audit.get("profile", {}).get("quarantined_out_of_domain_rows", {}).get("rows")
        return _receipt_source(source_dir, "audit-receipt.json", "Three-Year", "2021-12-31",
                               audit["profile"], "hmda-browser-three-year-2018") | {
            "quarantined_out_of_domain_rows_action_minus_1": quarantine,
            "source_receipt_sha256": digest_file(audit_path),
            "local_acquisition_receipt_sha256": digest_file(acquisition_path),
        }

    if 2019 <= year <= 2024:
        candidates = []
        for folder in hmda_root.glob(f"hmda-national-one-year-{year}-*"):
            receipt_path = folder / "acquisition-complete.json"
            if not receipt_path.is_file():
                continue
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("requested_activity_year") == year:
                candidates.append((folder, receipt))
        if len(candidates) != 1:
            raise AuditError(f"Expected one local {year} One-Year receipt; found {len(candidates)}")
        folder, receipt = candidates[0]
        expected_status = f"VERIFIED_HMDA_{year}_ONE_YEAR_NATIONAL"
        if (receipt.get("status") != expected_status or receipt.get("visibility") != "private"
                or receipt.get("public_release_approved") is not False
                or receipt.get("loan_performance_labels") is not False
                or receipt.get("forecast_or_imputation") is not False):
            raise AuditError(f"{year} One-Year private source receipt contract failed")
        profile = receipt.get("profile", {})
        local = _receipt_source(folder, "acquisition-complete.json", "One-Year",
                                str(receipt.get("freeze_date")), profile, receipt.get("source_id"))
        local["source_receipt_sha256"] = digest_file(receipt_path)
        return local

    if year == 2025:
        candidates = []
        for folder in hmda_root.glob("hmda-national-snapshot-2025-*"):
            receipt_path = folder / "acquisition-complete.json"
            if receipt_path.is_file():
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if receipt.get("status") == "VERIFIED_HMDA_NATIONAL_SNAPSHOT_2025":
                    candidates.append((folder, receipt))
        if len(candidates) != 1:
            raise AuditError(f"Expected one verified 2025 Snapshot receipt; found {len(candidates)}")
        folder, receipt = candidates[0]
        if (receipt.get("snapshot_freeze_date") != "2026-06-02"
                or receipt.get("visibility") != "private"
                or receipt.get("public_release_approved") is not False
                or receipt.get("loan_performance_labels") is not False
                or receipt.get("forecast_or_imputation") is not False):
            raise AuditError("2025 Snapshot private source receipt contract failed")
        profile = receipt["datasets"]["lar"]["profile"]
        local = _receipt_source(folder, "acquisition-complete.json", "Snapshot", "2026-06-02",
                                profile, receipt["source_id"])
        local["source_receipt_sha256"] = digest_file(folder / "acquisition-complete.json")
        return local

    raise AuditError(f"Unsupported HMDA activity year: {year}")


def fetch_browser_actions(year: int, timeout: int = 90) -> tuple[dict, bytes, dict]:
    url = f"{API_BASE}?years={year}&actions_taken={ACTION_FILTER}"
    request = urllib.request.Request(url, headers={
        "User-Agent": "CreditAtlas public aggregate release audit/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise AuditError(f"HMDA API returned HTTP {response.status} for {year}")
        body = response.read()
        headers = {
            name: response.headers.get(name)
            for name in ("Date", "ETag", "Last-Modified", "Cache-Control")
            if response.headers.get(name) is not None
        }
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AuditError(f"HMDA API response for {year} was not JSON") from exc
    if payload.get("parameters", {}).get("actions_taken") != ACTION_FILTER:
        raise AuditError(f"HMDA API echoed unexpected filters for {year}")
    actions: dict[str, int] = {}
    for row in payload.get("aggregations", []):
        code = str(row.get("actions_taken", ""))
        if code not in ACTIONS or code in actions:
            raise AuditError(f"HMDA API returned invalid/duplicate action code for {year}: {code}")
        count = row.get("count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise AuditError(f"HMDA API returned invalid action count for {year}/{code}")
        actions[code] = count
    if set(actions) != set(ACTIONS):
        raise AuditError(f"HMDA API did not return exactly actions 1–8 for {year}")
    return {"url": url, "year": year, "served_from": payload.get("servedFrom"),
            "actions": actions, "summary": totals(actions)}, body, headers


def compare(browser: dict, local: dict, browser_release: str) -> dict:
    same_vintage = local["release_vintage"] == browser_release
    action_deltas = {code: browser["actions"][code] - local["actions"][code] for code in ACTIONS}
    browser_summary, local_summary = browser["summary"], local["summary"]
    exact = action_deltas == {code: 0 for code in ACTIONS}
    if same_vintage and not exact:
        raise AuditError(
            f"Matching {browser['year']} release does not match local receipt: {action_deltas}"
        )
    return {
        "local_release_vintage": local["release_vintage"],
        "local_freeze_date": local["freeze_date"],
        "local_source_id": local["source_id"],
        "local_source_receipt_sha256": local.get("source_receipt_sha256"),
        "same_vintage_as_browser": same_vintage,
        "comparison_status": "PASS_EXACT_SAME_VINTAGE" if exact and same_vintage else "CROSS_VINTAGE_DIAGNOSTIC",
        "local_actions_1_to_8": local["actions"],
        "local_summary": local_summary,
        "quarantined_out_of_domain_rows_action_minus_1": local.get(
            "quarantined_out_of_domain_rows_action_minus_1", 0
        ),
        "browser_minus_local_archive": {
            "actions_1_to_8": action_deltas,
            "action_1_to_8_records": browser_summary["action_1_to_8_records"]
                - local_summary["action_1_to_8_records"],
            "decision_denominator_actions_1_2_3": browser_summary["decision_denominator_actions_1_2_3"]
                - local_summary["decision_denominator_actions_1_2_3"],
            "denied_numerator_action_3": browser_summary["denied_numerator_action_3"]
                - local_summary["denied_numerator_action_3"],
            "descriptive_denied_share_percentage_points": pp_delta(
                browser_summary["descriptive_denied_share"], local_summary["descriptive_denied_share"]
            ),
        },
        "matching_action_counts": exact,
    }


def audit(data_root: Path, output_path: Path) -> dict:
    data_root = data_root.resolve()
    if data_root.drive.upper() != "D:":
        raise AuditError("HMDA source receipts and API response captures must remain on D:")
    run_id = "hmda-browser-selected-release-audit-" + uuid.uuid4().hex[:12]
    private_dir = data_root / "artifacts/private" / run_id
    private_dir.mkdir(parents=True, exist_ok=False)
    years = []
    private_inputs = []
    for year in FREEZES:
        release, freeze_date = FREEZES[year]
        browser, body, headers = fetch_browser_actions(year)
        response_path = private_dir / f"hmda-browser-actions-{year}.json"
        response_path.write_bytes(body)
        local = local_release_for_year(data_root, year)
        if local["release_vintage"] == release and local["freeze_date"] != freeze_date:
            raise AuditError(f"{year} matching local vintage has unexpected freeze date")
        comparison = compare(browser, local, release)
        years.append({
            "activity_year": year,
            "browser_selected_release": release,
            "browser_freeze_date": freeze_date,
            "official_api_url": browser["url"],
            "api_served_from": browser["served_from"],
            "api_response_sha256": digest_bytes(body),
            "browser_actions_1_to_8": browser["actions"],
            "browser_summary": browser["summary"],
            "local_archive_comparison": comparison,
        })
        private_inputs.append({
            "activity_year": year,
            "api_response_file": response_path.name,
            "api_response_sha256": digest_bytes(body),
            "api_response_bytes": len(body),
            "http_response_headers": headers,
            "local_source_id": local["source_id"],
            "local_receipt_file": local["receipt_file"],
            "local_source_receipt_sha256": local.get("source_receipt_sha256"),
            "local_acquisition_receipt_sha256": local.get("local_acquisition_receipt_sha256"),
            "local_release_vintage": local["release_vintage"],
            "local_freeze_date": local["freeze_date"],
        })

    public = {
        "evidence_type": "hmda_browser_selected_release_action_counts_2018_2025",
        "status": "PASS",
        "captured_at_utc": timestamp(),
        "activity_years": "2018–2025",
        "source": "FFIEC / CFPB HMDA Data Browser nationwide aggregations API",
        "source_documentation": API_DOCS,
        "source_release_mapping": FAQ,
        "method": {
            "query": "One official nationwide API request per activity year; actions_taken=1,2,3,4,5,6,7,8",
            "row_measure": "Sum of official API counts for action codes 1–8; 2018 action=-1 rows are outside this published action domain and remain quarantined locally.",
            "denominator": "count(action_taken in 1,2,3)",
            "numerator": "count(action_taken == 3)",
            "rate": "descriptive_denied_share = numerator / denominator; application disposition only, not repayment/default PD",
            "local_comparison": "Compare each Browser-selected release to the receipt-bound local archive for the same activity year. For 2019–2022, the local archive is One-Year while the current Browser selects Three-Year, so deltas are cross-vintage aggregate diagnostics, not matched-row changes.",
        },
        "years": years,
        "interpretation_limits": [
            "Action-count aggregates do not identify which application rows changed between releases; no row-level matching was performed.",
            "Late submissions and resubmissions can change counts or action composition. Aggregate differences are not borrower transitions or repayment performance.",
            "The selected Browser static release changes by year and reporting coverage can change; raw year-to-year rates are descriptive and are not a controlled causal trend.",
            "The official API query filters to actions 1–8. The 1,961 action=-1 rows in the local 2018 CSV remain quarantined and are not silently counted as a Browser action.",
            "This audit adds no forecast, imputation, PD, default, or model output.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "run_id": run_id,
        "audited_at_utc": public["captured_at_utc"],
        "source_documentation": API_DOCS,
        "release_mapping_source": FAQ,
        "private_api_responses": private_inputs,
        "public_output": str(output_path.resolve()),
        "public_output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "visibility": "private_receipt_public_aggregate_output",
        "loan_level_rows_read_or_emitted": False,
        "forecasts_or_imputations": False,
    }
    (private_dir / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    return {"status": "PASS", "run_id": run_id, "public_output": str(output_path),
            "private_receipt": str(private_dir / "receipt.json"),
            "years": len(years),
            "same_vintage_exact_matches": sum(
                row["local_archive_comparison"]["comparison_status"] == "PASS_EXACT_SAME_VINTAGE"
                for row in years),
            "cross_vintage_diagnostics": sum(
                row["local_archive_comparison"]["comparison_status"] == "CROSS_VINTAGE_DIAGNOSTIC"
                for row in years)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.data_root, args.output), ensure_ascii=False, indent=2))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, AuditError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
