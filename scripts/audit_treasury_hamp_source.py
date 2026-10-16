"""Profile a private local copy of Treasury's HAMP performance supplement.

The receipt contains file-level hashes and aggregate diagnostics only. It never
copies loan rows or identifiers into the public source register.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import duckdb


SOURCE_PAGE = "https://home.treasury.gov/data/troubled-assets-relief-program/reports/mha-public-file"
SOURCE_ARCHIVE = "https://home.treasury.gov/system/files/256/HMP_Govt_Agency_Perf_Data.zip"
EXPECTED_FIELDS = [
    "rec_typ", "mha_ln_id", "fncl_ast_id", "pgm_mdfc_typ", "ln_mdfc_eff_dt",
    "ln_st_nme", "ln_mdfc_end_dt", "ln_owdrwn_rsn_nme", "ln_rcst_eff_yr",
    "ln_mthy_pi_with_rcst_amt", "ln_mthy_pi_wtho_rcst_amt", "ln_pmt_acvy_mth_dt",
    "ln_drvd_aft_mfdc_eff_dt_term", "ln_lpi_dt", "rptg_stat",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _package_metadata(archive: Path) -> dict:
    with zipfile.ZipFile(archive) as bundle:
        members = [item for item in bundle.infolist() if not item.is_dir()]
        csv_members = [item for item in members if item.filename.lower().endswith(".csv")]
        meta_members = [item for item in members if item.filename.lower().endswith(".meta")]
        if len(csv_members) != 1 or len(meta_members) != 1 or len(members) != 2:
            raise ValueError("Expected one CSV payload and one Treasury metadata file")
        if any(item.flag_bits & 0x1 for item in members):
            raise ValueError("Encrypted Treasury archive members are not supported")
        root = ElementTree.fromstring(bundle.read(meta_members[0]))
        payload = root.find(".//payloadInfo")
        if payload is None:
            raise ValueError("Treasury metadata has no payload record")
        payload_name = payload.findtext("payloadFile")
        meta = payload.find("payloadFileMetaInfo")
        if meta is None or payload_name != csv_members[0].filename:
            raise ValueError("Treasury metadata does not identify the archive CSV")
        try:
            expected_rows = int(meta.attrib["recordCount"])
            raw_timestamp = meta.attrib["timestamp"]
            generated_at = datetime.strptime(raw_timestamp, "%Y%m%d%H%M%S%f").replace(
                tzinfo=timezone.utc
            ).isoformat().replace("+00:00", "Z")
        except (KeyError, ValueError) as error:
            raise ValueError("Treasury payload count/timestamp metadata is invalid") from error
        return {
            "payload_name": payload_name,
            "payload_bytes": csv_members[0].file_size,
            "payload_crc32": f"{csv_members[0].CRC:08x}",
            "metadata_record_count": expected_rows,
            "publisher_package_generated_at_utc": generated_at,
            "metadata_file": meta_members[0].filename,
            "metadata_bytes": meta_members[0].file_size,
        }


def _verify_extracted_payload(archive: Path, csv_path: Path, metadata: dict) -> str:
    if csv_path.stat().st_size != metadata["payload_bytes"]:
        raise ValueError("Extracted CSV byte count differs from the archive member")
    digest = hashlib.sha256()
    total = 0
    with zipfile.ZipFile(archive) as bundle, bundle.open(metadata["payload_name"]) as source, csv_path.open("rb") as extracted:
        while block := source.read(8 * 1024 * 1024):
            extracted_block = extracted.read(len(block))
            if extracted_block != block:
                raise ValueError("Extracted CSV content differs from the verified archive member")
            digest.update(block)
            total += len(block)
        if extracted.read(1):
            raise ValueError("Extracted CSV contains bytes beyond the archive member")
    if total != metadata["payload_bytes"]:
        raise ValueError("Archive member length differs from Treasury metadata")
    return digest.hexdigest()


def _profile_csv(csv_path: Path) -> dict:
    with csv_path.open("r", encoding="ascii", newline="") as stream:
        header = next(csv.reader(stream))
    if header != EXPECTED_FIELDS:
        raise ValueError("Treasury CSV header differs from the documented 15-field layout")

    query = """
    SELECT COUNT(*) AS native_rows,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information') AS modification_rows,
           COUNT(*) FILTER (WHERE rec_typ='Payment Information') AS payment_activity_rows,
           COUNT(DISTINCT mha_ln_id) AS distinct_mha_loan_ids,
           COUNT(DISTINCT fncl_ast_id) AS distinct_financial_asset_ids,
           COUNT(DISTINCT (rec_typ, fncl_ast_id, COALESCE(ln_pmt_acvy_mth_dt,''))) AS distinct_documented_keys,
           MIN(TRY_CAST(ln_pmt_acvy_mth_dt AS DATE)) AS activity_start,
           MAX(TRY_CAST(ln_pmt_acvy_mth_dt AS DATE)) AS activity_end,
           COUNT(DISTINCT TRY_CAST(ln_pmt_acvy_mth_dt AS DATE)) AS activity_period_count,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND pgm_mdfc_typ='Tier 1 HAMP') AS tier1_hamp_mods,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND pgm_mdfc_typ='Tier 2 HAMP') AS tier2_hamp_mods,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND pgm_mdfc_typ='Streamline HAMP') AS streamline_hamp_mods,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND pgm_mdfc_typ='FHA HAMP') AS fha_hamp_mods,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND pgm_mdfc_typ='RD HAMP') AS rd_hamp_mods,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND ln_st_nme='Active Payment') AS status_active_payment,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND ln_st_nme='Disqualified') AS status_disqualified,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND ln_st_nme='Paid Off') AS status_paid_off,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND ln_st_nme='Withdrawn') AS status_withdrawn,
           COUNT(*) FILTER (WHERE rec_typ='Payment Information' AND rptg_stat='Reported') AS payment_reported,
           COUNT(*) FILTER (WHERE rec_typ='Payment Information' AND rptg_stat='Not Reported') AS payment_not_reported,
           COUNT(*) FILTER (WHERE rec_typ='Modification Information' AND fncl_ast_id IS NULL) AS modification_rows_missing_asset_id,
           COUNT(*) FILTER (WHERE rec_typ='Payment Information' AND ln_pmt_acvy_mth_dt IS NULL) AS payment_rows_missing_activity_date
    FROM read_csv_auto(?, header=true, all_varchar=true, ignore_errors=false)
    """
    connection = duckdb.connect(":memory:")
    try:
        cursor = connection.execute(query, [str(csv_path.resolve())])
        values = cursor.fetchone()
        columns = [description[0] for description in cursor.description]
    finally:
        connection.close()
    profile = dict(zip(columns, values))
    for key, value in profile.items():
        if hasattr(value, "isoformat"):
            profile[key] = value.isoformat()
    profile["field_count"] = len(header)
    if profile["native_rows"] != profile["distinct_documented_keys"]:
        raise ValueError("Documented Treasury key is not unique in the local CSV")
    if profile["native_rows"] != profile["modification_rows"] + profile["payment_activity_rows"]:
        raise ValueError("Treasury record types do not reconcile to the native row count")
    if profile["modification_rows"] != profile["tier1_hamp_mods"] + profile["tier2_hamp_mods"] + profile["streamline_hamp_mods"] + profile["fha_hamp_mods"] + profile["rd_hamp_mods"]:
        raise ValueError("Observed modification program categories do not reconcile")
    if profile["payment_activity_rows"] != profile["payment_reported"] + profile["payment_not_reported"]:
        raise ValueError("Observed payment reporting states do not reconcile")
    if profile["modification_rows_missing_asset_id"] or profile["payment_rows_missing_activity_date"]:
        raise ValueError("Required identifiers/activity dates are missing")
    return profile


def audit(archive: Path, csv_path: Path) -> dict:
    archive, csv_path = archive.resolve(), csv_path.resolve()
    if not archive.is_file() or not csv_path.is_file():
        raise FileNotFoundError("Both the private Treasury ZIP and extracted CSV are required")
    metadata = _package_metadata(archive)
    content_sha256 = _verify_extracted_payload(archive, csv_path, metadata)
    profile = _profile_csv(csv_path)
    if profile["native_rows"] != metadata["metadata_record_count"]:
        raise ValueError("CSV row count differs from Treasury ZIP metadata")
    return {
        "schema_version": 1,
        "source_id": "treasury-hamp-performance-update-2023-02",
        "publisher": "U.S. Department of the Treasury",
        "publisher_page_url": SOURCE_PAGE,
        "source_object_url": SOURCE_ARCHIVE,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieved_at_utc": None,
        "retrieval_timestamp_status": "No local acquisition receipt records the download time.",
        "archive": {
            "file_name": archive.name,
            "bytes": archive.stat().st_size,
            "sha256": _sha256(archive),
            **metadata,
        },
        "payload": {
            "file_name": csv_path.name,
            "bytes": csv_path.stat().st_size,
            "sha256": content_sha256,
            **profile,
        },
        "checks": {
            "extracted_payload_byte_for_byte_matches_archive": True,
            "archive_member_crc_verified_on_read": True,
            "payload_record_count_matches_treasury_metadata": True,
            "documented_primary_key_unique": True,
            "record_type_counts_reconcile": True,
            "program_counts_reconcile": True,
            "reporting_status_counts_reconcile": True,
            "model_qualified": False,
            "public_release_approved": False,
        },
        "scope_note": (
            "Aggregate audit only. This is a selected modified-loan cohort, not an all-mortgage "
            "origination population or a general underwriting PD dataset."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit(args.archive, args.csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "AUDIT_COMPLETE", "source_id": result["source_id"], "native_rows": result["payload"]["native_rows"], "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
