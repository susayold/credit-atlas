"""Count aggregate-only support for observed NSMO delinquency transitions.

The source contains mortgage identifiers. Identifiers are used only in memory
to check uniqueness and de-duplicate each mortgage's transition support; the
receipt contains no identifiers, row data, target labels, rates, or model data.
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


EXPECTED_ROWS = 62359
EXPECTED_COLUMNS = 587
EXPECTED_STATUS_COLUMNS = 51
BASELINES = set("C12")
PRIMARY_EVENT = set("3456")
OTHER_ADVERSE = set("789")
OBSERVED = set("C123456789")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mortgage_transition_summary(statuses: list[str]) -> dict:
    """Return one mortgage's transition facts without retaining its identifier."""
    repeated = Counter()
    for before, after in zip(statuses, statuses[1:]):
        if before in BASELINES and after in PRIMARY_EVENT:
            repeated[before] += 1

    first_event = next((i for i, status in enumerate(statuses) if status in PRIMARY_EVENT), None)
    first_from = None
    if first_event is not None and first_event > 0:
        prior = statuses[first_event - 1]
        if prior in BASELINES:
            first_from = prior
    return {"repeated_transitions": repeated, "first_event_from": first_from,
            "first_event_observed": first_event is not None,
            "first_event_has_observed_prior": first_event is not None and first_event > 0
            and statuses[first_event - 1] in OBSERVED}


def audit(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        positions = {name.casefold(): index for index, name in enumerate(headers)}
        status_columns = sorted(
            (name for name in headers if name.casefold().startswith("perf_status_")),
            key=parse_performance_column,
        )
        if (len(headers) != EXPECTED_COLUMNS or len(status_columns) != EXPECTED_STATUS_COLUMNS
                or not {"nsmoid", "open_year"}.issubset(positions)):
            raise ValueError("Expected the reconciled NSMO v7.0 PUF schema")
        id_index, vintage_index = positions["nsmoid"], positions["open_year"]
        status_indices = [positions[name.casefold()] for name in status_columns]

        repeated_by_state: Counter[str] = Counter()
        repeated_by_vintage_state: Counter[tuple[str, str]] = Counter()
        unique_by_state: Counter[str] = Counter()
        unique_by_vintage_state: Counter[tuple[str, str]] = Counter()
        first_event_by_state: Counter[str] = Counter()
        first_event_by_vintage_state: Counter[tuple[str, str]] = Counter()
        first_event_without_observed_prior = 0
        first_event_with_other_adverse_prior = 0
        first_event_with_baseline_prior = 0
        first_event_rows = 0
        rows = width_errors = empty_ids = duplicate_ids = 0
        seen_ids: set[str] = set()

        for row in reader:
            rows += 1
            if len(row) != len(headers):
                width_errors += 1
                continue
            loan_id = row[id_index].strip()
            if not loan_id:
                empty_ids += 1
                continue
            if loan_id in seen_ids:
                duplicate_ids += 1
                continue
            seen_ids.add(loan_id)

            vintage = row[vintage_index].strip()
            if not vintage.isdigit() or not 2013 <= int(vintage) <= 2024:
                vintage = "unknown"
            statuses = [row[index].strip().upper() for index in status_indices]
            facts = mortgage_transition_summary(statuses)

            for state, count in facts["repeated_transitions"].items():
                repeated_by_state[state] += count
                repeated_by_vintage_state[(vintage, state)] += count
                unique_by_state[state] += 1
                unique_by_vintage_state[(vintage, state)] += 1

            if facts["first_event_observed"]:
                first_event_rows += 1
                if not facts["first_event_has_observed_prior"]:
                    first_event_without_observed_prior += 1
                if facts["first_event_from"]:
                    state = facts["first_event_from"]
                    first_event_with_baseline_prior += 1
                    first_event_by_state[state] += 1
                    first_event_by_vintage_state[(vintage, state)] += 1
                elif facts["first_event_has_observed_prior"]:
                    first_event_with_other_adverse_prior += 1

    valid = (rows == EXPECTED_ROWS and width_errors == 0 and empty_ids == 0
             and duplicate_ids == 0 and len(seen_ids) == rows)
    return {
        "schema_version": "nsmo-first-observed-transition-support-v1",
        "status": "PASS" if valid else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "source": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
        "schema": {"rows": rows, "columns": len(headers), "quarterly_status_columns": len(status_columns)},
        "checks": {"width_errors": width_errors, "empty_mortgage_ids": empty_ids,
                   "duplicate_mortgage_ids": duplicate_ids, "unique_mortgage_ids": len(seen_ids)},
        "definition": {
            "repeated_transition": "every adjacent observed snapshot transition from C/1/2 to 90+ codes 3/4/5/6",
            "unique_mortgage": "one source-state count per mortgage if it has one or more matching repeated transitions",
            "first_observed_event": "first observed quarterly status 3/4/5/6 anywhere in each mortgage history",
            "first_event_source_state": "immediately preceding observed quarterly status, only if C/1/2",
            "risk_set_or_event_incidence": False,
            "target_or_label_created": False,
            "weights_or_rate_calculated": False,
        },
        "all_vintages": {
            "repeated_90plus_transition_count_by_source_state": dict(sorted(repeated_by_state.items())),
            "unique_mortgages_with_any_90plus_transition_by_source_state": dict(sorted(unique_by_state.items())),
            "first_observed_90plus_event_count": first_event_rows,
            "first_observed_90plus_event_with_baseline_source_state": first_event_with_baseline_prior,
            "first_observed_90plus_event_without_observed_prior": first_event_without_observed_prior,
            "first_observed_90plus_event_after_other_adverse_state": first_event_with_other_adverse_prior,
            "first_observed_90plus_event_by_prior_baseline_state": dict(sorted(first_event_by_state.items())),
            "first_event_partition_reconciles": first_event_rows == (
                first_event_with_baseline_prior + first_event_without_observed_prior
                + first_event_with_other_adverse_prior),
        },
        "by_origination_vintage_and_source_state": [
            {"origination_year": vintage, "source_state": state,
             "repeated_90plus_transition_count": repeated_by_vintage_state[(vintage, state)],
             "unique_mortgages_with_any_90plus_transition": unique_by_vintage_state[(vintage, state)],
             "first_observed_90plus_event_count": first_event_by_vintage_state[(vintage, state)]}
            for vintage, state in sorted(set(repeated_by_vintage_state) | set(unique_by_vintage_state)
                                         | set(first_event_by_vintage_state))
        ],
        "limitations": [
            "Unweighted descriptive transition support only; repeated transitions from one mortgage are dependent.",
            "A first observed 90+ snapshot is not necessarily the first true delinquency event; quarterly snapshots can miss events between waves.",
            "The screen does not establish at-risk eligibility, event-versus-close ordering, censoring assumptions, survey variance, or a target estimand.",
            "Mortgage identifiers are used only in memory for uniqueness checks and are never included in the receipt.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puf-csv", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.puf_csv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise SystemExit("NSMO transition support audit did not reconcile; inspect the private receipt")


if __name__ == "__main__":
    main()
