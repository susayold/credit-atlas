from datetime import date

import pytest
pytest.importorskip('sklearn')

from crsl.models.tuning import tune_logistic

FEATURES = {'numeric': ['classic_fico'], 'categorical': []}
FOLDS = [dict(fit_cutoff='2008-01-01', holdout_landmark_end='2009-01-01', evaluation_cutoff='2010-01-01'),
         dict(fit_cutoff='2010-01-01', holdout_landmark_end='2011-01-01', evaluation_cutoff='2012-01-01')]


def rows():
    return [dict(loan_id=f'synthetic-{year}-{i}', partition='train', included=True,
        classic_fico=600+i, target=int(i % 3 == 0), landmark=date(year,1,1),
        label_known_month=date(year+1,1,1)) for year in (2006,2008,2010,2012) for i in range(30)]


def tune(data=None, **changes):
    return tune_logistic(rows() if data is None else data, FEATURES, **(dict(
        outer_fit_cutoff='2014-01-01', folds=FOLDS, C_grid=['.1','1'],
        evidence_class='synthetic_demo', minimum_train_class=5, minimum_holdout_class=5) | changes))


def test_training_only_temporal_grid_and_fresh_encoders():
    data = rows()
    result = tune(data)
    assert result['status'] == 'training_selection_complete'
    assert result['selected_C'] in ('.1', '0.1', '1')
    assert len(result['candidates']) == 2
    for candidate in result['candidates']:
        assert [f['encoder_fit_rows'] for f in candidate['folds']] == [30,60]
        assert candidate['pooled_holdout_log_loss'] >= 0
    assert data == rows()
    assert not result['outer_validation_data_used'] and not result['final_test_access']


@pytest.mark.parametrize('partition', ['calibration','validation','test'])
def test_outer_nontrain_rows_never_tune(partition):
    data = rows()
    data[0]['partition'] = partition
    with pytest.raises(ValueError, match='train'):
        tune(data)


def test_invalid_grid_and_under_supported_fold_fail():
    with pytest.raises(ValueError, match='Duplicate'):
        tune(C_grid=['1','1.0'])
    with pytest.raises(ValueError, match='support'):
        tune(minimum_holdout_class=50)


def test_duplicate_holdout_or_bad_chronology_fail():
    with pytest.raises(ValueError):
        tune(folds=[FOLDS[0], FOLDS[0]])


def test_every_failed_candidate_and_fold_remains_visible(monkeypatch):
    from crsl.models.baseline import Baseline
    def fail(*args, **kwargs):
        raise ValueError('Synthetic injected convergence failure')
    monkeypatch.setattr(Baseline, 'fit', fail)
    result = tune()
    assert result['status'] == 'all_candidates_failed' and result['selected_C'] is None
    assert len(result['candidates']) == 2
    assert all(len(c['failures']) == 2 for c in result['candidates'])
    assert all(c['pooled_holdout_log_loss'] is None for c in result['candidates'])
