import csv
import zipfile
from pathlib import Path

import pytest

from scripts.audit_treasury_hamp_source import EXPECTED_FIELDS, audit


def _row(record_type, *, loan_id="1", asset_id="1", activity_date="", status="", reporting=""):
    row = [""] * len(EXPECTED_FIELDS)
    values = {
        "rec_typ": record_type,
        "mha_ln_id": loan_id,
        "fncl_ast_id": asset_id,
        "pgm_mdfc_typ": "Tier 1 HAMP",
        "ln_st_nme": status,
        "ln_pmt_acvy_mth_dt": activity_date,
        "rptg_stat": reporting,
    }
    for key, value in values.items():
        row[EXPECTED_FIELDS.index(key)] = value
    return row


def _package(tmp_path: Path, rows, *, metadata_count=None):
    csv_path = tmp_path / "HMP_Govt_Agency_Perf_Data_20220101_20220201.csv"
    with csv_path.open("w", encoding="ascii", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(EXPECTED_FIELDS)
        writer.writerows(rows)
    count = len(rows) if metadata_count is None else metadata_count
    meta = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<outboundDocument><documentDataMetaInfo><payloadGroup fileCount="1">'
        '<payloadInfo><payloadFile>HMP_Govt_Agency_Perf_Data_20220101_20220201.csv</payloadFile>'
        f'<payloadFileMetaInfo recordCount="{count}" timestamp="20230317194319951082" />'
        '</payloadInfo></payloadGroup></documentDataMetaInfo></outboundDocument>'
    )
    archive = tmp_path / "treasury-hamp.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(csv_path, csv_path.name)
        bundle.writestr("payload.meta", meta)
    return archive, csv_path


def test_treasury_hamp_audit_matches_metadata_and_keeps_mixed_grain(tmp_path):
    archive, csv_path = _package(tmp_path, [
        _row("Modification Information", status="Disqualified"),
        _row("Payment Information", activity_date="2022-01-01", reporting="Reported"),
    ])

    result = audit(archive, csv_path)

    assert result["payload"]["native_rows"] == 2
    assert result["payload"]["modification_rows"] == 1
    assert result["payload"]["payment_activity_rows"] == 1
    assert result["payload"]["distinct_mha_loan_ids"] == 1
    assert result["payload"]["activity_start"] == "2022-01-01"
    assert result["checks"]["payload_record_count_matches_treasury_metadata"] is True
    assert result["retrieved_at_utc"] is None


def test_treasury_hamp_audit_rejects_duplicate_documented_key(tmp_path):
    archive, csv_path = _package(tmp_path, [
        _row("Modification Information", status="Disqualified"),
        _row("Payment Information", activity_date="2022-01-01", reporting="Reported"),
        _row("Payment Information", loan_id="2", activity_date="2022-01-01", reporting="Reported"),
    ])

    with pytest.raises(ValueError, match="Documented Treasury key is not unique"):
        audit(archive, csv_path)


def test_treasury_hamp_audit_rejects_mismatched_zip_row_count(tmp_path):
    archive, csv_path = _package(tmp_path, [
        _row("Modification Information", status="Disqualified"),
        _row("Payment Information", activity_date="2022-01-01", reporting="Reported"),
    ], metadata_count=10)

    with pytest.raises(ValueError, match="CSV row count differs from Treasury ZIP metadata"):
        audit(archive, csv_path)
