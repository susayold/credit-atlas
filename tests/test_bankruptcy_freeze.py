import pytest

from credit_atlas import bankruptcy_comparison
from credit_atlas.bankruptcy_assessment import CANDIDATES, run_assessment
from credit_atlas.bankruptcy_freeze import freeze_model, select_candidate, verify_freeze
from tests.test_bankruptcy_study import case
from tests.test_bankruptcy_assessment import features


def metrics():
    return {name: {'brier_score': .1, 'log_loss': .3, 'roc_auc': .5} for name in CANDIDATES}


def test_prefit_rule_primary_brier_not_auc():
    values = metrics()
    values['logistic_raw']['brier_score'] = .05
    values['boosting_platt']['roc_auc'] = .99
    values['boosting_platt']['log_loss'] = .1
    assert select_candidate(values) == 'logistic_raw'


def test_prefit_rule_secondary_then_complexity_tie_order():
    values = metrics()
    values['boosting_raw']['brier_score'] -= 0.5e-6
    values['logistic_raw']['log_loss'] = .2
    assert select_candidate(values) == 'logistic_raw'
    values = metrics()
    assert select_candidate(values) == 'constant_raw'


def test_incomplete_or_nonfinite_candidate_metrics_rejected():
    values = metrics()
    values.pop('constant_raw')
    with pytest.raises(ValueError):
        select_candidate(values)
    values = metrics()
    values['logistic_raw']['brier_score'] = float('nan')
    with pytest.raises(ValueError):
        select_candidate(values)


def test_model_freeze_copies_selected_artifacts_and_cannot_be_silently_changed(features, monkeypatch):
    root, feature = features
    assessment = run_assessment(root, feature['feature_id'])
    monkeypatch.setitem(bankruptcy_comparison.BOOTSTRAP, 'replicates', 100)
    comparison = bankruptcy_comparison.run_comparison(root, assessment['assessment_id'])
    result = freeze_model(root, comparison['comparison_id'])
    folder, receipt = verify_freeze(root, result['freeze_id'])
    assert receipt['champion_selected'] and not receipt['final_test_scored'] and not receipt['production_qualified']
    assert freeze_model(root, comparison['comparison_id'])['freeze_id'] == receipt['freeze_id']
    path = folder / 'model.json'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='bytes changed'):
        verify_freeze(root, result['freeze_id'])
