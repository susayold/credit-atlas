"""Typed private exposure snapshots and explicit factorized research assumptions."""
import csv
import json
import re
import shutil
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .workspace import contained, read_json, sha256, timestamp, write_new

FIELDS = ('position_id', 'pool_key', 'representation', 'as_of', 'currency', 'amount_unit',
          'reported_amount', 'segment', 'region', 'source_state', 'pd', 'lgd', 'ead')
CURRENCIES = ('USD', 'EUR', 'GBP', 'VND', 'TWD')
UNITS = {'major': Decimal(1), 'thousand': Decimal(1000), 'million': Decimal(1000000)}
PATTERN = re.compile(r'exposure-import-[0-9a-f]{12}\Z')
MAX_BYTES = 100 * 1024**2
MAX_ROWS = 500000
RISK_KEYS = {'pd_semantics', 'lgd_semantics', 'ead_semantics', 'basis', 'default_definition', 'horizon_months'}
META_KEYS = {'schema_version', 'dataset_kind', 'amount_kind', 'as_of', 'date_grain', 'source_namespace',
             'source_description', 'risk_contract', 'source_lineage', 'visibility', 'public_release_approved'}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('exposure_imports', 'workspace')}


def numeric(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:0|[1-9]\d{0,23})(?:\.\d{1,18})?', value):
        raise ValueError('Finite nonnegative decimal string required; no scientific notation or silent rounding')
    return Decimal(value)


def text(value):
    return isinstance(value, str) and 0 < len(value) <= 240 and value == value.strip() and not any(ord(c) < 32 for c in value)


def validate_metadata(metadata):
    if (not isinstance(metadata, dict) or set(metadata) != META_KEYS or type(metadata['schema_version']) is not int
            or metadata['schema_version'] != 1 or metadata['visibility'] != 'private'
            or metadata['public_release_approved'] is not False
            or metadata['dataset_kind'] not in ('source_observation', 'declared_portfolio')
            or metadata['amount_kind'] not in ('reported_outstanding_principal', 'declared_position_amount')
            or not text(metadata['source_namespace']) or not text(metadata['source_description'])):
        raise ValueError('Explicit private exposure metadata contract required')
    period = metadata['as_of']
    if metadata['date_grain'] == 'month':
        if not isinstance(period, str) or not re.fullmatch(r'\d{4}-\d{2}', period): raise ValueError('ISO observation month required')
        date.fromisoformat(period + '-01')
    elif metadata['date_grain'] == 'day':
        if not isinstance(period, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', period): raise ValueError('ISO as-of day required')
        date.fromisoformat(period)
    else: raise ValueError('Explicit month/day grain required')
    if not isinstance(metadata['source_lineage'], list): raise ValueError('Source lineage list required')
    if len({row['path'] for row in metadata['source_lineage']}) != len(metadata['source_lineage']): raise ValueError('Duplicate lineage path')
    for row in metadata['source_lineage']:
        if set(row) != {'path', 'sha256'} or not isinstance(row['path'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256']):
            raise ValueError('Invalid pinned source lineage')
    risk = metadata['risk_contract']
    if risk is not None:
        if (not isinstance(risk, dict) or set(risk) != RISK_KEYS or metadata['dataset_kind'] != 'declared_portfolio'
                or risk['pd_semantics'] != 'cumulative_default_probability'
                or risk['lgd_semantics'] != 'conditional_fraction_of_ead_on_default'
                or risk['ead_semantics'] != 'declared_exposure_at_default_major_currency'
                or risk['basis'] != 'declared_research_assumption' or not text(risk['default_definition'])
                or type(risk['horizon_months']) is not int or not 1 <= risk['horizon_months'] <= 1200):
            raise ValueError('Unknown/mixed score semantics; explicit cumulative default research assumptions required')
    return metadata


def verify_lineage(root, metadata):
    for row in metadata['source_lineage']:
        if sha256(contained(root, row['path'])) != row['sha256']: raise ValueError('Pinned upstream lineage changed')


def normalize(path, metadata):
    validate_metadata(metadata)
    if not 0 < path.stat().st_size <= MAX_BYTES: raise ValueError('Exposure CSV exceeds size bound')
    result = []; identifiers = set(); pools = defaultdict(set)
    with path.open(encoding='utf-8-sig', newline='') as stream, localcontext() as context:
        context.prec = 120
        reader = csv.reader(stream, strict=True)
        if next(reader, []) != list(FIELDS): raise ValueError('Exact exposure CSV header required; untyped score fields rejected')
        for ordinal, values in enumerate(reader, 1):
            if ordinal > MAX_ROWS or len(values) != len(FIELDS): raise ValueError('Exposure row bound/width mismatch')
            row = dict(zip(FIELDS, values))
            if (not all(text(row[field]) for field in ('position_id', 'pool_key', 'segment', 'region', 'source_state'))
                    or row['position_id'] in identifiers or row['as_of'] != metadata['as_of']
                    or row['currency'] not in CURRENCIES or row['amount_unit'] not in UNITS
                    or row['representation'] not in ('DIRECT_ASSET', 'SECURITY_POSITION')):
                raise ValueError('Invalid/duplicate position, mixed date/scope, currency/unit or representation')
            identifiers.add(row['position_id']); pools[row['pool_key']].add(row['representation'])
            amount = numeric(row['reported_amount']) * UNITS[row['amount_unit']]
            risk = metadata['risk_contract']; expected_loss = None
            if risk is None:
                if any(row[key] != '' for key in ('pd', 'lgd', 'ead')): raise ValueError('Risk values have no qualified semantics; not inferred from scores/balances')
            else:
                if row['source_state'] != 'DECLARED_PERFORMING': raise ValueError('Factorized scenario supports declared-performing positions only')
                pd, lgd, ead = (numeric(row[field]) for field in ('pd', 'lgd', 'ead'))
                if pd > 1 or lgd > 1: raise ValueError('PD/LGD use fractions in [0,1], not percentages')
                expected_loss = pd * lgd * ead
            result.append({**row, 'source_row': ordinal, 'reported_amount_major_exact': str(amount),
                'research_el_major_exact': None if expected_loss is None else str(expected_loss)})
    if not result: raise ValueError('Exposure CSV has no records')
    if any(len(values) > 1 for values in pools.values()):
        raise ValueError('Overlapping direct assets and security representations in same declared pool; no double counting')
    return result


def typed_schema():
    return pa.schema([pa.field(field, pa.string(), nullable=False) for field in FIELDS] +
        [pa.field('source_row', pa.int64(), nullable=False), pa.field('reported_amount_major_exact', pa.string(), nullable=False),
         pa.field('research_el_major_exact', pa.string())])


def aggregate(rows, metadata):
    currencies = {}; groups = defaultdict(lambda: [0, Decimal(0), Decimal(0), 0])
    with localcontext() as context:
        context.prec = 120
        for row in rows:
            currency = row['currency']; amount = Decimal(row['reported_amount_major_exact'])
            el = row['research_el_major_exact']; item = currencies.setdefault(currency,
                {'records': 0, 'zero_amount_records': 0, 'amount': Decimal(0), 'el': Decimal(0), 'el_records': 0})
            item['records'] += 1; item['zero_amount_records'] += amount == 0; item['amount'] += amount
            if el is not None: item['el'] += Decimal(el); item['el_records'] += 1
            for dimension in ('segment', 'region', 'source_state', 'representation'):
                group = groups[(currency, dimension, row[dimension])]; group[0] += 1; group[1] += amount
                if el is not None: group[2] += Decimal(el); group[3] += 1
        totals = [{'currency': currency, 'records': item['records'], 'zero_amount_records': item['zero_amount_records'],
            'reported_amount_major_exact': str(item['amount']), 'research_el_major_exact': str(item['el']) if item['el_records'] else None,
            'el_status': 'DECLARED_FACTORIZED_RESEARCH_SCENARIO' if item['el_records'] else 'UNAVAILABLE_NO_RISK_INPUTS'}
            for currency, item in sorted(currencies.items())]
        concentrations = [{'currency': currency, 'dimension': dimension, 'bucket': bucket, 'records': count,
            'reported_amount_major_exact': str(amount), 'amount_share': str(amount / currencies[currency]['amount']) if currencies[currency]['amount'] else None,
            'research_el_major_exact': str(el) if el_count else None}
            for (currency, dimension, bucket), (count, amount, el, el_count) in sorted(groups.items())]
    return {'records': len(rows), 'as_of': metadata['as_of'], 'date_grain': metadata['date_grain'],
        'dataset_kind': metadata['dataset_kind'], 'amount_kind': metadata['amount_kind'], 'source_namespace': metadata['source_namespace'],
        'source_description': metadata['source_description'], 'risk_contract': metadata['risk_contract'],
        'currencies': totals, 'concentrations': concentrations, 'global_cross_currency_total': None,
        'contract': {'fx_conversion_performed': False, 'borrower_identity_linkage': False, 'ownership_certified': False,
            'overlap_identity_certified': False, 'production_pd_qualified': False, 'accounting_ecl': False, 'regulatory_irb': False,
            'amount_is_ead': False, 'el_formula': 'Declared performing point assumptions: cumulative PD × conditional LGD × explicitly declared EAD',
            'pool_guard': 'Exact declared pool keys only; representation conflicts rejected, unknown real-world links not certified',
            'concentration_grain': 'Position/observation segments, not obligor concentration; no borrower identity available'},
        'visibility': 'private', 'public_release_approved': False}


def import_exposures(root, csv_path, metadata_path):
    csv_path = contained(root, csv_path); metadata_path = contained(root, metadata_path)
    metadata = validate_metadata(read_json(metadata_path)); verify_lineage(root, metadata)
    frozen = methods(); originals = {csv_path: sha256(csv_path), metadata_path: sha256(metadata_path)}
    rows = normalize(csv_path, metadata); report = aggregate(rows, metadata)
    identifier = 'exposure-import-' + uuid.uuid4().hex[:12]; folder = contained(root, 'artifacts/private/' + identifier)
    folder.mkdir(parents=True)
    shutil.copyfile(csv_path, folder / 'source.csv'); shutil.copyfile(metadata_path, folder / 'metadata.json')
    schema = typed_schema()
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), folder / 'positions.parquet', compression='zstd')
    write_new(folder / 'report.json', report); verify_lineage(root, metadata)
    if methods() != frozen or any(sha256(path) != digest for path, digest in originals.items()): raise ValueError('Import methods/inputs changed')
    if sha256(folder / 'source.csv') != originals[csv_path] or sha256(folder / 'metadata.json') != originals[metadata_path]: raise ValueError('Copied source bytes changed')
    receipt = {'import_id': identifier, 'status': 'VERIFIED_TYPED_EXPOSURE_IMPORT', 'completed_at': timestamp(), 'methods': frozen,
        'outputs_sha256': {name: sha256(folder / name) for name in ('source.csv', 'metadata.json', 'positions.parquet', 'report.json')},
        'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'import-complete.json', receipt)
    return receipt


def verify_import(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier): raise ValueError('Invalid exposure import ID')
    folder = contained(root, 'artifacts/private/' + identifier); receipt = read_json(folder / 'import-complete.json')
    if (receipt['import_id'] != identifier or receipt['status'] != 'VERIFIED_TYPED_EXPOSURE_IMPORT' or receipt['methods'] != methods()
            or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
            or set(receipt['outputs_sha256']) != {'source.csv', 'metadata.json', 'positions.parquet', 'report.json'}):
        raise ValueError('Exposure import contract changed')
    for name, digest in receipt['outputs_sha256'].items():
        if sha256(contained(folder, name)) != digest: raise ValueError('Exposure payload changed')
    metadata = validate_metadata(read_json(folder / 'metadata.json')); verify_lineage(root, metadata)
    rows = normalize(folder / 'source.csv', metadata)
    table = pq.read_table(folder / 'positions.parquet')
    if table.schema != typed_schema() or table.to_pylist() != rows: raise ValueError('Typed exposure positions differ from original CSV/schema')
    expected = aggregate(rows, metadata); report = read_json(folder / 'report.json')
    if json.dumps(report, sort_keys=True) != json.dumps(expected, sort_keys=True): raise ValueError('Exposure report differs from source projection')
    return folder, receipt, report
