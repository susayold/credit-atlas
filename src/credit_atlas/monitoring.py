"""Descriptive monitoring from frozen evidence, separate from live model drift."""
from __future__ import annotations

VERSION = "d01-frozen-quality-monitor-v1"


def build(snapshot: dict) -> dict:
    profile = snapshot["source_quality"]["technical_profile"]
    count = snapshot["snapshot"]["loans"]
    checks = []
    for field in ["duplicate_origination_keys", "duplicate_monthly_keys", "orphan_performance_rows"]:
        value = profile[field]
        checks.append({"check": field, "value": value, "status": "pass" if value == 0 else "investigate",
                       "action": "If nonzero, stop dependent analytics; inspect source keys and parent joins."})
    for field in ["loans_without_performance", "loans_with_gaps"]:
        value = profile[field]
        checks.append({"check": field, "value": value, "status": "observed" if value else "pass",
                       "action": "Inspect observation/censoring exclusions; do not fill absent performance as current."})
    availability = []
    for field, missing in snapshot["source_quality"]["canonical_missing_counts"].items():
        if type(missing) is not int or not 0 <= missing <= count:
            raise ValueError("Missingness counts must reconcile to the loan population")
        availability.append({"field": field, "missing": missing, "population": count,
                             "missing_share": missing / count if count else None,
                             "status": "no_usable_values" if count and missing == count else
                                       "partial_availability" if missing else "complete",
                             "interpretation": "Availability in this frozen source; a causal reason or drift is not established."})
    monthly = snapshot["snapshot"]["monthly"]
    readiness = snapshot["model_readiness"]
    return {"schema_version": 1, "method_version": VERSION, "case_id": snapshot["case_id"],
            "pipeline_run": snapshot["pipeline_run"], "scope": "whole_frozen_sample",
            "integrity_checks": checks, "field_availability": availability,
            "reporting_coverage": {"first_month": monthly[0]["period"] if monthly else None,
                                   "last_month": monthly[-1]["period"] if monthly else None,
                                   "months_observed": len(monthly),
                                   "freshness_status": "frozen_historical_source_not_live_feed",
                                   "action": "Compare release/cutoff metadata when acquiring a new snapshot; calendar age alone is not a source-lag alert."},
            "model_monitoring": {"status": "unavailable_no_validated_model" if not readiness["actual_model_fit"]
                                else "requires_mature_labels_and_reference_cohort",
                                "missing_vintages": readiness["missing_years"],
                                "blocking_reasons": readiness["blocking_reasons"],
                                "calibration_alert": None, "drift_alert": None},
            "investigation_order": ["Verify source release/hash/layout and serving lineage.",
                                   "Review key/gap/sentinel diagnostics and feature coverage.",
                                   "Review eligible/outcome support by vintage and Relief.",
                                   "Only compare drift with a compatible frozen reference population.",
                                   "Only evaluate calibration when a validated model and mature labels exist."],
            "visibility": "private", "public_release_approved": False}
