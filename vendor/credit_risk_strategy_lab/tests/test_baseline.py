import json
import math

import pytest

pytest.importorskip('sklearn')
from crsl.models.baseline import Baseline
from crsl.source import sha256

FEATURES = {'numeric': ['classic_fico'], 'categorical': ['occupancy']}


def rows():
    return [dict(loan_id=f'synthetic-{i:03}', classic_fico=600 + i, occupancy='P',
                 partition='train', included=True, target=int(i % 4 == 0),
                 landmark='2012-01-01', label_known_month='2013-01-01') for i in range(80)]


def fit(kind='logistic', data=None):
    return Baseline(FEATURES, kind=kind).fit(rows() if data is None else data,
        fit_cutoff='2014-01-01', evidence_class='synthetic_demo')


@pytest.mark.parametrize('kind', ['constant', 'logistic'])
def test_prediction_bounds_and_json_roundtrip(tmp_path, kind):
    model = fit(kind)
    data = [{**r, 'partition': 'validation', 'landmark': '2016-01-01', 'target': 1, 'occupancy': 'unseen'} for r in rows()]
    predictions = model.predict(data)
    assert all(math.isfinite(p) and 0 <= p <= 1 for p in predictions)
    path = tmp_path / 'model.json'
    digest = model.save(path)
    assert Baseline.load(path, expected_sha256=digest).predict(data) == predictions
    if kind == 'constant':
        assert set(predictions) == {.25}
    with pytest.raises(FileExistsError):
        model.save(path)


@pytest.mark.parametrize('change', [dict(partition='test'), dict(partition='calibration'),
    dict(included=False), dict(target=True), dict(label_known_month='2014-01-01')])
def test_fit_rejects_leakage(change):
    data = rows()
    data[0].update(change)
    with pytest.raises(ValueError):
        fit(data=data)


def test_no_final_test_predictions():
    with pytest.raises(ValueError, match='final test'):
        fit().predict([{**rows()[0], 'partition': 'test'}])
    with pytest.raises(ValueError, match='precedes'):
        fit().predict([{**rows()[0], 'partition': 'validation'}])


def test_json_mutation_detected(tmp_path):
    path = tmp_path / 'model.json'
    digest = fit().save(path)
    payload = json.loads(path.read_text())
    payload['model']['intercept'] += 1
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='hash mismatch'):
        Baseline.load(path, expected_sha256=digest)
    payload['model']['coefficients'].append(0)
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='dimensions'):
        Baseline.load(path, expected_sha256=sha256(path))


def test_manual_scoring_matches_library():
    from sklearn.linear_model import LogisticRegression
    model = fit()
    data = sorted(rows(), key=lambda r: r['loan_id'])
    matrix = model.encoder.transform(data)
    library = LogisticRegression(C=1, solver='lbfgs', max_iter=2000, tol=1e-8,
                                 class_weight=None).fit(matrix, [r['target'] for r in data])
    assert model.predict(data) == pytest.approx(library.predict_proba(matrix)[:, 1], abs=1e-12)


def test_training_gate_cannot_be_bypassed_by_one_ready_flag():
    from crsl.models.train import require_training_gate
    manifest = dict(status='SPLIT_AUDIT_COMPLETE', training_ready=True,
                    config=dict(status='approved', claim='retrospective_temporal_not_strict_pit'))
    audit = dict(training_ready=True, blocking_reasons=[], missing_years=[],
                 support={r: dict(positive=200, negative=200) for r in ('train', 'calibration', 'validation', 'test')})
    require_training_gate(manifest, audit)
    audit['support']['train']['positive'] = 100
    with pytest.raises(ValueError, match='support'):
        require_training_gate(manifest, audit)
    audit['training_ready'] = False
    with pytest.raises(ValueError, match='blocked'):
        require_training_gate(manifest, audit)
