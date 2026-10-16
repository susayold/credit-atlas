import csv
from pathlib import Path

from scripts.audit_treasury_hamp_performance import EXPECTED_COLUMNS, profile_csv


def write_source(path: Path, records):
    with path.open("w", encoding="ascii", newline="") as stream:
        writer = csv.writer(stream, quoting=csv.QUOTE_ALL)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerows(records)


def modification(loan, modification_id, status="Active Payment"):
    values = [""] * len(EXPECTED_COLUMNS)
    values[0:6] = ["Modification Information", loan, modification_id, "Tier 1 HAMP",
                   "2017-12-01", status]
    return values


def payment(loan, modification_id, period, status="Reported"):
    values = [""] * len(EXPECTED_COLUMNS)
    values[0:3] = ["Payment Information", loan, modification_id]
    values[11] = period
    values[12] = "60"
    values[14] = status
    return values


def test_profile_reconciles_official_record_types_ids_periods_and_statuses(tmp_path):
    path = tmp_path / "hamp.csv"
    rows = [modification("L1", "M1"), payment("L1", "M1", "2022-01-01"),
            payment("L1", "M1", "2022-02-01", "Not Reported"),
            modification("L2", "M2", "Disqualified")]
    write_source(path, rows)

    result = profile_csv(path, expected_rows=4)

    assert result["summary"]["rows"] == 4
    assert result["summary"]["modification_rows"] == 2
    assert result["summary"]["payment_rows"] == 2
    assert result["summary"]["distinct_loan_ids"] == 2
    assert result["summary"]["distinct_modification_ids"] == 2
    assert result["summary"]["first_activity_period"] == "2022-01-01"
    assert result["summary"]["last_activity_period"] == "2022-02-01"
    assert result["summary"]["duplicate_primary_key_groups"] == 0
    assert result["primary_key_unique"] is True
    assert not result["unexpected_states"]
    assert not result["unexpected_reporting_statuses"]
    assert {"loan_id", "mha_ln_id", "financial_asset_id"}.isdisjoint(result)


def test_profile_detects_duplicate_primary_key_and_metadata_mismatch(tmp_path):
    path = tmp_path / "hamp-duplicate.csv"
    repeated = payment("L1", "M1", "2022-01-01")
    write_source(path, [modification("L1", "M1"), repeated, repeated])

    result = profile_csv(path, expected_rows=3)

    assert result["summary"]["duplicate_primary_key_groups"] == 1
    assert result["primary_key_unique"] is False
