"""Profile a private Treasury HAMP ZIP and expose aggregate-only evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import uuid
import zlib
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from credit_atlas.workspace import timestamp


EXPECTED_COLUMNS = [
    "rec_typ", "mha_ln_id", "fncl_ast_id", "pgm_mdfc_typ", "ln_mdfc_eff_dt",
    "ln_st_nme", "ln_mdfc_end_dt", "ln_owdrwn_rsn_nme", "ln_rcst_eff_yr",
    "ln_mthy_pi_with_rcst_amt", "ln_mthy_pi_wtho_rcst_amt", "ln_pmt_acvy_mth_dt",
    "ln_drvd_aft_mfdc_eff_dt_term", "ln_lpi_dt", "rptg_stat",
]
DOCUMENTED_HEADER_DIFFERENCES = [{
    "field_order": 13,
    "guide_field": "ln_drvd_aft_mdfc_eff_dt_term",
    "published_csv_header": "ln_drvd_aft_mfdc_eff_dt_term",
    "note": "Treasury CSV header spelling differs from the March 2018 guide; preserve source spelling in raw adapter.",
}]
EXPECTED_RECORD_TYPES = {"Modification Information", "Payment Information"}
EXPECTED_STATES = {"Active", "Active Payment", "Active Non-Payment", "Cancelled",
                   "Disqualified", "Paid Off", "Not Accepted / Not Approved", "Submitted", "Withdrawn"}
EXPECTED_REPORTING = {"Reported", "Not Reported"}


class AuditError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_data_member(archive_path: Path, output_dir: Path) -> tuple[Path, int, int]:
    """Extract one bounded CSV member safely and return its metadata row count."""
    with zipfile.ZipFile(archive_path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        csvs = [item for item in files if item.filename.casefold().endswith(".csv")]
        metas = [item for item in files if item.filename.casefold().endswith(".meta")]
        if len(csvs) != 1 or len(metas) != 1 or len(files) != 2:
            raise AuditError("Expected exactly one CSV and one metadata member")
        csv_info, meta_info = csvs[0], metas[0]
        if (PurePosixPath(csv_info.filename).name != csv_info.filename
                or PurePosixPath(meta_info.filename).name != meta_info.filename
                or csv_info.file_size <= 0 or meta_info.file_size > 1024 * 1024):
            raise AuditError("Archive member path or size is outside the source contract")
        metadata = ET.fromstring(archive.read(meta_info))
        records = metadata.find(".//payloadFileMetaInfo")
        if records is None or not str(records.get("recordCount", "")).isdigit():
            raise AuditError("Official metadata recordCount is missing or malformed")
        expected_rows = int(records.get("recordCount"))
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / csv_info.filename
        partial = target.with_suffix(target.suffix + ".partial")
        if partial.exists():
            raise AuditError("Partial extracted CSV exists; preserve and review it first")
        if target.exists():
            if target.stat().st_size != csv_info.file_size:
                raise AuditError("Existing extracted CSV size differs from official ZIP metadata")
            crc = 0
            with target.open("rb") as existing:
                while chunk := existing.read(1024 * 1024):
                    crc = zlib.crc32(chunk, crc)
            if crc & 0xffffffff != csv_info.CRC:
                raise AuditError("Existing extracted CSV CRC differs from its original ZIP member")
            return target, expected_rows, csv_info.file_size
        written = 0
        try:
            with archive.open(csv_info) as source, partial.open("xb") as dest:
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > csv_info.file_size:
                        raise AuditError("Extracted bytes exceed the ZIP member size")
                    dest.write(chunk)
            if written != csv_info.file_size:
                raise AuditError("Extracted CSV byte count does not match ZIP metadata")
            partial.replace(target)
        except Exception:
            partial.unlink(missing_ok=True)
            raise
        return target, expected_rows, written


def profile_csv(csv_path: Path, expected_rows: int) -> dict:
    db = duckdb.connect()
    db.execute("SET memory_limit='1GB'")
    db.execute("SET threads=2")
    db.execute(f"SET temp_directory='{str(csv_path.parent / 'duckdb-temp').replace(chr(39), chr(39)*2)}'")
    try:
        relation = "read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)"
        columns = db.execute(f"SELECT * FROM {relation} LIMIT 0", [str(csv_path)]).description
        actual_columns = [column[0] for column in columns]
        if actual_columns != EXPECTED_COLUMNS:
            raise AuditError("Treasury CSV header/order differs from the official guide contract")
        totals = db.execute(f"""
            SELECT count(*) AS rows,
                   count(*) FILTER (WHERE rec_typ='Modification Information') AS modification_rows,
                   count(*) FILTER (WHERE rec_typ='Payment Information') AS payment_rows,
                   count(*) FILTER (WHERE rec_typ NOT IN ('Modification Information','Payment Information')
                                      OR rec_typ IS NULL) AS invalid_record_types,
                   count(DISTINCT mha_ln_id) AS distinct_loan_ids,
                   count(*) FILTER (WHERE mha_ln_id IS NULL OR mha_ln_id='') AS blank_loan_ids,
                   count(DISTINCT fncl_ast_id) AS distinct_modification_ids,
                   count(*) FILTER (WHERE fncl_ast_id IS NULL OR fncl_ast_id='') AS blank_modification_ids,
                   min(ln_mdfc_eff_dt) FILTER (WHERE ln_mdfc_eff_dt <> '') AS first_modification_effective_date,
                   max(ln_mdfc_eff_dt) FILTER (WHERE ln_mdfc_eff_dt <> '') AS last_modification_effective_date,
                   min(ln_pmt_acvy_mth_dt) FILTER (WHERE ln_pmt_acvy_mth_dt <> '') AS first_activity_period,
                   max(ln_pmt_acvy_mth_dt) FILTER (WHERE ln_pmt_acvy_mth_dt <> '') AS last_activity_period,
                   count(DISTINCT ln_pmt_acvy_mth_dt) FILTER (WHERE ln_pmt_acvy_mth_dt <> '') AS distinct_activity_periods
            FROM {relation}
        """, [str(csv_path)]).fetchone()
        total_names = ["rows", "modification_rows", "payment_rows", "invalid_record_types",
                       "distinct_loan_ids", "blank_loan_ids", "distinct_modification_ids",
                       "blank_modification_ids", "first_modification_effective_date",
                       "last_modification_effective_date", "first_activity_period",
                       "last_activity_period", "distinct_activity_periods"]
        summary = dict(zip(total_names, totals))
        if summary["rows"] != expected_rows:
            raise AuditError("CSV data rows do not reconcile to Treasury metadata recordCount")

        key_dupes = db.execute(f"""
            SELECT count(*) FROM (
              SELECT rec_typ, fncl_ast_id, coalesce(ln_pmt_acvy_mth_dt,''), count(*) AS n
              FROM {relation}
              GROUP BY 1,2,3 HAVING count(*) > 1
            )
        """, [str(csv_path)]).fetchone()[0]
        summary["duplicate_primary_key_groups"] = key_dupes

        states = db.execute(f"""
            SELECT coalesce(ln_st_nme,'<blank>') AS value, count(*) AS rows
            FROM {relation} WHERE rec_typ='Modification Information'
            GROUP BY 1 ORDER BY rows DESC, value
        """, [str(csv_path)]).fetchall()
        reporting = db.execute(f"""
            SELECT coalesce(rptg_stat,'<blank>') AS value, count(*) AS rows
            FROM {relation} WHERE rec_typ='Payment Information'
            GROUP BY 1 ORDER BY rows DESC, value
        """, [str(csv_path)]).fetchall()
        unexpected_states = [value for value, _ in states if value != "<blank>" and value not in EXPECTED_STATES]
        unexpected_reporting = [value for value, _ in reporting
                               if value != "<blank>" and value not in EXPECTED_REPORTING]
        return {"columns": actual_columns, "summary": summary,
                "documented_header_differences": DOCUMENTED_HEADER_DIFFERENCES,
                "loan_state_distribution": [{"value": value, "rows": count} for value, count in states],
                "reporting_status_distribution": [{"value": value, "rows": count} for value, count in reporting],
                "unexpected_states": unexpected_states,
                "unexpected_reporting_statuses": unexpected_reporting,
                "record_type_domain_ok": summary["invalid_record_types"] == 0,
                "metadata_row_count_match": summary["rows"] == expected_rows,
                "primary_key_unique": key_dupes == 0}
    finally:
        db.close()


def audit(root: Path, archive_path: Path) -> dict:
    root = root.resolve()
    archive_path = archive_path.resolve()
    if root.drive.upper() != "D:" or not archive_path.is_relative_to(root / "data/private/mortgage/treasury-hamp"):
        raise AuditError("Audit inputs and extracted rows must remain in the private D: Treasury folder")
    if not archive_path.is_file() or not zipfile.is_zipfile(archive_path):
        raise AuditError("Input must be an existing official ZIP archive")
    extract_dir = archive_path.parent / "extracted"
    csv_path, expected_rows, extracted_bytes = extract_data_member(archive_path, extract_dir)
    profile = profile_csv(csv_path, expected_rows)
    audit_id = "treasury-hamp-audit-" + uuid.uuid4().hex[:12]
    result = {
        "schema_version": 1,
        "status": "PASS" if (profile["record_type_domain_ok"] and profile["metadata_row_count_match"]
                               and profile["primary_key_unique"] and not profile["unexpected_states"]
                               and not profile["unexpected_reporting_statuses"]
                               and not profile["summary"]["blank_loan_ids"]
                               and not profile["summary"]["blank_modification_ids"]) else "REVIEW_REQUIRED",
        "audit_id": audit_id,
        "source": "U.S. Treasury MHA / HAMP Performance Supplemental Data File",
        "archive_name": archive_path.name,
        "archive_sha256": sha256(archive_path),
        "csv_member_sha256": sha256(csv_path),
        "csv_member_bytes": extracted_bytes,
        "metadata_rows": expected_rows,
        "profile": profile,
        "visibility": "private",
        "loan_level_data_emitted": False,
        "model_fit_performed": False,
        "completed_at_utc": timestamp(),
    }
    output = root / "artifacts/private" / audit_id
    output.mkdir(parents=True, exist_ok=False)
    with (output / "audit.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return {key: result[key] for key in ("status", "audit_id", "archive_name", "archive_sha256",
                                        "csv_member_bytes", "metadata_rows", "profile")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.root, args.archive), indent=2, ensure_ascii=False))
    except (OSError, zipfile.BadZipFile, duckdb.Error, AuditError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
