"""Compare two complete eight-stage development runs, without publishing records."""
import argparse
import json
from pathlib import Path

import duckdb

from crsl.pipeline import STAGES
from crsl.source import sha256

TABLES = {
    'canonical': ('dim_loan.parquet', 'fact_loan_month.parquet'),
    'labels': ('observation.parquet', 'labels.parquet'),
    'audit': ('loss_audit.parquet', 'spotcheck_loans.parquet'),
    'portfolio': ('monthly.parquet', 'transition_matrix.parquet', 'episodes.parquet'),
    'splits': ('split_manifest.parquet',),
    'attrition': ('feature_distributions.parquet',),
    'vintage': ('vintage_ledger.parquet', 'vintage_stock.parquet'),
}


def resolve(root, pipeline):
    manifest = json.loads((pipeline/'run-complete.json').read_text())
    if manifest.get('status') != 'DEVELOPMENT_PIPELINE_COMPLETE':
        raise ValueError('Completed development pipeline required')
    receipts = manifest['stages']
    if [s['stage'] for s in receipts] != [s[0] for s in STAGES]:
        raise ValueError('Full eight-stage coverage required; no silent common-subset comparison')
    stages = {}
    base = (root/'artifacts/private').resolve()
    for receipt in receipts:
        if receipt.get('status') != 'PASS':
            raise ValueError('Incomplete stage')
        name = receipt['output_run']
        path = (base/name).resolve()
        if path.parent != base:
            raise ValueError('Stage path is outside private run directory')
        stages[receipt['stage']] = path
        if receipt['stage'] == 'vintage':
            if sha256(path/'verification.json') != receipt['verification_sha256']:
                raise ValueError('Vintage verification changed')
            if sha256(path/'run-complete.json') != receipt['output_manifest_sha256']:
                raise ValueError('Vintage completion receipt changed')
            if json.loads((path/'verification.json').read_text()).get('status') != 'PASS':
                raise ValueError('Vintage verification not passed')
    return manifest, stages


def compare(root, left, right):
    lm, ls = resolve(root, left)
    rm, rs = resolve(root, right)
    if lm['source_manifest_sha256'] != rm['source_manifest_sha256']:
        raise ValueError('Different source snapshots cannot establish reproduction')
    results = []
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        db.execute('SET threads=2')
        for stage, files in TABLES.items():
            for name in files:
                paths = [stages[stage]/name for stages in (ls, rs)]
                for path in paths:
                    receipt = json.loads((path.parent/'run-complete.json').read_text())
                    if sha256(path) != receipt['outputs_sha256'][name]:
                        raise ValueError('Saved stage artifact changed')
                db.read_parquet(str(paths[0])).create_view('left_table', replace=True)
                db.read_parquet(str(paths[1])).create_view('right_table', replace=True)
                if db.table('left_table').columns != db.table('right_table').columns or db.table('left_table').types != db.table('right_table').types:
                    raise ValueError('Table schema differs')
                if sha256(paths[0]) == sha256(paths[1]):
                    difference = 0
                    method = 'identical_file_sha256'
                else:
                    difference = db.execute('''SELECT COUNT(*) FROM (
                        (SELECT * FROM left_table EXCEPT ALL SELECT * FROM right_table)
                        UNION ALL (SELECT * FROM right_table EXCEPT ALL SELECT * FROM left_table))''').fetchone()[0]
                    method = 'symmetric_except_all'
                if difference:
                    raise ValueError(f'Non-reproducible table: {stage}/{name}')
                results.append(dict(stage=stage, artifact=name, method=method,
                    rows=db.table('left_table').count('*').fetchone()[0], difference_rows=difference))
    # Stable summaries include estimates and seeded bootstrap intervals, not run timestamps.
    for stage, name in [('audit','findings.json'),('splits','audit.json'),
                        ('metrics','registry.json'),('vintage','summary.json')]:
        if json.loads((ls[stage]/name).read_text()) != json.loads((rs[stage]/name).read_text()):
            raise ValueError(f'Stable summary differs: {stage}/{name}')
    return dict(status='PASS', left_pipeline=left.name, right_pipeline=right.name,
        same_code_fingerprint=lm['code_sha256']==rm['code_sha256'], tables=results,
        stable_summaries_checked=4, research_ready=False,
        limitation='Development data/summary reproducibility only; not complete V4 model, website, workbook or research release.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--left', required=True, type=Path)
    parser.add_argument('--right', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(Path(__file__).resolve().parents[1], args.left.resolve(), args.right.resolve()), indent=2))
