"""Acquire and audit the official 2023 One-Year national HMDA LAR privately.

Requires Microsoft Edge and Playwright. The public HMDA CSV endpoint redirects
to an attachment; using a browser download avoids buffering the multi-gigabyte
response in Python memory. Row-level data and receipts stay under the private D:
workspace and must never be committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from playwright.sync_api import sync_playwright

YEAR = 2023
DATA_PAGE = "https://ffiec.cfpb.gov/data-publication/2023"
BROWSER_PAGE = "https://ffiec.cfpb.gov/data-browser/data/2023?category=nationwide"
API_DOCS = "https://ffiec.cfpb.gov/documentation/api/data-browser/"
FREEZE_DATE = "2025-05-19"
ACTION_CODES = tuple(str(value) for value in range(1, 9))
EXPECTED_ACTIONS = {
    "1": 5_710_399,
    "2": 310_898,
    "3": 2_037_094,
    "4": 1_468_108,
    "5": 536_137,
    "6": 1_263_097,
    "7": 62_622,
    "8": 175_823,
}
CSV_FILE = "2023_one_year_national_lar.csv"
REQUIRED_FIELDS = {
    "activity_year", "lei", "state_code", "county_code", "action_taken",
    "loan_type", "loan_purpose", "lien_status", "occupancy_type",
    "derived_dwelling_category", "debt_to_income_ratio", "derived_race",
    "derived_ethnicity", "derived_sex", "applicant_credit_score_type",
    "denial_reason-1", "loan_amount",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def get_api_json(page, url: str) -> tuple[dict, dict]:
    response = page.evaluate("""async (url) => {
      const response = await fetch(url, {credentials: 'omit'});
      return {status: response.status, url: response.url,
        contentType: response.headers.get('content-type'), body: await response.json()};
    }""", url)
    if response["status"] != 200 or not isinstance(response.get("body"), dict):
        raise RuntimeError(f"Official aggregation request failed: {response}")
    return response["body"], {key: response[key] for key in ("status", "url", "contentType")}


def download_csv(page, browser, url: str, target: Path, downloads: Path) -> dict:
    downloads.mkdir(parents=True, exist_ok=True)
    # Configure Edge's download directory on D: so the large temporary file does
    # not consume the Windows system drive.
    context = browser.new_context(accept_downloads=True)
    download_page = context.new_page()
    with download_page.expect_download(timeout=3_600_000) as pending:
        try:
            download_page.goto(url, wait_until="domcontentloaded", timeout=3_600_000)
        except Exception as exc:
            # Navigation reports an interrupted document load for attachment
            # responses in some Edge versions; the download event is authoritative.
            if "Download is starting" not in str(exc):
                raise
    download = pending.value
    temporary = downloads / ("hmda-2023-download-" + download.suggested_filename)
    download.save_as(str(temporary))
    if download.failure():
        raise RuntimeError("Browser reported a failed HMDA CSV download")
    temporary.replace(target)
    context.close()
    return {"suggested_filename": download.suggested_filename, "file": target.name}


def audit_csv(csv_path: Path, temp_dir: Path) -> dict:
    temp_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    connection.execute("SET threads=4")
    connection.execute("SET temp_directory=?", [str(temp_dir)])
    relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}", [str(csv_path)]).fetchall()]
        if len(columns) != 99 or len(set(columns)) != 99 or not REQUIRED_FIELDS.issubset(columns):
            raise ValueError(f"Unexpected 2023 One-Year public schema: {len(columns)} columns")
        profile = connection.execute(f"""
            SELECT count(*) AS records,
                   count(DISTINCT lei) FILTER (WHERE lei IS NOT NULL AND lei <> '') AS distinct_leis,
                   count(DISTINCT state_code) AS state_code_count,
                   count(*) FILTER (WHERE activity_year <> '2023' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS invalid_state_rows,
                   count(*) FILTER (WHERE loan_type NOT IN ('1','2','3','4') OR loan_type IS NULL) AS invalid_loan_type_rows,
                   count(*) FILTER (WHERE NOT regexp_matches(lei, '^[A-Z0-9]{{20}}$')) AS invalid_lei_rows,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS invalid_amount_rows
            FROM {relation}
        """, [str(csv_path)]).fetchone()
        summary = dict(zip(("records", "distinct_leis", "state_code_count", "wrong_year_rows",
            "invalid_action_rows", "invalid_state_rows", "invalid_loan_type_rows", "invalid_lei_rows",
            "invalid_amount_rows"), profile))
        actions = dict(connection.execute(f"SELECT action_taken, count(*) FROM {relation} GROUP BY action_taken", [str(csv_path)]).fetchall())
        actions = {str(key): value for key, value in actions.items()}
        if actions != EXPECTED_ACTIONS:
            raise ValueError(f"CSV action counts differ from official API: {actions}")
        if summary["records"] != sum(EXPECTED_ACTIONS.values()):
            raise ValueError(f"Unexpected row total: {summary['records']}")
        if any(summary[key] != 0 for key in ("wrong_year_rows", "invalid_action_rows", "invalid_state_rows",
                "invalid_loan_type_rows", "invalid_lei_rows", "invalid_amount_rows")):
            raise ValueError(f"2023 HMDA row-level quality checks failed: {summary}")
        return {"columns": columns, "summary": summary, "actions": actions}
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="CreditAtlas private workspace on D:")
    parser.add_argument("--finalize-existing-download", action="store_true",
        help="Audit and receipt a completed Edge download already saved in the private staging folder")
    args = parser.parse_args()
    root = args.root.resolve()
    data_dir = root / "data/private/hmda"
    data_dir.mkdir(parents=True, exist_ok=True)
    staging = data_dir / "hmda-national-one-year-2023-pending"
    if staging.exists() and not args.finalize_existing_download:
        raise FileExistsError(f"Refusing to overwrite existing staging directory: {staging}")
    if not staging.exists():
        staging.mkdir()
    csv_path = staging / CSV_FILE
    actions_query = ",".join(ACTION_CODES)
    aggregation_url = (f"https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/aggregations"
        f"?years=2023&actions_taken={actions_query}")
    csv_url = (f"https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv"
        f"?years=2023&actions_taken={actions_query}")
    start = {"status": "ACQUISITION_STARTED", "year": YEAR, "data_page": DATA_PAGE,
        "api_aggregation_url": aggregation_url, "api_csv_url": csv_url,
        "started_at": datetime.now(timezone.utc).isoformat(), "visibility": "private",
        "public_release_approved": False}
    if not args.finalize_existing_download:
        (staging / "acquisition-start.json").write_text(json.dumps(start, indent=2), encoding="utf-8")
        with sync_playwright() as playwright:
            downloads = staging / "browser-downloads"
            downloads.mkdir(parents=True, exist_ok=True)
            browser = playwright.chromium.launch(channel="msedge", headless=True,
                downloads_path=str(downloads))
            page = browser.new_page()
            page.goto(BROWSER_PAGE, wait_until="domcontentloaded", timeout=120_000)
            api_body, api_response = get_api_json(page, aggregation_url)
            api_actions = {str(row.get("actions_taken")): int(row.get("count", 0)) for row in api_body.get("aggregations", [])}
            if api_actions != EXPECTED_ACTIONS:
                browser.close()
                raise ValueError(f"Live FFIEC action counts changed from pinned audit: {api_actions}")
            (staging / "official-api-aggregation.json").write_text(json.dumps(api_body, indent=2), encoding="utf-8")
            download_info = download_csv(page, browser, csv_url, csv_path, downloads)
            browser.close()
    else:
        downloads = staging / "browser-downloads"
        if not csv_path.is_file():
            candidates = list(downloads.glob("hmda-2023-download-year_2023.csv")) + list(downloads.glob("year_2023.csv"))
            if not candidates:
                raise FileNotFoundError("No completed 2023 Edge download exists in the private staging folder")
            candidates[0].replace(csv_path)
        api_body = json.loads((staging / "official-api-aggregation.json").read_text(encoding="utf-8"))
        api_actions = {str(row.get("actions_taken")): int(row.get("count", 0)) for row in api_body.get("aggregations", [])}
        if api_actions != EXPECTED_ACTIONS:
            raise ValueError(f"Stored FFIEC action counts changed from pinned audit: {api_actions}")
        api_response = {"status": 200, "url": aggregation_url, "content_type": "application/json",
            "retrieved_in_browser": True, "finalized_existing_browser_download": True}
        download_info = {"suggested_filename": "year_2023.csv", "file": CSV_FILE}

    audit = audit_csv(csv_path, staging / "duckdb-temp")
    csv_meta = {"file": CSV_FILE, "bytes": csv_path.stat().st_size, "sha256": sha256(csv_path),
        "retrieved_at": datetime.now(timezone.utc).isoformat(), **download_info}
    api_hash = sha256(staging / "official-api-aggregation.json")
    source_id = "hmda-national-one-year-2023-" + csv_meta["sha256"][:12]
    receipt = {"source_id": source_id, "status": "VERIFIED_HMDA_2023_ONE_YEAR_NATIONAL",
        "publisher": "FFIEC / Consumer Financial Protection Bureau", "data_page": DATA_PAGE,
        "data_browser_page": BROWSER_PAGE, "api_docs": API_DOCS, "api_aggregation_url": aggregation_url,
        "api_csv_url": csv_url, "api_aggregation_response": api_response,
        "dataset_type": "one-year national; static 12-month post-deadline resubmission vintage",
        "freeze_date": FREEZE_DATE, "requested_activity_year": YEAR,
        "requested_action_codes": list(ACTION_CODES), "official_api_actions": EXPECTED_ACTIONS,
        "official_api_aggregation_sha256": api_hash, "csv": csv_meta,
        "profile": {**audit, "denominator_contract": "action_taken 1+2+3; descriptive application denied share only, not PD/default"},
        "visibility": "private", "public_release_approved": False,
        "loan_performance_labels": False, "forecast_or_imputation": False,
        "limitations": ["HMDA records applications and underwriting outcomes, not monthly repayment/default performance.",
            "2023 One-Year is a static release frozen 2025-05-19; comparisons to 2024 remain descriptive.",
            "The descriptive denied share is actions 3 divided by actions 1-3; it is not PD/default.",
            "No forecast, imputation, synthetic value, or model target has been created."]}
    (staging / "acquisition-complete.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    final_dir = data_dir / source_id
    if final_dir.exists():
        raise FileExistsError(f"Refusing to overwrite source folder: {final_dir}")
    staging.rename(final_dir)
    print(json.dumps({"source_id": source_id, "status": receipt["status"], "records": audit["summary"]["records"],
        "bytes": csv_meta["bytes"], "sha256": csv_meta["sha256"], "actions": audit["actions"],
        "private_folder": str(final_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
