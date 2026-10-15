"""Build a hash-verified, aggregate-only origination portfolio profile mart."""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import duckdb

from .cli import code_fingerprint
from .evidence_checks import require, require_hash
from .source import sha256, utc_now, write_json_new


def build(db, sql_dir: Path):
    """Return the profile relation; dim_loan must already be registered."""
    return db.sql((sql_dir / 'portfolio_profile.sql').read_text(encoding='utf-8'))


def run(root: Path, canonical_run: Path):
    root, canonical_run = root.resolve(), canonical_run.resolve()
    canonical_receipt = json.loads((canonical_run / 'run-complete.json').read_text())
    require(canonical_receipt.get('status') == 'CANONICAL_COMPLETE',
            'Completed canonical input required')
    dim_path = canonical_run / 'dim_loan.parquet'
    require_hash(dim_path, canonical_receipt['outputs_sha256']['dim_loan.parquet'])
    destination = root / 'artifacts/private' / ('portfolio-profile-' + uuid.uuid4().hex[:12])
    destination.mkdir()
    start = {'started_at': utc_now(), 'canonical_run': canonical_run.name,
             'visibility': 'private', 'public_release_approved': False,
             'evidence_class': 'derived_observed_sample', 'model_training': False,
             'code_sha256': code_fingerprint(root)}
    write_json_new(destination / 'run-start.json', start)
    with duckdb.connect() as db:
        db.read_parquet(str(dim_path)).create_view('dim_loan')
        relation = build(db, root / 'sql')
        relation.write_parquet(str(destination / 'profile.parquet'), compression='zstd')
    # Re-open the artifact to avoid making the receipt depend on an in-memory relation.
    with duckdb.connect() as db:
        db.read_parquet(str(destination / 'profile.parquet')).create_view('profile')
        summary = {
            'rows': db.execute('SELECT COUNT(*) FROM profile').fetchone()[0],
            'dimensions': [r[0] for r in db.execute(
                'SELECT DISTINCT dimension FROM profile ORDER BY dimension').fetchall()],
            'segments': [r[0] for r in db.execute(
                'SELECT DISTINCT segment FROM profile ORDER BY segment').fetchall()],
            'segment_counts': [dict(segment=r[0], dimension=r[1], loans=r[2],
                                    known_upb_loans=r[3]) for r in db.execute('''
                SELECT segment,dimension,MAX(segment_loans),MAX(segment_known_upb_loans)
                FROM profile GROUP BY segment,dimension ORDER BY segment,dimension''').fetchall()],
        }
    write_json_new(destination / 'summary.json', summary)
    receipt = dict(start, completed_at=utc_now(), status='PORTFOLIO_PROFILE_COMPLETE',
                   canonical_sha256=sha256(canonical_run / 'run-complete.json'),
                   outputs_sha256={'profile.parquet': sha256(destination / 'profile.parquet'),
                                   'summary.json': sha256(destination / 'summary.json')})
    write_json_new(destination / 'run-complete.json', receipt)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical-run', type=Path, required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[2], args.canonical_run))
