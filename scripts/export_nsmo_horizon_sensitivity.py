"""Export only aggregate NSMO horizon totals and vintage breakdowns."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


CLASS_MAP = {
    "observation_censor_M": "CENSOR_M", "observation_censor_S": "CENSOR_S",
    "observed_90plus_event": "90PLUS", "termination_competing_censor": "CLOSE_PRE",
    "termination_same_month_ambiguous": "CLOSE_TIED",
    "observed_other_adverse_state_7": "OTHER_7",
    "observed_other_adverse_state_8": "OTHER_8",
    "observed_other_adverse_state_9": "OTHER_9",
}


def export(receipt_path: Path, output_path: Path, interpretation_path: Path) -> int:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    with interpretation_path.open(encoding="utf-8-sig", newline="") as stream:
        interpretations = {row["outcome_class"]: row["outcome_interpretation"]
                           for row in csv.DictReader(stream)}
    interpretations.setdefault("CENSOR_OTHER", "Censor quan sát: mã thiếu/không quan sát khác M/S")
    interpretations.setdefault("NOT_OPEN", "Không còn mở tại baseline; không thuộc risk set")
    headers = ["scope", "origination_year", "horizon_quarters", "horizon_months",
               "c_baseline_snapshots_with_full_horizon", "unique_mortgages_with_c_baseline",
               "outcome_class", "outcome_interpretation", "snapshot_count",
               "unique_mortgage_count_nonexclusive"]
    rows = []
    for horizon in receipt["horizon_results"]:
        groups = [("all", "", horizon)]
        groups.extend(("origination_year", vintage["origination_year"], vintage)
                      for vintage in horizon["by_origination_year"])
        for scope, year, group in groups:
            outcomes = group["snapshot_outcomes_unweighted"]
            unique = group["unique_mortgages_by_outcome_nonexclusive"]
            for outcome, snapshot_count in sorted(outcomes.items()):
                label = CLASS_MAP.get(outcome)
                if outcome.startswith("observed_no_90plus_within_"):
                    label = "NO_90PLUS"
                elif outcome.startswith("observation_censor_"):
                    suffix = outcome.removeprefix("observation_censor_")
                    label = "CENSOR_" + suffix if suffix in {"M", "S"} else "CENSOR_OTHER"
                elif outcome == "not_open_at_baseline":
                    label = "NOT_OPEN"
                if label is None or label not in interpretations:
                    raise ValueError(f"No reviewed public interpretation for {outcome}")
                rows.append({
                    "scope": scope, "origination_year": year,
                    "horizon_quarters": horizon["horizon_quarters"],
                    "horizon_months": horizon["approx_months"],
                    "c_baseline_snapshots_with_full_horizon": group["c_baseline_snapshots_with_full_horizon_unweighted"],
                    "unique_mortgages_with_c_baseline": group["unique_mortgages_with_at_least_one_c_baseline"],
                    "outcome_class": label, "outcome_interpretation": interpretations[label],
                    "snapshot_count": snapshot_count,
                    "unique_mortgage_count_nonexclusive": unique.get(outcome, 0),
                })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    class_order = {name: index for index, name in enumerate(interpretations)}
    rows.sort(key=lambda row: (0 if row["scope"] == "all" else 1,
                               int(row["origination_year"] or 0),
                               int(row["horizon_quarters"]),
                               class_order.get(row["outcome_class"], len(class_order))))
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interpretations", type=Path, required=True)
    args = parser.parse_args()
    count = export(args.receipt, args.output, args.interpretations)
    print(json.dumps({"status": "PASS", "aggregate_rows": count, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
