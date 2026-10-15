import pytest

from credit_atlas.monitoring import build


def sample():
    return {"case_id": "SYNTHETIC", "pipeline_run": "SYNTHETIC",
            "snapshot": {"loans": 10, "monthly": [{"period": "2020-01-01"}]},
            "source_quality": {"technical_profile": {
                "duplicate_origination_keys": 0, "duplicate_monthly_keys": 0,
                "orphan_performance_rows": 0, "loans_without_performance": 2, "loans_with_gaps": 1},
                "canonical_missing_counts": {"vantagescore": 10, "original_dti": 3}},
            "model_readiness": {"actual_model_fit": False, "missing_years": [2014],
                                "blocking_reasons": ["missing_required_vintages"]}}


def test_source_coverage_is_not_claimed_as_drift_or_calibration_failure():
    result = build(sample())
    fields = {r["field"]: r for r in result["field_availability"]}
    assert fields["vantagescore"]["status"] == "no_usable_values"
    assert fields["original_dti"]["missing_share"] == .3
    assert result["model_monitoring"]["calibration_alert"] is None
    assert result["model_monitoring"]["drift_alert"] is None
    assert result["reporting_coverage"]["freshness_status"] == "frozen_historical_source_not_live_feed"


def test_duplicate_key_is_an_integrity_issue_not_a_model_alarm():
    data = sample()
    data["source_quality"]["technical_profile"]["duplicate_monthly_keys"] = 1
    checks = {r["check"]: r for r in build(data)["integrity_checks"]}
    assert checks["duplicate_monthly_keys"]["status"] == "investigate"
    assert checks["loans_with_gaps"]["status"] == "observed"


@pytest.mark.parametrize("count", [-1, 11, True])
def test_impossible_missingness_is_rejected(count):
    data = sample()
    data["source_quality"]["canonical_missing_counts"]["original_dti"] = count
    with pytest.raises(ValueError):
        build(data)
