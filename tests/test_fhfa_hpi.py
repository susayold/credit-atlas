from __future__ import annotations

import csv

import pytest

from credit_atlas.fhfa_hpi import FHFAHPIError, normalize_state_hpi_csv


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
