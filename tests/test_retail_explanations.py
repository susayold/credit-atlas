import math
import numpy as np
import pytest
from credit_atlas import retail_explanations as module
from credit_atlas.workspace import sha256


def plan():
    return dict(module.CONFIG, freeze_id='retail-freeze-aaaaaaaaaaaa')


def fixture():
    names = list(module.GROUPS['credit_limit'] + module.GROUPS['bill_history'] + module.GROUPS['payment_history'])
    names += [f'{name}={value}' for name in module.GROUPS['repayment_status'] for value in (0, 1)]
    rows = []
    for role, start, n in [('train', 0, 40), ('validation', 100, 40)]:
        for i in range(n):
            features = [i / 40] + [0.] * 12 + [float(i % 2 == v) for name in module.GROUPS['repayment_status'] for v in (0, 1)]
            rows.append({'source_client_id': start + i, 'partition': role, 'target': i % 2, 'features': features})
    predict = lambda x: .1 + .7 * x[:, 0]
    validation = [r for r in rows if r['partition'] == 'validation']
    scores = [{'source_client_id': r['source_client_id'], 'target': r['target'], 'probability': .1 + .7 * r['features'][0]} for r in validation]
    return rows[:40], validation, scores, names, predict


def test_exact_shapley_additive_interaction_symmetry_dummy_and_efficiency():
    values = [.05 + sum([.1, .2, .3, .0][i] for i in range(4) if mask & (1 << i)) for mask in range(16)]
    assert module.shapley(values) == pytest.approx([.1, .2, .3, 0.], abs=1e-14)
    # Pure two-player interaction splits equally, regardless of dummy players.
    interaction = [.8 if mask & 1 and mask & 2 else 0. for mask in range(16)]
    assert module.shapley(interaction) == pytest.approx([.4, .4, 0, 0], abs=1e-14)
    with pytest.raises(ValueError): module.shapley([math.nan] * 16)


def test_whole_validation_permutation_and_exact_local_reference_no_ids():
    train, validation, scores, names, predict = fixture()
    report, private = module.calculate(train, validation, scores, names, predict, plan())
    assert report['records'] == 40 and report['events'] == 20 and not any(report['qualification'].values())
    assert len(report['local_explanations']) == 12 and len(private['background_source_ids']) == 32
    assert all(i < 40 for i in private['background_source_ids'])
    assert 'source_client_id' not in str(report) and 'background_source_ids' not in str(report)
    for row in report['local_explanations']:
        assert row['predicted_probability'] == pytest.approx(row['reference_probability'] + sum(r['probability_contribution'] for r in row['contributions']), abs=1e-12)
        assert all(abs(r['probability_contribution']) < 1e-12 for r in row['contributions'] if r['group'] != 'credit_limit')
    assert all(r['mean_brier_increase'] == 0 and r['mean_auc_decrease'] == 0 for r in report['global_permutation'] if r['group'] != 'credit_limit')
    assert module.calculate(train, validation, scores, names, predict, plan()) == (report, private)


@pytest.mark.parametrize('change', [{'background_records': 8}, {'local_cases': True}, {'schema_version': True}, {'public_release_approved': True}, {'permutation_seeds': [True, 20261011, 20261012]}, {'freeze_id': '../escape'}])
def test_strict_configuration(change):
    with pytest.raises(ValueError): module.validate(plan() | change)


def test_saved_score_parity_partition_overlap_feature_and_prediction_guards():
    args = list(fixture())
    invalid = [dict(r) for r in args[2]]; invalid[0]['probability'] += .01
    with pytest.raises(ValueError, match='saved validation'): module.calculate(*args[:2], invalid, *args[3:], plan())
    validation = [dict(r) for r in args[1]]; validation[0]['partition'] = 'final_test'
    with pytest.raises(ValueError, match='partition'): module.calculate(args[0], validation, *args[2:], plan())
    with pytest.raises(ValueError, match='predictor fields'): module.grouped_columns(args[3] + ['SEX'])
    with pytest.raises(ValueError, match='predictor output'): module.calculate(*args[:4], lambda x: np.full(len(x), np.nan), plan())


def test_immutable_build_full_replay_and_cached_source_corruption(tmp_path, monkeypatch):
    file = tmp_path / 'source.txt'; file.write_text('saved frozen inputs')
    args = fixture(); lineage = {'freeze_id': plan()['freeze_id'], 'case_id': 'case', 'assessment_id': 'assessment', 'selected_model': 'logistic', 'selected_variant': 'raw'}
    monkeypatch.setattr(module, 'source', lambda root, p: (*args, {'source.txt': sha256(file)}, lineage))
    identifier = module.build(tmp_path, plan())['explanations_id']
    _, _, report = module.verify(tmp_path, identifier)
    assert report['selected_model'] == 'logistic'
    file.write_text('corrupt')
    with pytest.raises(ValueError, match='input evidence'): module.verify(tmp_path, identifier)


def test_source_query_materializes_only_train_and_validation_not_holdout(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from credit_atlas.workspace import write_new
    train, validation, scores, names, _ = fixture()
    bundle = tmp_path / 'artifacts/private' / plan()['freeze_id']; bundle.mkdir(parents=True)
    feature = tmp_path / 'artifacts/private/features-fixture'; feature.mkdir()
    write_new(bundle / 'freeze-complete.json', {'feature_id': feature.name, 'selected_variant': 'raw'})
    write_new(bundle / 'encoder.json', {'feature_names': names})
    write_new(bundle / 'model.json', {'kind': 'constant', 'prevalence': .5, 'feature_dimension': len(names)})
    path = feature / 'development.parquet'
    pq.write_table(pa.Table.from_pylist(train + validation + [{'source_client_id': 9999, 'partition': 'final_test', 'target': 1, 'features': [math.nan] * len(names)}]), path)
    monkeypatch.setattr(module, 'policy_source', lambda root, freeze: (scores, {}))
    monkeypatch.setattr(module, 'lineage_pins', lambda root, lineage: {str(path.relative_to(tmp_path)): sha256(path)})
    selected_train, selected_validation, *_ = module.source(tmp_path, plan())
    assert selected_train == train and selected_validation == validation


def test_independent_audit_tree_threshold_ties_constant_logistic_and_auc():
    from scripts.audit_retail_explanations import independent_predict, independent_auc
    from credit_atlas.retail_assessment import predict_json
    matrix = np.asarray([[-1.], [0.], [1.], [2.]])
    tree = [{'is_leaf': False, 'value': 0., 'feature': 0, 'threshold': 0., 'left': 1, 'right': 2},
            {'is_leaf': True, 'value': -.5}, {'is_leaf': True, 'value': .75}]
    models = [{'kind': 'constant', 'prevalence': .25, 'feature_dimension': 1},
              {'kind': 'logistic', 'coefficients': [1.], 'intercept': -.5, 'feature_dimension': 1},
              {'kind': 'histogram_boosting', 'initial_raw_score': .1, 'trees': [tree], 'feature_dimension': 1}]
    for model in models:
        assert independent_predict(model, matrix) == pytest.approx(predict_json(model, matrix), abs=1e-14)
    assert independent_auc([0, 1, 0, 1], [.2, .2, .8, .8]) == .5
    assert independent_auc([0, 0, 1, 1], [0, 0, 1, 1]) == 1.
