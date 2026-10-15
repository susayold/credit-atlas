import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.bankruptcy_assessment import CANDIDATES, apply_platt, clipped_logit, probability_metrics, run_assessment, verify_assessment
from credit_atlas.bankruptcy_study import create_study, prepare_features
from credit_atlas.retail_assessment import predict_json
from credit_atlas.workspace import sha256
from tests.test_bankruptcy_study import case


@pytest.fixture
def features(case):
    root, identifier, _ = case
    study = create_study(root, identifier)
    feature = prepare_features(root, study['study_id'])
    return root, feature


def test_development_fit_persistence_five_candidates_and_final_exclusion(features):
    root, feature = features
    result = run_assessment(root, feature['feature_id'])
    folder, receipt, metrics = verify_assessment(root, result['assessment_id'])
    assert set(metrics) == set(CANDIDATES) and not receipt['final_test_scored']
    assert not receipt['champion_selected'] and not receipt['production_qualified']
    assert all(row['max_absolute_difference'] <= 1e-12 for row in receipt['parity'].values())
    for candidate, values in metrics.items():
        assert values['statements'] == receipt['support']['validation']['rows']
        assert sum(row['statements'] for row in values['reliability_bins']) == values['statements']
    scores = pq.read_table(folder / 'private-validation-scores.parquet').to_pylist()
    assert len(scores) == metrics['constant_raw']['statements']*5
    development = pq.read_table(root / 'artifacts/private' / feature['feature_id'] / 'development.parquet').to_pylist()
    validation_ids = {row['source_row_ordinal'] for row in development if row['partition'] == 'validation'}
    assert {row['source_row_ordinal'] for row in scores} == validation_ids
    constant = json.loads((folder / 'constant-model.json').read_text())
    assert constant['prevalence'] == receipt['support']['train']['positive']/receipt['support']['train']['rows']
    boosting = json.loads((folder / 'boosting-model.json').read_text())
    assert len(boosting['trees']) == 120


def test_encoder_recomputation_rejects_tampered_features_even_with_updated_digest(features):
    root, feature = features
    folder = root / 'artifacts/private' / feature['feature_id']
    path = folder / 'development.parquet'
    table = pq.read_table(path)
    rows = table.to_pylist()
    rows[0]['x001'] += 1
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    receipt = json.loads((folder / 'features-complete.json').read_text())
    receipt['files'][path.name] = sha256(path)
    (folder / 'features-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='features differ from canonical'):
        run_assessment(root, feature['feature_id'])


def test_changed_persisted_model_rejected(features):
    root, feature = features
    result = run_assessment(root, feature['feature_id'])
    path = root / 'artifacts/private' / result['assessment_id'] / 'logistic-model.json'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='bytes changed'):
        verify_assessment(root, result['assessment_id'])


def test_saved_validation_identity_mismatch_fails_even_with_updated_digest(features):
    root, feature = features
    result = run_assessment(root, feature['feature_id'])
    folder = root / 'artifacts/private' / result['assessment_id']
    path = folder / 'private-validation-scores.parquet'
    table = pq.read_table(path)
    rows = table.to_pylist()
    rows[0]['source_row_ordinal'] += 100000
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    receipt = json.loads((folder / 'assessment-complete.json').read_text())
    receipt['files'][path.name] = sha256(path)
    (folder / 'assessment-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='scores/metrics'):
        verify_assessment(root, result['assessment_id'])


def test_brier_and_reliability_boundary_values():
    values = probability_metrics([0, 0, 1, 1], [0, .5, .5, 1])
    assert values['brier_score'] == .125 and values['roc_auc'] == .875
    assert values['reliability_bins'][0]['statements'] == 1
    assert values['reliability_bins'][5]['statements'] == 2
    assert values['reliability_bins'][9]['statements'] == 1


@pytest.mark.parametrize('values', [[float('nan'), .2], [-.1, .2], [1.1, .2]])
def test_invalid_probability_metrics_fail(values):
    with pytest.raises(ValueError):
        probability_metrics([0, 1], values)


def test_json_tree_numeric_threshold_and_leaf_values_are_not_multiplied_twice():
    model = {'kind': 'histogram_boosting', 'feature_dimension': 1, 'initial_raw_score': 0,
        'trees': [[{'value': 0, 'feature': 0, 'threshold': 2, 'left': 1, 'right': 2, 'is_leaf': False},
                   {'value': -1, 'feature': 0, 'threshold': 0, 'left': 0, 'right': 0, 'is_leaf': True},
                   {'value': 1, 'feature': 0, 'threshold': 0, 'left': 0, 'right': 0, 'is_leaf': True}]]}
    assert predict_json(model, [[2], [3]]).tolist() == pytest.approx([1/(1+np.e), np.e/(1+np.e)])


def test_calibration_clipping_and_frozen_epsilon():
    assert np.isfinite(clipped_logit([0, 1])).all()
    state = {'method': 'platt_logistic_on_clipped_raw_logit', 'C': 1.0, 'clip_epsilon': 1e-12,
             'slope': 1.0, 'intercept': 0.0, 'fit_partition': 'calibration'}
    assert apply_platt([.2, .8], state).tolist() == pytest.approx([.2, .8])
    state['clip_epsilon'] = .01
    with pytest.raises(ValueError):
        apply_platt([.2, .8], state)
