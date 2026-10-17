"""Validation for FHFA quarterly state All-Transactions HPI snapshots."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


class FHFAHPIError(ValueError):
    """Raised when an FHFA state HPI source file violates the chosen contract."""


@dataclass(frozen=True)
class FHFAHPIResult:
    records: tuple[tuple[str, int, int, float], ...]
    geography_count: int
    first_period: str
    latest_period: str
    status: str = "PASS"


@dataclass(frozen=True)
class FHFAUSCensusHPIResult:
    records: tuple[tuple[str, int, int, float], ...]
    geography_count: int
    period_count: int
    first_period: str
    latest_period: str
    status: str = "PASS"


_STATE_CODES = {
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA",
    "HI", "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME",
    "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM",
    "NV", "NY", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX",
    "UT", "VA", "VT", "WA", "WI", "WV", "WY",
}
_INTEGER = re.compile(r"^\d+$")


def normalize_state_hpi_csv(path: str | Path) -> FHFAHPIResult:
    """Read the official headerless four-column state HPI CSV and validate it."""

    source = Path(path)
    if not source.is_file():
        raise FHFAHPIError("FHFA HPI source CSV does not exist")

    records: list[tuple[str, int, int, float]] = []
    keys: set[tuple[str, int, int]] = set()
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as stream:
            for line_number, row in enumerate(csv.reader(stream), start=1):
                if len(row) != 4:
                    raise FHFAHPIError(f"Expected 4 columns at source row {line_number}")
                state_code, year_text, quarter_text, value_text = [v.strip() for v in row]
                if state_code not in _STATE_CODES:
                    raise FHFAHPIError(f"Invalid state/DC code at source row {line_number}")
                if not _INTEGER.fullmatch(year_text) or not _INTEGER.fullmatch(quarter_text):
                    raise FHFAHPIError(f"Year/quarter must be integers at source row {line_number}")
                year, quarter = int(year_text), int(quarter_text)
                if year < 1975 or quarter not in {1, 2, 3, 4}:
                    raise FHFAHPIError(f"Year/quarter is outside expected range at source row {line_number}")
                try:
                    index_value = float(value_text)
                except ValueError as exc:
                    raise FHFAHPIError(f"Index value is not numeric at source row {line_number}") from exc
                if not index_value > 0 or index_value == float("inf"):
                    raise FHFAHPIError(f"Index value must be positive and finite at source row {line_number}")
                key = (state_code, year, quarter)
                if key in keys:
                    raise FHFAHPIError(f"Duplicate state-period key at source row {line_number}")
                keys.add(key)
                records.append((state_code, year, quarter, index_value))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise FHFAHPIError("Source is not valid UTF-8 CSV") from exc

    if not records:
        raise FHFAHPIError("FHFA HPI source CSV is empty")
    places = {row[0] for row in records}
    periods = sorted({(row[1], row[2]) for row in records})
    if places != _STATE_CODES:
        raise FHFAHPIError("Source must contain all 50 states and DC")
    expected_periods = [
        (year, quarter)
        for year in range(periods[0][0], periods[-1][0] + 1)
        for quarter in range(1, 5)
        if (year, quarter) >= periods[0] and (year, quarter) <= periods[-1]
    ]
    if periods != expected_periods:
        raise FHFAHPIError("Quarterly source periods contain a gap")
    expected_keys = len(places) * len(periods)
    if len(records) != expected_keys:
        raise FHFAHPIError("State-period panel is unbalanced or contains missing values")

    # Source order is geography-major; output order is deterministic geography then period.
    records.sort(key=lambda row: (row[0], row[1], row[2]))
    first_period = f"{periods[0][0]}Q{periods[0][1]}"
    latest_period = f"{periods[-1][0]}Q{periods[-1][1]}"
    return FHFAHPIResult(tuple(records), len(places), first_period, latest_period)


_US_CENSUS_CODES = {
    "USA", "DV_ENC", "DV_ESC", "DV_MA", "DV_MT", "DV_NE", "DV_PAC",
    "DV_SA", "DV_WNC", "DV_WSC",
}


def normalize_us_census_hpi_csv(path: str | Path) -> FHFAUSCensusHPIResult:
    """Validate FHFA's headerless quarterly U.S. and Census Division file."""

    source = Path(path)
    if not source.is_file():
        raise FHFAHPIError("FHFA U.S./Census HPI source CSV does not exist")

    records: list[tuple[str, int, int, float]] = []
    keys: set[tuple[str, int, int]] = set()
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as stream:
            for line_number, row in enumerate(csv.reader(stream), start=1):
                if len(row) != 4:
                    raise FHFAHPIError(f"Expected 4 columns at source row {line_number}")
                geography, year_text, quarter_text, value_text = [value.strip() for value in row]
                if geography not in _US_CENSUS_CODES:
                    raise FHFAHPIError(f"Unexpected U.S./Census geography at source row {line_number}")
                if not _INTEGER.fullmatch(year_text) or not _INTEGER.fullmatch(quarter_text):
                    raise FHFAHPIError(f"Year/quarter must be integers at source row {line_number}")
                year, quarter = int(year_text), int(quarter_text)
                if year < 1975 or quarter not in {1, 2, 3, 4}:
                    raise FHFAHPIError(f"Year/quarter is outside expected range at source row {line_number}")
                try:
                    index_value = float(value_text)
                except ValueError as exc:
                    raise FHFAHPIError(f"Index value is not numeric at source row {line_number}") from exc
                if not index_value > 0 or index_value == float("inf"):
                    raise FHFAHPIError(f"Index value must be positive and finite at source row {line_number}")
                key = (geography, year, quarter)
                if key in keys:
                    raise FHFAHPIError(f"Duplicate geography-period key at source row {line_number}")
                keys.add(key)
                records.append((geography, year, quarter, index_value))
    except (UnicodeDecodeError, csv.Error) as exc:
        raise FHFAHPIError("Source is not valid UTF-8 CSV") from exc

    if not records:
        raise FHFAHPIError("FHFA U.S./Census HPI source CSV is empty")
    geographies = {row[0] for row in records}
    if geographies != _US_CENSUS_CODES:
        raise FHFAHPIError("Source must contain U.S. and all nine Census Divisions")
    periods_by_geography = {
        geography: {(year, quarter) for code, year, quarter, _ in records if code == geography}
        for geography in _US_CENSUS_CODES
    }
    first_period = min(min(periods) for periods in periods_by_geography.values())
    latest_period = max(max(periods) for periods in periods_by_geography.values())
    expected_periods = {
        (year, quarter)
        for year in range(first_period[0], latest_period[0] + 1)
        for quarter in range(1, 5)
        if first_period <= (year, quarter) <= latest_period
    }
    if any(periods != expected_periods for periods in periods_by_geography.values()):
        raise FHFAHPIError("U.S./Census quarterly periods contain gaps or differ by geography")
    if len(records) != len(_US_CENSUS_CODES) * len(expected_periods):
        raise FHFAHPIError("U.S./Census panel is unbalanced")

    records.sort(key=lambda row: (row[0], row[1], row[2]))
    return FHFAUSCensusHPIResult(
        tuple(records), len(geographies), len(expected_periods),
        f"{first_period[0]}Q{first_period[1]}",
        f"{latest_period[0]}Q{latest_period[1]}",
    )
