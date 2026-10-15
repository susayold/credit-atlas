"""Positional staging contract, cross-checked against July 2026 official headers/layout.

All staged fields remain strings. Numeric conversion here is validation only.
No global sentinel replacement, target construction or loss arithmetic.
"""
from __future__ import annotations
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

SCHEMA_VERSION = "sfll_47_july2026"
ORIGINATION = (
    "classic_fico", "first_payment_date", "first_time_homebuyer", "maturity_date",
    "msa", "mi_percent", "units", "occupancy", "original_cltv", "original_dti",
    "original_upb", "original_ltv", "original_interest_rate", "channel",
    "prepayment_penalty", "amortization_type", "property_state", "property_type",
    "postal_code", "loan_id", "loan_purpose", "original_term", "borrowers",
    "seller", "super_conforming", "pre_harp_id", "special_eligibility",
    "harp", "property_valuation_method", "interest_only", "vantagescore")
PERFORMANCE = (
    "loan_id", "period", "current_upb", "delinquency", "loan_age", "remaining_months",
    "defect_settlement_date", "modification", "zero_balance_code",
    "zero_balance_date", "current_rate", "non_interest_bearing_upb", "ddlpi",
    "mi_recoveries", "net_sales_proceeds", "non_mi_recoveries", "total_expenses",
    "legal_costs", "maintenance_costs", "taxes_insurance", "misc_expenses",
    "actual_loss", "cumulative_modification_costs", "rate_step", "payment_deferral",
    "eltv", "removal_upb", "delinquent_accrued_interest", "disaster",
    "assistance", "current_modification_costs", "interest_bearing_upb",
    "mi_cancellation", "servicer", "bankruptcy_cramdown_costs")
ORIG_DATES = {"first_payment_date", "maturity_date"}
PERF_DATES = {"period", "defect_settlement_date", "zero_balance_date", "ddlpi"}
ORIG_NUMERIC = {"classic_fico", "msa", "mi_percent", "units", "original_cltv",
    "original_dti", "original_upb", "original_ltv", "original_interest_rate",
    "original_term", "borrowers", "property_valuation_method", "vantagescore"}
PERF_NUMERIC = {"current_upb", "loan_age", "remaining_months", "current_rate",
    "non_interest_bearing_upb", "mi_recoveries", "non_mi_recoveries", "total_expenses",
    "legal_costs", "maintenance_costs", "taxes_insurance", "misc_expenses",
    "actual_loss", "cumulative_modification_costs", "eltv", "removal_upb",
    "delinquent_accrued_interest", "current_modification_costs",
    "interest_bearing_upb", "bankruptcy_cramdown_costs"}
DELINQUENCY_CODES = {f"{n:02d}" for n in range(100)} | {"RA", "XX"}
# Raw codes preserved. Their label/credit-event classification is not implemented.
ZERO_BALANCE_CODES = {"", "01", "02", "03", "09", "15", "16", "96"}

def fields_for(table: str) -> tuple[str, ...]:
    if table == "origination":
        return ORIGINATION
    if table == "performance":
        return PERFORMANCE
    raise ValueError("Unknown table")

def validate_row(values: list[str], table: str, *, format_example: bool = False) -> list[str]:
    fields = fields_for(table)
    if len(values) != len(fields):
        return [f"field_count_expected_{len(fields)}_got_{len(values)}"]
    row = dict(zip(fields, values))
    errors = []
    loan = row["loan_id"].strip()
    # The official format-example ZIP uses Q5/Q6 identifiers. Permit that exact
    # documented fixture deviation ONLY in format mode, never annual research.
    pattern = r"[FA]\d{2}Q[1-6]\d{7}" if format_example else r"[FA]\d{2}Q[1-4]\d{7}"
    if not re.fullmatch(pattern, loan):
        errors.append("loan_id_format")
    date_fields = ORIG_DATES if table == "origination" else PERF_DATES
    for name in date_fields:
        value = row[name].strip()
        if not value:
            if name == "period":
                errors.append("period_required")
            continue
        try:
            if not re.fullmatch(r"\d{6}", value):
                raise ValueError()
            datetime.strptime(value, "%Y%m")
        except ValueError:
            errors.append(name + "_invalid_month")
    for name in ORIG_NUMERIC if table == "origination" else PERF_NUMERIC:
        value = row[name].strip()
        if not value:
            continue
        try:
            number = Decimal(value)
            if not number.is_finite():
                raise InvalidOperation()
        except InvalidOperation:
            errors.append(name + "_invalid_numeric")
    if table == "performance":
        if row["delinquency"].strip() not in DELINQUENCY_CODES:
            errors.append("delinquency_unknown")
        if row["zero_balance_code"].strip() not in ZERO_BALANCE_CODES:
            errors.append("zero_balance_code_unknown")
    else:
        for name in ("classic_fico", "vantagescore"):
            value = row[name].strip()
            if value:
                try:
                    number = Decimal(value)
                    if (not number.is_finite() or number != number.to_integral_value()
                            or not (300 <= number <= 850 or number == 9999)):
                        errors.append(name + "_invalid_domain")
                except InvalidOperation:
                    pass  # numeric validator already records this error
        if row["amortization_type"].strip() not in {"FRM", "ARM"}:
            errors.append("amortization_type_unknown")
    return sorted(errors)
