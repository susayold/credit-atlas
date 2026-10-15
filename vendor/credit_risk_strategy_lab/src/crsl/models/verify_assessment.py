"""Read-only assessment receipt, source identity and metric reconciliation."""
import json
import math

import pyarrow.parquet as pq

from .evaluation import evaluate_probabilities
from ..evidence_checks import require, require_hash
from ..policy.engine import fingerprint


def verify(assessment_run, split_run, label_run, *, pending_manifest=None):
    manifest = pending_manifest if pending_manifest is not None else json.loads((assessment_run / 'run-complete.json').read_text())
    expected_status = 'PENDING_ASSESSMENT_VERIFICATION' if pending_manifest is not None else 'DEVELOPMENT_ASSESSMENT_COMPLETE'
    require(manifest['status'] == expected_status, 'Incorrect assessment verification lifecycle')
    require(manifest['split_run'] == split_run.name and manifest['label_run'] == label_run.name,
            'Assessment input lineage mismatch')
    require_hash(assessment_run / 'assessment.json', manifest['outputs_sha256']['assessment.json'])
    require_hash(split_run / 'run-complete.json', manifest['inputs_sha256']['split_receipt'])
    require_hash(label_run / 'run-complete.json', manifest['inputs_sha256']['label_receipt'])
    split = json.loads((split_run / 'run-complete.json').read_text())
    labels_manifest = json.loads((label_run / 'run-complete.json').read_text())
    require_hash(split_run / 'split_manifest.parquet', split['outputs_sha256']['split_manifest.parquet'])
    require_hash(label_run / 'labels.parquet', labels_manifest['outputs_sha256']['labels.parquet'])
    labels = pq.read_table(label_run / 'labels.parquet').to_pylist()
    label_index = {r['loan_id']: r for r in labels}
    require(len(label_index) == len(labels), 'Duplicate source label keys')
    assignments = pq.read_table(split_run / 'split_manifest.parquet').to_pylist()
    require(len({r['loan_id'] for r in assignments}) == len(assignments), 'Duplicate split keys')
    identities = {r['loan_id'] for r in assignments if r['included'] and r['partition'] == 'validation'}
    require(bool(identities) and identities <= label_index.keys(), 'Validation source coverage missing')
    result = json.loads((assessment_run / 'assessment.json').read_text())
    require(result['settings'] == manifest['settings'] and result['evidence_class'] == manifest['evidence_class'],
            'Assessment settings/evidence differ from receipt')
    require(result['final_test_access'] is False and result['research_ready'] is False
            and result['public_release_approved'] is False, 'Invalid development claim')
    expected_models = {'constant','logistic'}
    if result['settings'].get('challenger_parameters') is not None:
        expected_models.add('challenger')
    require(set(result['models']) == expected_models, 'Configured model omitted or replaced')
    checked = 0
    for kind, model in result['models'].items():
        model_digest = fingerprint(model['model'])
        require(model_digest == model['model_content_sha256'], 'Model content hash mismatch')
        require(model['calibration']['model_sha256'] == model_digest, 'Calibration model lineage mismatch')
        require(set(model['private_validation_scores']) == {'raw', 'calibrated'}
                and set(model['validation_metrics']) == {'raw', 'calibrated'}, 'Score variant omitted')
        for variant, scores in model['private_validation_scores'].items():
            require(len(scores) == len(identities) and {r['loan_id'] for r in scores} == identities,
                    'Score identities differ from validation cohort')
            digest = fingerprint({'model_sha256': model_digest, 'version': variant,
                'calibration': model['calibration'] if variant == 'calibrated' else None, 'scores': scores})
            available = result['settings']['train_cutoff' if variant == 'raw' else 'calibration_cutoff']
            rows = [{**label_index[r['loan_id']], 'partition': 'validation', 'included': True,
                     'pd': r['pd'], 'score_sha256': digest, 'score_available_at': available} for r in scores]
            expected = evaluate_probabilities(rows, evaluation_cutoff=result['settings']['evaluation_cutoff'],
                bin_edges=result['settings']['bin_edges'], minimum_events=result['settings']['minimum_events'])
            require(expected == model['validation_metrics'][variant], 'Saved validation metrics differ from source recomputation')
            # Independent elementary calculation, in addition to shared metric API.
            brier = math.fsum((r['pd'] - label_index[r['loan_id']]['target'])**2 for r in scores) / len(scores)
            require(math.isclose(brier, expected['brier_score'], rel_tol=1e-12, abs_tol=1e-15), 'Independent Brier mismatch')
            checked += 1
    return {'status': 'PASS', 'score_sets_checked': checked, 'validation_loans': len(identities),
            'verification_scope': 'receipt_source_identities_and_metrics_not_model_refitting',
            'research_ready': False}
