from decimal import Decimal

import pytest

from crsl.policy.uncertainty import paired_bootstrap


def rows():
    return [dict(loan_id=f'synthetic-{i:03}', principal=100 + i, target=i % 2,
                 landmark='2016-01-01', label_known_at='2017-02-01',
                 estimand='numeric_d3_before_prepayment', horizon_months=12,
                 baseline_selected=True, candidate_selected=i < 80) for i in range(100)]


def evaluate(data=None, **changes):
    settings = dict(seed=22, resamples=100, confidence='.95', evaluation_cutoff='2018-01-01',
                    evidence_class='synthetic_demo', minimum_events=10)
    return paired_bootstrap(rows() if data is None else data, **(settings | changes))


def test_identical_policies_have_exact_zero_paired_difference():
    result = evaluate([{**r, 'candidate_selected': True} for r in rows()])
    for metric in result['metrics'].values():
        assert Decimal(metric['candidate_minus_baseline']) == 0
        assert list(map(Decimal, metric['percentile_interval'])) == [0, 0]


def test_order_and_seed_reproducible_and_input_unchanged():
    data = rows()
    assert evaluate(data) == evaluate(list(reversed(data)))
    assert data == rows()
    result = evaluate(data)
    assert Decimal(result['metrics']['count_retention']['candidate_minus_baseline']) == Decimal('-.2')
    assert not result['policy_selection_performed']


def test_empty_selection_is_undefined_not_zero_risk():
    result = evaluate([{**r, 'candidate_selected': False} for r in rows()])
    risk = result['metrics']['selected_event_rate']
    assert risk['candidate'] is None and risk['percentile_interval'] is None
    assert risk['undefined_resamples'] == 100
    assert result['metrics']['count_retention']['candidate_minus_baseline'] == '-1'


def test_rare_events_suppress_risk_interval_not_volume():
    result = evaluate(minimum_events=50)
    assert result['metrics']['selected_event_rate']['percentile_interval'] is None
    assert result['metrics']['principal_retention']['percentile_interval'] is not None


@pytest.mark.parametrize('change', [dict(target=None), dict(target=True), dict(principal=0),
    dict(label_known_at='2018-01-01'), dict(label_known_at='2015-01-01'),
    dict(horizon_months=24), dict(candidate_selected=1)])
def test_invalid_cohort_never_silently_dropped(change):
    data = rows()
    data[0].update(change)
    with pytest.raises(ValueError):
        evaluate(data)


def test_duplicate_loans_rejected():
    with pytest.raises(ValueError, match='One origination'):
        evaluate(rows() + rows()[:1])
