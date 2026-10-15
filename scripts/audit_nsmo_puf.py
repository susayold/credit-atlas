"""Validate an already downloaded FHFA NSMO CSV without exporting row data.

The generated receipt contains aggregate counts only. NSMO identifiers and
loan-level records stay in the private data directory and are never printed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from credit_atlas.nsmo import _PERFORMANCE_CODES, parse_performance_column


def audit(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        headers = next(csv.reader(handle), None)
    if not headers:
        raise ValueError("NSMO CSV is empty")
    if len({column.casefold() for column in headers}) != len(headers):
        raise ValueError("NSMO CSV has duplicate case-insensitive column names")

    positions = {column.casefold(): index for index, column in enumerate(headers)}
    required = ("nsmoid", "open_year", "open_month", "analysis_weight")
    missing = [column for column in required if column not in positions]
    if missing:
        raise ValueError(f"NSMO CSV is missing required fields: {missing}")
    performance_columns = sorted(
        (column for column in headers if column.casefold().startswith("perf_status_")),
        key=parse_performance_column,
    )
    if not performance_columns:
        raise ValueError("NSMO CSV contains no quarterly performance columns")
    performance_positions = [positions[column.casefold()] for column in performance_columns]

    identifiers: set[str] = set()
    duplicate_ids = blank_ids = width_errors = rows = 0
    width_examples: list[dict[str, int]] = []
    origination_years: Counter[str] = Counter()
    origination_months: Counter[str] = Counter()
    waves: Counter[str] = Counter()
    weights: list[float] = []
    weight_missing = weight_invalid = weight_nonpositive = 0
    status_counts: Counter[str] = Counter()
    weighted_status: Counter[str] = Counter()
    quarter_counts: dict[str, Counter[str]] = {
        column: Counter() for column in performance_columns
    }
    quarter_weighted: dict[str, Counter[str]] = {
        column: Counter() for column in performance_columns
    }
    unknown_status: Counter[str] = Counter()
    idx_id, idx_year, idx_month, idx_weight = (positions[column] for column in required)
    idx_wave = positions.get("survey_wave")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        for line_number, row in enumerate(reader, start=2):
            rows += 1
            if len(row) != len(headers):
                width_errors += 1
                if len(width_examples) < 5:
                    width_examples.append({"line": line_number, "observed_width": len(row)})
                continue

            identifier = row[idx_id].strip()
            if not identifier:
                blank_ids += 1
            elif identifier in identifiers:
                duplicate_ids += 1
            else:
                identifiers.add(identifier)

            origination_years[row[idx_year].strip() or "<blank>"] += 1
            origination_months[row[idx_month].strip() or "<blank>"] += 1
            if idx_wave is not None:
                waves[row[idx_wave].strip() or "<blank>"] += 1

            weight_text = row[idx_weight].strip()
            row_weight: float | None = None
            if not weight_text:
                weight_missing += 1
            else:
                try:
                    row_weight = float(weight_text)
                except ValueError:
                    weight_invalid += 1
                else:
                    if not math.isfinite(row_weight):
                        weight_invalid += 1
                        row_weight = None
                    else:
                        weights.append(row_weight)
                        if row_weight <= 0:
                            weight_nonpositive += 1

            for column, index in zip(performance_columns, performance_positions):
                status = row[index].strip().upper()
                label = status or "<blank>"
                status_counts[label] += 1
                quarter_counts[column][label] += 1
                if status and status not in _PERFORMANCE_CODES:
                    unknown_status[status] += 1
                elif row_weight is not None:
                    weighted_status[label] += row_weight
                    quarter_weighted[column][label] += row_weight

    if rows == 0:
        raise ValueError("NSMO CSV has a header but no data rows")
    quarter_dates = [parse_performance_column(column) for column in performance_columns]
    status = "PASS" if (
        rows > 0
        and len(identifiers) == rows
        and duplicate_ids == 0
        and blank_ids == 0
        and width_errors == 0
        and weight_missing == 0
        and weight_invalid == 0
        and weight_nonpositive == 0
        and not unknown_status
    ) else "FAIL"
    return {
        "status": status,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "csv": str(path),
        "csv_bytes": path.stat().st_size,
        "csv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "column_count": len(headers),
        "case_insensitive_duplicate_columns": 0,
        "row_count": rows,
        "unique_nonblank_nsmoid": len(identifiers),
        "duplicate_nsmoid_rows": duplicate_ids,
        "blank_nsmoid_rows": blank_ids,
        "bad_width_rows": width_errors,
        "bad_width_examples": width_examples,
        "origination_year_counts": dict(sorted(origination_years.items())),
        "origination_month_counts": dict(sorted(origination_months.items())),
        "survey_wave_counts": dict(sorted(waves.items())),
        "analysis_weight": {
            "missing": weight_missing,
            "invalid": weight_invalid,
            "nonpositive": weight_nonpositive,
            "valid_n": len(weights),
            "min": min(weights) if weights else None,
            "p01": statistics.quantiles(weights, n=100, method="inclusive")[0]
            if len(weights) >= 100
            else None,
            "median": statistics.median(weights) if weights else None,
            "p99": statistics.quantiles(weights, n=100, method="inclusive")[98]
            if len(weights) >= 100
            else None,
            "max": max(weights) if weights else None,
            "sum": round(sum(weights), 2),
        },
        "performance": {
            "column_count": len(performance_columns),
            "first_column": performance_columns[0],
            "last_column": performance_columns[-1],
            "first_quarter_end": quarter_dates[0].isoformat(),
            "last_quarter_end": quarter_dates[-1].isoformat(),
            "cell_count": rows * len(performance_columns),
            "status_counts_unweighted": dict(sorted(status_counts.items())),
            "status_weight_sums_descriptive_only": {
                key: round(value, 2) for key, value in sorted(weighted_status.items())
            },
            "unknown_status_counts": dict(sorted(unknown_status.items())),
            "quarterly_counts": [
                {
                    "quarter_end": parse_performance_column(column).isoformat(),
                    "source_column": column,
                    "status_counts_unweighted": dict(sorted(quarter_counts[column].items())),
                    "status_weight_sums_descriptive_only": {
                        key: round(value, 2)
                        for key, value in sorted(quarter_weighted[column].items())
                    },
                }
                for column in performance_columns
            ],
        },
        "pd_target_created": False,
        "limitations": [
            "Weighted status sums are descriptive only, not event rates or PD estimates.",
            "Quarterly point-in-time states do not identify exact event dates or between-quarter events.",
            "No labels, transitions, target, model, or row-level export are created by this audit.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.csv_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    performance = report["performance"]
    print(json.dumps({
        key: report[key] for key in (
            "status", "csv_bytes", "csv_sha256", "column_count", "row_count",
            "unique_nonblank_nsmoid", "duplicate_nsmoid_rows", "blank_nsmoid_rows",
            "bad_width_rows", "analysis_weight",
        )
    } | {
        "performance": {
            "column_count": performance["column_count"],
            "first_quarter_end": performance["first_quarter_end"],
            "last_quarter_end": performance["last_quarter_end"],
            "cell_count": performance["cell_count"],
            "unknown_status_counts": performance["unknown_status_counts"],
        }
    }, indent=2))


if __name__ == "__main__":
    main()
