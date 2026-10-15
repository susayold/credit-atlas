"""Audit NSMO quarterly states and termination coding; emit aggregates only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from credit_atlas.nsmo import _PERFORMANCE_CODES, parse_performance_column
from credit_atlas.nsmo_codebook import parse_sas_formats, parse_sas_labels


OBSERVED_STATUS_CODES = set("C123456789")
ADMIN_STATUS_CODES = set("ABKM PQS".replace(" ", ""))
_NUMBER_OR_RANGE = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(?:\s*-\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)))?$"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _compile_formats(sas_formats: dict[str, list[dict[str, str]]]) -> dict[str, list[tuple]]:
    compiled: dict[str, list[tuple]] = {}
    for name, rows in sas_formats.items():
        rules: list[tuple] = []
        for row in rows:
            value = row["format_value"].strip()
            if value.startswith("'") and value.endswith("'"):
                rules.append(("string", value[1:-1]))
                continue
            match = _NUMBER_OR_RANGE.fullmatch(value)
            if not match:
                raise ValueError(f"Unsupported FHFA SAS format domain in {name}")
            lower = float(match.group(1))
            upper = float(match.group(2) or match.group(1))
            rules.append(("number", lower, upper))
        compiled[name.casefold()] = rules
    return compiled


def _value_in_format(value: str, rules: list[tuple]) -> bool:
    for rule in rules:
        if rule[0] == "string":
            if value == rule[1]:
                return True
            continue
        try:
            number = float(value)
        except ValueError:
            continue
        if math.isfinite(number) and rule[1] <= number <= rule[2]:
            return True
    return False


def audit(path: Path, sas_labels_path: Path, sas_formats_path: Path) -> dict:
    labels = parse_sas_labels(sas_labels_path)
    formats = parse_sas_formats(sas_formats_path)
    compiled = _compile_formats(formats)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader, [])
        if len(headers) != 587 or len({name.casefold() for name in headers}) != 587:
            raise ValueError("NSMO PUF must have 587 unique case-insensitive headers")
        if {name.casefold() for name in headers} != set(labels):
            raise ValueError("NSMO PUF headers do not match official SAS labels")

        positions = {name.casefold(): index for index, name in enumerate(headers)}
        status_columns = sorted(
            (name for name in headers if name.casefold().startswith("perf_status_")),
            key=parse_performance_column,
        )
        if len(status_columns) != 51:
            raise ValueError(f"Expected 51 quarterly status fields, found {len(status_columns)}")
        status_indices = [positions[name.casefold()] for name in status_columns]
        quarter_labels = [parse_performance_column(name).isoformat() for name in status_columns]
        weight_index = positions["analysis_weight"]
        close_status_index = positions["close_status_0925"]
        close_year_index = positions["close_year"]
        close_month_index = positions["close_month"]
        invalid_format_cells: Counter[str] = Counter()
        blank_cells: Counter[str] = Counter()
        row_width_errors = 0
        row_count = 0
        close_status_counts: Counter[str] = Counter()
        close_date_consistency: Counter[str] = Counter()
        final_status_by_close: Counter[tuple[str, str]] = Counter()
        ab_status_by_close: Counter[tuple[str, str]] = Counter()
        status_counts_by_quarter = [Counter() for _ in status_columns]
        status_weight_by_quarter: list[Counter[str]] = [Counter() for _ in status_columns]
        transition_observation_class: list[Counter[str]] = [Counter() for _ in range(len(status_columns) - 1)]
        transitions: list[Counter[tuple[str, str]]] = [Counter() for _ in range(len(status_columns) - 1)]
        weighted_transitions: list[Counter[tuple[str, str]]] = [Counter() for _ in range(len(status_columns) - 1)]
        first_observed: Counter[tuple[int, str]] = Counter()
        last_observed: Counter[tuple[int, str]] = Counter()
        observed_span_quarters: Counter[int] = Counter()
        ever_status_loans: Counter[str] = Counter()
        no_observed_history = 0

        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            if len(row) != len(headers):
                row_width_errors += 1
                continue

            for index, name in enumerate(headers):
                value = row[index].strip()
                if not value:
                    blank_cells[name.casefold()] += 1
                elif not _value_in_format(value, compiled[labels[name.casefold()]["sas_format"].casefold()]):
                    invalid_format_cells[name.casefold()] += 1

            weight_text = row[weight_index].strip()
            try:
                weight = float(weight_text)
            except ValueError:
                weight = 0.0
            if not math.isfinite(weight) or weight <= 0:
                weight = 0.0

            close_status = row[close_status_index].strip()
            close_year = row[close_year_index].strip()
            close_month = row[close_month_index].strip()
            close_status_counts[close_status] += 1
            if close_status == "1" and close_year == "-2" and close_month == "-2":
                close_date_consistency["open_with_not_applicable_close_date"] += 1
            elif close_status == "2" and close_year not in {"", "-2"} and close_month not in {"", "-2"}:
                close_date_consistency["terminated_with_year_and_month"] += 1
            else:
                close_date_consistency["other_status_or_date_pattern"] += 1

            statuses = [row[index].strip().upper() for index in status_indices]
            final_status_by_close[(statuses[-1] or "<blank>", close_status)] += 1
            for status in statuses:
                if status in {"A", "B"}:
                    ab_status_by_close[(status, close_status)] += 1

            seen_positions: list[int] = []
            seen_states: list[str] = []
            for position, status in enumerate(statuses):
                label = status or "<blank>"
                status_counts_by_quarter[position][label] += 1
                if status and status in _PERFORMANCE_CODES:
                    status_weight_by_quarter[position][status] += weight
                if status in OBSERVED_STATUS_CODES:
                    seen_positions.append(position)
                    seen_states.append(status)
            for status in set(statuses):
                if status in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
                    ever_status_loans[status] += 1

            if seen_positions:
                first_observed[(seen_positions[0], seen_states[0])] += 1
                last_observed[(seen_positions[-1], seen_states[-1])] += 1
                observed_span_quarters[seen_positions[-1] - seen_positions[0] + 1] += 1
            else:
                no_observed_history += 1

            for position, (previous, current) in enumerate(zip(statuses, statuses[1:])):
                previous_observed = previous in OBSERVED_STATUS_CODES
                current_observed = current in OBSERVED_STATUS_CODES
                pair_class = (
                    "observed_to_observed" if previous_observed and current_observed
                    else "observed_to_nonobservation" if previous_observed
                    else "nonobservation_to_observed" if current_observed
                    else "nonobservation_to_nonobservation"
                )
                transition_observation_class[position][pair_class] += 1
                if previous_observed and current_observed:
                    transitions[position][(previous, current)] += 1
                    weighted_transitions[position][(previous, current)] += weight

    status = "PASS" if row_width_errors == 0 and not invalid_format_cells else "FAIL"
    term_code_labels = {
        row["format_value"].strip(): row["format_label"]
        for row in formats["pcstatfm"]
    }
    quarters = []
    for index, quarter in enumerate(quarter_labels):
        quarters.append({
            "quarter_end": quarter,
            "status_counts_unweighted": dict(sorted(status_counts_by_quarter[index].items())),
            "status_weight_sums_descriptive_only": {
                key: round(value, 2)
                for key, value in sorted(status_weight_by_quarter[index].items())
            },
            "paired_transition_to_next_quarter": None if index == len(quarter_labels) - 1 else {
                "next_quarter_end": quarter_labels[index + 1],
                "observation_classes": dict(sorted(transition_observation_class[index].items())),
                "observed_state_transitions": [
                    {
                        "from": previous,
                        "to": current,
                        "n": count,
                        "weight_sum_descriptive_only": round(weighted_transitions[index][(previous, current)], 2),
                    }
                    for (previous, current), count in sorted(transitions[index].items())
                ],
            },
        })

    return {
        "schema_version": "nsmo-performance-state-audit-v1",
        "status": status,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "puf_csv": {"bytes": path.stat().st_size, "sha256": _sha256(path)},
            "sas_labels_sha256": _sha256(sas_labels_path),
            "sas_formats_sha256": _sha256(sas_formats_path),
        },
        "schema": {"rows": row_count, "columns": len(headers), "quarterly_status_columns": len(status_columns)},
        "sas_domain_validation": {
            "status": status,
            "observed_unknown_domain_cells": sum(invalid_format_cells.values()),
            "unknown_fields": sorted(invalid_format_cells),
            "row_width_errors": row_width_errors,
            "blank_cells_by_field": dict(sorted(blank_cells.items())),
        },
        "termination": {
            "code_labels_from_official_sas_formats": term_code_labels,
            "close_status_counts": dict(sorted(close_status_counts.items())),
            "close_date_consistency": dict(sorted(close_date_consistency.items())),
            "final_2025q3_performance_by_close_status": [
                {"performance_status": perf, "close_status": close, "n_mortgages": count}
                for (perf, close), count in sorted(final_status_by_close.items())
            ],
            "history_ended_or_potentially_closed_cells_by_close_status": [
                {"performance_status": state, "close_status": close, "n_loan_quarter_cells": count}
                for (state, close), count in sorted(ab_status_by_close.items())
            ],
            "codebook_note_issue": "Appendix C page C-148 references Close_Status_1224; v7.0 PUF labels the termination field Close_Status_0925. This audit uses the actual v7.0 field; A cells reconcile to terminated loans, while B is not observed in the sample.",
        },
        "observed_history": {
            "observed_status_codes": sorted(OBSERVED_STATUS_CODES),
            "administrative_or_nonobservation_codes": sorted(ADMIN_STATUS_CODES),
            "loans_with_no_observed_performance_status": no_observed_history,
            "first_observed_quarter_and_state": [
                {"quarter_end": quarter_labels[index], "status": state, "n_mortgages": count}
                for (index, state), count in sorted(first_observed.items())
            ],
            "last_observed_quarter_and_state": [
                {"quarter_end": quarter_labels[index], "status": state, "n_mortgages": count}
                for (index, state), count in sorted(last_observed.items())
            ],
            "span_between_first_and_last_observed_quarters": dict(sorted(observed_span_quarters.items())),
            "mortgages_ever_observed_each_numeric_status_over_all_available_quarters": dict(sorted(ever_status_loans.items())),
        },
        "quarterly_state_matrix": quarters,
        "target_created": False,
        "limitations": [
            "The code family C and 1-9 is counted as an observed reported state; this audit does not declare those loans statistically at risk.",
            "Transitions are between adjacent quarter-end snapshots only. Intermediate monthly states and exact event dates are not observed here.",
            "Codes A, B, K, M, P, Q, S and blank remain distinct and are not mapped to current or performing.",
            "Loan-quarter weighted sums and transition weights are descriptive; no variance estimator or PD is specified.",
            "A mortgage termination flag/date does not identify prepayment versus other closure reason.",
            "No row-level data, identifiers, target labels, or model outputs are included in this report.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puf-csv", required=True, type=Path)
    parser.add_argument("--sas-labels", required=True, type=Path)
    parser.add_argument("--sas-formats", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.puf_csv, args.sas_labels, args.sas_formats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "rows": report["schema"]["rows"],
        "columns": report["schema"]["columns"],
        "unknown_domain_cells": report["sas_domain_validation"]["observed_unknown_domain_cells"],
        "close_status_counts": report["termination"]["close_status_counts"],
        "close_date_consistency": report["termination"]["close_date_consistency"],
        "closed_history_cells": report["termination"]["history_ended_or_potentially_closed_cells_by_close_status"],
        "loans_with_no_observed_performance_status": report["observed_history"]["loans_with_no_observed_performance_status"],
        "target_created": report["target_created"],
    }, indent=2))


if __name__ == "__main__":
    main()
