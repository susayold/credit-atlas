"""Aggregate-only feasibility screen for a candidate NSMO 12-month endpoint.

This does not create target labels, PD estimates, or a model dataset. It counts
quarterly baseline snapshots and the first observable outcome/censoring reason.
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
PRIMARY_EVENT = set("3456")  # 90+ days past due, based on official SAS labels
OTHER_ADVERSE = set("789")
BASELINES = {"C": "current", "1": "1_month_past_due", "2": "2_months_past_due"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def classify_followup(statuses: list[str], close_ordinal: int | None,
                      baseline_index: int, horizon: int = 4) -> str:
    """Classify an observed sequence conservatively; same-month close is ambiguous.

    Quarter ordinals are YYYY*12+MM. A close in the same month as a quarter-end
    cannot be ordered against that quarter's snapshot because close day is absent.
    """
    if baseline_index + horizon >= len(statuses):
        return "administratively_short_followup"
    for step in range(1, horizon + 1):
        q_index = baseline_index + step
        q_ordinal = _quarter_ordinal(q_index)
        status = statuses[q_index]
        if close_ordinal is not None and close_ordinal <= q_ordinal:
            return "termination_same_month_ambiguous" if close_ordinal == q_ordinal else "termination_competing_censor"
        if status in PRIMARY_EVENT:
            return "observed_90plus_event"
        if status in OTHER_ADVERSE:
            return f"observed_other_adverse_state_{status}"
        if status not in OBSERVED:
            return f"observation_censor_{status or 'blank'}"
    return "four_quarters_observed_no_event"


def first_eligible_c_landmark(statuses: list[str], close_ordinal: int | None,
                              open_year: int, open_month: int,
                              horizon: int = 4) -> tuple[int, str] | None:
    """Choose one earliest fully-followed C landmark per mortgage for support checks.

    This is a diagnostic anchor only. It does not freeze cohort eligibility or
    create a target label.
    """
    first_post_open = _first_post_open_index(open_year, open_month, len(statuses))
    for baseline_index in range(first_post_open, len(statuses)):
        status = statuses[baseline_index]
        if status != "C":
            continue
        if baseline_index + horizon >= len(statuses):
            break
        if close_ordinal is not None and close_ordinal <= _quarter_ordinal(baseline_index):
            continue
        return baseline_index, classify_followup(statuses, close_ordinal, baseline_index, horizon)
    return None


def same_month_close_snapshot_status(statuses: list[str], close_ordinal: int | None,
                                     baseline_index: int, horizon: int = 4) -> str | None:
    """Expose the quarter snapshot status when close month ties that quarter.

    The returned status is an ambiguity diagnostic only: the file has no day of
    month, so it cannot order that snapshot against the termination.
    """
    if close_ordinal is None or baseline_index + horizon >= len(statuses):
        return None
    for step in range(1, horizon + 1):
        q_index = baseline_index + step
        q_ordinal = _quarter_ordinal(q_index)
        if close_ordinal <= q_ordinal:
            return statuses[q_index] if close_ordinal == q_ordinal else None
    return None


def _quarter_ordinal(index: int) -> int:
    # Performance columns are ordered from March 2013, then June, September,
    # December. Index 0 therefore maps to YYYY=2013, MM=3.
    month = 3 + (index % 4) * 3
    year = 2013 + index // 4
    return year * 12 + month


def _first_post_open_index(open_year: int, open_month: int,
                           status_count: int = 51) -> int:
    """First quarter-end strictly after the quarter containing origination.

    Origination is reported only at month grain, so a snapshot in the same
    quarter cannot be ordered reliably relative to the opening date.
    """
    open_quarter_end = open_year * 12 + ((open_month - 1) // 3 + 1) * 3
    return next((i for i in range(status_count)
                 if _quarter_ordinal(i) > open_quarter_end), status_count)


def _close_ordinal(year_text: str, month_text: str) -> int | None:
    try:
        year, month = int(year_text), int(month_text)
    except ValueError:
        return None
    if year < 1900 or not 1 <= month <= 12:
        return None
    return year * 12 + month


def _commit_unique_vintage_support(row_outcomes: set[tuple[tuple[str, str], str]],
                                   unique_baselines: Counter,
                                   unique_outcomes: dict[tuple[str, str], Counter]) -> None:
    """Count each mortgage once per vintage/state and observed outcome class."""
    for key in {group for group, _ in row_outcomes}:
        unique_baselines[key] += 1
    for key, outcome in row_outcomes:
        unique_outcomes[key][outcome] += 1


def audit(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        pos = {name.casefold(): i for i, name in enumerate(headers)}
        status_cols = sorted((h for h in headers if h.casefold().startswith("perf_status_")), key=parse_performance_column)
        if len(headers) != 587 or len(status_cols) != 51:
            raise ValueError("Expected the reconciled 587-column NSMO v7.0 PUF")
        indices = [pos[c.casefold()] for c in status_cols]
        id_i = pos.get("nsmoid")
        if id_i is None:
            raise ValueError("NSMOID is required to verify one record per mortgage")
        close_status_i = pos["close_status_0925"]
        close_year_i, close_month_i = pos["close_year"], pos["close_month"]
        open_year_i, open_month_i = pos["open_year"], pos["open_month"]
        weight_i = pos["analysis_weight"]
        vintage_i = pos["open_year"]
        quarter_ends = [parse_performance_column(c).isoformat() for c in status_cols]
        counts: dict[tuple[int, str], Counter] = defaultdict(Counter)
        weight_sums: dict[tuple[int, str], Counter] = defaultdict(Counter)
        vintage_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
        vintage_weight_sums: dict[tuple[str, str], Counter] = defaultdict(Counter)
        vintage_unique_baselines: Counter[tuple[str, str]] = Counter()
        vintage_unique_outcomes: dict[tuple[str, str], Counter] = defaultdict(Counter)
        same_month_status_counts: dict[str, Counter] = defaultdict(Counter)
        same_month_vintage_status_counts: dict[tuple[str, str], Counter] = defaultdict(Counter)
        first_c_landmark_by_vintage: dict[str, Counter] = defaultdict(Counter)
        first_c_landmark_by_quarter: dict[tuple[str, str], Counter] = defaultdict(Counter)
        first_c_landmark_weights: dict[str, Counter] = defaultdict(Counter)
        seen_ids: set[str] = set()
        rows = width_errors = missing_ids = duplicate_ids = invalid_open_dates = 0
        for row in reader:
            rows += 1
            if len(row) != len(headers):
                width_errors += 1
                continue
            loan_id = row[id_i].strip()
            if not loan_id:
                missing_ids += 1
                continue
            if loan_id in seen_ids:
                duplicate_ids += 1
                continue
            seen_ids.add(loan_id)
            try:
                weight = float(row[weight_i])
            except ValueError:
                weight = 0.0
            if weight <= 0:
                weight = 0.0
            close_status = row[close_status_i].strip()
            close = _close_ordinal(row[close_year_i].strip(), row[close_month_i].strip()) if close_status in {"2", "3", "4"} else None
            try:
                open_year, open_month = int(row[open_year_i]), int(row[open_month_i])
            except ValueError:
                invalid_open_dates += 1
                continue
            if not 1900 <= open_year <= 2100 or not 1 <= open_month <= 12:
                invalid_open_dates += 1
                continue
            vintage = row[vintage_i].strip()
            if not vintage.isdigit() or not 2013 <= int(vintage) <= 2024:
                vintage = "unknown"
            states = [row[i].strip().upper() for i in indices]
            first_landmark = first_eligible_c_landmark(
                states, close, open_year, open_month
            )
            if first_landmark is not None:
                baseline_index, first_result = first_landmark
                first_c_landmark_by_vintage[vintage][first_result] += 1
                first_c_landmark_by_quarter[(quarter_ends[baseline_index], vintage)][first_result] += 1
                first_c_landmark_weights[vintage][first_result] += weight
            unique_baseline_outcomes: set[tuple[tuple[str, str], str]] = set()
            first_post_open = _first_post_open_index(open_year, open_month, len(states))
            for baseline_i in range(first_post_open, len(states)):
                baseline_status = states[baseline_i]
                if baseline_status not in BASELINES:
                    continue
                key = (baseline_i, baseline_status)
                counts[key]["eligible_snapshot"] += 1
                weight_sums[key]["eligible_snapshot"] += weight
                # A loan closed by the baseline quarter-end is not considered at risk.
                baseline_ord = _quarter_ordinal(baseline_i)
                if close is not None and close <= baseline_ord:
                    result = "not_open_at_baseline"
                else:
                    result = classify_followup(states, close, baseline_i)
                counts[key][result] += 1
                weight_sums[key][result] += weight
                if result == "termination_same_month_ambiguous":
                    tied_status = same_month_close_snapshot_status(states, close, baseline_i) or "<BLANK>"
                    same_month_status_counts[baseline_status][tied_status] += 1
                    same_month_vintage_status_counts[(vintage, baseline_status)][tied_status] += 1
                # The distinct-loan support screen uses only baselines with a
                # complete four-quarter window in the PUF. The same loan may
                # contribute multiple snapshots, so unique outcomes are
                # de-duplicated within loan × vintage × baseline state × class.
                if baseline_i + 4 < len(status_cols):
                    vintage_key = (vintage, baseline_status)
                    vintage_counts[vintage_key][result] += 1
                    vintage_weight_sums[vintage_key][result] += weight
                    unique_baseline_outcomes.add((vintage_key, result))
            _commit_unique_vintage_support(
                unique_baseline_outcomes, vintage_unique_baselines,
                vintage_unique_outcomes,
            )
        out = []
        for (i, state), counter in sorted(counts.items()):
            outcome_weight_sums = {
                name: round(value, 2)
                for name, value in sorted(weight_sums[(i, state)].items())
                if name != "eligible_snapshot"
            }
            out.append({
                "baseline_quarter": quarter_ends[i],
                "baseline_state": state,
                "baseline_state_label": BASELINES[state],
                "full_12m_snapshot_horizon_available": i + 4 < len(status_cols),
                "outcomes_unweighted": dict(sorted(counter.items())),
                "outcome_weight_sums_descriptive_only": outcome_weight_sums,
                "baseline_weight_sum_descriptive_only": round(weight_sums[(i, state)]["eligible_snapshot"], 2),
            })
        vintage_out = []
        for (vintage, state), counter in sorted(vintage_counts.items()):
            key = (vintage, state)
            vintage_out.append({
                "origination_year": vintage,
                "baseline_state": state,
                "full_horizon_baseline_snapshots_unweighted": dict(sorted(counter.items())),
                "unique_mortgages_with_at_least_one_full_horizon_baseline": vintage_unique_baselines[key],
                "unique_mortgages_by_snapshot_outcome_class_nonexclusive": dict(sorted(vintage_unique_outcomes[key].items())),
                "snapshot_outcome_weight_sums_descriptive_only": {
                    name: round(value, 2)
                    for name, value in sorted(vintage_weight_sums[key].items())
                },
            })
        same_month_by_vintage = [
            {"origination_year": vintage, "baseline_state": state,
             "snapshot_status_counts_unweighted": dict(sorted(counter.items()))}
            for (vintage, state), counter in sorted(same_month_vintage_status_counts.items())
        ]
        first_c_vintage_out = []
        for vintage, counter in sorted(first_c_landmark_by_vintage.items()):
            first_c_vintage_out.append({
                "origination_year": vintage,
                "unique_mortgage_count": sum(counter.values()),
                "first_eligible_c_landmark_outcomes_unweighted": dict(sorted(counter.items())),
                "outcome_weight_sums_descriptive_only": {
                    name: round(value, 2)
                    for name, value in sorted(first_c_landmark_weights[vintage].items())
                },
            })
        first_c_quarter_out = [
            {
                "landmark_quarter": quarter,
                "origination_year": vintage,
                "unique_mortgage_count": sum(counter.values()),
                "outcomes_unweighted": dict(sorted(counter.items())),
            }
            for (quarter, vintage), counter in sorted(first_c_landmark_by_quarter.items())
        ]
    return {
        "schema_version": "nsmo-target-feasibility-v1",
        "status": "PASS" if rows == 62359 and len(seen_ids) == rows and not (
            width_errors or missing_ids or duplicate_ids or invalid_open_dates
        ) else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "source": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
        "schema": {"rows": rows, "columns": 587, "quarterly_status_columns": 51},
        "candidate_definition_for_feasibility_only": {
            "baseline_states": {k: v for k, v in BASELINES.items()},
            "origination_timing": "only quarter-end snapshots strictly after the quarter containing the reported origination month are eligible; within-quarter ordering is unavailable",
            "horizon": "next four quarterly snapshots (~12 months)",
            "primary_event_codes": ["3", "4", "5", "6"],
            "separate_other_adverse_codes": ["7", "8", "9"],
            "same-month termination": "ambiguous ordering; censored separately",
            "weights": "unweighted counts plus baseline descriptive weight sums; no variance estimator",
        },
        "integrity": {"width_errors": width_errors, "missing_ids": missing_ids,
                      "duplicate_ids": duplicate_ids,
                      "invalid_open_dates": invalid_open_dates,
                      "unique_mortgages": len(seen_ids)},
        "baseline_quarter_state_aggregates": out,
        "origination_vintage_baseline_aggregates": vintage_out,
        "same_month_ambiguous_snapshot_status_counts_by_baseline_state": {
            state: dict(sorted(counter.items())) for state, counter in sorted(same_month_status_counts.items())
        },
        "same_month_ambiguous_snapshot_status_counts_by_vintage_and_baseline_state": same_month_by_vintage,
        "one_landmark_per_mortgage_support": {
            "selection_rule": "earliest C snapshot strictly after the quarter containing origination, with a full four-quarter horizon, excluding known closed-by-baseline loans",
            "target_created": False,
            "outcomes_by_origination_vintage": first_c_vintage_out,
            "outcomes_by_landmark_quarter_and_vintage": first_c_quarter_out,
        },
        "target_created": False,
        "limitations": [
            "Feasibility counts only; no row-level labels, rates, PD, model matrix, or target file is created.",
            "Quarterly snapshots can miss within-quarter delinquency; exact event dates are unavailable.",
            "Termination cause is unknown. Close year/month cannot order an event and termination in the same month.",
            "Admin/non-observation codes censor follow-up; no imputation to performing is allowed.",
            "Repeated quarterly baselines can include the same mortgage; observations are not independent.",
            "Weights are descriptive sums only; design strata, replicate weights, variance, and inference are not specified.",
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
    print(json.dumps({"status": result["status"], "rows": result["schema"]["rows"], "aggregate_cells": len(result["baseline_quarter_state_aggregates"]), "receipt": str(args.output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
