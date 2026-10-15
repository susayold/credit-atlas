"""Build an aggregate-only resolved-loss summary from one audit run."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb

from crsl.losses import summarize
from crsl.source import sha256, utc_now, write_json_new


def run(root, audit_run, severity_denominator='removal_upb'):
    root, audit_run = root.resolve(), audit_run.resolve()
    manifest = json.loads((audit_run / 'run-complete.json').read_text())
    if manifest.get('status') != 'AUDIT_COMPLETE':
        raise ValueError('Completed audit run required')
    path = audit_run / 'loss_audit.parquet'
    if sha256(path) != manifest['outputs_sha256']['loss_audit.parquet']:
        raise ValueError('Audit input changed')
    with duckdb.connect() as db:
        records = db.execute('SELECT * FROM read_parquet(?) ORDER BY loan_id,period', [str(path)]).to_arrow_table().to_pylist()
    summary = summarize(records, severity_denominator=severity_denominator)
    output = root / 'artifacts/private' / ('loss-summary-' + uuid.uuid4().hex[:12])
    output.mkdir()
    write_json_new(output / 'summary.json', {**summary, 'audit_run': audit_run.name,
        'audit_loss_audit_sha256': sha256(path), 'visibility': 'private',
        'public_release_approved': False, 'created_at': utc_now()})
    write_json_new(output / 'run-complete.json', {'status': 'LOSS_SUMMARY_COMPLETE',
        'audit_run': audit_run.name, 'visibility': 'private', 'public_release_approved': False,
        'outputs_sha256': {'summary.json': sha256(output / 'summary.json')}, 'completed_at': utc_now()})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit-run', type=Path, required=True)
    parser.add_argument('--severity-denominator', choices=['removal_upb', 'original_upb'], default='removal_upb')
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[1], args.audit_run, args.severity_denominator))
