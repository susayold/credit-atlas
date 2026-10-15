"""Gated train-only baseline runner. Calibration/validation remain separate."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .baseline import Baseline
from ..cli import code_fingerprint
from ..evidence_checks import require, require_hash
from ..source import sha256, utc_now, write_json_new
from ..splits import split_records


def verify_split_assignments(label_rows, saved_assignments, config, saved_audit):
    """Recompute split eligibility, not model scores or final-test performance."""
    expected, audit = split_records(label_rows, config)
    key = lambda row: row['loan_id']
    require(sorted(expected, key=key) == sorted(saved_assignments, key=key),
            'Saved split assignments differ from source-derived protocol')
    require(audit == saved_audit, 'Saved split audit differs from recomputed support')
    return audit


def require_training_gate(manifest, audit):
    require(manifest['status'] == 'SPLIT_AUDIT_COMPLETE', 'Completed split audit required')
    require(manifest['training_ready'] is True and audit['training_ready'] is True
            and not audit['blocking_reasons'] and not audit['missing_years'],
            'Training blocked: missing vintages, insufficient support or unapproved protocol')
    require(manifest['config']['status'] == 'approved', 'Approved split protocol required')
    require(manifest['config']['claim'] == 'retrospective_temporal_not_strict_pit', 'Invalid evidence claim')
    for role in ('train', 'calibration', 'validation', 'test'):
        support = audit['support'][role]
        minimum = 200 if role == 'train' else 50
        require(all(type(support[k]) is int and support[k] >= minimum for k in ('positive', 'negative')),
                'Baseline minimum class support not met: ' + role)


def run(root, split_run, label_run, canonical_run, *, C):
    split = json.loads((split_run / 'run-complete.json').read_text())
    for name in ('audit.json', 'split_manifest.parquet'):
        require_hash(split_run / name, split['outputs_sha256'][name])
    audit = json.loads((split_run / 'audit.json').read_text())
    # Fail before loading feature/target tables or creating model artifacts.
    require_training_gate(split, audit)
    require(split['label_run'] == label_run.name, 'Split label lineage mismatch')
    labels = json.loads((label_run / 'run-complete.json').read_text())
    canonical = json.loads((canonical_run / 'run-complete.json').read_text())
    require(labels['status'] == 'LABELS_DEVELOPMENT_COMPLETE'
            and canonical['status'] == 'CANONICAL_COMPLETE', 'Completed upstream inputs required')
    require(labels['canonical_run'] == canonical_run.name, 'Canonical lineage mismatch')
    contract = labels['config']
    require(contract['horizon_months'] == 12 and contract['endpoint'] == 'numeric_delinquency_03_through_99'
            and contract['prepayment_estimand'] == 'event_before_prepayment', 'Unsupported model target')
    require_hash(label_run / 'labels.parquet', split['labels_sha256'])
    require_hash(label_run / 'labels.parquet', labels['outputs_sha256']['labels.parquet'])
    require_hash(canonical_run / 'dim_loan.parquet', canonical['outputs_sha256']['dim_loan.parquet'])
    # This upstream audit rederives partition/support only. Test observations are
    # never passed to a fit/scoring function and no test performance is computed.
    label_rows = pq.read_table(label_run / 'labels.parquet', columns=[
        'loan_id', 'origination_year', 'target', 'label_known_month', 'landmark']).to_pylist()
    verify_split_assignments(label_rows, pq.read_table(split_run / 'split_manifest.parquet').to_pylist(),
                             split['config'], audit)
    del label_rows
    features = json.loads((root / 'configs/features_origination.json').read_text())
    # Validate allowlist before forming the projection from these local names.
    Baseline(features, kind='logistic', C=C)
    columns = ','.join('d.' + name for name in features['numeric'] + features['categorical'])
    with duckdb.connect() as db:
        db.read_parquet(str(split_run / 'split_manifest.parquet')).create_view('assignments')
        db.read_parquet(str(label_run / 'labels.parquet')).create_view('labels')
        db.read_parquet(str(canonical_run / 'dim_loan.parquet')).create_view('loans')
        # No final-test feature rows or labels are materialized into the model.
        rows = db.sql(f'''SELECT l.loan_id,l.target,l.landmark,l.label_known_month,
            a.partition,a.included,{columns} FROM assignments a
            JOIN labels l USING(loan_id) JOIN loans d USING(loan_id)
            WHERE a.partition='train' AND a.included ORDER BY l.loan_id''').arrow().read_all().to_pylist()
    require(len(rows) == sum(audit['support']['train'].values()), 'Training join count mismatch')
    require(sum(r['target'] for r in rows) == audit['support']['train']['positive'], 'Training event count mismatch')
    output = root / 'artifacts/private' / ('baseline-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    manifest = dict(started_at=utc_now(), split_run=split_run.name, label_run=label_run.name,
        canonical_run=canonical_run.name, code_sha256=code_fingerprint(root),
        inputs_sha256={'split_receipt': sha256(split_run / 'run-complete.json'),
                      'label_receipt': sha256(label_run / 'run-complete.json'),
                      'canonical_receipt': sha256(canonical_run / 'run-complete.json')},
        feature_config=features, logistic_C=C, evidence_class='retrospective_development',
        calibration_complete=False, validation_complete=False, final_test_access=False,
        public_release_approved=False, visibility='private', research_ready=False)
    write_json_new(output / 'run-start.json', manifest)
    try:
        outputs = {}
        for kind in ('constant', 'logistic'):
            model = Baseline(features, kind=kind, C=C).fit(rows,
                fit_cutoff=split['config']['train_fit_month'], evidence_class='retrospective_development')
            name = kind + '.json'
            outputs[name] = model.save(output / name)
            restored = Baseline.load(output / name, expected_sha256=outputs[name])
            require(model.predict(rows) == restored.predict(rows), 'Persisted model prediction mismatch')
        manifest.update(status='BASELINE_TRAINING_ONLY_COMPLETE', completed_at=utc_now(), outputs_sha256=outputs)
        write_json_new(output / 'run-complete.json', manifest)
    except Exception as error:
        write_json_new(output / 'run-failed.json', {'exception_type': type(error).__name__, 'failed_at': utc_now()})
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split-run', type=Path, required=True)
    parser.add_argument('--label-run', type=Path, required=True)
    parser.add_argument('--canonical-run', type=Path, required=True)
    parser.add_argument('--C', type=float, required=True, help='Predeclared training regularization, not test-tuned')
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[3], args.split_run.resolve(), args.label_run.resolve(),
              args.canonical_run.resolve(), C=args.C))
