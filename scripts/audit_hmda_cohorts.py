"""Independent raw CSV aggregation and rational-weight HMDA cohort audit."""
import argparse
import json
import uuid
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import duckdb

from credit_atlas.hmda_cohorts import verify_cohorts
from credit_atlas.workspace import app_root, contained, read_json, sha256, timestamp, write_new

FIELDS = ('loan_type', 'occupancy_type', 'total_units', 'lien_status', 'reverse_mortgage', 'open-end_line_of_credit')
PRESETS = {
    'all_source': [],
    'principal_1_4_units': [('occupancy_type', ('1',)), ('total_units', ('1', '2', '3', '4'))],
    'principal_1_4_first_lien_closed_non_reverse': [('occupancy_type', ('1',)),
        ('total_units', ('1', '2', '3', '4')), ('lien_status', ('1',)),
        ('reverse_mortgage', ('2',)), ('open-end_line_of_credit', ('2',))],
}
SQL = ('SELECT activity_year,' + ','.join('"' + field + '"' for field in FIELDS) +
       ',action_taken,count(*),sum(CAST(loan_amount AS DECIMAL(38,2))) '
       'FROM read_csv(?,header=true,all_varchar=true,force_not_null=?,strict_mode=true) GROUP BY ALL ORDER BY ALL')


def as_fraction(value):
    return None if value is None else Fraction(int(value['numerator']), int(value['denominator']))


def summary(rows):
    counts = {str(i): 0 for i in range(1, 9)}; amounts = {key: Decimal(0) for key in counts}
    for row in rows: counts[row['action_code']] += row['records']; amounts[row['action_code']] += Decimal(row['public_amount_usd'])
    return {'records': sum(counts.values()), 'denominator': counts['1'] + counts['2'] + counts['3'],
            'denied': counts['3'], 'amount': sum(amounts.values()), 'counts': counts, 'amounts': amounts}


def matches(derived, expected):
    return (derived['records'] == expected['records'] and derived['denominator'] == expected['decision_denominator']
            and derived['denied'] == expected['denied_numerator'] and derived['amount'] == Decimal(expected['public_amount_sum_usd'])
            and all(derived['counts'][row['code']] == row['records'] and derived['amounts'][row['code']] == Decimal(row['public_amount_sum_usd']) for row in expected['actions']))


def audit(root, identifier):
    folder, receipt, payload = verify_cohorts(root, identifier)
    source = contained(root, 'data/private/hmda/' + receipt['source_id'])
    pins = {folder / 'cohort-complete.json': sha256(folder / 'cohort-complete.json')}
    pins.update({folder / name: digest for name, digest in receipt['outputs_sha256'].items()})
    pins[source / 'source-complete.json'] = sha256(source / 'source-complete.json')
    pins.update({contained(source, row['file']): row['sha256'] for row in read_json(source / 'source-complete.json')['files']})
    rows = []; checks = []; connection = duckdb.connect()
    def check(name, passed): checks.append({'check': name, 'passed': bool(passed)})
    try:
        for year in receipt['years']:
            values = connection.execute(SQL, [str(source / f'{year}-MD-home-purchase-site-built.csv'),
                ['activity_year', *FIELDS, 'action_taken', 'loan_amount']]).fetchall()
            rows.extend({'year': int(row[0]), 'categories': dict(zip(FIELDS, row[1:7])),
                         'action_code': row[7], 'records': row[8], 'public_amount_usd': str(row[9])} for row in values)
    finally: connection.close()
    check('Entire six-field joint mart equals independently read original CSV', rows == read_json(folder / 'joint-mart.json'))
    for name, steps in PRESETS.items():
        selected = list(rows); observed = next(row for row in payload['cohorts'] if row['cohort'] == name)
        for step_index, (field, allowed) in enumerate(steps):
            excluded = [row for row in selected if row['categories'][field] not in allowed]
            retained = [row for row in selected if row['categories'][field] in allowed]
            for year_index, year in enumerate(receipt['years']):
                step = observed['attrition'][step_index]['years'][year_index]
                check(f'{name}/{year}/{field}/ordered attrition', all(matches(summary([row for row in cohort if row['year'] == year]), step[key])
                    for key, cohort in [('before', selected), ('excluded', excluded), ('retained', retained)]))
            selected = retained
        cells = {year: defaultdict(lambda: [0, 0]) for year in receipt['years']}
        for row in selected:
            if row['action_code'] not in ('1', '2', '3'): continue
            key = tuple(row['categories'][field] for field in ('loan_type', 'occupancy_type', 'total_units'))
            cells[row['year']][key][0] += row['records']
            if row['action_code'] == '3': cells[row['year']][key][1] += row['records']
        reference = cells[2023]; reference_denominator = sum(value[0] for value in reference.values())
        common = set(reference).intersection(*(set(cells[year]) for year in receipt['years']))
        common_denominator = sum(reference[key][0] for key in common)
        check(name + '/common reference scope', observed['comparison']['common_reference_denominator'] == common_denominator and observed['comparison']['common_support_cells'] == len(common))
        for index, year in enumerate(receipt['years']):
            current = cells[year]; missing = set(reference) - set(current)
            full = None if not reference_denominator or missing else sum((Fraction(reference[key][0] * current[key][1], reference_denominator * current[key][0]) for key in reference), Fraction(0))
            shared = None if not common_denominator else sum((Fraction(reference[key][0] * current[key][1], common_denominator * current[key][0]) for key in common), Fraction(0))
            result = observed['comparison']['years'][index]
            check(f'{name}/{year}/all-action totals and amounts', matches(summary([row for row in selected if row['year'] == year]), observed['years'][index]))
            check(f'{name}/{year}/full reference rate', as_fraction(result['full_reference_standardized_rate']) == full)
            check(f'{name}/{year}/common support rate', as_fraction(result['common_support_standardized_rate']) == shared)
            check(f'{name}/{year}/missing reference cells', {tuple(row[field] for field in ('loan_type', 'occupancy_type', 'total_units')) for row in result['missing_reference_cells']} == missing)
            covered = sum(reference[key][0] for key in reference if key in current)
            check(f'{name}/{year}/weight coverage', result['covered_reference_denominator'] == covered and result['reference_denominator'] == reference_denominator)
    if any(sha256(path) != digest for path, digest in pins.items()): raise ValueError('Source/cohort evidence changed during independent audit')
    audit_id = 'hmda-cohort-audit-' + uuid.uuid4().hex[:12]
    result = {'audit_id': audit_id, 'cohort_id': identifier, 'status': 'PASS' if all(row['passed'] for row in checks) else 'FAIL',
        'completed_at': timestamp(), 'checks': checks, 'query': SQL, 'audit_script_sha256': sha256(Path(__file__)),
        'cohort_receipt_sha256': pins[folder / 'cohort-complete.json'], 'visibility': 'private', 'public_release_approved': False}
    write_new(contained(root, 'artifacts/private/' + audit_id + '/audit-complete.json'), result)
    if result['status'] != 'PASS': raise ValueError('Independent cohort audit failed')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--cohort', required=True)
    result = audit(app_root(), parser.parse_args().cohort)
    print(json.dumps({'audit_id': result['audit_id'], 'status': result['status'], 'checks': len(result['checks'])}))
