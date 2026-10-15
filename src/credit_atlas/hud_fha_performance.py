"""Curated public FHA aggregate benchmark transcribed from the HUD monthly PDF."""

from __future__ import annotations

import csv
import re
from pathlib import Path


REPORT_URL = "https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf"
INDEX_URL = "https://www.hud.gov/hud-partners/single-family-loan-performance"

MONTH_FIELDS = {
    "month", "adjustment", "active_iif_count", "delinquency_30d_pct",
    "delinquency_60d_pct", "delinquency_90d_pct", "foreclosure_pct",
    "bankruptcy_pct", "serious_delinquency_pct", "source_table", "source_page",
}
SUBGROUP_FIELDS = {
    "dimension", "parent_category", "category", "iif_count", "iif_share_pct",
    "share_denominator", "all_past_due_pct",
    "delinquency_30d_pct", "delinquency_60d_pct", "delinquency_90plus_pct",
    "foreclosure_pct", "bankruptcy_pct", "serious_delinquency_pct",
    "source_table", "source_page",
}
RATE_FIELDS = {
    "delinquency_30d_pct", "delinquency_60d_pct", "delinquency_90d_pct",
    "delinquency_90plus_pct", "foreclosure_pct", "bankruptcy_pct",
    "serious_delinquency_pct", "all_past_due_pct", "iif_share_pct",
}
MONTHS = [f"{year}-{month:02d}" for year, month in
          [(2025, month) for month in range(8, 13)] + [(2026, month) for month in range(1, 9)]]


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"Unexpected HUD FHA aggregate schema: {path.name}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"HUD FHA aggregate source is empty: {path.name}")
    return rows


def hud_fha_performance_report(root: Path) -> dict:
    """Load and validate the separately scoped HUD FHA public aggregates."""
    base = root / "docs" / "data"
    monthly = _read_csv(base / "hud-fha-performance-2026-08.csv", MONTH_FIELDS)
    subgroups = _read_csv(base / "hud-fha-performance-2026-08-subgroups.csv", SUBGROUP_FIELDS)
    if len(monthly) != 26 or {r["adjustment"] for r in monthly} != {"NSA", "SA"}:
        raise ValueError("HUD FHA monthly table must contain 13 NSA and 13 SA observations")
    for adjustment in ("NSA", "SA"):
        series = [row for row in monthly if row["adjustment"] == adjustment]
        if [row["month"] for row in series] != MONTHS:
            raise ValueError("HUD FHA monthly coverage is incomplete or out of order")
    expected_dimensions = {
        "loan_purpose", "refinance", "credit_score", "fiscal_year_cohort",
        "origination_loan_amount", "property_type", "purchase_loan_type",
        "down_payment_assistance",
    }
    if len(subgroups) != 60 or {row["dimension"] for row in subgroups} != expected_dimensions:
        raise ValueError("HUD FHA subgroup table has unexpected coverage")

    def numbers(rows: list[dict[str, str]]) -> list[dict]:
        output = []
        for row in rows:
            converted = dict(row)
            for key, value in row.items():
                if value == "":
                    converted[key] = None
                    continue
                if key in RATE_FIELDS and value != "":
                    number = float(value)
                    if not 0 <= number <= 100:
                        raise ValueError(f"HUD FHA rate outside percentage bounds: {key}")
                    converted[key] = number
            for key in ("active_iif_count", "iif_count", "source_table", "source_page"):
                if key in row and row[key] != "":
                    if not re.fullmatch(r"\d+", row[key]):
                        raise ValueError(f"HUD FHA count/page is not an integer: {key}")
                    converted[key] = int(row[key])
            output.append(converted)
        return output

    monthly_rows = numbers(monthly)
    subgroup_rows = numbers(subgroups)
    latest = {adjustment: next(row for row in reversed(monthly_rows)
                               if row["adjustment"] == adjustment)
              for adjustment in ("NSA", "SA")}
    return {
        "schema_version": "hud-fha-performance-aggregate-v1",
        "status": "AVAILABLE",
        "source": {
            "title": "FHA Single-Family Loan Performance Trends — August 2026",
            "publisher": "U.S. Department of Housing and Urban Development / FHA",
            "published": "2026-09",
            "report_month": "2026-08",
            "index_url": INDEX_URL,
            "report_url": REPORT_URL,
            "extraction": "Values transcribed from official HUD PDF text, Table 1 (page 2) and Table 3 (pages 4–5); source PDF was not downloaded into the repository.",
            "raw_pdf_sha256": None,
        },
        "monthly": monthly_rows,
        "latest": latest,
        "subgroups": subgroup_rows,
        "definitions": {
            "active_iif_count": "Active Insurance in Force count at end of month (EOM).",
            "delinquency_90d_pct": "At least three months delinquent, excluding loans in foreclosure or bankruptcy processing.",
            "serious_delinquency_pct": "90+ day delinquency plus in-foreclosure plus in-bankruptcy rates.",
            "subgroup_denominator": "HUD Table 3 delinquency rates are percentages of active loan counts. IIF shares use the panel-specific denominator recorded on each row; some panels (such as refinance and fully-underwritten credit-score ranges) do not sum to the overall IIF population.",
            "credit_score_coverage": "Credit-score reporting became mandatory in July 2008; streamline refinance loans do not require credit-score reporting and are excluded from the credit-score range panel.",
            "cohort_comparison": "Fiscal-year cohorts are active portfolio snapshots as of August 2026, not cumulative lifetime default curves; the 2026 cohort has shorter exposure time.",
        },
        "limitations": [
            "This is an FHA program portfolio aggregate benchmark, not NSMO or Freddie Mac loan-level data; do not pool it into either sample.",
            "Monthly rates are descriptive portfolio KPIs and do not provide borrower-level outcomes, event timing, or model training rows.",
            "HUD notes reporting-method differences may prevent full reconciliation with other FHA reporting areas.",
            "Table 3 subgroup comparisons are unadjusted and use active-loan denominators; they do not establish causal effects.",
            "IIF share figures are rounded as published; nested refinance rows overlap by design and must not be added to their parent categories.",
            "The 2026 origination fiscal-year cohort is incomplete at the August report date and has shorter exposure time than prior cohorts.",
            "Credit-score coverage differs by reporting availability; streamline refinances are excluded from the score-range panel.",
            "The checked PDF text was publicly accessible through the official HUD report page, while direct binary retrieval returned HTTP 403; no raw PDF hash is claimed.",
        ],
    }
