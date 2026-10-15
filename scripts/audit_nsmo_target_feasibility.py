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


def _quarter_ordinal(index: int) -> int:
    # Performance columns are ordered from March 2013, then June, September,
    # December. Index 0 therefore maps to YYYY=2013, MM=3.
    month = 3 + (index % 4) * 3
    year = 2013 + index // 4
    return year * 12 + month


def _close_ordinal(year_text: str, month_text: str) -> int | None:
    try:
        year, month = int(year_text), int(month_text)
    except ValueError:
        return None
    if year < 1900 or not 1 <= month <= 12:
        return None
    return year * 12 + month


def audit(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        pos = {name.casefold(): i for i, name in enumerate(headers)}
        status_cols = sorted((h for h in headers if h.casefold().startswith("perf_status_")), key=parse_performance_column)
        if len(headers) != 587 or len(status_cols) != 51:
            raise ValueError("Expected the reconciled 587-column NSMO v7.0 PUF")
        indices = [pos[c.casefold()] for c in status_cols]
        close_status_i = pos["close_status_0925"]
        close_year_i, close_month_i = pos["close_year"], pos["close_month"]
        weight_i = pos["analysis_weight"]
        quarter_ends = [parse_performance_column(c).isoformat() for c in status_cols]
        counts: dict[tuple[int, str], Counter] = defaultdict(Counter)
        weight_sums: dict[tuple[int, str], Counter] = defaultdict(Counter)
        rows = width_errors = 0
        for row in reader:
            rows += 1
            if len(row) != len(headers):
                width_errors += 1
                continue
            try:
                weight = float(row[weight_i])
            except ValueError:
                weight = 0.0
            if weight <= 0:
                weight = 0.0
            close_status = row[close_status_i].strip()
            close = _close_ordinal(row[close_year_i].strip(), row[close_month_i].strip()) if close_status in {"2", "3", "4"} else None
            states = [row[i].strip().upper() for i in indices]
            for baseline_i, baseline_status in enumerate(states):
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
    return {
        "schema_version": "nsmo-target-feasibility-v1",
        "status": "PASS" if rows == 62359 and not width_errors else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "source": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
        "schema": {"rows": rows, "columns": 587, "quarterly_status_columns": 51},
        "candidate_definition_for_feasibility_only": {
            "baseline_states": {k: v for k, v in BASELINES.items()},
            "horizon": "next four quarterly snapshots (~12 months)",
            "primary_event_codes": ["3", "4", "5", "6"],
            "separate_other_adverse_codes": ["7", "8", "9"],
            "same-month termination": "ambiguous ordering; censored separately",
            "weights": "unweighted counts plus baseline descriptive weight sums; no variance estimator",
        },
        "width_errors": width_errors,
        "baseline_quarter_state_aggregates": out,
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
