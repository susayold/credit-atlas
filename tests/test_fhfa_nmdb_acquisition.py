import csv
import io
import zipfile

import pytest

from scripts.acquire_fhfa_nmdb_performance import EXPECTED_COLUMNS, profile_archive


def _archive(path, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=EXPECTED_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("nmdb-mortgage-performance-statistics-all-quarterly.csv", buffer.getvalue())
    return path


def _row(series, value, *, suppressed="0", market="All Mortgages", geography="National", geoid="USA"):
    return {
        "SOURCE": "NMDB", "FREQUENCY": "Quarterly", "GEOLEVEL": geography,
        "GEOID": geoid, "GEONAME": "United States", "MARKET": market,
        "PERIOD": "2026Q2", "YEAR": "2026", "QUARTER": "2", "MONTH": "06",
        "SUPPRESSED": suppressed, "SERIESID": series, "VALUE1": value,
    }


def test_profile_keeps_suppression_as_missing_and_builds_national_series(tmp_path):
    path = _archive(tmp_path / "aggregate.zip", [
        _row("P3089DL", "1.7"), _row("P90DL", "1.0"),
        _row("PFORB", "", suppressed="1"), _row("PFORECL", "0.2"),
        _row("P3089DL", "2.1", geography="State", geoid="CA"),
    ])
    result = profile_archive(path)
    assert result["rows"] == 5
    assert result["unique_aggregate_keys"] == 5
    assert result["national_all_mortgages_series"] == [{
        "period": "2026Q2", "P3089DL": 1.7, "P90DL": 1.0,
        "PFORB": None, "PFORECL": 0.2,
    }]
    assert result["suppression_row_counts"] == {"0": 4, "1": 1}


def test_profile_rejects_duplicate_aggregate_keys(tmp_path):
    path = _archive(tmp_path / "duplicates.zip", [
        _row("P3089DL", "1.7"), _row("P3089DL", "1.7"),
        _row("P90DL", "1.0"), _row("PFORB", "0.2"), _row("PFORECL", "0.2"),
    ])
    with pytest.raises(ValueError, match="Duplicate source aggregate key"):
        profile_archive(path)


def test_profile_rejects_unexpected_csv_schema(tmp_path):
    path = tmp_path / "bad-schema.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bad.csv", "SOURCE,FREQUENCY\nNMDB,Quarterly\n")
    with pytest.raises(ValueError, match="Unexpected FHFA CSV schema"):
        profile_archive(path)


def test_profile_rejects_performance_percentage_outside_bounds(tmp_path):
    path = _archive(tmp_path / "out-of-range.zip", [
        _row("P3089DL", "101"), _row("P90DL", "1.0"),
        _row("PFORB", "0.2"), _row("PFORECL", "0.2"),
    ])
    with pytest.raises(ValueError, match=r"outside \[0, 100\]"):
        profile_archive(path)
