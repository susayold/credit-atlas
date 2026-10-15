from __future__ import annotations

import csv
import json
import zipfile

import pytest

from credit_atlas.ginnie_liquidation import (
    GinnieLiquidationError,
    audit_ginnie_liquidation_zip,
)


def _lr(*, sequence: str, period: str = "201808", reason: str = "1"):
    row = [""] * 15
    row[0] = "LR"
    row[1] = "123456789"
    row[2] = "ABC123"
    row[6] = sequence
    row[8] = period
    row[11] = "250000.00"
    row[12] = "200000.00"
    row[13] = "195000.00"
    row[14] = reason
    return row


def _zip(path, rows, *, report_period="201808", trailer_count=None, trailing_delimiter=False):
    header = ["HH", report_period, "20180907"]
    trailer = ["TT", report_period, str(len(rows) if trailer_count is None else trailer_count)]
    suffix = [""] if trailing_delimiter else []
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        with archive.open("liquidation.txt", "w") as raw:
            import io

            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            writer = csv.writer(text, delimiter="|", lineterminator="\n")
            writer.writerow(header + suffix)
            writer.writerows([row + suffix for row in rows])
            writer.writerow(trailer + suffix)
            text.flush()


def test_audit_profiles_liquidation_without_exposing_identifiers(tmp_path):
    path = tmp_path / "llmonliq_201808.zip"
    _zip(
        path,
        [
            _lr(sequence="0000000001", reason="1"),
            _lr(sequence="0000000002", reason="2"),
            _lr(sequence="0000000003", reason="6"),
        ],
        trailing_delimiter=True,
    )

    audit = audit_ginnie_liquidation_zip(path, terms_accepted=True)
    payload = json.dumps(audit.to_dict())

    assert audit.report_period == "201808"
    assert audit.liquidation_rows == 3
    assert audit.unique_loan_keys == 3
    assert audit.removal_reason_counts == {"1": 1, "2": 1, "6": 1}
    assert audit.blank_amount_counts == {}
    assert "123456789" not in payload
    assert "ABC123" not in payload


def test_terms_gate_precedes_file_access(tmp_path):
    with pytest.raises(GinnieLiquidationError, match="Terms of Use"):
        audit_ginnie_liquidation_zip(tmp_path / "missing.zip")


def test_rejects_trailer_count_mismatch(tmp_path):
    path = tmp_path / "bad-trailer.zip"
    _zip(path, [_lr(sequence="0000000001")], trailer_count=2)
    with pytest.raises(GinnieLiquidationError, match="TT loan count"):
        audit_ginnie_liquidation_zip(path, terms_accepted=True)


def test_rejects_duplicate_key_and_period_mismatch(tmp_path):
    path = tmp_path / "duplicate.zip"
    row = _lr(sequence="0000000001")
    _zip(path, [row, row])
    with pytest.raises(GinnieLiquidationError, match="Duplicate liquidation"):
        audit_ginnie_liquidation_zip(path, terms_accepted=True)

    path = tmp_path / "period-mismatch.zip"
    _zip(path, [_lr(sequence="0000000001", period="201807")])
    with pytest.raises(GinnieLiquidationError, match="differs from HH"):
        audit_ginnie_liquidation_zip(path, terms_accepted=True)


def test_rejects_unknown_removal_code_and_wrong_width(tmp_path):
    path = tmp_path / "bad-reason.zip"
    _zip(path, [_lr(sequence="0000000001", reason="9")])
    with pytest.raises(GinnieLiquidationError, match="removal reason"):
        audit_ginnie_liquidation_zip(path, terms_accepted=True)

    path = tmp_path / "bad-width.zip"
    _zip(path, [_lr(sequence="0000000001")[:-1]])
    with pytest.raises(GinnieLiquidationError, match="15 fields"):
        audit_ginnie_liquidation_zip(path, terms_accepted=True)
