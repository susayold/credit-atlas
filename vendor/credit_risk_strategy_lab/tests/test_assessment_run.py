import json
from datetime import date
from pathlib import Path

import pytest
import pyarrow as pa
import pyarrow.parquet as pq
pytest.importorskip('sklearn')

from crsl.models.assessment_run import run
from crsl.source import sha256, write_json_new
from crsl.splits import split_records


@pytest.fixture
def source(tmp_path):
    root = Path(__file__).resolve().parents[1]
    write_json_new(tmp_path / 'configs/features_origination.json', {'numeric': ['classic_fico'], 'categorical': ['occupancy']})
    # This fixture tests file integration, with a predeclared fixed-C contract.
    # Separate temporal-tuning tests supply earlier training vintages.
    write_json_new(tmp_path / 'configs/baseline_assessment.json',
        json.loads((root / 'configs/baseline_assessment.json').read_text()) | {'logistic_C': 1, 'logistic_tuning': None, 'challenger_parameters': None})
    labels = []
    for year in (2012, 2014, 2016, 2018):
        for i in range(400):
            labels.append(dict(loan_id=f'synthetic-{year}-{i}', origination_year=year,
                landmark=date(year,1,1), label_known_month=date(year+1,1,1),
                target=int(i % 4 != 0) if i < 200 else int(i % 4 == 0)))
    loans = [dict(loan_id=r['loan_id'], classic_fico=600 if int(r['loan_id'].split('-')[-1]) < 200 else 780,
                  occupancy='P') for r in labels]
    canonical, label_run, splits = [tmp_path / name for name in ('canonical', 'labels', 'splits')]
    for directory in (canonical, label_run, splits):
        directory.mkdir()
    pq.write_table(pa.Table.from_pylist(loans), canonical / 'dim_loan.parquet')
    pq.write_table(pa.Table.from_pylist(labels), label_run / 'labels.parquet')
    write_json_new(canonical / 'run-complete.json', dict(status='CANONICAL_COMPLETE',
        outputs_sha256={'dim_loan.parquet': sha256(canonical / 'dim_loan.parquet')}))
    write_json_new(label_run / 'run-complete.json', dict(status='LABELS_DEVELOPMENT_COMPLETE', canonical_run=canonical.name,
        config=dict(horizon_months=12, landmark='first_observed_month', endpoint='numeric_delinquency_03_through_99',
                    prepayment_estimand='event_before_prepayment'),
        outputs_sha256={'labels.parquet': sha256(label_run / 'labels.parquet')}))
    config = json.loads((root / 'configs/split.json').read_text()) | dict(status='approved', train_years=[2012])
    assignments, audit = split_records(labels, config)
    pq.write_table(pa.Table.from_pylist(assignments), splits / 'split_manifest.parquet')
    write_json_new(splits / 'audit.json', audit)
    write_json_new(splits / 'run-complete.json', dict(status='SPLIT_AUDIT_COMPLETE', training_ready=True,
        config=config, label_run=label_run.name, labels_sha256=sha256(label_run / 'labels.parquet'),
        outputs_sha256={name:sha256(splits / name) for name in ('audit.json','split_manifest.parquet')}))
    return tmp_path, splits, label_run, canonical


def test_file_backed_assessment_keeps_test_out_of_scores(source):
    output = run(*source, evidence_class='synthetic_demo')
    receipt = json.loads((output / 'run-complete.json').read_text())
    require_hash = receipt['outputs_sha256']['assessment.json']
    assert sha256(output / 'assessment.json') == require_hash
    assert sha256(output / 'verification.json') == receipt['outputs_sha256']['verification.json']
    result = json.loads((output / 'assessment.json').read_text())
    assert result['cohort_counts'] == {'train':400, 'calibration':400, 'validation':400}
    assert result['evidence_class'] == 'synthetic_demo'
    for model in result['models'].values():
        for scores in model['private_validation_scores'].values():
            assert len(scores) == 400
            assert all(r['loan_id'].startswith('synthetic-2016-') for r in scores)
    assert not result['final_test_access'] and not result['research_ready']
    from crsl.models.verify_assessment import verify
    assert verify(output, source[1], source[2])['score_sets_checked'] == 4


def test_input_tampering_fails_before_any_model_output(source):
    root, splits, labels, canonical = source
    (canonical / 'dim_loan.parquet').write_bytes(b'broken fixture')
    with pytest.raises(ValueError, match='hash mismatch'):
        run(*source, evidence_class='synthetic_demo')
    assert not (root / 'artifacts').exists()


def test_failed_tuning_has_private_evidence_but_no_completion_receipt(source, monkeypatch):
    import crsl.models.assessment_run as runner
    from crsl.models.tuning import TuningFailed
    payload = dict(status='all_candidates_failed', selected_C=None, evidence_class='synthetic_demo',
                   candidates=[dict(C='1', status='failed', failures=[dict(fold=0, message='Injected test failure')])])
    def fail(*args, **kwargs):
        raise TuningFailed(payload)
    monkeypatch.setattr(runner, 'assess', fail)
    with pytest.raises(TuningFailed):
        run(*source, evidence_class='synthetic_demo')
    outputs = list((source[0] / 'artifacts/private').glob('assessment-*'))
    assert len(outputs) == 1
    output = outputs[0]
    assert not (output / 'run-complete.json').exists()
    assert json.loads((output / 'tuning-failed.json').read_text()) == payload
    receipt = json.loads((output / 'run-failed.json').read_text())
    assert receipt['outputs_sha256']['tuning-failed.json'] == sha256(output / 'tuning-failed.json')


def test_rehashed_wrong_metric_is_still_rejected(source):
    from crsl.models.verify_assessment import verify
    output = run(*source, evidence_class='synthetic_demo')
    path = output / 'assessment.json'
    result = json.loads(path.read_text())
    result['models']['logistic']['validation_metrics']['raw']['brier_score'] = 0
    path.write_text(json.dumps(result))
    receipt_path = output / 'run-complete.json'
    receipt = json.loads(receipt_path.read_text())
    receipt['outputs_sha256']['assessment.json'] = sha256(path)
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='metrics differ'):
        verify(output, source[1], source[2])


def test_failed_verification_never_writes_completion(source, monkeypatch):
    import crsl.models.assessment_run as runner
    def fail(*args, **kwargs):
        raise ValueError('Injected assessment reconciliation failure')
    monkeypatch.setattr(runner, 'verify', fail)
    with pytest.raises(ValueError, match='reconciliation'):
        run(*source, evidence_class='synthetic_demo')
    output, = (source[0] / 'artifacts/private').glob('assessment-*')
    assert (output / 'assessment.json').exists()
    assert (output / 'run-failed.json').exists()
    assert not (output / 'run-complete.json').exists()


def test_file_backed_challenger_uses_same_validation_cohort(source):
    config_path = source[0] / 'configs/baseline_assessment.json'
    config = json.loads(config_path.read_text())
    config['challenger_parameters'] = dict(learning_rate=.05,max_iter=10,max_leaf_nodes=7,
        min_samples_leaf=10,l2_regularization=1,random_state=17)
    config_path.write_text(json.dumps(config))
    output = run(*source, evidence_class='synthetic_demo')
    result = json.loads((output / 'assessment.json').read_text())
    assert set(result['models']) == {'constant','logistic','challenger'}
    reference = result['models']['logistic']['private_validation_scores']['raw']
    challenger = result['models']['challenger']['private_validation_scores']['raw']
    assert [r['loan_id'] for r in reference] == [r['loan_id'] for r in challenger]
    assert json.loads((output / 'verification.json').read_text())['score_sets_checked'] == 6
    from crsl.models.challenger import BoostingChallenger
    payload = result['models']['challenger']['model']
    restored = BoostingChallenger.from_payload(dict(schema_version=1,
        feature_config=payload['features'], encoder=payload['encoder'], model=payload['state']))
    assert restored.state['actual_iterations'] == 10
    assert not result['champion_selected']
