import csv

import pytest

from credit_atlas.hud_fha_iif import EXPECTED_HEADERS, profile_csv


def _write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=EXPECTED_HEADERS)
        writer.writeheader()
        for index, overrides in enumerate(rows, 1):
            row = {name: "1" for name in EXPECTED_HEADERS}
            row.update({"OBJECTID": str(index), "GEOID": f"0100100000{index}", "STUSAB": "AL"})
            row.update(overrides)
            writer.writerow(row)


def test_profiles_state_totals_and_quarantines_undocumented_negative_code(tmp_path):
    path = tmp_path / "hud.csv"
    _write(path, [
        {"IIF_CNT": "4", "UNPD_BAL_SUM": "1000", "ORIG_MRTG_AMT_SUM": "1500"},
        {"IIF_CNT": "2", "UNPD_BAL_SUM": "-4", "ORIG_MRTG_AMT_SUM": "-4"},
        {"IIF_CNT": "", "UNPD_BAL_SUM": "", "ORIG_MRTG_AMT_SUM": ""},
    ])
    profile = profile_csv(path, expected_rows=3, verify_release=False)
    assert profile["unique_tracts"] == 3
    assert profile["national_totals_nonblank_tracts"] == {
        "active_insured_loans": 6, "unpaid_balance_usd": 1000.0, "original_mortgage_amount_usd": 1500.0,
    }
    assert profile["missing_metric_tracts"] == {
        "active_insured_loans": 1, "unpaid_balance_usd": 1, "original_mortgage_amount_usd": 1,
    }
    assert profile["uninterpreted_source_codes"] == {
        "unpaid_balance_usd": {"-4": 1}, "original_mortgage_amount_usd": {"-4": 1},
    }
    assert profile["state_aggregates"]["AL"]["active_insured_loans"] == 6


def test_rejects_duplicate_geoid(tmp_path):
    path = tmp_path / "duplicate.csv"
    _write(path, [{"GEOID": "01001000001"}, {"GEOID": "01001000001"}])
    with pytest.raises(ValueError, match="duplicate tract key"):
        profile_csv(path, expected_rows=2, verify_release=False)


def test_rejects_wrong_schema(tmp_path):
    path = tmp_path / "wrong.csv"
    path.write_text("GEOID,COUNT\n01001000001,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unexpected HUD FHA tract CSV schema"):
        profile_csv(path, expected_rows=1, verify_release=False)


def test_rejects_fractional_insured_loan_counts(tmp_path):
    path = tmp_path / "fractional.csv"
    _write(path, [{"IIF_CNT": "1.5"}])
    with pytest.raises(ValueError, match="Non-integer insured-loan count"):
        profile_csv(path, expected_rows=1, verify_release=False)
