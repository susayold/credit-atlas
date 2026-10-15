"""Cross-check FHFA Appendix D Table 1 against weighted NSMO PUF aggregates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


YEARS = tuple(str(year) for year in range(2014, 2025))
PURPOSES = ("purchase", "refinance")
ITEMS = ("x05a", "x05b", "x05c", "x05d", "x05e", "x05f", "x05g")
RESPONSES = ("1", "2", "3")
RESPONSE_LABELS = {"1": "Very", "2": "Somewhat", "3": "Not at all"}
_RESPONSE_ROW = re.compile(r"^\s*(Very|Somewhat|Not at all)\s+(.+)$", re.IGNORECASE)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_table1_response_rows(page_text: str) -> list[tuple[str, list[int]]]:
    """Return the 21 published category rows, each with 22 year percentages."""
    rows = []
    for line in page_text.splitlines():
        match = _RESPONSE_ROW.fullmatch(line.strip())
        if not match:
            continue
        values = [int(value) for value in re.findall(r"\b(\d{1,3})%", match.group(2))]
        if not values:
            continue
        if len(values) != 22:
            raise ValueError(f"Expected 22 annual percentages in an Appendix D row, found {len(values)}")
        label = match.group(1).casefold()
        response = {value.casefold(): key for key, value in RESPONSE_LABELS.items()}[label]
        rows.append((response, values))
    if len(rows) != len(ITEMS) * len(RESPONSES):
        raise ValueError(f"Expected 21 Appendix D Table 1 rows, found {len(rows)}")
    for index, (response, _) in enumerate(rows):
        if response != RESPONSES[index % len(RESPONSES)]:
            raise ValueError("Appendix D response row order is not Very/Somewhat/Not at all")
    return rows


def _round_percent(numerator: float, denominator: float) -> int:
    return math.floor(100.0 * numerator / denominator + 0.5)


def audit(puf_csv: Path, weighted_pdf: Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as error:  # pragma: no cover - exercised by CLI setup
        raise RuntimeError("Install the optional PDF parser: python -m pip install pypdf") from error

    reader = PdfReader(weighted_pdf)
    if len(reader.pages) < 4:
        raise ValueError("FHFA Appendix D has no Table 1 page")
    published = extract_table1_response_rows(reader.pages[3].extract_text() or "")
    # Purchase years occupy columns 0-10; refinance years occupy columns 11-21.
    published_by_field: dict[str, dict[tuple[str, str, str], int]] = {}
    for item_index, field in enumerate(ITEMS):
        field_values: dict[tuple[str, str, str], int] = {}
        for response_index, response in enumerate(RESPONSES):
            values = published[item_index * len(RESPONSES) + response_index][1]
            for year_index, year in enumerate(YEARS):
                field_values[(year, "purchase", response)] = values[year_index]
                field_values[(year, "refinance", response)] = values[year_index + len(YEARS)]
        published_by_field[field] = field_values

    weighted = defaultdict(float)
    denominator = defaultdict(float)
    row_count = 0
    with puf_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = csv.reader(stream)
        header = next(rows, [])
        positions = {name.casefold(): index for index, name in enumerate(header)}
        required = {"open_year", "x33", "analysis_weight", *ITEMS}
        if not required.issubset(positions):
            raise ValueError(f"PUF is missing benchmark fields: {sorted(required - positions.keys())}")
        if len(header) != 587 or len(positions) != 587:
            raise ValueError("Expected the 587-field NSMO v7.0 PUF")

        for row in rows:
            row_count += 1
            year = row[positions["open_year"]].strip()
            purpose_code = row[positions["x33"]].strip()
            purpose = "purchase" if purpose_code == "1" else "refinance" if purpose_code in {"2", "3", "4", "5"} else "other"
            if year not in YEARS or purpose not in PURPOSES:
                continue
            try:
                weight = float(row[positions["analysis_weight"]])
            except ValueError:
                continue
            if not math.isfinite(weight) or weight <= 0:
                continue
            for field in ITEMS:
                response = row[positions[field]].strip()
                if response not in RESPONSES:
                    continue
                key = (field, year, purpose)
                denominator[key] += weight
                weighted[(field, year, purpose, response)] += weight

    comparisons = []
    for field in ITEMS:
        for year in YEARS:
            for purpose in PURPOSES:
                den = denominator[(field, year, purpose)]
                if den <= 0:
                    raise ValueError(f"No valid weighted responses for {field}/{year}/{purpose}")
                for response in RESPONSES:
                    estimate = 100.0 * weighted[(field, year, purpose, response)] / den
                    published_value = published_by_field[field][(year, purpose, response)]
                    rounded = _round_percent(weighted[(field, year, purpose, response)], den)
                    comparisons.append({
                        "field": field,
                        "response_code": response,
                        "response_label": RESPONSE_LABELS[response],
                        "origination_year": int(year),
                        "loan_purpose_group": purpose,
                        "published_weighted_percent": published_value,
                        "recomputed_weighted_percent": round(estimate, 4),
                        "rounded_recomputed_percent": rounded,
                        "difference_percentage_points": round(estimate - published_value, 4),
                        "matches_published_after_rounding": rounded == published_value,
                        "valid_weight_sum": round(den, 2),
                    })

    exact = sum(item["matches_published_after_rounding"] for item in comparisons)
    max_abs_difference = max(abs(item["difference_percentage_points"]) for item in comparisons)
    return {
        "schema_version": "nsmo-weighted-tabulation-audit-v1",
        "status": "PASS" if exact == len(comparisons) else "REVIEW",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "puf_csv": {"bytes": puf_csv.stat().st_size, "sha256": _sha256(puf_csv)},
            "weighted_tabulations_pdf": {"bytes": weighted_pdf.stat().st_size, "sha256": _sha256(weighted_pdf)},
            "weighted_tabulations_url": "https://www.fhfa.gov/document/d/nsmo/nsmo-appendix-d-v70.pdf",
        },
        "scope": {
            "puf_rows_scanned": row_count,
            "fields_compared": list(ITEMS),
            "published_table": "Appendix D Table 1, Appendix D physical page 4 / printed page D-2",
            "published_groups": "Purchase (X33=1); refinance grouping covers X33=2-5 per FHFA Appendix D introduction",
            "denominator": "Positive finite Analysis_Weight on response codes 1-3, separately by item, origination year, and purpose group",
            "compared_cells": len(comparisons),
        },
        "validation": {
            "matches_after_whole_percent_rounding": exact,
            "mismatches_after_rounding": len(comparisons) - exact,
            "maximum_absolute_difference_percentage_points": round(max_abs_difference, 4),
            "analysis_weight_is_validated_for_this_selected_published_table": exact == len(comparisons),
        },
        "comparisons": comparisons,
        "limitations": [
            "This is a selected weighted consistency check, not a survey-design variance validation.",
            "The Appendix D percentages are rounded to whole percents and may not sum to 100 because of rounding.",
            "No unweighted results, row-level records, or individual identifiers are included.",
            "A matching descriptive benchmark does not define mortgage-performance risk sets, censoring, a PD target, or model suitability.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puf-csv", required=True, type=Path)
    parser.add_argument("--weighted-pdf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.puf_csv, args.weighted_pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "rows_scanned": report["scope"]["puf_rows_scanned"],
        "fields_compared": len(report["scope"]["fields_compared"]),
        "compared_cells": report["scope"]["compared_cells"],
        "matches_after_rounding": report["validation"]["matches_after_whole_percent_rounding"],
        "mismatches": report["validation"]["mismatches_after_rounding"],
        "max_abs_diff_pp": report["validation"]["maximum_absolute_difference_percentage_points"],
    }, indent=2))


if __name__ == "__main__":
    main()
