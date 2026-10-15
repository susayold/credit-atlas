"""Aggregate-only feasibility screen for an origination-anchored NSMO endpoint.

This diagnostic does not create target labels, PD estimates, or a model dataset.
It excludes the quarter in which the mortgage opened (coded Q) and examines
quarter-end snapshots within the following 12 calendar months.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from credit_atlas.nsmo import parse_performance_column


OBSERVED = set("C123456789")
PRIMARY_EVENT = set("3456")
OTHER_ADVERSE = set("789")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _month_ordinal(year: int, month: int) -> int:
    return year * 12 + month


def _quarter_months_after_open(year: int, month: int, quarter_ends: list[tuple[int, int]]) -> tuple[int, list[int]]:
    """Return the open-quarter ordinal and observed quarter indices in 12m.

    `open_month` has month, not day, precision. The quarter containing the
    opening month is excluded because FHFA codes it Q (opened during quarter),
    not as a performance observation. The diagnostic then includes reported
    quarter ends strictly after that quarter and no later than open month + 12.
    """
    opening = _month_ordinal(year, month)
    opening_quarter = next(
        (ordinal for ordinal, _ in quarter_ends if ordinal >= opening
         and ordinal // 12 == year and ordinal % 12 in {3, 6, 9}),
        None,
    )
    # December is ordinal year*12+12, whose modulo is 0.
    if opening_quarter is None:
        opening_quarter = next(
            (ordinal for ordinal, _ in quarter_ends if ordinal >= opening
             and (ordinal % 12 in {3, 6, 9} or ordinal % 12 == 0)),
            None,
        )
    if opening_quarter is None:
        return -1, []
    horizon_end = opening + 12
    indices = [i for i, (ordinal, _) in enumerate(quarter_ends)
               if opening_quarter < ordinal <= horizon_end]
    return opening_quarter, indices


def _expected_followup_quarters(opening_quarter: int, horizon_end: int) -> list[int]:
    """Quarter-end month ordinals expected after opening quarter, through +12m."""
    result = []
    rem = opening_quarter % 12
    year = opening_quarter // 12
    if rem == 0:
        year -= 1
        month = 12
    else:
        month = rem
    while True:
        month += 3
        if month > 12:
            year += 1
            month -= 12
        ordinal = _month_ordinal(year, month)
        if ordinal > horizon_end:
            return result
        result.append(ordinal)


def classify_origination_followup(
    observations: list[tuple[int, str]],
    expected_quarters: list[int],
    available_quarters: set[int],
    close_ordinal: int | None,
) -> str:
    """Classify first observed outcome/censor without converting gaps to good."""
    seen_quarters = {quarter for quarter, _ in observations}
    for quarter, raw_status in observations:
        status = raw_status.strip().upper()
        if close_ordinal is not None and close_ordinal <= quarter:
            return "termination_same_month_ambiguous" if close_ordinal == quarter else "termination_competing_censor"
        if status in PRIMARY_EVENT:
            return "observed_90plus"
        if status in OTHER_ADVERSE:
            return f"observed_other_adverse_state_{status}"
        if status not in OBSERVED:
            return f"observation_censor_{status or 'blank'}"
    if any(quarter not in available_quarters for quarter in expected_quarters):
        return "administratively_short_followup"
    if not expected_quarters or not set(expected_quarters).issubset(seen_quarters):
        return "administratively_short_followup"
    return "all_in_window_snapshots_observed_no_90plus"


def audit(path: Path) -> dict:
    overall: Counter[str] = Counter()
    by_vintage: dict[str, Counter[str]] = defaultdict(Counter)
    followup_count_by_vintage: dict[str, Counter[str]] = defaultdict(Counter)
    invalid_dates = width_errors = rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        position = {name.casefold(): i for i, name in enumerate(headers)}
        if len(headers) != 587:
            raise ValueError("Expected the reconciled 587-column NSMO v7.0 PUF")
        status_columns = sorted(
            (name for name in headers if name.casefold().startswith("perf_status_")),
            key=parse_performance_column,
        )
        if len(status_columns) != 51:
            raise ValueError("Expected 51 quarterly performance snapshots")
        quarter_ends = [
            (_month_ordinal(date.year, date.month), position[name.casefold()])
            for name in status_columns
            for date in [parse_performance_column(name)]
        ]
        available_quarters = {ordinal for ordinal, _ in quarter_ends}
        open_year_i, open_month_i = position["open_year"], position["open_month"]
        close_status_i = position["close_status_0925"]
        close_year_i, close_month_i = position["close_year"], position["close_month"]

        for row in reader:
            rows += 1
            if len(row) != len(headers):
                width_errors += 1
                continue
            try:
                year, month = int(row[open_year_i]), int(row[open_month_i])
            except ValueError:
                invalid_dates += 1
                overall["invalid_origination_month"] += 1
                continue
            if not 2013 <= year <= 2024 or not 1 <= month <= 12:
                invalid_dates += 1
                overall["invalid_origination_month"] += 1
                continue

            opening, indices = _quarter_months_after_open(year, month, quarter_ends)
            if opening < 0:
                invalid_dates += 1
                overall["missing_open_quarter_in_source"] += 1
                continue
            horizon_end = _month_ordinal(year, month) + 12
            expected = _expected_followup_quarters(opening, horizon_end)
            vintage = str(year)
            followup_count_by_vintage[vintage][f"source_quarters_within_month_window_{len(indices)}"] += 1
            observations = [
                (quarter_ends[index][0], row[quarter_ends[index][1]].strip())
                for index in indices
            ]
            close = None
            if row[close_status_i].strip() in {"2", "3", "4"}:
                try:
                    close_year, close_month = int(row[close_year_i]), int(row[close_month_i])
                    if close_year >= 1900 and 1 <= close_month <= 12:
                        close = _month_ordinal(close_year, close_month)
                except ValueError:
                    pass
            result = classify_origination_followup(
                observations, expected, available_quarters, close
            )
            overall[result] += 1
            by_vintage[vintage][result] += 1

    classified_rows = sum(overall.values())
    vintage_rows = sum(sum(counts.values()) for counts in by_vintage.values())
    reconciliation = {
        "source_rows": rows,
        "classified_rows": classified_rows,
        "origination_vintage_rows": vintage_rows,
        "reconciles": not width_errors and not invalid_dates and rows == classified_rows == vintage_rows,
    }
    return {
        "schema_version": "nsmo-origination-feasibility-v1",
        "status": "PASS" if rows == 62359 and reconciliation["reconciles"] else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "source": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
        "schema": {"rows": rows, "columns": len(headers), "quarterly_status_columns": len(status_columns)},
        "candidate_definition_for_feasibility_only": {
            "anchor": "open_year/open_month, month precision",
            "exclude": "quarter containing origination; FHFA status Q means loan opened during quarter",
            "follow_up_window": "quarter-end snapshots strictly after origination quarter and through open month + 12 months",
            "primary_event_codes": ["3", "4", "5", "6"],
            "separate_other_adverse_codes": ["7", "8", "9"],
            "termination": "same-month ordering ambiguous; earlier close is a competing censor",
            "weights": "unweighted support counts only; no design variance or population rate",
        },
        "outcomes_unweighted": dict(sorted(overall.items())),
        "reconciliation": reconciliation,
        "outcomes_by_origination_year_unweighted": {
            year: dict(sorted(counts.items())) for year, counts in sorted(by_vintage.items())
        },
        "available_snapshot_count_by_origination_year_unweighted": {
            year: dict(sorted(counts.items()))
            for year, counts in sorted(followup_count_by_vintage.items())
        },
        "target_created": False,
        "limitations": [
            "This is an aggregate feasibility diagnostic; it creates no row-level target, PD, rate, or model matrix.",
            "Origination day is unavailable, so the 12-month boundary is month-precision and quarter-end sampled.",
            "Quarterly snapshots can miss delinquency between reporting dates; 90+ codes are observed status proxies, not event dates.",
            "Closed-loan cause is unknown; same-month closure and snapshot ordering is ambiguous.",
            "Non-observation and administrative truncation remain separate from no observed 90+ status.",
            "Unweighted support counts are not population estimates; the analysis weight is not used and design variance is unavailable.",
            "The public-use survey sample and response process do not establish a production mortgage application population.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--puf-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.puf_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rows": result["schema"]["rows"],
                      "outcome_classes": len(result["outcomes_unweighted"]),
                      "receipt": str(args.output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
