"""Exact HMDA cohort composition and descriptive fixed-weight comparisons."""
import json
import re
import uuid
from collections import defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import duckdb

from .hmda_views import HmdaViews, summarize
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'hmda-cohort-[0-9a-f]{12}\Z')
FIELDS = ('loan_type', 'occupancy_type', 'total_units', 'lien_status', 'reverse_mortgage', 'open-end_line_of_credit')
STRATA = ('loan_type', 'occupancy_type', 'total_units')
COHORTS = {
    'all_source': [],
    'principal_1_4_units': [('occupancy_type', ['1']), ('total_units', ['1', '2', '3', '4'])],
    'principal_1_4_first_lien_closed_non_reverse': [('occupancy_type', ['1']),
        ('total_units', ['1', '2', '3', '4']), ('lien_status', ['1']),
        ('reverse_mortgage', ['2']), ('open-end_line_of_credit', ['2'])],
}
CONTRACT = {
    'reference_year': 2023, 'strata': list(STRATA), 'decision_codes': ['1', '2', '3'], 'denied_code': '3',
    'weights': 'Reference-year decided counts / reference decided denominator; never loan amount weights',
    'full_reference': 'Unavailable if any positive reference-weight cell has zero target decided records; no renormalization',
    'common_support': 'Positive decided denominator in every observed year, among positive reference cells; explicit narrower descriptive cohort',
    'zero_denominator': 'Unavailable, never zero denial rate',
    'unit_bins': 'Exact public categories, no numerical midpoint imputation',
    'exclusions': 'Ordered, disjoint attrition counts; 1111 exempt is not a known non-reverse or closed-end value',
    'default_pd': False, 'causal_effect': False, 'fully_risk_adjusted': False,
    'historical_availability': False, 'national_representativeness': False,
}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
            ('hmda_cohorts', 'hmda_views', 'hmda_applications', 'hmda_sources', 'workspace')}


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def rational(value):
    if value is None: return None
    with localcontext() as context:
        context.prec = 50
        return {'numerator': str(value.numerator), 'denominator': str(value.denominator),
                'decimal': str(Decimal(value.numerator) / Decimal(value.denominator))}


def joint_mart(path):
    columns = ','.join('"' + field + '"' for field in FIELDS)
    connection = duckdb.connect()
    try:
        rows = connection.execute('SELECT activity_year,' + columns +
            ',action_taken,count(*),sum(CAST(loan_amount AS DECIMAL(38,2))) FROM read_parquet(?)'
            ' GROUP BY ALL ORDER BY ALL', [str(path)]).fetchall()
        return [{'year': int(row[0]), 'categories': dict(zip(FIELDS, row[1:7])),
                 'action_code': row[7], 'records': row[8], 'public_amount_usd': str(row[9])} for row in rows]
    finally: connection.close()


def totals(rows):
    values = defaultdict(lambda: [0, Decimal(0)])
    for row in rows:
        values[row['action_code']][0] += row['records']
        values[row['action_code']][1] += Decimal(row['public_amount_usd'])
    return summarize([(code, count, amount) for code, (count, amount) in sorted(values.items())])


def compare(rows, years, reference_year=2023):
    if reference_year not in years or len(set(years)) != len(years): raise ValueError('Invalid comparison reference/year scope')
    cells = {year: defaultdict(lambda: [0, 0]) for year in years}
    for row in rows:
        if row['year'] not in cells or row['action_code'] not in tuple(str(i) for i in range(1, 9)):
            raise ValueError('Comparison row outside year/action contract')
        if type(row['records']) is not int or row['records'] <= 0: raise ValueError('Invalid comparison count')
        if row['action_code'] in ('1', '2', '3'):
            key = tuple(row['categories'][field] for field in STRATA)
            cells[row['year']][key][0] += row['records']
            cells[row['year']][key][1] += row['records'] if row['action_code'] == '3' else 0
    reference = cells[reference_year]; denominator = sum(value[0] for value in reference.values())
    common = {key for key in reference if all(cells[year].get(key, [0, 0])[0] > 0 for year in years)}
    common_reference = sum(reference[key][0] for key in common)
    result = []
    for year in years:
        native_denominator = sum(value[0] for value in cells[year].values())
        native_denied = sum(value[1] for value in cells[year].values())
        missing = [key for key in sorted(reference) if not cells[year].get(key, [0, 0])[0]]
        covered = sum(reference[key][0] for key in reference if key not in missing)
        full = (sum((Fraction(reference[key][0], denominator) * Fraction(cells[year][key][1], cells[year][key][0])
                     for key in reference), Fraction(0)) if denominator and not missing else None)
        common_rate = (sum((Fraction(reference[key][0], common_reference) * Fraction(cells[year][key][1], cells[year][key][0])
                           for key in common), Fraction(0)) if common_reference else None)
        common_denominator = sum(cells[year][key][0] for key in common)
        common_denied = sum(cells[year][key][1] for key in common)
        result.append({'year': year, 'native_decision_denominator': native_denominator,
            'native_denied_numerator': native_denied,
            'native_rate': rational(Fraction(native_denied, native_denominator)) if native_denominator else None,
            'full_reference_status': 'NO_REFERENCE_DENOMINATOR' if not denominator else 'INCOMPLETE_SUPPORT' if missing else 'COMPLETE_SUPPORT',
            'full_reference_standardized_rate': rational(full),
            'covered_reference_denominator': covered, 'reference_denominator': denominator,
            'reference_weight_coverage': rational(Fraction(covered, denominator)) if denominator else None,
            'missing_reference_cells': [dict(zip(STRATA, key)) for key in missing],
            'common_support_decision_denominator': common_denominator,
            'common_support_denied_numerator': common_denied,
            'common_support_native_rate': rational(Fraction(common_denied, common_denominator)) if common_denominator else None,
            'common_support_standardized_rate': rational(common_rate),
            'non_reference_decision_denominator': sum(value[0] for key, value in cells[year].items() if key not in reference)})
    return {'reference_year': reference_year, 'strata': list(STRATA), 'reference_cells': len(reference),
            'common_support_cells': len(common), 'common_reference_denominator': common_reference,
            'common_reference_weight_coverage': rational(Fraction(common_reference, denominator)) if denominator else None,
            'reference_weights': [{'categories': dict(zip(STRATA, key)), 'decided': reference[key][0],
                'weight': rational(Fraction(reference[key][0], denominator)), 'in_common_support': key in common}
                for key in sorted(reference)], 'years': result}


def project(mart, years):
    cohorts = []
    for name, steps in COHORTS.items():
        selected = list(mart); attrition = []
        for field, allowed in steps:
            before = selected; selected = [row for row in before if row['categories'][field] in allowed]
            attrition.append({'field': field, 'allowed': allowed, 'years': [
                {'year': year, 'before': totals([row for row in before if row['year'] == year]),
                 'excluded': totals([row for row in before if row['year'] == year and row['categories'][field] not in allowed]),
                 'retained': totals([row for row in selected if row['year'] == year])} for year in years]})
        cohorts.append({'cohort': name, 'criteria': [[field, allowed] for field, allowed in steps],
            'attrition': attrition, 'years': [{'year': year, **totals([row for row in selected if row['year'] == year])} for year in years],
            'comparison': compare(selected, years)})
    profiles = []
    for year in years:
        rows = [row for row in mart if row['year'] == year]
        for field in FIELDS:
            for value in sorted({row['categories'][field] for row in rows}):
                profiles.append({'year': year, 'field': field, 'value': value,
                                 **totals([row for row in rows if row['categories'][field] == value])})
    return {'contract': CONTRACT, 'cohorts': cohorts, 'profiles': profiles,
            'visibility': 'private', 'public_release_approved': False}


def build_cohorts(root, case_id):
    service = HmdaViews(root); cached = service.case(case_id)
    frozen = methods(); folder = cached['folder']; case = cached['case']
    mart = joint_mart(folder / 'source_rows.parquet')
    years = sorted({row['year'] for row in mart}); report = project(mart, years)
    original = read_json(folder / 'evidence.json')
    for annual in original['years']:
        total = totals([row for row in mart if row['year'] == annual['year']])
        if (total['records'] != annual['records'] or total['decision_denominator'] != annual['decision_denominator']
                or total['denied_numerator'] != annual['denied_numerator']
                or {row['code']: row['records'] for row in total['actions']} != {str(i): annual['actions'].get(str(i), 0) for i in range(1, 9)}
                or any(Decimal(row['public_amount_sum_usd']) != Decimal(annual['public_amounts_by_action_usd'].get(row['code'], '0')) for row in total['actions'])):
            raise ValueError('Cohort source totals differ from verified canonical annual evidence')
    identifier = 'hmda-cohort-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    write_new(output / 'joint-mart.json', mart); write_new(output / 'coverage.json', report)
    service.case(case_id)
    if methods() != frozen: raise ValueError('Cohort methods changed during build')
    receipt = {'cohort_id': identifier, 'case_id': case_id, 'source_id': case['source_id'],
        'case_receipt_sha256': sha256(folder / 'case-complete.json'), 'status': 'VERIFIED_HMDA_COHORT_COMPOSITION',
        'completed_at': timestamp(), 'methods': frozen, 'years': years,
        'outputs_sha256': {name: sha256(output / name) for name in ('joint-mart.json', 'coverage.json')},
        'visibility': 'private', 'public_release_approved': False}
    write_new(output / 'cohort-complete.json', receipt)
    return receipt


def verify_cohorts(root, identifier, service=None):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier): raise ValueError('Invalid HMDA cohort identifier')
    folder = contained(root, 'artifacts/private/' + identifier); receipt = read_json(folder / 'cohort-complete.json')
    if (receipt['cohort_id'] != identifier or receipt['status'] != 'VERIFIED_HMDA_COHORT_COMPOSITION'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or receipt['public_release_approved'] is not False or set(receipt['outputs_sha256']) != {'joint-mart.json', 'coverage.json'}):
        raise ValueError('Cohort receipt contract changed')
    service = service or HmdaViews(root); cached = service.case(receipt['case_id'])
    if receipt['source_id'] != cached['case']['source_id'] or sha256(cached['folder'] / 'case-complete.json') != receipt['case_receipt_sha256']:
        raise ValueError('Cohort bound canonical source changed')
    for name, digest in receipt['outputs_sha256'].items():
        if sha256(contained(folder, name)) != digest: raise ValueError('Cohort output bytes changed')
    mart = joint_mart(cached['folder'] / 'source_rows.parquet'); years = sorted({row['year'] for row in mart})
    if receipt['years'] != years or not same(read_json(folder / 'joint-mart.json'), mart) or not same(read_json(folder / 'coverage.json'), project(mart, years)):
        raise ValueError('Cohort outputs differ from raw source projection')
    service.case(receipt['case_id'])
    return folder, receipt, read_json(folder / 'coverage.json')
