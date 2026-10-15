from __future__ import annotations

import csv
import json
import zipfile

import pytest

from credit_atlas.ginnie_performance import (
    GinnieLoanPerfError,
    audit_ginnie_loanperf_zip,
)


def _lp(*, sequence: str, period: str, status: str = "0", reason: str = "", history: str = ""):
    row = [""] * 59
    row[0] = "LP"
    row[1] = "123456789"
    row[2] = "ABC123"
    row[6] = sequence
    row[16] = "250000.00"
    row[20] = status
    row[23] = "95.00"
    row[25] = "42.50"
    row[26] = "720"
    row[38] = reason
    row[39] = period
    row[40] = "20200115"
    row[58] = history
    return row


def _zip(
    path,
    records,
    *,
    report_period="202003",
    frequency="Q",
    trailer_count=None,
    trailing_delimiter=False,
):
    header = ["HH", report_period, frequency, "20200410"]
    trailer = ["TT", report_period, str(len(records) if trailer_count is None else trailer_count)]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        with archive.open("loanperf.txt", "w") as raw:
            import io

            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            writer = csv.writer(text, delimiter="|", lineterminator="\n")
            suffix = [""] if trailing_delimiter else []
            writer.writerow(header + suffix)
            writer.writerows([row + suffix for row in records])
            writer.writerow(trailer + suffix)
            text.flush()


def test_audit_profiles_only_aggregates_and_keeps_identifiers_out_of_receipt(tmp_path):
    path = tmp_path / "LoanPerf_202003.zip"
    rows = [
        _lp(sequence="0000000001", period="202001", status="0", history="00XX"),
        _lp(sequence="0000000001", period="202002", status="2", history="0002"),
        _lp(sequence="0000000002", period="202003", status="6", reason="3", history="010203"),
    ]
    _zip(path, rows)

    audit = audit_ginnie_loanperf_zip(path, terms_accepted=True)
    payload = json.dumps(audit.to_dict())

    assert audit.file_frequency == "Q"
    assert audit.loan_period_rows == 3
    assert audit.distinct_loan_keys == 2
    assert audit.min_as_of_period == "202001"
    assert audit.max_as_of_period == "202003"
    assert audit.delinquency_status_counts == {"0": 1, "2": 1, "6": 1}
    assert audit.removal_reason_counts == {"3": 1, "blank": 2}
    assert audit.delinquency_history_counts == {"2": 2, "3": 1}
    assert "123456789" not in payload
    assert "ABC123" not in payload


def test_audit_accepts_official_pipe_files_with_one_trailing_delimiter(tmp_path):
    path = tmp_path / "sample-with-trailing-delimiters.zip"
    _zip(
        path,
        [_lp(sequence="0000000001", period="202003", status="2", history="00XX")],
        trailing_delimiter=True,
    )

    audit = audit_ginnie_loanperf_zip(path, terms_accepted=True)

    assert audit.loan_period_rows == 1
    assert audit.delinquency_status_counts == {"2": 1}
    assert audit.delinquency_history_counts == {"2": 1}


def test_terms_gate_is_checked_before_opening_file(tmp_path):
    missing = tmp_path / "does-not-exist.zip"
    with pytest.raises(GinnieLoanPerfError, match="Terms of Use"):
        audit_ginnie_loanperf_zip(missing)


def test_rejects_trailer_count_mismatch(tmp_path):
    path = tmp_path / "bad-count.zip"
    _zip(path, [_lp(sequence="0000000001", period="202003")], trailer_count=2)
    with pytest.raises(GinnieLoanPerfError, match="TT loan count"):
        audit_ginnie_loanperf_zip(path, terms_accepted=True)


def test_rejects_duplicate_loan_period_key(tmp_path):
    path = tmp_path / "duplicate.zip"
    row = _lp(sequence="0000000001", period="202003")
    _zip(path, [row, row])
    with pytest.raises(GinnieLoanPerfError, match="Duplicate loan-period"):
        audit_ginnie_loanperf_zip(path, terms_accepted=True)


def test_rejects_malformed_history_and_wrong_row_width(tmp_path):
    bad_history = _lp(sequence="0000000001", period="202003", history="0X")
    path = tmp_path / "bad-history.zip"
    _zip(path, [bad_history])
    with pytest.raises(GinnieLoanPerfError, match="LP-59"):
        audit_ginnie_loanperf_zip(path, terms_accepted=True)

    bad_width = _lp(sequence="0000000001", period="202003")[:-1]
    _zip(path, [bad_width])
    with pytest.raises(GinnieLoanPerfError, match="59 fields"):
        audit_ginnie_loanperf_zip(path, terms_accepted=True)


def test_rejects_future_period_and_frequency_excess(tmp_path):
    path = tmp_path / "future.zip"
    _zip(path, [_lp(sequence="0000000001", period="202004")])
    with pytest.raises(GinnieLoanPerfError, match="exceeds HH"):
        audit_ginnie_loanperf_zip(path, terms_accepted=True)

    rows = [_lp(sequence="0000000001", period=f"20200{month}") for month in (1, 2, 3, 4)]
    _zip(path, rows, report_period="202004")
    with pytest.raises(GinnieLoanPerfError, match="too many times"):
        audit_ginnie_loanperf_zip(path, terms_accepted=True)
