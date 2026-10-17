"""Compare selected 2025 Browser API dimensions to the receipt-bound Snapshot LAR.

The public output contains aggregate KPI parity summaries only. Exact per-action
counts, requests, responses, paths and source hashes are written to a private
receipt on D:.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

import duckdb
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.hmda_national_views import verify_source  # noqa: E402
from credit_atlas.workspace import sha256  # noqa: E402

API = "https://ffiec.cfpb.gov/v2/data-browser-api/view/aggregations"
NATIONWIDE_API = "https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/aggregations"
SOURCE_ID_PATTERN = re.compile(r"hmda-national-snapshot-2025-[0-9a-f]{12}\Z")
ACTION_CODES = tuple(str(code) for code in range(1, 9))
ACTION_FILTER = ",".join(ACTION_CODES)
PARAMETER_ECHO_NAMES = {"states": "state", "counties": "county", "leis": "lei",
                        "actions_taken": "actions_taken", "loan_types": "loan_types"}


def read_api_profile(session: requests.Session, scope_id: str, params: dict[str, str], endpoint: str = API) -> dict:
    query = {"years": "2025", **params, "actions_taken": ACTION_FILTER}
    response = session.get(endpoint, params=query, timeout=(10, 120))
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("aggregations"), list):
        raise ValueError(f"Unexpected official API response for {scope_id}")
    counts: dict[str, int] = {}
    for row in payload["aggregations"]:
        if not isinstance(row, dict):
            raise ValueError(f"Non-object aggregation for {scope_id}")
        action = str(row.get("actions_taken", ""))
        count = row.get("count")
        if action not in ACTION_CODES or action in counts or isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"Invalid/duplicate action count for {scope_id}")
        counts[action] = count
    if not counts or set(counts) - set(ACTION_CODES):
        raise ValueError(f"No recognized action profile for {scope_id}")
    profile = {code: counts.get(code, 0) for code in ACTION_CODES}
    echoed = payload.get("parameters", {})
    echo_matches = all(echoed.get(PARAMETER_ECHO_NAMES.get(key, key)) == value
                       for key, value in query.items() if key != "years")
    if not echo_matches:
        raise ValueError(f"Official API did not echo requested filters for {scope_id}")
    return {
        "scope_id": scope_id,
        "endpoint": endpoint,
        "query": query,
        "request_url": response.url,
        "http_status": response.status_code,
        "served_from": payload.get("servedFrom"),
        "response_sha256": hashlib.sha256(response.content).hexdigest(),
        "parameters": payload.get("parameters", {}),
        "parameter_echo_matches": echo_matches,
        "action_counts": profile,
    }


def local_profiles(csv_path: Path) -> tuple[str, dict[str, dict[str, int]]]:
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    connection.execute("SET threads=4")
    connection.execute("SET temp_directory=?", [str(csv_path.parent.parent / "duckdb-hmda-dimension-parity-temp")])
    relation = "read_csv(?, delim=',', header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = {row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}", [str(csv_path)]).fetchall()}
        required = {"activity_year", "state_code", "county_code", "lei", "loan_type", "action_taken"}
        if not required.issubset(columns):
            raise ValueError("Snapshot LAR schema is missing required parity fields")

        top_lei_rows = connection.execute(
            f"""SELECT lei, count(*) AS n FROM {relation}
                WHERE activity_year='2025' AND action_taken IN ('1','2','3','4','5','6','7','8')
                    AND lei <> '' AND lei IS NOT NULL
                GROUP BY lei ORDER BY n DESC, lei ASC LIMIT 1""",
            [str(csv_path)],
        ).fetchone()
        if not top_lei_rows:
            raise ValueError("No eligible reporting LEI in the local Snapshot")
        lei = str(top_lei_rows[0])

        rows = connection.execute(
            f"""WITH lar AS (
                    SELECT state_code, county_code, lei, loan_type, action_taken
                    FROM {relation}
                    WHERE activity_year='2025' AND action_taken IN ('1','2','3','4','5','6','7','8')
                ), scoped AS (
                    SELECT 'state_ca' AS scope_id, action_taken FROM lar WHERE state_code='CA'
                    UNION ALL
                    SELECT 'county_los_angeles', action_taken FROM lar WHERE county_code='06037'
                    UNION ALL
                    SELECT 'state_ca_conventional', action_taken FROM lar WHERE state_code='CA' AND loan_type='1'
                    UNION ALL
                    SELECT 'largest_reporter_lei', action_taken FROM lar WHERE lei=?
                    UNION ALL
                    SELECT 'nationwide_conventional', action_taken FROM lar WHERE loan_type='1'
                )
                SELECT scope_id, action_taken, count(*) AS n
                FROM scoped GROUP BY scope_id, action_taken ORDER BY scope_id, action_taken""",
            [str(csv_path), lei],
        ).fetchall()
        profiles = {name: {code: 0 for code in ACTION_CODES} for name in
                    ("state_ca", "county_los_angeles", "state_ca_conventional", "largest_reporter_lei", "nationwide_conventional")}
        for scope_id, action, count in rows:
            if scope_id not in profiles or str(action) not in ACTION_CODES:
                raise ValueError("Local action profile contains an unexpected scope or action")
            profiles[scope_id][str(action)] = int(count)
        return lei, profiles
    finally:
        connection.close()


def summary(counts: dict[str, int]) -> dict:
    records = sum(counts.values())
    denominator = sum(counts[code] for code in ("1", "2", "3"))
    denied = counts["3"]
    return {
        "action_1_to_8_records": records,
        "decision_denominator_1_2_3": denominator,
        "denied_numerator_action_3": denied,
        "descriptive_denied_share": str(Decimal(denied) / denominator) if denominator else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True, type=Path,
                        help="Private CreditAtlas workspace with data/private/hmda on D:")
    parser.add_argument("--source-id", default="hmda-national-snapshot-2025-9a5e89600e3c")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/data/hmda-browser-dimension-api-parity-2026-10-17.json")
    parser.add_argument("--private-receipt-dir", type=Path,
                        default=Path(r"D:\data\Codex\credit-atlas\artifacts\private"))
    args = parser.parse_args()
    root = args.workspace_root.resolve()
    if root.drive.upper() != "D:" or not root.is_dir():
        raise ValueError("The authorized private workspace must be an existing D: directory")
    if not SOURCE_ID_PATTERN.fullmatch(args.source_id):
        raise ValueError("Expected a receipt-bound 2025 Snapshot source ID")

    source_folder, source_receipt, source_receipt_path, _ = verify_source(root, args.source_id, hash_payloads=True)
    csv_path = source_folder / "extracted" / "2025_public_lar_csv.csv"
    if not csv_path.is_file() or csv_path.drive.upper() != "D:":
        raise ValueError("The verified Snapshot LAR CSV must remain on D:")
    source_digest = sha256(source_receipt_path)
    lar_digest = sha256(csv_path)
    if source_receipt.get("snapshot_freeze_date") != "2026-06-02":
        raise ValueError("The source is not the expected 2025 Snapshot freeze")

    lei, local = local_profiles(csv_path)
    filter_specs = {
        "state_ca": {"endpoint": API, "params": {"states": "CA"}, "app_dimension": "state_code", "app_bucket": "CA"},
        "county_los_angeles": {"endpoint": API, "params": {"counties": "06037"}, "app_dimension": "county_code", "app_bucket": "06037"},
        "state_ca_conventional": {"endpoint": API, "params": {"states": "CA", "loan_types": "1"}},
        "largest_reporter_lei": {"endpoint": API, "params": {"leis": lei}, "app_dimension": "lei", "app_bucket": lei},
        "nationwide_conventional": {"endpoint": NATIONWIDE_API, "params": {"loan_types": "1"}, "app_dimension": "loan_type", "app_bucket": "1"},
    }
    session = requests.Session()
    session.headers.update({"User-Agent": "CreditAtlas aggregate release parity research"})
    api = {scope: read_api_profile(session, scope, spec["params"], spec["endpoint"])
           for scope, spec in filter_specs.items()}

    # Exercise the same receipt-verified service report used by the local 2025
    # national UI/API; its one-dimension breakdowns are compared to matching
    # publisher-filtered API scopes. The CA × product intersection has no
    # equivalent in this marginal-only view and stays explicitly unclaimed.
    from credit_atlas.hmda_national_views import HmdaNationalViews  # noqa: E402
    from credit_atlas.workspace import read_json  # noqa: E402
    service = HmdaNationalViews(root)
    view_receipts = sorted((root / "artifacts/private").glob("hmda-national-view-*/view-complete.json"))
    view_id = None
    for receipt_path in view_receipts:
        try:
            receipt = read_json(receipt_path)
            if receipt.get("source_id") == args.source_id and receipt.get("status") == "VERIFIED_HMDA_NATIONAL_AGGREGATE_VIEW":
                view_id = receipt_path.parent.name
                break
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if not view_id:
        raise ValueError("No verified local HMDA National Snapshot aggregate view was found")

    app_profiles = {}
    for scope, spec in filter_specs.items():
        dimension = spec.get("app_dimension")
        if not dimension:
            app_profiles[scope] = {"dimension": None, "bucket": None, "summary": None, "matches_official_api": None}
            continue
        report = service.report(view_id, {"view_id": view_id, "dimension": dimension})
        bucket = spec["app_bucket"]
        row = next((item for item in report["breakdown"] if item.get("bucket") == bucket), None)
        if row is None:
            raise ValueError(f"Expected local app aggregate bucket was absent for {scope}")
        app_summary = {
            "action_1_to_8_records": int(row["records"]),
            "decision_denominator_1_2_3": int(row["decision_denominator"]),
            "denied_numerator_action_3": int(row["denied_numerator"]),
            "descriptive_denied_share": row["descriptive_denial_rate"],
        }
        app_profiles[scope] = {"dimension": dimension, "bucket": bucket, "summary": app_summary,
                               "matches_official_api": False}

    results = []
    for scope, spec in filter_specs.items():
        local_counts = local[scope]
        api_counts = api[scope]["action_counts"]
        local_summary = summary(local_counts)
        api_summary = summary(api_counts)
        differences = {code: api_counts[code] - local_counts[code] for code in ACTION_CODES}
        app_profile = app_profiles[scope]
        if app_profile["summary"] is not None:
            app_summary = app_profile["summary"]
            app_profile["matches_official_api"] = (
                app_summary["action_1_to_8_records"] == api_summary["action_1_to_8_records"]
                and app_summary["decision_denominator_1_2_3"] == api_summary["decision_denominator_1_2_3"]
                and app_summary["denied_numerator_action_3"] == api_summary["denied_numerator_action_3"]
                and abs(Decimal(app_summary["descriptive_denied_share"])
                        - Decimal(api_summary["descriptive_denied_share"])) <= Decimal("0.000000000001")
            )
        results.append({
            "scope": scope,
            "query_dimension": spec.get("app_dimension"),
            "official_api_http_status": api[scope]["http_status"],
            "official_api_parameter_echo_matches": api[scope]["parameter_echo_matches"],
            "api_served_from": api[scope]["served_from"],
            "all_action_counts_match": all(delta == 0 for delta in differences.values()),
            "max_absolute_action_count_delta": max(abs(delta) for delta in differences.values()),
            "api_summary": api_summary,
            "local_snapshot_summary": local_summary,
            "app_marginal_bucket_summary": app_profile["summary"],
            "app_marginal_summary_match": app_profile["matches_official_api"],
            "descriptive_denied_share_delta": str(Decimal(api_summary["descriptive_denied_share"] or "0")
                                                       - Decimal(local_summary["descriptive_denied_share"] or "0")),
        })
    if any(row["official_api_http_status"] != 200 or not row["official_api_parameter_echo_matches"]
           or not row["all_action_counts_match"]
           or row["api_summary"] != row["local_snapshot_summary"]
           or (row["app_marginal_bucket_summary"] is not None and not row["app_marginal_summary_match"])
           or Decimal(row["descriptive_denied_share_delta"]) != 0 for row in results):
        status = "FAIL"
    else:
        status = "PASS"

    run_id = "hmda-dimension-parity-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    private_dir = args.private_receipt_dir.resolve() / run_id
    if private_dir.drive.upper() != "D:":
        raise ValueError("Private API captures and source hashes may only be written to D:")
    private_dir.mkdir(parents=True, exist_ok=False)
    private_receipt = {
        "run_id": run_id,
        "status": status,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_id": args.source_id,
        "source_receipt_sha256": source_digest,
        "lar_csv_sha256": lar_digest,
        "snapshot_freeze_date": source_receipt["snapshot_freeze_date"],
        "lei_scope_selector": "Largest source reporting LEI by action 1–8 count; ties sorted ascending by LEI",
        "selected_lei_private": lei,
        "verified_app_view_id_private": view_id,
        "app_marginal_profiles": app_profiles,
        "api_responses": api,
        "local_action_profiles": local,
        "comparisons": results,
        "visibility": "private",
        "public_release_approved": False,
    }
    private_receipt_path = private_dir / "receipt.json"
    private_receipt_path.write_text(json.dumps(private_receipt, indent=2) + "\n", encoding="utf-8")
    sanitized = {
        "evidence_type": "hmda_browser_2025_snapshot_dimension_api_parity",
        "run_id": run_id,
        "status": status,
        "captured_at_utc": private_receipt["captured_at_utc"],
        "source": "FFIEC / CFPB HMDA Data Browser aggregations API",
        "source_id": args.source_id,
        "snapshot_freeze_date": source_receipt["snapshot_freeze_date"],
        "source_receipt_sha256": source_digest,
        "lar_csv_sha256": lar_digest,
        "method": {
            "endpoints": [API, NATIONWIDE_API],
            "query": "Five official API requests: four geographic/LEI subsets plus one nationwide loan-type filter; years=2025; actions_taken=1..8",
            "dimensions": ["state", "county", "state × loan type", "one largest-reporting LEI", "nationwide loan type"],
            "validation": "Exact action 1–8 count equality between official API and same-freeze local public LAR; matching app marginal bucket summaries are also checked for state, county, LEI and nationwide loan type.",
            "privacy": "Public JSON excludes raw rows, local paths, exact LEI, request URLs and action-level counts; full evidence remains in the private receipt on D:.",
        },
        "results": results,
        "scope_limitations": [
            "This is a five-scope parity spot check of the 2025 Snapshot, not proof of all years, all geography codes, all institutions, or every filter combination.",
            "The app's one-dimension buckets match the official API for state, county, selected LEI, and nationwide loan-type code 1. The California × loan-type intersection is checked against local raw data but is not an app marginal bucket; no app intersection parity is claimed.",
            "The check exercises the receipt-verified app service used by its UI/API, but does not verify browser rendering or filtered Excel export for every query.",
            "Denied share is an application disposition measure, not repayment/default performance or PD.",
            "No forecast, imputation, row linkage, or borrower-level inference was used.",
        ],
        "private_receipt_sha256": sha256(private_receipt_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "scopes": len(results), "exact_profile_matches": sum(r["all_action_counts_match"] for r in results),
                      "output": str(args.output), "private_receipt_created": True}, ensure_ascii=False))
    if status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
