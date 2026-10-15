"""Build a field-level, conservative predictor-gate inventory from the NSMO dictionary."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


OUTPUT_FIELDS = [
    "codebook_order", "csv_column", "codebook_name", "field_family", "timing_class",
    "publisher_predictor_gate", "eligibility_bucket", "intended_scope", "decision_status",
    "required_review", "sas_label",
]


def classify(field: dict[str, str]) -> dict[str, str]:
    name = field["csv_column"]
    family = field["field_family"]
    timing = field["timing_class"]
    bucket = ""
    scope = ""
    review = ""

    if family == "sample_identifier":
        bucket, scope, review = "IDENTIFIER_EXCLUDE", "Never a model feature", "Use only for controlled joins/deduplication; remove before modeling or display."
    elif family == "survey_wave":
        bucket, scope, review = "COHORT_AND_STRATIFICATION_ONLY", "Cohort, trend, or temporal split", "Do not interpret wave as borrower risk; report wave-level selection and mode limitations."
    elif family == "analysis_weight":
        bucket, scope, review = "ESTIMATION_WEIGHT_ONLY", "Survey estimation after design review", "Never a predictor; confirm estimand, weight construction, and variance method before inference."
    elif family == "survey_response":
        bucket, scope, review = "POST_ORIGINATION_RESPONSE_EXCLUDE", "Descriptive survey analysis only", "Collected after mortgage origination; respondent and questionnaire/mode selection; not application-time predictors."
    elif family == "mortgage_termination":
        bucket, scope, review = "COMPETING_EVENT_OR_CENSOR_ONLY", "Outcome/censoring construction", "Do not use as predictor; define competing event and observation cutoff before target creation."
    elif family == "quarterly_performance_status":
        bucket, scope, review = "OUTCOME_HISTORY_OR_LAGGED_ONLY", "Target or strictly prior dynamic history", "Never use same-quarter/future status as a feature; freeze index date, lag rule, and event/censor definitions first."
    elif family == "quarterly_credit_score":
        bucket, scope, review = "DYNAMIC_CANDIDATE_ASOF", "Dynamic monitoring only", "Verify score observation/as-of date and borrower role; use only information available at or before index; exclude future quarters."
    elif family == "quarterly_forbearance":
        bucket, scope, review = "DYNAMIC_CANDIDATE_ASOF", "Dynamic monitoring only", "Verify response timing, known-response denominator, missingness, and availability before index; never origination-time."
    elif family == "quarterly_mark_to_market_ltv":
        bucket, scope, review = "DYNAMIC_CANDIDATE_LOOKAHEAD_REVIEW", "Dynamic monitoring only", "Verify valuation date, refresh lag, and lookahead; only a value available before index may be considered."
    elif family == "origination_credit_score":
        bucket, scope = "ORIGINATION_CANDIDATE_REVIEW", "Origination-time candidate; not approved"
        review = "Verify score vintage/as-of date, respondent/co-borrower role, missingness and bins; label as VantageScore 3.0, never FICO."
    elif family == "cashout_refinance_flag":
        bucket, scope = "ORIGINATION_CANDIDATE_DEFINITION_REVIEW", "Origination-time candidate; not approved"
        review = "Confirm cash-out definition, decision-time availability, intended population and missingness before feature use."
    elif family == "origination_mortgage_or_borrower_attribute":
        if name in {"open_year", "open_month"}:
            bucket, scope = "COHORT_AND_TIME_CONTROL_ONLY", "Cohort, temporal split, or calendar control"
            review = "Use to define origination cohort/time split; do not treat calendar time alone as borrower creditworthiness."
        elif name.startswith(("age_", "sex_")) or name == "metro_lmi":
            bucket, scope = "SENSITIVE_OR_PROXY_POLICY_REVIEW", "No decision-feature use pending governance review"
            review = "Requires independent fair-lending, legal, and policy review; keep segregated from model features unless explicitly approved."
        else:
            bucket, scope = "ORIGINATION_CANDIDATE_REVIEW", "Origination-time candidate; not approved"
            review = "Verify the exact attribute was available at the intended decision point, definitions, role, missingness, selection, and permitted use."
    else:
        raise ValueError(f"Unclassified NSMO field family: {family} ({name})")

    if bucket in {
        "ORIGINATION_CANDIDATE_REVIEW", "ORIGINATION_CANDIDATE_DEFINITION_REVIEW",
        "DYNAMIC_CANDIDATE_ASOF", "DYNAMIC_CANDIDATE_LOOKAHEAD_REVIEW",
    }:
        decision = "NOT_APPROVED_TARGET_AND_POLICY_GATES_OPEN"
    elif bucket == "SENSITIVE_OR_PROXY_POLICY_REVIEW":
        decision = "NOT_APPROVED_GOVERNANCE_REVIEW_REQUIRED"
    else:
        decision = "AUXILIARY_ONLY_OR_EXCLUDED_FROM_FEATURES"

    return {
        **field,
        "publisher_predictor_gate": field["predictor_use"],
        "eligibility_bucket": bucket,
        "intended_scope": scope,
        "decision_status": decision,
        "required_review": review,
    }


def build(source: Path, output: Path) -> dict:
    with source.open(encoding="utf-8-sig", newline="") as stream:
        fields = list(csv.DictReader(stream))
    if len(fields) != 587 or len({row["csv_column"].casefold() for row in fields}) != 587:
        raise ValueError("Expected the reviewed 587-field NSMO v7.0 dictionary")
    rows = [classify(field) for field in fields]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows({key: row[key] for key in OUTPUT_FIELDS} for row in rows)
    from collections import Counter

    return {"rows": len(rows), "eligibility_buckets": dict(sorted(Counter(row["eligibility_bucket"] for row in rows).items())),
            "decision_statuses": dict(sorted(Counter(row["decision_status"] for row in rows).items()))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path, default=Path("docs/data/nsmo-v70-field-dictionary.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/data/nsmo-v70-predictor-gates.csv"))
    args = parser.parse_args()
    result = build(args.dictionary, args.output)
    print(result)


if __name__ == "__main__":
    main()
