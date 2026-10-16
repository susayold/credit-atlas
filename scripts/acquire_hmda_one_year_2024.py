"""Download and audit the public 2024 HMDA One-Year national CSV via Edge."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import duckdb
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.workspace import contained, sha256, timestamp, write_new

YEAR = 2024
PUBLISHER = "FFIEC / Consumer Financial Protection Bureau"
DATA_PAGE = "https://ffiec.cfpb.gov/data-publication/2024"
DATA_BROWSER_PAGE = "https://ffiec.cfpb.gov/data-browser/data/2024?category=nationwide"
API_ROOT = "https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide"
ALL_ACTIONS = tuple(str(code) for code in range(1, 9))
EXPECTED_ACTIONS = {
    "1": 6_197_085, "2": 361_232, "3": 2_103_462, "4": 1_538_273,
    "5": 581_940, "6": 1_276_504, "7": 47_312, "8": 153_391,
}
EXPECTED_RECORDS = sum(EXPECTED_ACTIONS.values())
REQUIRED_FIELDS = {"activity_year", "lei", "state_code", "county_code", "action_taken",
                   "loan_type", "loan_purpose", "lien_status", "occupancy_type",
                   "derived_dwelling_category", "debt_to_income_ratio", "loan_amount"}


def profile_csv(path: Path, aggregate_report: dict) -> dict:
    connection = duckdb.connect()
    connection.execute("SET memory_limit='3GB'")
    connection.execute("SET threads=4")
    temp_dir = path.parent / "duckdb-temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    connection.execute("SET temp_directory=?", [str(temp_dir)])
    relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in connection.execute(f"DESCRIBE SELECT * FROM {relation}", [str(path)]).fetchall()]
        if (len(columns) != 99 or len(set(columns)) != len(columns)
                or not REQUIRED_FIELDS.issubset(columns)):
            raise ValueError(f"2024 HMDA LAR schema failed: {len(columns)} columns")
        summary_row = connection.execute(f"""
            SELECT count(*) AS records,
                   count(DISTINCT lei) AS distinct_leis,
                   count(*) FILTER (WHERE activity_year <> '2024' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS invalid_state_rows,
                   count(*) FILTER (WHERE loan_type NOT IN ('1','2','3','4') OR loan_type IS NULL) AS invalid_loan_type_rows,
                   count(*) FILTER (WHERE lei IS NULL OR length(lei) <> 20) AS invalid_lei_rows,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS invalid_amount_rows
            FROM {relation}
        """, [str(path)]).fetchone()
        summary = dict(zip(("records", "distinct_leis", "wrong_year_rows", "invalid_action_rows",
            "invalid_state_rows", "invalid_loan_type_rows", "invalid_lei_rows", "invalid_amount_rows"), summary_row))
        actions = connection.execute(f"SELECT action_taken, count(*) FROM {relation} GROUP BY 1 ORDER BY 1", [str(path)]).fetchall()
        action_counts = {str(code): int(count) for code, count in actions}
        expected_api = {str(row["actions_taken"]): int(row["count"]) for row in aggregate_report["aggregations"]}
        if (summary["records"] != EXPECTED_RECORDS or action_counts != EXPECTED_ACTIONS
                or expected_api != EXPECTED_ACTIONS or sum(action_counts.values()) != summary["records"]):
            raise ValueError("2024 LAR action counts do not reconcile to official API preflight")
        if any(summary[name] != 0 for name in ("wrong_year_rows", "invalid_action_rows", "invalid_state_rows",
                                                "invalid_loan_type_rows", "invalid_lei_rows", "invalid_amount_rows")):
            raise ValueError("2024 LAR quality profile has invalid rows")
        state_count = connection.execute(f"SELECT count(DISTINCT state_code) FROM {relation}", [str(path)]).fetchone()[0]
        return {"columns": columns, "summary": summary,
                "actions": [{"value": code, "records": action_counts[code]} for code in sorted(action_counts)],
                "state_code_count": state_count,
                "decision_denominator": sum(action_counts[code] for code in ("1", "2", "3")),
                "denied_numerator": action_counts["3"],
                "descriptive_denied_share": action_counts["3"] / sum(action_counts[code] for code in ("1", "2", "3")),
                "quality": {key: summary[key] for key in ("wrong_year_rows", "invalid_action_rows", "invalid_state_rows",
                    "invalid_loan_type_rows", "invalid_lei_rows", "invalid_amount_rows")},
                "denominator_contract": "action_taken 1+2+3; descriptive application denied share only, not PD/default"}
    finally:
        connection.close()


def acquire(root: Path, source_id: str | None = None) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("HMDA data and acquisition receipts must remain on D:")
    if shutil.disk_usage(root).free < 16 * 1024**3:
        raise ValueError("Need at least 16 GiB free on D: before national CSV download")
    if source_id is None:
        source_id = "hmda-national-one-year-2024-" + uuid.uuid4().hex[:12]
        folder = contained(root, "data/private/hmda/" + source_id)
        folder.mkdir(parents=True)
    else:
        if not re.fullmatch(r"hmda-national-one-year-2024-[0-9a-f]{12}", source_id):
            raise ValueError("Invalid 2024 HMDA source id")
        folder = contained(root, "data/private/hmda/" + source_id)
        if not folder.is_dir() or (folder / "acquisition-complete.json").exists():
            raise ValueError("Resume requires an incomplete private acquisition folder")
    download_dir = contained(folder, "browser-downloads")
    download_dir.mkdir(exist_ok=True)
    csv_path = contained(folder, "2024_one_year_national_lar.csv")
    aggregate_path = contained(folder, "official-api-aggregation.json")
    aggregate_url = API_ROOT + "/aggregations?" + urlencode({"years": str(YEAR), "actions_taken": ",".join(ALL_ACTIONS)})
    csv_url = API_ROOT + "/csv?" + urlencode({"years": str(YEAR), "actions_taken": ",".join(ALL_ACTIONS)})
    if not (folder / "acquisition-start.json").exists():
        write_new(folder / "acquisition-start.json", {"source_id": source_id,
            "status": "HMDA_2024_ONE_YEAR_ACQUISITION_STARTED", "publisher": PUBLISHER,
            "data_page": DATA_PAGE, "data_browser_page": DATA_BROWSER_PAGE,
            "api_aggregation_url": aggregate_url, "api_csv_url": csv_url,
            "dataset_type": "one-year national; frozen after the 12-month resubmission window",
            "freeze_date": "2026-06-02", "requested_activity_year": YEAR,
            "requested_action_codes": list(ALL_ACTIONS), "started_at": timestamp(),
            "visibility": "private", "public_release_approved": False,
            "loan_performance_labels": False, "forecast_or_imputation": False})
    response_log = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True,
                downloads_path=str(download_dir))
            page = browser.new_page(accept_downloads=True)
            page.on("response", lambda response: response_log.append({"url": response.url,
                "status": response.status, "content_type": response.headers.get("content-type"),
                "content_disposition": response.headers.get("content-disposition"),
                "location": response.headers.get("location")})
                if "/v2/data-browser-api/view/nationwide/" in response.url else None)
            aggregation_response = page.goto(aggregate_url, wait_until="domcontentloaded", timeout=120_000)
            if not aggregation_response or aggregation_response.status != 200:
                raise ValueError("Official HMDA 2024 aggregation API did not return HTTP 200")
            aggregate = json.loads(page.locator("body").inner_text())
            action_counts = {str(row["actions_taken"]): int(row["count"]) for row in aggregate.get("aggregations", [])}
            if (action_counts != EXPECTED_ACTIONS or aggregate.get("parameters", {}).get("actions_taken") != ",".join(ALL_ACTIONS)):
                raise ValueError("Official HMDA 2024 aggregation API differs from audited source counts")
            if aggregate_path.exists():
                saved_aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
                saved_counts = {str(row["actions_taken"]): int(row["count"])
                    for row in saved_aggregate.get("aggregations", [])}
                if (saved_counts != action_counts
                        or saved_aggregate.get("parameters", {}).get("actions_taken") != ",".join(ALL_ACTIONS)):
                    raise ValueError("Previously saved HMDA API aggregate changed during resume")
            else:
                write_new(aggregate_path, aggregate)

            redirect = page.request.get(csv_url, max_redirects=0, timeout=120_000)
            redirect_location = redirect.headers.get("location", "")
            parsed = urlsplit(redirect_location)
            if (redirect.status != 301 or parsed.scheme != "https" or parsed.netloc != "files.ffiec.cfpb.gov"
                    or not parsed.path.startswith("/data-browser/datasets/2024/filtered-queries/one-year/")
                    or not parsed.path.endswith(".csv")):
                raise ValueError("HMDA API did not redirect to the expected official 2024 One-Year CSV host")
            response_log.append({"url": csv_url, "status": redirect.status,
                "content_type": redirect.headers.get("content-type"),
                "content_disposition": redirect.headers.get("content-disposition"),
                "location": redirect_location, "redirect_verified": True})
            suggested_filename = redirect.headers.get("content-disposition", "")
            suggested_filename = suggested_filename.split('filename="')[-1].rstrip('"')
            if csv_path.exists():
                if csv_path.stat().st_size < 1_000_000:
                    raise ValueError("Existing 2024 CSV is too small to resume as a complete national payload")
            else:
                with page.expect_download(timeout=3_600_000) as download_info:
                    try:
                        page.goto(csv_url, wait_until="domcontentloaded", timeout=3_600_000)
                    except Exception as error:
                        if "Download is starting" not in str(error):
                            raise
                download = download_info.value
                if download.failure() is not None or not download.suggested_filename.casefold().endswith(".csv"):
                    raise ValueError("Official HMDA API download failed or did not return CSV")
                suggested_filename = download.suggested_filename
                download.save_as(csv_path)
                download.delete()
            browser.close()
        profile = profile_csv(csv_path, aggregate)
        payload = {"source_id": source_id, "status": "VERIFIED_HMDA_2024_ONE_YEAR_NATIONAL",
            "publisher": PUBLISHER, "data_page": DATA_PAGE, "data_browser_page": DATA_BROWSER_PAGE,
            "api_aggregation_url": aggregate_url, "api_csv_url": csv_url,
            "dataset_type": "one-year national; static 12-month post-deadline resubmission vintage",
            "freeze_date": "2026-06-02", "requested_activity_year": YEAR,
            "requested_action_codes": list(ALL_ACTIONS), "response_log": response_log,
            "csv": {"file": csv_path.name, "bytes": csv_path.stat().st_size, "sha256": sha256(csv_path),
                    "retrieved_at": timestamp(), "suggested_filename": suggested_filename},
            "official_api_aggregation_sha256": sha256(aggregate_path),
            "profile": profile, "visibility": "private", "public_release_approved": False,
            "loan_performance_labels": False, "forecast_or_imputation": False,
            "limitations": ["HMDA records applications, underwriting actions, and purchased loans; it does not provide monthly repayment/default performance.",
                "2024 One-Year is a distinct official release vintage from the 2025 Snapshot; do not describe the two as an identical frozen-release design.",
                "The descriptive denied share is actions 3 divided by actions 1-3; it is not PD/default.",
                "Public records are privacy-modified and do not provide a reliable borrower/loan key for performance-source joins."]}
        write_new(folder / "acquisition-complete.json", payload)
        for temporary in download_dir.iterdir():
            if temporary.is_file() and temporary.stat().st_size == csv_path.stat().st_size:
                if sha256(temporary) != payload["csv"]["sha256"]:
                    raise ValueError("Temporary Edge download differs from the verified source CSV")
                temporary.unlink()
        return {"source_id": source_id, "status": payload["status"], "records": profile["summary"]["records"],
                "distinct_leis": profile["summary"]["distinct_leis"], "csv_bytes": payload["csv"]["bytes"],
                "csv_sha256": payload["csv"]["sha256"], "descriptive_denied_share": profile["descriptive_denied_share"],
                "folder": str(folder)}
    except Exception as error:
        if not (folder / "acquisition-failed.json").exists():
            write_new(folder / "acquisition-failed.json", {"source_id": source_id,
                "status": "HMDA_2024_ONE_YEAR_ACQUISITION_FAILED", "exception_type": type(error).__name__,
                "message": str(error)[:500], "response_log": response_log,
                "completed_at": timestamp(), "visibility": "private"})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    parser.add_argument("--source-id", help="Resume auditing an existing acquisition folder without overwriting it")
    args = parser.parse_args()
    try:
        print(json.dumps(acquire(args.root, args.source_id), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
