"""Verify and profile the official 2019 HMDA One-Year national LAR archive.

Raw archive, extracted public CSV, and receipts are private on D:. The One-Year
2019 release is distinct from the current Data Browser's Three-Year vintage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import duckdb

YEAR = 2019
DATA_PAGE = "https://ffiec.cfpb.gov/data-publication/one-year-national-loan-level-dataset/2019"
ZIP_URL = "https://files.ffiec.cfpb.gov/static-data/one-year/2019/2019_public_lar_one_year_csv.zip"
ZIP_FILE = "2019_public_lar_one_year_csv.zip"
CSV_FILE = "2019_public_lar_one_year.csv"
ZIP_BYTES = 985_323_790
CSV_BYTES = 6_837_866_739
ZIP_ETAG = '"8b3accc27ee5339303f7e3e963f6d2de-118"'
FREEZE_DATE = "2022-04-05"
REQUIRED_FIELDS = {
    "activity_year", "lei", "state_code", "county_code", "action_taken",
    "loan_type", "loan_purpose", "lien_status", "occupancy_type",
    "derived_dwelling_category", "debt_to_income_ratio", "derived_race",
    "derived_ethnicity", "derived_sex", "applicant_credit_score_type",
    "denial_reason_1", "loan_amount", "combined_loan_to_value_ratio",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_csv(path: Path, temp_dir: Path) -> dict:
    temp_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET memory_limit='3GB'")
    con.execute("SET threads=4")
    con.execute("SET temp_directory=?", [str(temp_dir)])
    relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {relation}", [str(path)]).fetchall()]
        if len(columns) != 99 or len(set(c.lower() for c in columns)) != 99 or not REQUIRED_FIELDS.issubset(columns):
            raise ValueError(f"Unexpected 2019 One-Year schema ({len(columns)} fields)")
        values = con.execute(f"""
            SELECT count(*) AS records,
                   count(DISTINCT lei) FILTER (WHERE lei IS NOT NULL AND lei <> '') AS distinct_leis,
                   count(DISTINCT state_code) AS state_code_count,
                   count(*) FILTER (WHERE activity_year <> '2019' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS invalid_state_rows,
                   count(*) FILTER (WHERE loan_type NOT IN ('1','2','3','4') OR loan_type IS NULL) AS invalid_loan_type_rows,
                   count(*) FILTER (WHERE lei IS NULL OR NOT regexp_matches(lei, '^[A-Z0-9]{{20}}$')) AS invalid_lei_rows,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS invalid_amount_rows
            FROM {relation}
        """, [str(path)]).fetchone()
        names = ("records", "distinct_leis", "state_code_count", "wrong_year_rows", "invalid_action_rows",
            "invalid_state_rows", "invalid_loan_type_rows", "invalid_lei_rows", "invalid_amount_rows")
        summary = dict(zip(names, values))
        actions = {str(code): count for code, count in con.execute(
            f"SELECT action_taken, count(*) FROM {relation} GROUP BY action_taken", [str(path)]).fetchall()}
        if set(actions) != {str(i) for i in range(1, 9)} or sum(actions.values()) != summary["records"]:
            raise ValueError(f"Unexpected action domain or totals: {actions}")
        quality = ("wrong_year_rows", "invalid_action_rows", "invalid_state_rows", "invalid_loan_type_rows",
            "invalid_lei_rows", "invalid_amount_rows")
        if any(summary[key] != 0 for key in quality):
            raise ValueError(f"2019 HMDA row-quality checks failed: {summary}")
        return {"columns": columns, "summary": summary, "actions": actions}
    finally:
        con.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    parser.add_argument("--finalize-existing-download", action="store_true",
        help="Finalize the exact official ZIP already staged privately")
    args = parser.parse_args()
    root = args.root.resolve()
    if root.drive.upper() != "D:":
        parser.error("Raw HMDA files and receipts must remain on D:")
    data_root = root / "data/private/hmda"
    staging = data_root / "hmda-national-one-year-2019-pending"
    archive, csv_path = staging / ZIP_FILE, staging / CSV_FILE
    if not staging.is_dir() or not archive.is_file() or archive.stat().st_size != ZIP_BYTES:
        parser.error("Official 2019 One-Year archive is missing or differs from pinned HTTP metadata")
    with zipfile.ZipFile(archive) as zf:
        members = zf.infolist()
        if len(members) != 1 or members[0].filename != CSV_FILE or members[0].file_size != CSV_BYTES:
            parser.error("Official ZIP member name/size does not match pinned archive profile")
        if zf.testzip() is not None:
            parser.error("Official HMDA ZIP CRC test failed")
        if not csv_path.exists():
            with zf.open(members[0]) as source, csv_path.open("xb") as target:
                while block := source.read(8 * 1024 * 1024):
                    target.write(block)
    if csv_path.stat().st_size != CSV_BYTES:
        parser.error("Extracted CSV size does not match official ZIP member")
    profile = audit_csv(csv_path, staging / "duckdb-temp")
    source_hash, archive_hash = sha256(csv_path), sha256(archive)
    source_id = "hmda-national-one-year-2019-" + source_hash[:12]
    receipt = {
        "source_id": source_id, "status": "VERIFIED_HMDA_2019_ONE_YEAR_NATIONAL",
        "publisher": "FFIEC / Consumer Financial Protection Bureau", "data_page": DATA_PAGE,
        "official_archive_url": ZIP_URL, "official_archive_member": CSV_FILE,
        "dataset_type": "One-Year National Loan-Level Dataset; static One-Year resubmission vintage; unusually includes more than 12 months of updates per publisher notice",
        "freeze_date": FREEZE_DATE, "package_last_modified": "2025-10-15T05:29:18Z",
        "requested_activity_year": YEAR,
        "publisher_vintage_caveat": "The official 2019 One-Year page says the product contains more than 12 months worth of updates due to timing of creation; comparisons with other annual vintages must retain this limitation.",
        "archive": {"file": ZIP_FILE, "bytes": archive.stat().st_size, "sha256": archive_hash,
            "http_etag": ZIP_ETAG, "http_status": 200},
        "csv": {"file": CSV_FILE, "bytes": csv_path.stat().st_size, "sha256": source_hash},
        "profile": profile,
        "external_reconciliation": {"status": "NOT_AVAILABLE_FOR_SAME_VINTAGE",
            "note": "The official Data Browser routes activity year 2019 to its Three-Year release; those counts are not used to validate this static One-Year file."},
        "denominator_contract": "action_taken 1+2+3; descriptive application denied share only; not PD/default",
        "visibility": "private", "public_release_approved": False,
        "loan_performance_labels": False, "forecast_or_imputation": False,
        "limitations": [
            "HMDA records application and underwriting outcomes, not monthly repayment, delinquency, default, loss, or recovery.",
            "The descriptive denied share is actions 3 divided by actions 1-3; it is not PD/default.",
            "This is the frozen 2019 One-Year release; current HMDA Data Browser queries for 2019 use a Three-Year vintage.",
            "No external aggregate from the current Three-Year API was used to claim reconciliation to this One-Year file.",
            "No forecast, imputation, synthetic value, or model target was created.",
            "Publisher warns that the 2019 One-Year vintage contains more than 12 months of updates because of the timing of product creation; it is not a clean 12-month cutoff vintage.",
        ],
    }
    receipt_path = staging / "acquisition-complete.json"
    if receipt_path.exists() and not args.finalize_existing_download:
        parser.error("Acquisition receipt already exists; inspect staging before re-finalizing")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    final_dir = data_root / source_id
    if final_dir.exists():
        parser.error(f"Refusing to overwrite existing source folder: {final_dir}")
    staging.rename(final_dir)
    print(json.dumps({"source_id": source_id, "status": receipt["status"],
        "records": profile["summary"]["records"], "distinct_leis": profile["summary"]["distinct_leis"],
        "actions": profile["actions"], "csv_sha256": source_hash, "zip_sha256": archive_hash,
        "private_folder": str(final_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


