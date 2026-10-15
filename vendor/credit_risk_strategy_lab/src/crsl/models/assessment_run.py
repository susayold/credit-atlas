"""File-backed, private baseline/calibration/validation development runner."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .assessment import assess
from .baseline import Baseline
from .train import require_training_gate, verify_split_assignments
from .tuning import TuningFailed
from .verify_assessment import verify
from ..cli import code_fingerprint
from ..evidence_checks import require, require_hash
from ..source import sha256, utc_now, write_json_new
from ..features import OriginationEncoder


def run(root, split_run, label_run, canonical_run, *, evidence_class='retrospective_development'):
    require(evidence_class in ('synthetic_demo', 'retrospective_development'), 'Explicit source evidence required')
    split = json.loads((split_run / 'run-complete.json').read_text())
    for name in ('audit.json', 'split_manifest.parquet'):
        require_hash(split_run / name, split['outputs_sha256'][name])
    audit = json.loads((split_run / 'audit.json').read_text())
    require_training_gate(split, audit)
    require(split['label_run'] == label_run.name, 'Mixed split/label run')
    labels = json.loads((label_run / 'run-complete.json').read_text())
    canonical = json.loads((canonical_run / 'run-complete.json').read_text())
    require(labels['status'] == 'LABELS_DEVELOPMENT_COMPLETE' and canonical['status'] == 'CANONICAL_COMPLETE',
            'Completed source tables required')
    require(labels['canonical_run'] == canonical_run.name, 'Mixed canonical lineage')
    contract = labels['config']
    require(contract['horizon_months'] == 12 and contract['landmark'] == 'first_observed_month'
            and contract['endpoint'] == 'numeric_delinquency_03_through_99'
            and contract['prepayment_estimand'] == 'event_before_prepayment', 'Unsupported assessment endpoint')
    require_hash(label_run / 'labels.parquet', labels['outputs_sha256']['labels.parquet'])
    require_hash(label_run / 'labels.parquet', split['labels_sha256'])
    require_hash(canonical_run / 'dim_loan.parquet', canonical['outputs_sha256']['dim_loan.parquet'])
    verify_split_assignments(pq.read_table(label_run / 'labels.parquet', columns=[
        'loan_id', 'origination_year', 'target', 'label_known_month', 'landmark']).to_pylist(),
        pq.read_table(split_run / 'split_manifest.parquet').to_pylist(), split['config'], audit)
    features = json.loads((root / 'configs/features_origination.json').read_text())
    settings = json.loads((root / 'configs/baseline_assessment.json').read_text())
    OriginationEncoder(features)  # validate allowlist before SQL; C may be selected by tuning
    columns = ','.join('d.' + name for name in features['numeric'] + features['categorical'])
    with duckdb.connect() as db:
        db.read_parquet(str(label_run / 'labels.parquet')).create_view('labels')
        db.read_parquet(str(canonical_run / 'dim_loan.parquet')).create_view('loans')
        db.read_parquet(str(split_run / 'split_manifest.parquet')).create_view('assignments')
        rows = db.sql(f'''SELECT l.loan_id,l.target,l.landmark,l.label_known_month,
            a.partition,a.included,{columns} FROM assignments a JOIN labels l USING(loan_id)
            JOIN loans d USING(loan_id) WHERE a.included AND a.partition IN ('train','calibration','validation')
            ORDER BY a.partition,l.loan_id''').arrow().read_all().to_pylist()
    for role in ('train', 'calibration', 'validation'):
        selected = [r for r in rows if r['partition'] == role]
        require(len(selected) == sum(audit['support'][role].values())
                and sum(r['target'] for r in selected) == audit['support'][role]['positive'],
                'Assessment join support mismatch: ' + role)
    output = root / 'artifacts/private' / ('assessment-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    manifest = dict(started_at=utc_now(), split_run=split_run.name, label_run=label_run.name,
        canonical_run=canonical_run.name, code_sha256=code_fingerprint(root),
        inputs_sha256={'split_receipt': sha256(split_run / 'run-complete.json'),
            'label_receipt': sha256(label_run / 'run-complete.json'),
            'canonical_receipt': sha256(canonical_run / 'run-complete.json')},
        settings=settings, feature_config=features, evidence_class=evidence_class,
        final_test_access=False, research_ready=False, public_release_approved=False, visibility='private')
    write_json_new(output / 'run-start.json', manifest)
    try:
        result = assess(rows, features, settings, evidence_class=evidence_class,
                        split_manifest=split, split_audit=audit)
        write_json_new(output / 'assessment.json', result)
        manifest.update(status='PENDING_ASSESSMENT_VERIFICATION',
                        outputs_sha256={'assessment.json': sha256(output / 'assessment.json')})
        verification = verify(output, split_run, label_run, pending_manifest=manifest)
        require(verification['status'] == 'PASS', 'Assessment verification failed')
        write_json_new(output / 'verification.json', verification)
        manifest['outputs_sha256']['verification.json'] = sha256(output / 'verification.json')
        manifest.update(status='DEVELOPMENT_ASSESSMENT_COMPLETE', completed_at=utc_now())
        write_json_new(output / 'run-complete.json', manifest)
    except Exception as error:
        failure = {'exception_type': type(error).__name__, 'failed_at': utc_now(),
                   'model_assessment_complete': False}
        if isinstance(error, TuningFailed):
            write_json_new(output / 'tuning-failed.json', error.result)
            failure['outputs_sha256'] = {'tuning-failed.json': sha256(output / 'tuning-failed.json')}
        write_json_new(output / 'run-failed.json', failure)
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('split-run', 'label-run', 'canonical-run'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[3], args.split_run.resolve(),
              args.label_run.resolve(), args.canonical_run.resolve()))
