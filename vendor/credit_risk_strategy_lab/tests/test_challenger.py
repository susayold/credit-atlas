import pytest
pytest.importorskip('sklearn')

from crsl.models.challenger import BoostingChallenger

FEATURES = {'numeric':['classic_fico'], 'categorical':['occupancy']}
PARAMETERS = dict(learning_rate=.05, max_iter=10, max_leaf_nodes=7,
                  min_samples_leaf=10, l2_regularization=1, random_state=17)


def rows():
    return [dict(loan_id=f'synthetic-{i:03}', partition='train', included=True,
        landmark='2012-01-01', label_known_month='2013-01-01', classic_fico=600+i,
        occupancy='P', target=int(i % 3 == 0)) for i in range(120)]


def fit(data=None):
    return BoostingChallenger(FEATURES, PARAMETERS).fit(rows() if data is None else data,
        fit_cutoff='2014-01-01', evidence_class='synthetic_demo')


def test_bounded_iterations_no_random_validation_and_determinism():
    model = fit()
    predictions = model.predict(rows())
    assert all(0 <= p <= 1 for p in predictions)
    assert model.state['actual_iterations'] == 10
    assert not model.state['internal_random_validation']
    assert fit(list(reversed(rows()))).predict(rows()) == predictions
    assert model.encoder.state['fit_rows'] == 120


def test_future_outcome_ignored_in_scoring():
    model = fit()
    data = [{**r,'partition':'validation','landmark':'2016-01-01'} for r in rows()]
    assert model.predict(data) == model.predict([{**r,'target':1-r['target'],'actual_loss':999} for r in data])


@pytest.mark.parametrize('partition', ['calibration','validation','test'])
def test_fit_only_training(partition):
    with pytest.raises(ValueError, match='train'):
        fit([{**r,'partition':partition} for r in rows()])


def test_scoring_rejects_test_or_pre_fit_dates():
    model = fit()
    with pytest.raises(ValueError):
        model.predict([{**rows()[0],'partition':'test'}])
    with pytest.raises(ValueError, match='precedes'):
        model.predict([{**rows()[0],'partition':'validation'}])


def test_unreviewed_parameters_and_forbidden_features_rejected():
    with pytest.raises(ValueError):
        BoostingChallenger(FEATURES, PARAMETERS | {'early_stopping':True})
    with pytest.raises(ValueError):
        BoostingChallenger(FEATURES, PARAMETERS | {'max_iter':100000})
    with pytest.raises(ValueError, match='allowlist'):
        BoostingChallenger({'numeric':['actual_loss'],'categorical':[]}, PARAMETERS)


def test_json_roundtrip_and_native_probability_parity(tmp_path):
    from threadpoolctl import threadpool_limits
    model = fit()
    data = [{**r,'partition':'validation','landmark':'2016-01-01','occupancy':'unseen'} for r in rows()]
    with threadpool_limits(limits=1):
        native = model.estimator.predict_proba(model.encoder.transform(data))[:,1]
    assert model.predict(data) == pytest.approx(native, abs=1e-12)
    path = tmp_path / 'challenger.json'
    digest = model.save(path)
    loaded = BoostingChallenger.load(path, expected_sha256=digest)
    assert loaded.estimator is None
    assert loaded.predict(data) == model.predict(data)
    with pytest.raises(FileExistsError):
        model.save(path)


def test_bad_tree_graph_rejected_even_with_updated_file_hash(tmp_path):
    import json
    from crsl.source import sha256
    model = fit()
    path = tmp_path / 'challenger.json'
    digest = model.save(path)
    payload = json.loads(path.read_text())
    payload['model']['trees'][0][0]['left'] = 0
    payload['model']['trees'][0][0]['is_leaf'] = False
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='hash mismatch'):
        BoostingChallenger.load(path, expected_sha256=digest)
    with pytest.raises(ValueError, match='tree graph'):
        BoostingChallenger.load(path, expected_sha256=sha256(path))
