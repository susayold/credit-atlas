"""HMDA public application evidence; exact fields and denominator-specific marts."""
import csv
import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .hmda_sources import verify_source
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'hmda-case-[0-9a-f]{12}\Z')
ACTIONS = {'1': 'ORIGINATED', '2': 'APPROVED_NOT_ACCEPTED', '3': 'DENIED', '4': 'WITHDRAWN',
           '5': 'CLOSED_INCOMPLETE', '6': 'PURCHASED_LOAN', '7': 'PREAPPROVAL_DENIED', '8': 'PREAPPROVAL_APPROVED_NOT_ACCEPTED'}
DIMENSIONS = ('county_code', 'lei', 'loan_type', 'derived_race', 'derived_ethnicity', 'derived_sex',
              'debt_to_income_ratio', 'derived_dwelling_category')
STRING_FIELDS = ('source_file', 'lei', 'state_code', 'county_code', 'loan_type', 'loan_purpose',
    'construction_method', 'action_code', 'action_name', 'public_loan_amount_usd_exact',
    'income_thousands_usd_exact', 'income_status', 'property_value_usd_exact', 'property_value_status',
    'interest_rate_percent_exact', 'interest_rate_status', 'dti_public_category', 'applicant_age_public_category',
    'ltv_source_raw_unqualified', 'derived_race', 'derived_ethnicity', 'derived_sex', 'derived_dwelling_category',
    'public_row_fingerprint')
SCHEMA = pa.schema([pa.field('source_row', pa.int64(), nullable=False),
    pa.field('activity_year', pa.int32(), nullable=False), pa.field('decision_denominator_eligible', pa.bool_(), nullable=False)] +
    [pa.field(name, pa.string(), nullable=name.endswith('_exact') and name != 'public_loan_amount_usd_exact') for name in STRING_FIELDS])


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('hmda_applications', 'hmda_sources', 'workspace')}


def exact_optional(raw):
    if raw == '': return None, 'SOURCE_BLANK'
    if raw == 'NA': return None, 'NOT_APPLICABLE'
    if raw == 'Exempt': return None, 'EXEMPT'
    try: value = Decimal(raw)
    except InvalidOperation as error: raise ValueError('Invalid HMDA exact numeric field') from error
    if not value.is_finite(): raise ValueError('Nonfinite HMDA numeric field')
    return format(value, 'f'), 'VALUE'


def application(row, name, ordinal):
    if not set(DIMENSIONS).issubset(row): raise ValueError('HMDA application dimensions missing from public source')
    action = row['action_taken']
    if action not in ACTIONS: raise ValueError('Unsupported HMDA action code')
    income, income_status = exact_optional(row['income'])
    property_value, property_status = exact_optional(row['property_value'])
    rate, rate_status = exact_optional(row['interest_rate'])
    return {'source_file': name, 'source_row': ordinal, 'activity_year': int(row['activity_year']),
        'lei': row['lei'], 'state_code': row['state_code'], 'county_code': row['county_code'],
        'loan_type': row['loan_type'], 'loan_purpose': row['loan_purpose'], 'construction_method': row['construction_method'],
        'action_code': action, 'action_name': ACTIONS[action], 'decision_denominator_eligible': action in ('1', '2', '3'),
        'public_loan_amount_usd_exact': format(Decimal(row['loan_amount']), 'f'),
        'income_thousands_usd_exact': income, 'income_status': income_status,
        'property_value_usd_exact': property_value, 'property_value_status': property_status,
        'interest_rate_percent_exact': rate, 'interest_rate_status': rate_status,
        'dti_public_category': row['debt_to_income_ratio'], 'applicant_age_public_category': row['applicant_age'],
        'ltv_source_raw_unqualified': row['loan_to_value_ratio'],
        **{key: row[key] for key in ('derived_race', 'derived_ethnicity', 'derived_sex', 'derived_dwelling_category')},
        'public_row_fingerprint': hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()}


def source_rows(folder, source):
    for profile in source['profiles']:
        name = f"{profile['year']}-MD-home-purchase-site-built.csv"
        with (folder / name).open(encoding='utf-8-sig', newline='') as stream:
            for ordinal, row in enumerate(csv.DictReader(stream), 1):
                yield name, ordinal, row


def evidence(folder, source):
    annual = defaultdict(lambda: {'actions': Counter(), 'amounts': defaultdict(Decimal), 'reporters': set()})
    groups = defaultdict(lambda: [0, Decimal(0)])
    fingerprint_counts = Counter(); missing = Counter(); nonmidpoint = Counter()
    for name, ordinal, raw in source_rows(folder, source):
        row = application(raw, name, ordinal); year = row['activity_year']; code = row['action_code']
        amount = Decimal(row['public_loan_amount_usd_exact'])
        annual[year]['actions'][code] += 1; annual[year]['amounts'][code] += amount; annual[year]['reporters'].add(row['lei'])
        fingerprint_counts[row['public_row_fingerprint']] += 1
        if amount % 10000 != 5000: nonmidpoint[year] += 1
        for key in ('income_status', 'property_value_status', 'interest_rate_status'):
            missing[(year, key, row[key])] += 1
        for dimension in DIMENSIONS:
            group = groups[(year, dimension, raw[dimension], code)]; group[0] += 1; group[1] += amount
    years = []
    for year, data in sorted(annual.items()):
        counts = data['actions']; denominator = sum(counts[code] for code in ('1', '2', '3'))
        years.append({'year': year, 'records': sum(counts.values()), 'reporters': len(data['reporters']),
            'actions': dict(sorted(counts.items())), 'public_amounts_by_action_usd': {code: str(value) for code, value in sorted(data['amounts'].items())},
            'decision_denominator': denominator, 'denied_numerator': counts['3'],
            'descriptive_denial_rate': str(Decimal(counts['3']) / denominator) if denominator else None,
            'public_amounts_nonmidpoint_rows': nonmidpoint[year]})
    return {'years': years, 'marts': [{'year': year, 'dimension': dimension, 'bucket': bucket,
        'action_code': code, 'records': count, 'public_loan_amount_sum_usd': str(amount)}
        for (year, dimension, bucket, code), (count, amount) in sorted(groups.items())],
        'quality': {'exact_public_duplicate_groups': sum(count > 1 for count in fingerprint_counts.values()),
            'exact_public_duplicate_rows_beyond_first': sum(count - 1 for count in fingerprint_counts.values()),
            'duplicates_retained': True, 'application_id_available': False,
            'optional_numeric_status_counts': [{'year': year, 'field': field, 'status': status, 'records': count}
                for (year, field, status), count in sorted(missing.items())]},
        'denominator_contract': {'codes': ['1', '2', '3'], 'numerator': '3',
            'excluded': ['4', '5', '6', '7', '8'], 'meaning': 'Denied / (originated + approved-not-accepted + denied), descriptive only; not default PD'},
        'field_contract': {'loan_amount': 'USD public interval midpoint; sum is not exact actual funded volume',
            'income': 'Reported annual thousands of USD; negative/zero/1111 remain numeric values, not missing codes',
            'property_value': 'USD public interval midpoint; NA/Exempt/blank distinct from value zero',
            'interest_rate': 'Percent units as published; no divide-by-100 in canonical exact field',
            'dti_age': 'Public categories retained; no category midpoint or individual precise values inferred',
            'ltv': 'Raw loan_to_value_ratio retained; dictionary-name mismatch unresolved; no derived leverage ratio',
            'identity': 'source_file + source_row is provenance; fingerprint is public-row equality, not borrower/loan ID'},
        'visibility': 'private', 'public_release_approved': False,
        'qualification': {'default_pd': False, 'historical_availability': False, 'borrower_linkage': False,
                          'causal_or_compliance_conclusions': False, 'national_representativeness': False}}


def build_case(root, source_id):
    source_folder, source = verify_source(root, source_id)
    identifier = 'hmda-case-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'artifacts/private/' + identifier); folder.mkdir(parents=True)
    frozen = methods(); source_digest = sha256(source_folder / 'source-complete.json')
    raw_schema = pa.schema([pa.field('source_file', pa.string(), nullable=False),
        pa.field('source_row', pa.int64(), nullable=False)] +
        [pa.field(name, pa.string(), nullable=False) for name in source['profiles'][0]['header']])
    raw_batch, typed_batch = [], []
    with pq.ParquetWriter(folder / 'source_rows.parquet', raw_schema, compression='zstd') as raw_writer, \
            pq.ParquetWriter(folder / 'applications.parquet', SCHEMA, compression='zstd') as writer:
        for name, ordinal, row in source_rows(source_folder, source):
            raw_batch.append({'source_file': name, 'source_row': ordinal, **row})
            typed_batch.append(application(row, name, ordinal))
            if len(raw_batch) == 5000:
                raw_writer.write_table(pa.Table.from_pylist(raw_batch, schema=raw_schema)); writer.write_table(pa.Table.from_pylist(typed_batch, schema=SCHEMA))
                raw_batch.clear(); typed_batch.clear()
        if raw_batch:
            raw_writer.write_table(pa.Table.from_pylist(raw_batch, schema=raw_schema)); writer.write_table(pa.Table.from_pylist(typed_batch, schema=SCHEMA))
    report = evidence(source_folder, source); write_new(folder / 'evidence.json', report)
    if methods() != frozen or sha256(source_folder / 'source-complete.json') != source_digest:
        raise ValueError('HMDA source/methods changed while building')
    receipt = {'case_id': identifier, 'source_id': source_id, 'status': 'VERIFIED_PUBLIC_HMDA_APPLICATION_CASE',
        'completed_at': timestamp(), 'source_receipt_sha256': source_digest, 'methods': frozen,
        'records': sum(row['records'] for row in report['years']), 'mart_rows': len(report['marts']),
        'outputs_sha256': {name: sha256(folder / name) for name in ('source_rows.parquet', 'applications.parquet', 'evidence.json')},
        'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'case-complete.json', receipt)
    verify_case(root, identifier)
    return receipt


def parquet_rows(path):
    for batch in pq.ParquetFile(path).iter_batches(batch_size=5000):
        yield from batch.to_pylist()


def verify_case(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier): raise ValueError('Invalid HMDA case ID')
    folder = contained(root, 'artifacts/private/' + identifier); receipt = read_json(folder / 'case-complete.json')
    if (receipt['case_id'] != identifier or receipt['status'] != 'VERIFIED_PUBLIC_HMDA_APPLICATION_CASE'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or receipt['public_release_approved'] is not False): raise ValueError('HMDA case contract changed')
    source_folder, source = verify_source(root, receipt['source_id'])
    if sha256(source_folder / 'source-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('HMDA source receipt changed')
    for name, digest in receipt['outputs_sha256'].items():
        if name not in ('source_rows.parquet', 'applications.parquet', 'evidence.json') or sha256(folder / name) != digest:
            raise ValueError('HMDA derived artifact changed')
    if set(receipt['outputs_sha256']) != {'source_rows.parquet', 'applications.parquet', 'evidence.json'}:
        raise ValueError('HMDA required output missing')
    expected_raw_schema = pa.schema([pa.field('source_file', pa.string(), nullable=False),
        pa.field('source_row', pa.int64(), nullable=False)] + [pa.field(name, pa.string(), nullable=False) for name in source['profiles'][0]['header']])
    if pq.read_schema(folder / 'source_rows.parquet') != expected_raw_schema or pq.read_schema(folder / 'applications.parquet') != SCHEMA:
        raise ValueError('HMDA canonical schema changed')
    raws = iter(parquet_rows(folder / 'source_rows.parquet')); typed = iter(parquet_rows(folder / 'applications.parquet'))
    count = 0
    for name, ordinal, row in source_rows(source_folder, source):
        if next(raws, None) != {'source_file': name, 'source_row': ordinal, **row} or next(typed, None) != application(row, name, ordinal):
            raise ValueError('HMDA canonical rows differ from original source')
        count += 1
    if next(raws, None) is not None or next(typed, None) is not None or receipt['records'] != count:
        raise ValueError('HMDA canonical extra rows/count mismatch')
    actual = evidence(source_folder, source); saved = read_json(folder / 'evidence.json')
    if json.dumps(saved, sort_keys=True) != json.dumps(actual, sort_keys=True) or receipt['mart_rows'] != len(actual['marts']):
        raise ValueError('HMDA evidence differs from original source/denominators')
    return folder, receipt
