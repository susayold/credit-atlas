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
REASON_FIELDS = {
    "fiscal_period", "new_90plus_count", "reduction_income_pct", "unemployed_pct",
    "excessive_obligations_pct", "death_illness_pct", "marital_difficulties_pct",
    "no_contact_pct", "national_emergency_pct", "other_pct", "source_table",
    "source_page", "partial_period",
}
FORECLOSURE_FIELDS = {
    "fiscal_year", "month", "active_iif_count", "foreclosure_starts",
    "in_foreclosure_count", "foreclosure_claims_paid", "foreclosure_starts_6m_moving_avg",
    "annualized_foreclosure_rate_pct", "source_table", "source_page",
}
RECOVERY_FIELDS = {
    "state_or_territory", "dispositions_jul2026", "recovery_jul2026_pct",
    "recovery_jun2026_pct", "recovery_jul2025_pct", "change_from_jun2026_pp",
    "change_from_jul2025_pp", "source_table", "source_page",
}
LOSS_FIELDS = {
    "disposition_month", "claim_expenses_pct", "holding_costs_pct", "loss_on_collateral_pct",
    "sales_expense_pct", "program_discounts_pct", "net_loss_rate_pct", "average_dollar_loss",
    "average_unpaid_balance", "dispositions", "discounts", "delinquency_stage_months",
    "foreclosure_stage_months", "deed_transfer_stage_months", "reo_stage_months",
    "all_stages_months", "source_table", "source_page",
}
RATE_FIELDS = {
    "delinquency_30d_pct", "delinquency_60d_pct", "delinquency_90d_pct",
    "delinquency_90plus_pct", "foreclosure_pct", "bankruptcy_pct",
    "serious_delinquency_pct", "all_past_due_pct", "iif_share_pct",
    "reduction_income_pct", "unemployed_pct", "excessive_obligations_pct",
    "death_illness_pct", "marital_difficulties_pct", "no_contact_pct",
    "national_emergency_pct", "other_pct", "annualized_foreclosure_rate_pct",
    "claim_expenses_pct",
    "holding_costs_pct", "loss_on_collateral_pct", "sales_expense_pct",
    "program_discounts_pct", "net_loss_rate_pct",
}
COUNT_FIELDS = {
    "active_iif_count", "iif_count", "source_table", "source_page", "new_90plus_count",
    "fiscal_year", "foreclosure_starts", "in_foreclosure_count", "foreclosure_claims_paid",
    "foreclosure_starts_6m_moving_avg", "dispositions_jul2026", "average_dollar_loss",
    "average_unpaid_balance", "dispositions", "discounts",
}
UNBOUNDED_RATE_FIELDS = {"recovery_jul2026_pct", "recovery_jun2026_pct", "recovery_jul2025_pct"}
SIGNED_CHANGE_FIELDS = {"change_from_jun2026_pp", "change_from_jul2025_pp"}
TIME_FIELDS = {
    "delinquency_stage_months", "foreclosure_stage_months", "deed_transfer_stage_months",
    "reo_stage_months", "all_stages_months",
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
    reasons = _read_csv(base / "hud-fha-new-90plus-reasons-2026-08.csv", REASON_FIELDS)
    foreclosure = _read_csv(base / "hud-fha-foreclosure-statistics-2026-08.csv", FORECLOSURE_FIELDS)
    recovery = _read_csv(base / "hud-fha-reo-recovery-2026-08.csv", RECOVERY_FIELDS)
    loss_components = _read_csv(base / "hud-fha-reo-loss-components-2026-08.csv", LOSS_FIELDS)
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
    if len(reasons) != 22 or [row["fiscal_period"] for row in reasons[:3]] != ["2021 Q4", "2022 Q1", "2022 Q2"]:
        raise ValueError("HUD FHA new-90+ reason table has unexpected coverage")
    reason_rate_fields = RATE_FIELDS & REASON_FIELDS
    if any(abs(sum(float(row[field]) for field in reason_rate_fields) - 100) > 0.03 for row in reasons):
        raise ValueError("HUD FHA reason shares do not reconcile to 100 percent")
    if len(foreclosure) != 37 or (foreclosure[0]["fiscal_year"], foreclosure[0]["month"]) != ("2023", "Aug"):
        raise ValueError("HUD FHA foreclosure time series has unexpected coverage")
    if (foreclosure[-1]["fiscal_year"], foreclosure[-1]["month"]) != ("2026", "Aug"):
        raise ValueError("HUD FHA foreclosure time series has unexpected endpoint")
    if len(recovery) != 50 or len({row["state_or_territory"] for row in recovery}) != len(recovery):
        raise ValueError("HUD FHA REO recovery table has unexpected geography coverage")
    if (recovery[0]["state_or_territory"], recovery[0]["dispositions_jul2026"],
            recovery[0]["recovery_jul2026_pct"]) != ("US", "392", "50.5"):
        raise ValueError("HUD FHA REO recovery national row does not match the report")
    if len(loss_components) != 13 or loss_components[0]["disposition_month"] != "2026-07":
        raise ValueError("HUD FHA REO loss table has unexpected monthly coverage")

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
                elif key in UNBOUNDED_RATE_FIELDS | SIGNED_CHANGE_FIELDS | TIME_FIELDS:
                    converted[key] = float(value)
            for key in COUNT_FIELDS:
                if key in row and row[key] != "":
                    if not re.fullmatch(r"\d+", row[key]):
                        raise ValueError(f"HUD FHA count/page is not an integer: {key}")
                    converted[key] = int(row[key])
            output.append(converted)
        return output

    monthly_rows = numbers(monthly)
    subgroup_rows = numbers(subgroups)
    reason_rows = numbers(reasons)
    foreclosure_rows = numbers(foreclosure)
    recovery_rows = numbers(recovery)
    loss_rows = numbers(loss_components)
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
            "extraction": "Values transcribed from official HUD PDF text, Tables 1–6 (report pages 2–8); source PDF was not downloaded into the repository.",
            "raw_pdf_sha256": None,
        },
        "monthly": monthly_rows,
        "latest": latest,
        "subgroups": subgroup_rows,
        "new_90plus_reasons": reason_rows,
        "foreclosure_statistics": foreclosure_rows,
        "reo_recovery": recovery_rows,
        "reo_loss_components": loss_rows,
        "definitions": {
            "active_iif_count": "Active Insurance in Force count at end of month (EOM).",
            "delinquency_90d_pct": "At least three months delinquent, excluding loans in foreclosure or bankruptcy processing.",
            "serious_delinquency_pct": "90+ day delinquency plus in-foreclosure plus in-bankruptcy rates.",
            "subgroup_denominator": "HUD Table 3 delinquency rates are percentages of active loan counts. IIF shares use the panel-specific denominator recorded on each row; some panels (such as refinance and fully-underwritten credit-score ranges) do not sum to the overall IIF population.",
            "credit_score_coverage": "Credit-score reporting became mandatory in July 2008; streamline refinance loans do not require credit-score reporting and are excluded from the credit-score range panel.",
            "cohort_comparison": "Fiscal-year cohorts are active portfolio snapshots as of August 2026, not cumulative lifetime default curves; the 2026 cohort has shorter exposure time.",
            "new_90plus_reasons": "HUD Table 2 gives the distribution of reported reasons for newly 90+ loans; shares sum to 100% and are descriptive, not predictor importance or causal drivers.",
            "foreclosure_starts": "Monthly inflow into foreclosure; distinct from the in-foreclosure stock and claims paid.",
            "annualized_foreclosure_rate_pct": "HUD Table 4 annualizes monthly foreclosure claims over beginning insurance-in-force; it is not the in-foreclosure portfolio share.",
            "reo_recovery_pct": "HUD Table 5 recovery as a percentage of unpaid principal balance at default; may exceed 100%, and small disposition counts can create volatile geography rates.",
            "reo_recovery_change_pp": "Difference between reported recovery rates in percentage points; negative values indicate a decline.",
            "reo_loss_components": "HUD Table 6 loss/cost components, amounts, counts and stage durations; components are not exhaustive and do not sum to net loss.",
        },
        "limitations": [
            "This is an FHA program portfolio aggregate benchmark, not NSMO or Freddie Mac loan-level data; do not pool it into either sample.",
            "Monthly rates are descriptive portfolio KPIs and do not provide borrower-level outcomes, event timing, or model training rows.",
            "HUD notes reporting-method differences may prevent full reconciliation with other FHA reporting areas.",
            "Table 3 subgroup comparisons are unadjusted and use active-loan denominators; they do not establish causal effects.",
            "IIF share figures are rounded as published; nested refinance rows overlap by design and must not be added to their parent categories.",
            "The 2026 origination fiscal-year cohort is incomplete at the August report date and has shorter exposure time than prior cohorts.",
            "New 90+ reason shares describe HUD's reported categories, not independent predictors or causal attributions; July and August 2026 are partial fiscal-quarter observations.",
            "Foreclosure starts, in-foreclosure stock, claims paid and annualized foreclosure rate are separate flow, stock and rate measures.",
            "REO recovery values can exceed 100% and may be volatile for geographies with few dispositions; REO cost components should not be added together as a net-loss decomposition.",
            "Credit-score coverage differs by reporting availability; streamline refinances are excluded from the score-range panel.",
            "The checked PDF text was publicly accessible through the official HUD report page, while direct binary retrieval returned HTTP 403; no raw PDF hash is claimed.",
        ],
    }
