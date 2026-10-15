"""Independent DuckDB raw JSON/CSV reconciliation of dated lender references."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb

from credit_atlas.hmda_references import verify_references
from credit_atlas.workspace import app_root, contained, sha256, timestamp, write_new

NAMES_SQL = '''SELECT i.period AS activity_year, i.lei,
    list_sort(list_distinct(list(i.name))) AS names
    FROM read_json_auto(?), UNNEST(institutions) AS u(i)
    GROUP BY 1,2 ORDER BY 1,2'''
JOIN_SQL = '''WITH names AS (
    SELECT i.period AS activity_year, i.lei, count(DISTINCT i.name) AS name_count
    FROM read_json_auto(?), UNNEST(institutions) AS u(i) GROUP BY 1,2)
    SELECT s.lei, count(*) AS records,
      CASE WHEN n.name_count IS NULL THEN 'UNMATCHED'
           WHEN n.name_count=1 THEN 'MATCHED' ELSE 'AMBIGUOUS' END AS status
    FROM read_csv(?, header=true, all_varchar=true) AS s
    LEFT JOIN names n ON s.activity_year=CAST(n.activity_year AS VARCHAR) AND s.lei=n.lei
    GROUP BY s.lei,n.name_count ORDER BY s.lei'''


def audit(root, identifier):
    folder, receipt, payload = verify_references(root, identifier)
    if receipt['reference_scope'] != 'lender_only':
        raise ValueError('This independent audit covers lender-only references; county audit not implemented')
    source = contained(root, 'data/private/hmda/' + receipt['source_id'])
    pins = {folder / 'reference-complete.json': sha256(folder / 'reference-complete.json'),
            folder / 'labels.json': receipt['labels_sha256'],
            source / 'source-complete.json': receipt['source_receipt_sha256']}
    pins.update({folder / item['file']: item['sha256'] for item in receipt['files']})
    from credit_atlas.workspace import read_json
    pins.update({source / item['file']: item['sha256'] for item in read_json(source / 'source-complete.json')['files']})
    checks = []; connection = duckdb.connect()
    try:
        for coverage in payload['coverage']:
            year = coverage['year']; json_path = str(folder / f'{year}-filers.json')
            names = connection.execute(NAMES_SQL, [json_path]).fetchall()
            projected = {lei: {'names': candidates, 'status': 'MATCHED' if len(candidates) == 1 else 'AMBIGUOUS'}
                         for period, lei, candidates in names if period == year}
            rows = connection.execute(JOIN_SQL, [json_path, str(source / f'{year}-MD-home-purchase-site-built.csv')]).fetchall()
            statuses = {}; unresolved = {}
            for lei, count, status in rows:
                statuses[status] = statuses.get(status, 0) + count
                if status != 'MATCHED': unresolved[lei] = count
            lender = coverage['lender']
            values = {'raw_filer_labels': projected == payload['references'][str(year)]['lender'],
                'status_counts': statuses == lender['row_status_counts'],
                'unresolved_source_keys': unresolved == lender['unresolved_source_keys'],
                'source_records': sum(count for lei, count, status in rows) == coverage['records'],
                'source_key_count': len(rows) == lender['unique_source_keys']}
            checks.extend({'year': year, 'check': name, 'passed': passed} for name, passed in values.items())
    finally: connection.close()
    if any(sha256(path) != digest for path, digest in pins.items()):
        raise ValueError('Reference/source changed during independent audit')
    output_id = 'hmda-reference-audit-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + output_id)
    result = {'audit_id': output_id, 'reference_id': identifier, 'completed_at': timestamp(),
        'status': 'PASS' if all(row['passed'] for row in checks) else 'FAIL', 'checks': checks,
        'reference_receipt_sha256': pins[folder / 'reference-complete.json'],
        'audit_script_sha256': sha256(Path(__file__)), 'queries': {'names': NAMES_SQL, 'join': JOIN_SQL},
        'scope': 'dated lender names and exact raw CSV joins; county references not covered',
        'visibility': 'private', 'public_release_approved': False}
    write_new(output / 'audit-complete.json', result)
    if result['status'] != 'PASS': raise ValueError('Independent reference reconciliation failed')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--reference', required=True)
    result = audit(app_root(), parser.parse_args().reference)
    print(json.dumps({'audit_id': result['audit_id'], 'status': result['status'], 'checks': len(result['checks'])}))
