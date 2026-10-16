"""Strictly audit the privately acquired FFIEC/CFPB HMDA 2018 Three-Year CSV."""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb


EXPECTED_ROWS = 15_138_510
EXPECTED_ACTIONS = {
    "1": 7_732_289,
    "2": 338_822,
    "3": 2_552_640,
    "4": 1_771_582,
    "5": 554_481,
    "6": 2_012_221,
    "7": 101_772,
    "8": 74_703,
}
REQUIRED_FIELDS = {
    "activity_year", "lei", "state_code", "county_code", "action_taken",
    "loan_type", "loan_purpose", "lien_status", "occupancy_type", "loan_amount",
}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(path: Path, temp_dir: Path) -> dict:
    connection = duckdb.connect()
    connection.execute("SET memory_limit='4GB'")
    connection.execute("SET threads=4")
    connection.execute("SET temp_directory=?", [str(temp_dir)])
    relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
    try:
        columns = [row[0] for row in connection.execute(
            f"DESCRIBE SELECT * FROM {relation}", [str(path)]).fetchall()]
        if len(columns) != len(set(columns)) or not REQUIRED_FIELDS.issubset(columns):
            raise ValueError(f"Missing/duplicate fields in 2018 schema: {len(columns)} columns")
        summary_row = connection.execute(f"""
            SELECT count(*) AS records,
                   count(*) FILTER (WHERE activity_year <> '2018' OR activity_year IS NULL) AS wrong_year_rows,
                   count(*) FILTER (WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL) AS invalid_action_rows,
                   count(DISTINCT lei) FILTER (WHERE lei IS NOT NULL AND lei <> '') AS distinct_leis,
                   count(*) FILTER (WHERE lei IS NULL OR lei = '') AS blank_lei_rows,
                   count(*) FILTER (WHERE lei IS NOT NULL AND lei <> '' AND NOT regexp_matches(lei, '^[A-Z0-9]{{20}}$')) AS malformed_lei_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS malformed_state_rows,
                   count(DISTINCT state_code) AS state_code_count,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS unparseable_loan_amount_rows
            FROM {relation}
        """, [str(path)]).fetchone()
        names = ("records", "wrong_year_rows", "invalid_action_rows", "distinct_leis", "blank_lei_rows",
                 "malformed_lei_rows", "malformed_state_rows", "state_code_count", "unparseable_loan_amount_rows")
        summary = dict(zip(names, summary_row))
        actions = {str(code): int(count) for code, count in connection.execute(
            f"SELECT action_taken, count(*) FROM {relation} GROUP BY action_taken", [str(path)]).fetchall()}
        recognized_actions = {key: actions.get(key, 0) for key in EXPECTED_ACTIONS}
        action_match = recognized_actions == EXPECTED_ACTIONS
        quarantined_row_profile = connection.execute(f"""
            SELECT count(*) AS rows,
                   count(*) FILTER (WHERE lei IS NULL OR lei = '') AS blank_lei_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS malformed_state_rows,
                   count(*) FILTER (WHERE try_cast(loan_amount AS DECIMAL(38,2)) IS NULL) AS unparseable_amount_rows,
                   count(DISTINCT state_code) AS state_code_count
            FROM {relation}
            WHERE action_taken NOT IN ('1','2','3','4','5','6','7','8') OR action_taken IS NULL
        """, [str(path)]).fetchone()
        quarantine_names = ("rows", "blank_lei_rows", "malformed_state_rows", "unparseable_amount_rows", "state_code_count")
        quarantined = dict(zip(quarantine_names, quarantined_row_profile))
        valid_core = connection.execute(f"""
            SELECT count(*) FILTER (WHERE lei IS NULL OR lei = '') AS blank_lei_rows,
                   count(*) FILTER (WHERE state_code IS NULL OR length(state_code) <> 2) AS malformed_state_rows
            FROM {relation}
            WHERE action_taken IN ('1','2','3','4','5','6','7','8')
        """, [str(path)]).fetchone()
        if not action_match or sum(recognized_actions.values()) != EXPECTED_ROWS:
            raise ValueError(f"2018 official action reconciliation failed: {summary}, actions={actions}")
        if summary["wrong_year_rows"] or any(valid_core) or quarantined["rows"] != summary["invalid_action_rows"]:
            raise ValueError(f"2018 source/domain audit failed: {summary}, quarantined={quarantined}")
        return {"columns": columns, "summary": summary, "actions": actions,
                "recognized_action_counts": recognized_actions,
                "quarantined_out_of_domain_rows": quarantined,
                "official_aggregation_reconciliation": "PASS_FOR_ACTION_CODES_1_TO_8",
                "release_status": "PASS_WITH_QUARANTINED_SOURCE_ROWS" if quarantined["rows"] else "PASS"}
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    args = parser.parse_args()
    root = args.root.resolve()
    if root.drive.upper() != "D:":
        parser.error("HMDA source files and receipts must remain on D:")
    data_dir = root / "data/private/hmda/hmda-browser-three-year-2018"
    csv_path = data_dir / "hmda-2018-three-year-national.csv"
    if not csv_path.is_file():
        parser.error("HMDA 2018 CSV not found; no acquisition is performed by this auditor")
    acquisition_path = data_dir / "acquisition-receipt.json"
    acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    if csv_path.stat().st_size != acquisition["bytes"] or sha256(csv_path) != acquisition["sha256"]:
        parser.error("Acquired CSV size or SHA-256 differs from the acquisition receipt")
    profile = audit(csv_path, data_dir / "duckdb-temp")
    receipt = {
        "schema_version": 1,
        "status": profile["release_status"],
        "audit_id": "hmda-2018-browser-audit-" + uuid.uuid4().hex[:12],
        "acquisition_receipt_id": acquisition["receipt_id"],
        "source": acquisition["source"],
        "source_url": acquisition["source_url"],
        "dataset_vintage": acquisition["dataset_vintage"],
        "freeze_date": acquisition["freeze_date"],
        "bytes": acquisition["bytes"],
        "sha256": acquisition["sha256"],
        "audited_at_utc": timestamp(),
        "profile": profile,
        "visibility": "private",
        "loan_level_rows_emitted_to_public_repo": False,
    }
    receipt_path = data_dir / "audit-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "audit_id": receipt["audit_id"],
                      "records": profile["summary"]["records"], "fields": len(profile["columns"]),
                      "actions": profile["recognized_action_counts"],
                      "quarantined_rows": profile["quarantined_out_of_domain_rows"],
                      "sha256": acquisition["sha256"]},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
