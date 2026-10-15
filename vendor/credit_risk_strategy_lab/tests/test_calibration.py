import math

import pytest
pytest.importorskip('sklearn')

from crsl.models.calibration import SigmoidCalibration, logit


def rows():
    return [dict(loan_id=f'synthetic-{i:03}', partition='calibration', included=True,
        target=int(i % 4 == 0) if i < 100 else int(i % 4 != 0),
        raw_pd=.2 if i < 100 else .8, model_sha256='a' * 64, evidence_class='synthetic_demo',
        landmark='2014-01-01', label_known_month='2015-01-01', model_available_at='2014-01-01')
        for i in range(200)]


def fit(data=None):
    return SigmoidCalibration(C=1).fit(rows() if data is None else data,
        fit_cutoff='2016-01-01', model_sha256='a' * 64, evidence_class='synthetic_demo')


def test_calibration_bounds_monotonic_and_repeatable():
    model = fit()
    data = [{**r, 'partition': 'validation', 'landmark': '2016-01-01'} for r in rows()]
    predictions = model.predict(data)
    assert all(math.isfinite(p) and 0 <= p <= 1 for p in predictions)
    assert predictions[0] < predictions[-1]
    assert fit(list(reversed(rows()))).predict(data) == predictions
    assert model.state['rows'] == 200 and model.state['events'] == 100


@pytest.mark.parametrize('change', [dict(partition='train'), dict(partition='test'),
    dict(label_known_month='2016-01-01'), dict(model_available_at='2014-02-01'),
    dict(model_sha256='b' * 64), dict(evidence_class='retrospective_development'), dict(target=True)])
def test_leakage_or_mixed_model_refused(change):
    data = rows()
    data[0].update(change)
    with pytest.raises(ValueError):
        fit(data)


def test_no_final_test_or_precalibration_scoring():
    model = fit()
    with pytest.raises(ValueError):
        model.predict([{**rows()[0], 'partition': 'test', 'landmark': '2018-01-01'}])
    with pytest.raises(ValueError, match='precedes'):
        model.predict([{**rows()[0], 'partition': 'validation'}])


def test_invalid_pd_not_clipped_into_validity():
    for value in (-.1, 1.1, None, True, 'NaN'):
        with pytest.raises(ValueError):
            logit(value)
    assert math.isfinite(logit(0)) and math.isfinite(logit(1))


def test_low_support_and_rank_reversal_fail():
    with pytest.raises(ValueError, match='support'):
        fit(rows()[:20])
    with pytest.raises(ValueError, match='Negative'):
        fit([{**r, 'target': 1-r['target']} for r in rows()])


def test_json_calibration_roundtrip(tmp_path):
    model = fit()
    path = tmp_path / 'calibration.json'
    digest = model.save(path)
    restored = SigmoidCalibration.load(path, expected_sha256=digest)
    data = [{**rows()[0], 'partition': 'validation', 'landmark': '2016-01-01'}]
    assert model.predict(data) == restored.predict(data)
    with pytest.raises(FileExistsError):
        model.save(path)


def test_constant_scores_use_calibration_prevalence_not_unidentified_slope():
    data = [{**r, 'raw_pd': .01} for r in rows()]
    model = fit(data)
    assert model.state['slope'] == 0
    assert model.state['fit_case'] == 'constant_input_intercept_only'
    scoring = [{**data[0], 'partition': 'validation', 'landmark': '2016-01-01', 'target': 0}]
    assert model.predict(scoring) == [.5]
