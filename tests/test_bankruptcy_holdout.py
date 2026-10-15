import copy
from concurrent.futures import ThreadPoolExecutor
import json

import numpy as np
import pyarrow.parquet as pq
import pytest

from credit_atlas import bankruptcy_comparison, bankruptcy_holdout as holdout
from credit_atlas.bankruptcy_assessment import run_assessment
from credit_atlas.bankruptcy_freeze import freeze_model
from credit_atlas.bankruptcy_study import RatioEncoder
from tests.test_bankruptcy_study import case, example
from tests.test_bankruptcy_assessment import features


@pytest.fixture
def frozen(features, monkeypatch):
    root, feature = features
    assessment = run_assessment(root, feature['feature_id'])
    monkeypatch.setitem(bankruptcy_comparison.BOOTSTRAP, 'replicates', 100)
    comparison = bankruptcy_comparison.run_comparison(root, assessment['assessment_id'])
    result = freeze_model(root, comparison['comparison_id'])
    monkeypatch.setitem(holdout.FINAL_SETTINGS, 'replicates', 100)
    return root, result


def test_frozen_codec_signed_extreme_null_parity_and_no_fit():
    rows = [example(i) for i in range(5)]
    encoder = RatioEncoder().fit(rows)
    probes = [{**row, 'partition': 'final_test'} for row in rows]
    probes[0]['A1'], probes[1]['A1'], probes[2]['A1'] = -1e308, 1e308, None
    before = copy.deepcopy(encoder.state)
    assert np.array_equal(holdout.frozen_transform(encoder.state, probes), encoder.transform(probes))
    assert encoder.state == before
    holdout.check_codec(encoder.state)
    with pytest.raises(ValueError):
        holdout.frozen_transform(encoder.state, rows)


def test_ledger_concurrency_one_winner_and_failed_access_remains_consumed(tmp_path):
    ledger = tmp_path / 'ledger.sqlite'
    frozen = {'study_id': 'study', 'freeze_id': 'freeze'}
    def attempt(index):
        try:
            holdout.claim(ledger, 'same-original-source-horizon', frozen, str(index), 'digest')
            return True, str(index)
        except ValueError:
            return False, str(index)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sum(row[0] for row in results) == 1
    winner = next(row[1] for row in results if row[0])
    holdout.finish(ledger, 'same-original-source-horizon', winner, 'failed')
    assert holdout.ledger_record(ledger, 'same-original-source-horizon')['status'] == 'failed'
    with pytest.raises(ValueError, match='already claimed'):
        holdout.claim(ledger, 'same-original-source-horizon', frozen, 'new-case-or-freeze', 'other-digest')


def test_actual_one_time_evaluation_and_read_only_saved_verification(frozen, monkeypatch):
    root, model = frozen
    # Any accidental fitting in the final workflow fails the test.
    monkeypatch.setattr(RatioEncoder, 'fit', lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('No refit')))
    result = holdout.evaluate_holdout(root, model['freeze_id'])
    folder, receipt, metrics, uncertainty = holdout.verify_holdout(root, result['evaluation_id'])
    assert receipt['final_test_scored'] and not receipt['model_training_performed'] and not receipt['model_selection_performed']
    assert metrics['statements'] > 0 and uncertainty['valid_replicates'] == 100
    scores = pq.read_table(folder / 'private-final-scores.parquet').to_pylist()
    assert len(scores) == metrics['statements']
    # Verification must not transform or score final predictors again.
    monkeypatch.setattr(holdout, 'frozen_transform', lambda *args: (_ for _ in ()).throw(AssertionError('No rescore')))
    monkeypatch.setattr(holdout, 'predict_json', lambda *args: (_ for _ in ()).throw(AssertionError('No rescore')))
    holdout.verify_holdout(root, result['evaluation_id'])
    record = holdout.ledger_record(holdout.ledger_path(root), receipt['lineage_key'])
    assert record['status'] == 'completed' and record['evaluation_id'] == receipt['evaluation_id']
    # Repeated scoring fails at the ledger before the predictor query.
    monkeypatch.setattr(holdout, 'check_codec', lambda *args: None)
    with pytest.raises(ValueError, match='already claimed'):
        holdout.evaluate_holdout(root, model['freeze_id'])


def test_post_claim_failure_consumes_access_and_changed_saved_evidence_rejected(frozen, monkeypatch):
    root, model = frozen
    original = holdout.frozen_transform
    monkeypatch.setattr(holdout, 'check_codec', lambda *args: None)
    monkeypatch.setattr(holdout, 'frozen_transform', lambda *args: (_ for _ in ()).throw(ValueError('Deliberate post-claim failure')))
    with pytest.raises(ValueError, match='Deliberate'):
        holdout.evaluate_holdout(root, model['freeze_id'])
    record = holdout.ledger_record(holdout.ledger_path(root), model['lineage_key'])
    assert record['status'] == 'failed'
    monkeypatch.setattr(holdout, 'frozen_transform', original)
    with pytest.raises(ValueError, match='already claimed'):
        holdout.evaluate_holdout(root, model['freeze_id'])


def test_changed_saved_scores_rejected(frozen):
    root, model = frozen
    result = holdout.evaluate_holdout(root, model['freeze_id'])
    path = root / 'artifacts/private' / result['evaluation_id'] / 'private-final-scores.parquet'
    with path.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='bytes changed'):
        holdout.verify_holdout(root, result['evaluation_id'])
