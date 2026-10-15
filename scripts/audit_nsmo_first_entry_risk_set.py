"""Feasibility-only first-entry risk-set screen for quarterly NSMO performance."""

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
BASELINE = set("C12")
PRIMARY_EVENT = set("3456")
COMPETING_ADVERSE = set("789")
OBSERVED = BASELINE | PRIMARY_EVENT | COMPETING_ADVERSE
NONOBSERVED_EXIT = {"A", "B", "K", "M", "P", "Q", "S", ""}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordinal(year: int, month: int) -> int:
    return year * 12 + month


def _open_quarter_end(year: int, month: int) -> int:
    quarter_end_month = ((month - 1) // 3 + 1) * 3
    return _ordinal(year, quarter_end_month)


def classify_first_entry_path(
    statuses: list[str], quarters: list[int], open_year: int, open_month: int,
    close_ordinal: int | None,
) -> dict:
    """Return one mortgage's first clean C/1/2 entry and subsequent first exit.

    Only the first post-origination C/1/2 observation is used. Observed 90+ or
    7-9 before entry excludes the mortgage from this incident-entry screen.
    After entry, only adjacent C/1/2 quarters remain at risk. A missing state,
    competing state, termination, or end of source closes the path.
    """
    start = next((i for i, q in enumerate(quarters) if q > _open_quarter_end(open_year, open_month)), None)
    if start is None:
        return {"entry": False, "reason": "administratively_no_post_open_quarter"}

    entry_index = None
    for index in range(start, len(quarters)):
        quarter = quarters[index]
        if close_ordinal is not None and close_ordinal < quarter:
            return {"entry": False, "reason": "termination_before_entry"}
        if close_ordinal is not None and close_ordinal == quarter:
            return {"entry": False, "reason": "termination_same_month_before_entry"}
        status = statuses[index]
        if status in BASELINE:
            entry_index = index
            break
        if status in PRIMARY_EVENT:
            return {"entry": False, "reason": "pre_entry_observed_90plus"}
        if status in COMPETING_ADVERSE:
            return {"entry": False, "reason": f"pre_entry_competing_{status}"}
        if status not in NONOBSERVED_EXIT:
            return {"entry": False, "reason": f"pre_entry_unknown_{status or 'blank'}"}
        return {"entry": False, "reason": f"pre_entry_nonobservation_{status or 'blank'}"}

    if entry_index is None:
        return {"entry": False, "reason": "administratively_no_baseline"}

    entry_state = statuses[entry_index]
    intervals = Counter()
    state_intervals = Counter()
    index = entry_index
    while True:
        state = statuses[index]
        if state not in BASELINE:
            raise ValueError("Risk-set path continued from a non-baseline status")
        state_intervals[state] += 1
        if index + 1 >= len(quarters):
            intervals["administrative_end"] += 1
            return {"entry": True, "entry_index": entry_index, "entry_state": entry_state,
                    "intervals": state_intervals, "exit": "administrative_end"}

        next_quarter = quarters[index + 1]
        if close_ordinal is not None and close_ordinal < next_quarter:
            intervals["termination_competing"] += 1
            return {"entry": True, "entry_index": entry_index, "entry_state": entry_state,
                    "intervals": state_intervals, "exit": "termination_competing"}
        if close_ordinal is not None and close_ordinal == next_quarter:
            intervals["termination_same_month_ambiguous"] += 1
            return {"entry": True, "entry_index": entry_index, "entry_state": entry_state,
                    "intervals": state_intervals, "exit": "termination_same_month_ambiguous"}

        next_state = statuses[index + 1]
        if next_state in PRIMARY_EVENT:
            intervals["observed_90plus"] += 1
            return {"entry": True, "entry_index": entry_index, "entry_state": entry_state,
                    "intervals": state_intervals, "exit": "observed_90plus"}
        if next_state in COMPETING_ADVERSE:
            intervals[f"competing_adverse_{next_state}"] += 1
            return {"entry": True, "entry_index": entry_index, "entry_state": entry_state,
                    "intervals": state_intervals, "exit": f"competing_adverse_{next_state}"}
        if next_state in BASELINE:
            intervals["remained_at_risk"] += 1
            index += 1
            continue
        if next_state not in NONOBSERVED_EXIT:
            next_state = "unknown"
        intervals[f"observation_censor_{next_state or 'blank'}"] += 1
        return {"entry": True, "entry_index": entry_index, "entry_state": entry_state,
                "intervals": state_intervals, "exit": f"observation_censor_{next_state or 'blank'}"}


def audit(path: Path) -> dict:
    partitions: Counter[str] = Counter()
    entry_states: Counter[str] = Counter()
    exits_after_entry: Counter[str] = Counter()
    intervals_by_state: Counter[str] = Counter()
    by_vintage_state: dict[tuple[str, str], dict[str, Counter[str]]] = defaultdict(
        lambda: {"loans": Counter(), "intervals": Counter(), "exits": Counter()})
    by_vintage_population: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: {"population": Counter(), "exclusions": Counter(), "exits": Counter()})
    seen_ids: set[str] = set()
    rows = width_errors = empty_ids = duplicate_ids = 0

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        pos = {name.casefold(): i for i, name in enumerate(headers)}
        if len(headers) != EXPECTED_COLUMNS:
            raise ValueError("Expected the reconciled 587-column NSMO v7.0 PUF")
        status_names = sorted((name for name in headers if name.casefold().startswith("perf_status_")),
                              key=parse_performance_column)
        if len(status_names) != 51:
            raise ValueError("Expected 51 quarterly performance snapshots")
        quarters = [_ordinal(date.year, date.month) for date in map(parse_performance_column, status_names)]
        idx = [pos[name.casefold()] for name in status_names]
        required = {"nsmoid", "open_year", "open_month", "close_status_0925", "close_year", "close_month"}
        if not required.issubset(pos):
            raise ValueError("Required origination/termination fields are absent")

        for row in reader:
            rows += 1
            if len(row) != len(headers):
                width_errors += 1
                continue
            loan_id = row[pos["nsmoid"]].strip()
            if not loan_id:
                empty_ids += 1
                continue
            if loan_id in seen_ids:
                duplicate_ids += 1
                continue
            seen_ids.add(loan_id)
            try:
                year, month = int(row[pos["open_year"]]), int(row[pos["open_month"]])
            except ValueError:
                by_vintage_population["unknown"]["population"]["puf_mortgages"] += 1
                by_vintage_population["unknown"]["exclusions"]["invalid_origination_month"] += 1
                partitions["invalid_origination_month"] += 1
                continue
            vintage = str(year) if 2013 <= year <= 2024 else "unknown"
            by_vintage_population[vintage]["population"]["puf_mortgages"] += 1
            if not (2013 <= year <= 2024 and 1 <= month <= 12):
                by_vintage_population[vintage]["exclusions"]["invalid_origination_month"] += 1
                partitions["invalid_origination_month"] += 1
                continue

            close = None
            if row[pos["close_status_0925"]].strip() == "2":
                try:
                    cy, cm = int(row[pos["close_year"]]), int(row[pos["close_month"]])
                    if cy >= 1900 and 1 <= cm <= 12:
                        close = _ordinal(cy, cm)
                except ValueError:
                    pass
            statuses = [row[i].strip().upper() for i in idx]
            result = classify_first_entry_path(statuses, quarters, year, month, close)
            if not result["entry"]:
                reason = result["reason"]
                partitions[reason] += 1
                by_vintage_population[vintage]["exclusions"][reason] += 1
                continue

            partitions["entered_risk_set"] += 1
            by_vintage_population[vintage]["population"]["entered_risk_set"] += 1
            entry_state = result["entry_state"]
            entry_states[entry_state] += 1
            exit_class = result["exit"]
            exits_after_entry[exit_class] += 1
            by_vintage_population[vintage]["exits"][exit_class] += 1
            key = (vintage, entry_state)
            by_vintage_state[key]["loans"]["entered"] += 1
            by_vintage_state[key]["exits"][exit_class] += 1
            for state, count in result["intervals"].items():
                intervals_by_state[state] += count
                by_vintage_state[key]["intervals"][state] += count

    partitioned = sum(partitions.values())
    valid = (rows == EXPECTED_ROWS and width_errors == empty_ids == duplicate_ids == 0
             and len(seen_ids) == rows and partitioned == rows)
    vintage_rows = []
    for (year, state), groups in sorted(by_vintage_state.items()):
        vintage_rows.append({"origination_year": year, "entry_state": state,
                             "mortgages_entered": groups["loans"]["entered"],
                             "at_risk_quarter_intervals": sum(groups["intervals"].values()),
                             "intervals_by_class": dict(sorted(groups["intervals"].items())),
                             "first_exit_by_class": dict(sorted(groups["exits"].items()))})
    vintage_population_rows = []
    for year, groups in sorted(by_vintage_population.items()):
        vintage_population_rows.append({
            "origination_year": year,
            "puf_mortgages": groups["population"]["puf_mortgages"],
            "entered_risk_set": groups["population"]["entered_risk_set"],
            "pre_entry_exclusions": dict(sorted(groups["exclusions"].items())),
            "first_exit_after_entry": dict(sorted(groups["exits"].items())),
        })
    return {
        "schema_version": "nsmo-first-entry-risk-set-feasibility-v1",
        "status": "PASS" if valid else "FAIL",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "source": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
        "schema": {"rows": rows, "columns": len(headers), "quarterly_status_columns": 51},
        "checks": {"row_width_errors": width_errors, "empty_ids": empty_ids,
                   "duplicate_ids": duplicate_ids, "partitioned_rows": partitioned},
        "definition": {
            "entry": "first post-origination-quarter adjacent observed C/1/2 status; any prior observed 3-9 or nonobservation prevents entry",
            "at_risk_unit": "one mortgage-quarter interval, starting from first eligible baseline and continuing only while adjacent quarterly status remains C/1/2",
            "event": "first adjacent observed status 3/4/5/6",
            "competing_outcomes": "first observed status 7/8/9, or a termination strictly before the next quarterly snapshot",
            "censoring": "same-month termination ordering, A/B/K/M/P/Q/S/blank, unknown status, or administrative end",
            "target_created": False, "risk_set_is_model_ready": False,
            "rates_or_weights_used": False,
        },
        "population_partition_unweighted": dict(sorted(partitions.items())),
        "risk_set_entry_by_state_unweighted": dict(sorted(entry_states.items())),
        "first_exit_after_entry_unweighted": dict(sorted(exits_after_entry.items())),
        "at_risk_quarter_intervals_by_start_state_unweighted": dict(sorted(intervals_by_state.items())),
        "population_and_entry_by_origination_vintage_unweighted": vintage_population_rows,
        "by_origination_vintage_and_entry_state_unweighted": vintage_rows,
        "limitations": [
            "First-entry dynamic-monitoring support only; this is not origination PD and has no frozen estimand.",
            "One first entry per mortgage avoids repeated-loan rows but conditions on surviving to the first eligible observed C/1/2 quarter.",
            "A non-observed state before entry is excluded because earlier event history is unknown; this selection boundary is not assumed random.",
            "Quarterly status snapshots cannot identify event dates between quarters; 3-6 are observed-state endpoints only.",
            "Termination reason is unavailable; same-month close/snapshot order remains ambiguous.",
            "All support is unweighted and has no design-based variance; no event rate, PD, target label, or model matrix is created.",
            "Mortgage identifiers are used only in memory for deduplication and are not written to the receipt.",
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
    print(json.dumps({"status": result["status"], "rows": result["schema"]["rows"],
                      "entries": result["population_partition_unweighted"].get("entered_risk_set", 0),
                      "events": result["first_exit_after_entry_unweighted"].get("observed_90plus", 0),
                      "risk_intervals": sum(result["at_risk_quarter_intervals_by_start_state_unweighted"].values()),
                      "receipt": str(args.output)}))
    if result["status"] != "PASS":
        raise SystemExit("NSMO first-entry risk-set audit did not reconcile")


if __name__ == "__main__":
    main()
