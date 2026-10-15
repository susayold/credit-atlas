import pytest

from crsl.monitoring import categorical_drift, freshness, mature_label_rate, missingness, triage_incident


def test_freshness_and_missingness_are_explicit():
    assert freshness('2024-01-01', '2024-01-10', max_age_days=10)['status'] == 'pass'
    result = missingness([None, 1, None, 2], field='score', minimum_support=1, warning_rate=.25, block_rate=.75)
    assert result['status'] == 'warning' and result['missing_rate'] == .5


def test_drift_does_not_alert_on_low_support():
    result = categorical_drift(['a', 'a'], ['b', 'b'], minimum_support=3)
    assert result['status'] == 'insufficient_support' and result['score'] is None


def test_mature_rate_excludes_immature_targets():
    result = mature_label_rate([{'mature': True, 'target': 1}, {'mature': False, 'target': 0}, {'mature': True, 'target': 0}], minimum_support=1)
    assert result['event_rate'] == pytest.approx(0.5)
    assert result['immature_or_unavailable_excluded'] == 1


def test_failed_check_rolls_back_only_synthetic_config():
    result = triage_incident(incident_type='missing_field', current_config_hash='new', previous_config_hash='old', checks={'schema': False, 'freshness': True})
    assert result['action'] == 'rollback_to_previous_config'
    assert result['selected_config_hash'] == 'old' and result['synthetic'] is True
