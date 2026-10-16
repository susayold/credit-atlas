import csv
import io
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from acquire_fhfa_nmdb_mortgage_statistics import AcquisitionError, HEADERS, profile_archive


def _archive(path: Path, member: str, rows: list[dict[str, str]]) -> Path:
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(member, text.getvalue())
    return path


def _row(**changes):
    values = {
        "SOURCE": "NMDB", "FREQUENCY": "Annual", "GEOLEVEL": "National",
        "GEOID": "USA", "GEONAME": "United States", "MARKET": "All Mortgages",
        "PERIOD": "2025", "YEAR": "2025", "QUARTER": "4", "MONTH": "12",
        "SUPPRESSED": "0", "SERIESID": "TOT_ORIG", "VALUE1": "100.0",
        "VALUE2": "250.0",
    }
    values.update(changes)
    return values


def _annual_rows():
    return [
        _row(PERIOD=str(year), YEAR=str(year))
        for year in range(1998, 2026)
    ]


def _quarterly_rows():
    result = []
    for ordinal in range(2013 * 4 + 1, 2026 * 4 + 3):
        year, quarter = divmod(ordinal, 4)
        if quarter == 0:
            year -= 1
            quarter = 4
        month = quarter * 3
        result.append(_row(
            FREQUENCY="Quarterly", PERIOD=f"{year}Q{quarter}", YEAR=str(year),
            QUARTER=str(quarter), MONTH=f"{month:02d}", SERIESID="TOT_LOANS",
        ))
    return result


def test_profiles_official_annual_aggregate_and_keeps_count_and_dollar_measures(tmp_path):
    path = _archive(tmp_path / "new.zip", "nmdb-new-mortgage-statistics-all-annual.csv", _annual_rows())

    profile = profile_archive(path, "new_annual")

    assert profile["rows"] == profile["unique_aggregate_keys"] == 28
    assert profile["first_year"] == 1998 and profile["last_year"] == 2025
    assert profile["distinct_periods"] == 28 and profile["periods_contiguous"] is True
    assert profile["not_loan_level"] is True
    assert profile["does_not_add_freddie_vintage"] is True
    assert profile["missing_value1_rows"] == profile["missing_value2_rows"] == 0


def test_profiles_quarterly_period_end_and_suppression(tmp_path):
    rows = _quarterly_rows()
    rows[-1].update(SUPPRESSED="1", VALUE1="", VALUE2=".")
    path = _archive(tmp_path / "outstanding.zip", "nmdb-outstanding-mortgage-statistics-all-quarterly.csv", rows)

    profile = profile_archive(path, "outstanding_quarterly")

    assert profile["rows"] == 54
    assert profile["distinct_periods"] == 54 and profile["periods_contiguous"] is True
    assert profile["suppression_row_counts"] == {"0": 53, "1": 1}
    assert profile["missing_value1_rows"] == profile["missing_value2_rows"] == 1


def test_rejects_inconsistent_period_duplicate_key_and_wrong_member(tmp_path):
    bad_period = _row(QUARTER="3")
    path = _archive(tmp_path / "period.zip", "nmdb-new-mortgage-statistics-all-annual.csv", [bad_period])
    with pytest.raises(AcquisitionError, match="PERIOD does not agree"):
        profile_archive(path, "new_annual")

    duplicate = _row()
    path = _archive(tmp_path / "duplicate.zip", "nmdb-new-mortgage-statistics-all-annual.csv", [duplicate, duplicate])
    with pytest.raises(AcquisitionError, match="Duplicate aggregate key"):
        profile_archive(path, "new_annual")

    path = _archive(tmp_path / "member.zip", "unexpected.csv", [_row()])
    with pytest.raises(AcquisitionError, match="member name/count"):
        profile_archive(path, "new_annual")
