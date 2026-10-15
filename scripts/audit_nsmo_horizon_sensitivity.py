"""Aggregate-only NSMO C-state horizon sensitivity screen.

Counts observed 90+ endpoint feasibility at 2, 4, and 8 following quarterly
snapshots. This is not a target-label or model-building pipeline.
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

try:
    from scripts.audit_nsmo_target_feasibility import (
        OBSERVED, PRIMARY_EVENT, OTHER_ADVERSE, _close_ordinal,
        _quarter_ordinal, classify_followup,
    )
except ModuleNotFoundError:  # direct execution puts scripts/ on sys.path
    from audit_nsmo_target_feasibility import (
        OBSERVED, PRIMARY_EVENT, OTHER_ADVERSE, _close_ordinal,
        _quarter_ordinal, classify_followup,
    )


HORIZONS = (2, 4, 8)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _classify(statuses: list[str], close_ordinal: int | None,
              baseline_index: int, horizon: int) -> str:
    outcome = classify_followup(statuses, close_ordinal, baseline_index, horizon)
    if outcome == "four_quarters_observed_no_event":
        return f"observed_no_90plus_within_{horizon}_quarters"
    return outcome


def audit(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        positions = {name.casefold(): index for index, name in enumerate(headers)}
        status_cols = sorted(
            (name for name in headers if name.casefold().startswith("perf_status_")),
            key=parse_performance_column,
        )
        if len(headers) != 587 or len(status_cols) != 51:
            raise ValueError("Expected the reconciled 587-column NSMO v7.0 PUF")
        # The published identifier is NSMOID; casefolding preserves its spelling.
        id_i = positions.get("nsmoid")
        if id_i is None:
            raise ValueError("NSMOID column is required for unique-mortgage support counts")
        close_status_i = positions["close_status_0925"]
        close_year_i, close_month_i = positions["close_year"], positions["close_month"]
        open_year_i = positions["open_year"]
        status_indices = [positions[name.casefold()] for name in status_cols]

        counts: dict[int, Counter] = {horizon: Counter() for horizon in HORIZONS}
        unique_outcomes: dict[int, dict[str, set[str]]] = {
            horizon: defaultdict(set) for horizon in HORIZONS
        }
        unique_eligible: dict[int, set[str]] = {horizon: set() for horizon in HORIZONS}
        vintage_counts: dict[int, dict[str, Counter]] = {
            horizon: defaultdict(Counter) for horizon in HORIZONS
        }
        vintage_eligible: dict[int, dict[str, set[str]]] = {
            horizon: defaultdict(set) for horizon in HORIZONS
        }
        vintage_unique_outcomes: dict[int, dict[str, dict[str, set[str]]]] = {
            horizon: defaultdict(lambda: defaultdict(set)) for horizon in HORIZONS
        }
        seen_ids: set[str] = set()
        rows = width_errors = missing_ids = duplicate_ids = 0
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
            else:
                seen_ids.add(loan_id)
            close_status = row[close_status_i].strip()
            origination_year = row[open_year_i].strip()
            if not (origination_year.isdigit() and 1900 <= int(origination_year) <= 2100):
                origination_year = "unknown"
            close = (
                _close_ordinal(row[close_year_i].strip(), row[close_month_i].strip())
                if close_status in {"2", "3", "4"} else None
            )
            statuses = [row[index].strip().upper() for index in status_indices]
            for horizon in HORIZONS:
                for baseline_index, baseline_status in enumerate(statuses):
                    if baseline_status != "C" or baseline_index + horizon >= len(statuses):
                        continue
                    if close is not None and close <= _quarter_ordinal(baseline_index):
                        outcome = "not_open_at_baseline"
                    else:
                        outcome = _classify(statuses, close, baseline_index, horizon)
                    counts[horizon]["full_horizon_c_baseline_snapshots"] += 1
                    counts[horizon][outcome] += 1
                    unique_eligible[horizon].add(loan_id)
                    unique_outcomes[horizon][outcome].add(loan_id)
                    vintage_counts[horizon][origination_year]["full_horizon_c_baseline_snapshots"] += 1
                    vintage_counts[horizon][origination_year][outcome] += 1
                    vintage_eligible[horizon][origination_year].add(loan_id)
                    vintage_unique_outcomes[horizon][origination_year][outcome].add(loan_id)

    outcomes = []
    for horizon in HORIZONS:
        horizon_counts = counts[horizon]
        outcomes.append({
            "horizon_quarters": horizon,
            "approx_months": horizon * 3,
            "c_baseline_snapshots_with_full_horizon_unweighted": horizon_counts["full_horizon_c_baseline_snapshots"],
            "unique_mortgages_with_at_least_one_c_baseline": len(unique_eligible[horizon]),
            "snapshot_outcomes_unweighted": {
                key: value for key, value in sorted(horizon_counts.items())
                if key != "full_horizon_c_baseline_snapshots"
            },
            "unique_mortgages_by_outcome_nonexclusive": {
                key: len(ids) for key, ids in sorted(unique_outcomes[horizon].items())
            },
                "by_origination_year": [
                    {
                        "origination_year": year,
                        "c_baseline_snapshots_with_full_horizon_unweighted": year_counts["full_horizon_c_baseline_snapshots"],
                        "unique_mortgages_with_at_least_one_c_baseline": len(vintage_eligible[horizon][year]),
                        "snapshot_outcomes_unweighted": {
                            key: value for key, value in sorted(year_counts.items())
                            if key != "full_horizon_c_baseline_snapshots"
                        },
                        "unique_mortgages_by_outcome_nonexclusive": {
                            key: len(ids) for key, ids in sorted(vintage_unique_outcomes[horizon][year].items())
                        },
                    }
                    for year, year_counts in sorted(vintage_counts[horizon].items())
                ],
        })
    passed = rows == 62359 and not (width_errors or missing_ids or duplicate_ids)
    return {
        "schema_version": "nsmo-horizon-sensitivity-v1",
        "status": "PASS" if passed else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "source": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
        "schema": {"rows": rows, "columns": 587, "quarterly_status_columns": 51},
        "integrity": {"width_errors": width_errors, "missing_ids": missing_ids,
                      "duplicate_ids": duplicate_ids},
        "candidate_definition_for_feasibility_only": {
            "baseline_state": "C",
            "primary_event_codes": sorted(PRIMARY_EVENT),
            "other_adverse_codes_separate": sorted(OTHER_ADVERSE),
            "observed_codes": sorted(OBSERVED),
            "horizons": "next 2, 4, and 8 quarterly snapshots; incomplete horizons excluded",
            "same_month_termination": "ambiguous ordering; censored separately",
            "weights": "unweighted support counts only; no rates or inference",
        },
        "horizon_results": outcomes,
        "target_created": False,
        "limitations": [
            "Feasibility counts only; no target labels, rates, PD, model matrix, or model are created.",
            "Quarterly snapshots can miss within-quarter delinquency; the event date is unknown.",
            "Termination cause is unknown; same-month closure and snapshot ordering is ambiguous.",
            "M/S and other non-observation codes censor follow-up; they are not performing outcomes.",
            "Repeated baseline snapshots from one mortgage are dependent; unique-loan outcome counts are nonexclusive across outcomes.",
            "No survey variance design is available in this audit; counts are descriptive support only.",
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
                      "horizons": len(result["horizon_results"]), "receipt": str(args.output)}))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
