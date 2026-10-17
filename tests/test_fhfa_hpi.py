from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

from credit_atlas.fhfa_hpi import (
    FHFAHPIError,
    normalize_state_hpi_csv,
    normalize_us_census_hpi_csv,
)

_COMPARE_SPEC = importlib.util.spec_from_file_location(
    "fhfa_hpi_parity", Path(__file__).resolve().parents[1] / "scripts/compare_fhfa_us_hpi_to_fred.py"
)
_COMPARE_MODULE = importlib.util.module_from_spec(_COMPARE_SPEC)
_COMPARE_SPEC.loader.exec_module(_COMPARE_MODULE)


def _write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(rows)


def test_normalizes_balanced_state_panel_including_dc(tmp_path):
    path = tmp_path / "hpi.csv"
    states = sorted({"AL", "AK", "DC"} | {
        "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "IA", "ID",
        "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO",
        "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
        "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT",
        "WA", "WI", "WV", "WY",
    })
    _write(path, [[state, year, quarter, "100.00"] for state in states for year, quarter in [(2020, 1), (2020, 2)]])

    result = normalize_state_hpi_csv(path)
    assert result.geography_count == 51
    assert result.first_period == "2020Q1"
    assert result.latest_period == "2020Q2"
    assert len(result.records) == 102


def test_rejects_duplicate_key_and_period_gap(tmp_path):
    path = tmp_path / "hpi.csv"
    states = sorted({"AL", "AK", "DC"} | {
        "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "IA", "ID",
        "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO",
        "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
        "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT",
        "WA", "WI", "WV", "WY",
    })
    rows = [[state, 2020, 1, "100"] for state in states]
    rows.append(rows[0])
    _write(path, rows)
    with pytest.raises(FHFAHPIError, match="Duplicate"):
        normalize_state_hpi_csv(path)

    _write(path, [[state, 2020, quarter, "100"] for state in states for quarter in (1, 3)])
    with pytest.raises(FHFAHPIError, match="gap"):
        normalize_state_hpi_csv(path)


def test_rejects_bad_geo_and_nonpositive_index(tmp_path):
    path = tmp_path / "hpi.csv"
    states = sorted({"AL", "AK", "DC"} | {
        "AR", "AZ", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "IA", "ID",
        "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO",
        "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
        "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT",
        "WA", "WI", "WV", "WY",
    })
    rows = [[state, 2020, 1, "100"] for state in states]
    rows[0][0] = "XX"
    _write(path, rows)
    with pytest.raises(FHFAHPIError, match="state/DC"):
        normalize_state_hpi_csv(path)

    rows[0][0] = "AK"
    rows[0][3] = "0"
    _write(path, rows)
    with pytest.raises(FHFAHPIError, match="positive"):
        normalize_state_hpi_csv(path)


def test_us_census_hpi_parser_validates_balanced_panel_and_periods(tmp_path):
    codes = ["USA", "DV_ENC", "DV_ESC", "DV_MA", "DV_MT", "DV_NE", "DV_PAC", "DV_SA", "DV_WNC", "DV_WSC"]
    path = tmp_path / "hpi_at_us_and_census.csv"
    _write(path, [[code, 2025, quarter, f"{100 + quarter}.00"]
                  for code in codes for quarter in (1, 2)])

    result = normalize_us_census_hpi_csv(path)
    assert result.status == "PASS"
    assert result.geography_count == 10 and result.period_count == 2
    assert result.first_period == "2025Q1" and result.latest_period == "2025Q2"
    assert len(result.records) == 20
    assert next(row for row in result.records if row[0] == "USA" and row[2] == 2)[3] == 102.0


@pytest.mark.parametrize("rows", [
    [["USA", 2025, 1, "100.00"], ["USA", 2025, 1, "101.00"]],
    [["USA", 2025, 1, "100.00"]],
    [["USA", 2025, 1, "100.00"], ["USA", 2025, 3, "101.00"]],
    [["USA", 2025, 1, "nan"]],
])
def test_us_census_hpi_rejects_duplicate_incomplete_or_invalid_rows(tmp_path, rows):
    path = tmp_path / "hpi_at_us_and_census.csv"
    _write(path, rows)
    with pytest.raises(FHFAHPIError):
        normalize_us_census_hpi_csv(path)


def test_fhfa_national_hpi_parity_receipt_uses_exact_quarter_values(tmp_path):
    codes = ["USA", "DV_ENC", "DV_ESC", "DV_MA", "DV_MT", "DV_NE", "DV_PAC", "DV_SA", "DV_WNC", "DV_WSC"]
    fhfa_path, fred_path = tmp_path / "fhfa.csv", tmp_path / "fred.csv"
    _write(fhfa_path, [[code, 2025, quarter, f"{100 + quarter}.00"]
                       for code in codes for quarter in (1, 2)])
    with fred_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["observation_date", "USSTHPI"])
        writer.writerows([["2025-01-01", "101.00"], ["2025-04-01", "102.00"]])

    receipt_path = tmp_path / "parity-receipt.json"
    result = _COMPARE_MODULE.compare(fhfa_path, fred_path, receipt_path)
    assert result["status"] == "PASS"
    assert result["overlap_rows"] == 2
    assert result["value_mismatches"] == result["missing_value_disagreements"] == 0
    assert result["direct_source"]["national_rows"] == result["fred_comparator"]["rows"] == 2

    fred_path.write_text("observation_date,USSTHPI\n2025-01-01,101.00\n2025-04-01,102.01\n", encoding="utf-8")
    result = _COMPARE_MODULE.compare(fhfa_path, fred_path, receipt_path)
    assert result["status"] == "FAIL" and result["value_mismatches"] == 1
