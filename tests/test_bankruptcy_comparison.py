import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.bankruptcy_assessment import CANDIDATES, run_assessment
from credit_atlas.bankruptcy_comparison import paired_group_bootstrap, verified_validation
from credit_atlas import bankruptcy_comparison
from credit_atlas.workspace import sha256
from tests.test_bankruptcy_study import case
from tests.test_bankruptcy_assessment import features


def arrays():
    group_numbers = np.concatenate([np.full(2 if i < 10 else 1, i) for i in range(40)])
    labels = group_numbers % 2
    groups = np.asarray(['group' + str(i) for i in group_numbers])
    return labels, groups


def test_duplicate_groups_are_resampled_whole_and_identical_models_have_zero_paired_deltas():
    y, groups = arrays()
    probabilities = {name: np.where(y, .7, .3) for name in CANDIDATES}
    summary, values, draws = paired_group_bootstrap(y, groups, probabilities, replicates=100, seed=7)
    assert summary['validation_groups'] == 40 and summary['validation_rows'] == 50
    assert summary['valid_replicates'] == 100 and len(draws) == 100
    assert summary['min_replicate_rows'] < 50 < summary['max_replicate_rows']
    assert np.array_equal(values[:, 0], values[:, -1])
    assert all(interval == {'point': 0.0, 'lower': 0.0, 'upper': 0.0}
               for delta in summary['paired_deltas'].values() for interval in delta.values())


def test_paired_group_seed_reproducibility_and_direction():
    y, groups = arrays()
    probabilities = {name: np.full(len(y), .5) for name in CANDIDATES}
    probabilities['boosting_platt'] = np.where(y, .9, .1)
    first = paired_group_bootstrap(y, groups, probabilities, replicates=100, seed=71)
    second = paired_group_bootstrap(y, groups, probabilities, replicates=100, seed=71)
    assert first[0] == second[0] and np.array_equal(first[1], second[1])
    assert first[0]['paired_deltas']['boosting_platt_minus_constant_raw']['brier_score']['upper'] < 0
    assert first[0]['paired_deltas']['boosting_platt_minus_constant_raw']['roc_auc']['lower'] > 0


def test_score_model_disagreement_rejected_even_when_metric_and_digest_match(features):
    root, feature = features
    result = run_assessment(root, feature['feature_id'])
    folder = root / 'artifacts/private' / result['assessment_id']
    path = folder / 'logistic-model.json'
    model = json.loads(path.read_text())
    model['intercept'] += 1
    path.write_text(json.dumps(model))
    receipt = json.loads((folder / 'assessment-complete.json').read_text())
    receipt['files'][path.name] = sha256(path)
    (folder / 'assessment-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='scores differ from frozen'):
        verified_validation(root, result['assessment_id'])


def test_complete_group_comparison_and_persisted_draw_verification(features, monkeypatch):
    root, feature = features
    assessment = run_assessment(root, feature['feature_id'])
    monkeypatch.setitem(bankruptcy_comparison.BOOTSTRAP, 'replicates', 100)
    result = bankruptcy_comparison.run_comparison(root, assessment['assessment_id'])
    folder, receipt, summary = bankruptcy_comparison.verify_comparison(root, result['comparison_id'])
    assert summary['valid_replicates'] == 100 and not receipt['final_test_scored']
    path = folder / 'paired-replicates.parquet'
    table = pq.read_table(path)
    rows = table.to_pylist()
    rows[0]['draw'] = 100000
    pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    receipt['files'][path.name] = sha256(path)
    (folder / 'comparison-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='draws/candidate'):
        bankruptcy_comparison.verify_comparison(root, result['comparison_id'])


@pytest.mark.parametrize('change', ['shape', 'nan', 'missing_candidate', 'replicates', 'groups'])
def test_invalid_paired_inputs_rejected(change):
    y, groups = arrays()
    probabilities = {name: np.full(len(y), .5) for name in CANDIDATES}
    replicates = 100
    if change == 'shape':
        probabilities['logistic_raw'] = np.zeros(1)
    elif change == 'nan':
        probabilities['logistic_raw'][0] = float('nan')
    elif change == 'missing_candidate':
        probabilities.pop('logistic_raw')
    elif change == 'replicates':
        replicates = True
    else:
        groups[:] = 'same'
    with pytest.raises(ValueError):
        paired_group_bootstrap(y, groups, probabilities, replicates=replicates)
