"""Independent fraction arithmetic for source-native import units and aggregates."""
import argparse
import csv
import json
import uuid
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import duckdb

from credit_atlas.exposure_imports import verify_import
from credit_atlas.workspace import app_root, contained, read_json, sha256, timestamp, write_new


def audit(root, identifier):
    folder, receipt, report = verify_import(root, identifier); metadata = read_json(folder / 'metadata.json')
    pins = {folder / 'import-complete.json': sha256(folder / 'import-complete.json')}
    pins.update({folder / name: digest for name, digest in receipt['outputs_sha256'].items()})
    pins.update({contained(root, row['path']): row['sha256'] for row in metadata['source_lineage']})
    currencies = defaultdict(lambda: [0, Fraction(0), Fraction(0), 0]); groups = defaultdict(lambda: [0, Fraction(0), Fraction(0)])
    with (folder / 'source.csv').open(encoding='utf-8-sig', newline='') as stream: raw = list(csv.DictReader(stream))
    connection = duckdb.connect()
    try: typed = connection.execute('SELECT source_row,reported_amount_major_exact,research_el_major_exact FROM read_parquet(?) ORDER BY source_row', [str(folder / 'positions.parquet')]).fetchall()
    finally: connection.close()
    checks = []; bad_amount = 0; bad_el = 0
    for index, row in enumerate(raw):
        major = Fraction(row['reported_amount']) * {'major': 1, 'thousand': 1000, 'million': 1000000}[row['amount_unit']]
        el = Fraction(row['pd']) * Fraction(row['lgd']) * Fraction(row['ead']) if metadata['risk_contract'] else None
        ordinal, typed_amount, typed_el = typed[index]
        bad_amount += ordinal != index + 1 or Fraction(typed_amount) != major
        bad_el += (typed_el is not None) if el is None else typed_el is None or Fraction(typed_el) != el
        currency = row['currency']; item = currencies[currency]; item[0] += 1; item[1] += major; item[3] += major == 0
        if el is not None: item[2] += el
        for dimension in ('segment', 'region', 'source_state', 'representation'):
            group = groups[(currency, dimension, row[dimension])]; group[0] += 1; group[1] += major
            if el is not None: group[2] += el
    def check(name, passed): checks.append({'check': name, 'passed': bool(passed)})
    check('Source/typed/report record counts', len(raw) == len(typed) == report['records'])
    check('Every row independently scaled major amount and ordinal', bad_amount == 0)
    check('Every row independently factorized EL or unavailable', bad_el == 0)
    for item in report['currencies']:
        count, amount, el, zeros = currencies[item['currency']]
        check(item['currency'] + '/currency counts/amount/zero-balance', item['records'] == count and Fraction(item['reported_amount_major_exact']) == amount and item['zero_amount_records'] == zeros)
        check(item['currency'] + '/research EL', item['research_el_major_exact'] is None if metadata['risk_contract'] is None else Fraction(item['research_el_major_exact']) == el)
    check('Entire concentration key set', {(row['currency'], row['dimension'], row['bucket']) for row in report['concentrations']} == set(groups))
    for item in report['concentrations']:
        count, amount, el = groups[(item['currency'], item['dimension'], item['bucket'])]
        check(item['currency'] + '/' + item['dimension'] + '/' + item['bucket'], item['records'] == count and Fraction(item['reported_amount_major_exact']) == amount
              and (item['research_el_major_exact'] is None if metadata['risk_contract'] is None else Fraction(item['research_el_major_exact']) == el))
    if any(sha256(path) != digest for path, digest in pins.items()): raise ValueError('Source/import changed during audit')
    audit_id = 'exposure-audit-' + uuid.uuid4().hex[:12]
    result = {'audit_id': audit_id, 'import_id': identifier, 'status': 'PASS' if all(row['passed'] for row in checks) else 'FAIL',
        'completed_at': timestamp(), 'checks': checks, 'script_sha256': sha256(Path(__file__)),
        'import_receipt_sha256': pins[folder / 'import-complete.json'], 'visibility': 'private', 'public_release_approved': False}
    write_new(contained(root, 'artifacts/private/' + audit_id + '/audit-complete.json'), result)
    if result['status'] != 'PASS': raise ValueError('Independent exposure audit failed')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--import-id', required=True)
    result = audit(app_root(), parser.parse_args().import_id)
    print(json.dumps({'audit_id': result['audit_id'], 'status': result['status'], 'checks': len(result['checks'])}))
