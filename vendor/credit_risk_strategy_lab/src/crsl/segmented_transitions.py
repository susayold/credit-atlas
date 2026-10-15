"""B12: observed adjacent transitions by Relief segment, with support counts."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb

from .source import sha256, write_json_new


def build(db, sql_dir):
    if db.execute('SELECT COUNT(*)-COUNT(DISTINCT loan_id) FROM dim_loan').fetchone()[0]:
        raise ValueError('Duplicate dimension loan keys')
    if db.execute('SELECT COUNT(*) FROM fact_loan_month f ANTI JOIN dim_loan d USING(loan_id)').fetchone()[0]:
        raise ValueError('Missing dimension loan keys')
    db.execute('CREATE TEMP VIEW pairs AS ' + (sql_dir / 'transitions.sql').read_text())
    return db.execute('''WITH grouped AS (
      SELECT CASE WHEN d.is_relief_refinance THEN 'relief'
                  WHEN d.is_relief_refinance IS FALSE THEN 'non_relief'
                  ELSE 'unknown' END AS segment,
             p.delinquency_state AS origin, p.destination,
             COUNT(*) AS pairs, COUNT(DISTINCT p.loan_id) AS distinct_loans,
             SUM(p.current_upb) AS opening_upb,
             COUNT(*) FILTER(WHERE p.current_upb IS NULL) AS missing_balance_pairs
      FROM pairs p JOIN dim_loan d USING(loan_id)
      WHERE adjacent GROUP BY ALL
    ) SELECT *, SUM(pairs) OVER(PARTITION BY segment,origin) AS origin_pairs,
      pairs / SUM(pairs) OVER(PARTITION BY segment,origin)::DOUBLE AS count_probability,
      opening_upb / NULLIF(SUM(opening_upb) OVER(PARTITION BY segment,origin),0)::DOUBLE AS balance_probability,
      distinct_loans < 30 AS sparse_cell
    FROM grouped ORDER BY segment,origin,destination''').to_arrow_table()


def run(root, canonical):
    receipt = json.loads((canonical / 'run-complete.json').read_text())
    if receipt.get('status') != 'CANONICAL_COMPLETE':
        raise ValueError('Completed canonical required')
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        for table in ('dim_loan', 'fact_loan_month'):
            path = canonical / (table + '.parquet')
            if sha256(path) != receipt['outputs_sha256'][path.name]:
                raise ValueError('Canonical hash mismatch')
            db.read_parquet(str(path)).create_view(table)
        result = build(db, root / 'sql')
        db.register('segmented', result)
        bad = db.execute('''SELECT COUNT(*) FROM (
          SELECT segment,origin FROM segmented GROUP BY ALL
          HAVING ABS(SUM(count_probability)-1)>1e-10)''').fetchone()[0]
        if bad:
            raise ValueError('Probability reconciliation failed')
        output = root / 'artifacts/private' / ('segmented-transitions-' + uuid.uuid4().hex[:12])
        output.mkdir()
        db.table('segmented').write_parquet(str(output / 'transitions.parquet'))
        total = db.execute('SELECT COUNT(*) FROM pairs WHERE adjacent').fetchone()[0]
        if sum(result.column('pairs').to_pylist()) != total:
            raise ValueError('Segment pair reconciliation failed')
    write_json_new(output / 'run-complete.json', {
        'status': 'SEGMENTED_TRANSITIONS_COMPLETE', 'canonical_run': canonical.name,
        'visibility': 'private', 'public_release_approved': False,
        'rows': result.num_rows, 'adjacent_pairs': total,
        'outputs_sha256': {'transitions.parquet': sha256(output / 'transitions.parquet')},
        'limitations': ['Repeated pairs from the same loan are dependent.',
          'Sparse means fewer than 30 distinct loans; threshold is descriptive.',
          'No causal Relief effect or independent-pair confidence interval claimed.']})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical-run', type=Path, required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[2], args.canonical_run.resolve()))
