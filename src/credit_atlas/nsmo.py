"""Codebook-grounded helpers for the FHFA/CFPB NSMO public-use file.

These helpers preserve observed quarterly status semantics. They deliberately do
not define a PD target or equate non-observation with a performing loan.
"""

from __future__ import annotations

import csv
import math
import re
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any, Mapping


_PERFORMANCE_COLUMN = re.compile(r"^Perf_Status_(\d{2})(\d{2})$", re.IGNORECASE)
_PERFORMANCE_CODES: dict[str, tuple[str, int | None, int | None]] = {
    "1": ("delinquent_30_59_dpd", 30, 59),
    "2": ("delinquent_60_89_dpd", 60, 89),
    "3": ("delinquent_90_119_dpd", 90, 119),
    "4": ("delinquent_120_149_dpd", 120, 149),
    "5": ("delinquent_150_179_dpd", 150, 179),
    "6": ("delinquent_180_plus_dpd", 180, None),
    "7": ("bankruptcy_chapter_13", None, None),
    "8": ("foreclosure_or_distressed_disposition", None, None),
    "9": ("other_adverse_or_chargeoff", None, None),
    "A": ("history_no_longer_reported", None, None),
    "B": ("potentially_closed", None, None),
    "C": ("current", None, None),
    "K": ("opened_not_yet_reported", None, None),
    "M": ("missing_archive_gap", None, None),
    "P": ("pre_open", None, None),
    "Q": ("opened_during_quarter", None, None),
    "S": ("servicer_suppressed", None, None),
}

# These are source fields to assess after ingestion, not a final feature allowlist.
NSMO_ORIGINATION_CANDIDATES = (
    "Open_Year",
    "Open_Month",
    "Loan_Amount_Cat",
    "Jumbo",
    "Rate_Spread",
    "PMMS",
    "Term",
    "LTV",
    "CLTV",
    "DTI",
    "PTI",
    "Loan_Type",
    "GSE",
    "Metro_LMI",
    "Borrower_Num",
    "First_Mort_R",
    "Score_Orig_R",
    "Score_Orig_S",
)


def _empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and value.strip() == ""


def decode_performance_code(value: Any) -> dict[str, Any]:
    """Decode one codebook status without collapsing adverse or censored states."""
    if _empty(value):
        return {
            "raw_status": None,
            "status_family": "blank_or_missing_code",
            "dpd_low": None,
            "dpd_high": None,
            "observation_available": False,
        }

    if isinstance(value, float) and value.is_integer():
        raw = str(int(value))
    else:
        raw = str(value).strip().upper()
    if raw not in _PERFORMANCE_CODES:
        raise ValueError(f"Unknown NSMO performance status code: {raw!r}")
    family, low, high = _PERFORMANCE_CODES[raw]
    return {
        "raw_status": raw,
        "status_family": family,
        "dpd_low": low,
        "dpd_high": high,
        "observation_available": family not in {
            "history_no_longer_reported",
            "potentially_closed",
            "opened_not_yet_reported",
            "missing_archive_gap",
            "pre_open",
            "servicer_suppressed",
        },
    }


def parse_performance_column(column: str) -> date:
    """Return the quarter-end date encoded by a Perf_Status_MMYY column."""
    match = _PERFORMANCE_COLUMN.fullmatch(column)
    if not match:
        raise ValueError(f"Not an NSMO quarterly performance column: {column!r}")
    month, short_year = (int(part) for part in match.groups())
    if month not in {3, 6, 9, 12}:
        raise ValueError(f"NSMO performance month must be quarter-end month: {column!r}")
    year = 2000 + short_year
    day = monthrange(year, month)[1]
    return date(year, month, day)


def wide_performance_to_long(
    record: Mapping[str, Any], *, id_column: str = "NSMOID"
) -> list[dict[str, Any]]:
    """Convert one wide NSMO row to ordered quarterly observations.

    Blank/missing status values remain explicit non-observations. The returned
    rows contain no synthesized outcome, PD, or competing-risk label.
    """
    if id_column not in record or _empty(record[id_column]):
        raise ValueError(f"Missing public-use loan identifier column {id_column!r}")
    columns = sorted(
        (column for column in record if _PERFORMANCE_COLUMN.fullmatch(column)),
        key=parse_performance_column,
    )
    if not columns:
        raise ValueError("No quarterly NSMO Perf_Status_MMYY fields found")

    loan_id = str(record[id_column]).strip()
    observations = []
    for column in columns:
        observations.append(
            {
                "nsmoid": loan_id,
                "observation_date": parse_performance_column(column).isoformat(),
                "source_column": column,
                **decode_performance_code(record[column]),
            }
        )
    return observations


def iter_nsmo_performance_csv(
    path: str | Path,
    *,
    id_column: str = "NSMOID",
    encoding: str = "utf-8-sig",
):
    """Stream a wide PUF CSV into quarterly rows, rejecting ambiguous input.

    The ID uniqueness set is intentionally held in memory (expected tens of
    thousands of loan IDs, not millions of monthly observations). Rows are
    yielded only after their status values have been validated.
    """
    with Path(path).open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate NSMO CSV column names")
        if id_column not in headers:
            raise ValueError(f"Missing public-use loan identifier column {id_column!r}")
        performance_columns = sorted(
            (column for column in headers if _PERFORMANCE_COLUMN.fullmatch(column)),
            key=parse_performance_column,
        )
        if not performance_columns:
            raise ValueError("No quarterly NSMO Perf_Status_MMYY fields found")

        seen_ids: set[str] = set()
        for row_number, record in enumerate(reader, start=2):
            loan_id = record.get(id_column)
            if _empty(loan_id):
                raise ValueError(f"Missing {id_column} at CSV row {row_number}")
            loan_id = str(loan_id).strip()
            if loan_id in seen_ids:
                raise ValueError(f"Duplicate {id_column} {loan_id!r} at CSV row {row_number}")
            seen_ids.add(loan_id)
            for column in performance_columns:
                try:
                    decoded = decode_performance_code(record.get(column))
                except ValueError as error:
                    raise ValueError(f"Invalid {column} at CSV row {row_number}: {error}") from error
                yield {
                    "nsmoid": loan_id,
                    "observation_date": parse_performance_column(column).isoformat(),
                    "source_column": column,
                    **decoded,
                }
