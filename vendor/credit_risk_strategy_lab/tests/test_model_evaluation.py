import math

import pytest
pytest.importorskip('sklearn')

from crsl.models.evaluation import evaluate_probabilities


def rows():
    return [dict(loan_id=str(i), partition='validation', included=True,
        target=y, pd=p, landmark='2016-01-01', score_available_at='2016-01-01',
        label_known_month='2017-01-01', score_sha256='a' * 64) for i, (y, p) in enumerate([(0,.1),(0,.4),(1,.35),(1,.8)])]


def evaluate(data=None, **changes):
    return evaluate_probabilities(rows() if data is None else data, **(dict(
        evaluation_cutoff='2018-01-01', bin_edges=['0','.2','.5','1'], minimum_events=1) | changes))


def test_known_metrics_and_reliability_reconcile():
    result = evaluate()
    assert result['roc_auc'] == .75
    assert result['average_precision'] == pytest.approx(5 / 6)
    assert result['brier_score'] == pytest.approx(.158125)
    assert [r['loans'] for r in result['reliability']] == [1, 2, 1]
    assert sum(r['events'] for r in result['reliability']) == 2


def test_empty_bins_are_null_and_edges_are_unique():
    data = [{**r, 'pd': 1 if r['target'] else 0} for r in rows()]
    result = evaluate(data)
    assert result['reliability'][1]['mean_pd'] is None
    assert result['reliability'][1]['event_rate'] is None
    assert result['brier_score'] == 0
    assert result['log_loss_clipped_predictions'] == 4
    assert math.isfinite(result['log_loss'])
    assert evaluate([{**r, 'pd': .2} for r in rows()])['reliability'][1]['loans'] == 4


def test_support_suppresses_discrimination_not_hides_counts():
    result = evaluate(minimum_events=50)
    assert result['roc_auc'] is None and result['average_precision'] is None
    assert result['loans'] == 4 and result['events'] == 2


@pytest.mark.parametrize('change', [dict(partition='test'), dict(included=False), dict(target=None),
    dict(pd='NaN'), dict(pd=True), dict(score_available_at='2016-02-01'),
    dict(label_known_month='2018-01-01'), dict(score_sha256='b' * 64)])
def test_invalid_or_leaking_records_fail(change):
    data = rows()
    data[0].update(change)
    with pytest.raises(ValueError):
        evaluate(data)


def test_invalid_bins_duplicate_loans_and_empty_inputs_fail():
    for bins in (['0','.5','.5','1'], ['.1','1'], ['0','NaN','1']):
        with pytest.raises(ValueError):
            evaluate(bin_edges=bins)
    with pytest.raises(ValueError):
        evaluate(rows() * 2)
    with pytest.raises(ValueError):
        evaluate([])
