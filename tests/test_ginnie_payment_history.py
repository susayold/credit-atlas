from __future__ import annotations

import csv
import json
import zipfile

import pytest

from credit_atlas.ginnie_payment_history import (
    GinniePaymentHistoryError,
    audit_ginnie_payment_history,
)


def _pool(cusip="123456789", pool="ABC123", count=1):
    return [
        ["PH", cusip, pool, "X", "SF", "20200101", "1234", "202001"],
        ["LL", pool, "0000000001", "1234", "0001XX"],
        ["PT", cusip, pool, "X", "SF", "20200101", "1234", "202001", str(count)],
    ]


def _write(path, pools=None, *, totals=None, extra=None):
    pools = [_pool()] if pools is None else pools
    rows = [["HH", "202001", "20200203"]]
    rows.extend(record for pool in pools for record in pool)
    if extra:
        rows.extend(extra)
    loan_count = sum(int(pool[-1][-1]) for pool in pools)
    actual_records = len(rows) + 1
    declared = totals or (len(pools), loan_count, actual_records)
    rows.append(["TT", "202001", "20200203", *map(str, declared)])
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, delimiter="|", lineterminator="\n").writerows(rows)


def test_audit_returns_aggregate_fields_without_identifiers(tmp_path):
    path = tmp_path / "history.txt"
    _write(path)

    result = audit_ginnie_payment_history(path, terms_accepted=True)
    payload = json.dumps(result.to_dict())

    assert result.pool_count == 1
    assert result.loan_count == 1
    assert result.history_length_counts == {3: 1}
    assert result.delinquency_code_counts == {"00": 1, "01": 1, "XX": 1}
    assert result.current_status_counts == {"00": 1}
    assert result.missing_history_occurrences == 1
    assert result.pool_count_reconciles
    assert result.loan_count_reconciles
    assert result.record_count_reconciles
    assert "123456789" not in payload
    assert "ABC123" not in payload
    assert "0000000001" not in payload


def test_terms_gate_precedes_file_access(tmp_path):
    with pytest.raises(GinniePaymentHistoryError, match="Terms of Use"):
        audit_ginnie_payment_history(tmp_path / "missing.txt")


def test_header_trailer_and_pool_totals_are_checked(tmp_path):
    path = tmp_path / "bad-trailer.txt"
    _write(path, totals=(2, 1, 99))
    result = audit_ginnie_payment_history(path, terms_accepted=True)
    assert not result.pool_count_reconciles
    assert not result.record_count_reconciles

    path = tmp_path / "bad-pool-total.txt"
    pools = [_pool(count=2)]
    _write(path, pools=pools)
    with pytest.raises(GinniePaymentHistoryError, match="PT loan count"):
        audit_ginnie_payment_history(path, terms_accepted=True)


def test_rejects_invalid_status_duplicate_sequence_and_unsorted_pool(tmp_path):
    path = tmp_path / "bad-status.txt"
    pools = [_pool()]
    pools[0][1][4] = "0A"
    _write(path, pools=pools)
    with pytest.raises(GinniePaymentHistoryError, match="invalid status"):
        audit_ginnie_payment_history(path, terms_accepted=True)

    path = tmp_path / "bad-sequence.txt"
    pools = [_pool()]
    pools[0].insert(2, ["LL", "ABC123", "0000000001", "1234", "00"])
    pools[0][-1][-1] = "2"
    _write(path, pools=pools)
    with pytest.raises(GinniePaymentHistoryError, match="not ascending"):
        audit_ginnie_payment_history(path, terms_accepted=True)

    path = tmp_path / "unsorted-pools.txt"
    _write(path, pools=[_pool(pool="ZZZ999"), _pool(pool="ABC123")])
    with pytest.raises(GinniePaymentHistoryError, match="Pool records are not sorted"):
        audit_ginnie_payment_history(path, terms_accepted=True)


def test_accepts_short_variable_history_and_trailing_delimiter(tmp_path):
    path = tmp_path / "short.txt"
    rows = [
        ["HH", "202001", "20200203"],
        ["PH", "123456789", "ABC123", "X", "SF", "20200101", "1234", "202001"],
        ["LL", "ABC123", "0000000001", "1234", "030201"],
        ["PT", "123456789", "ABC123", "X", "SF", "20200101", "1234", "202001", "1"],
        ["TT", "202001", "20200203", "1", "1", "5"],
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, delimiter="|", lineterminator="\n").writerows(
            [row + [""] for row in rows]
        )
    result = audit_ginnie_payment_history(path, terms_accepted=True)
    assert result.history_length_counts == {3: 1}
    assert result.current_status_counts == {"03": 1}


def test_audits_single_member_zip_without_exposing_identifiers(tmp_path):
    source = tmp_path / "history.txt"
    _write(source)
    zipped = tmp_path / "llpaymhist_202001.zip"
    with zipfile.ZipFile(zipped, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(source, "payment-history.txt")

    result = audit_ginnie_payment_history(zipped, terms_accepted=True)
    assert result.member_name == "payment-history.txt"
    assert result.member_bytes == source.stat().st_size
    assert result.pool_count == 1
    assert result.pool_count_reconciles


def test_rejects_ambiguous_multi_member_zip(tmp_path):
    zipped = tmp_path / "multiple.zip"
    with zipfile.ZipFile(zipped, "w") as archive:
        archive.writestr("one.txt", "")
        archive.writestr("two.txt", "")
    with pytest.raises(GinniePaymentHistoryError, match="exactly one"):
        audit_ginnie_payment_history(zipped, terms_accepted=True)
