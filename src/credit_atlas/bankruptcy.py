"""UCI365 horizon-specific financial-statement facts; no invented firm identity."""
from __future__ import annotations

import csv
import hashlib
import math
import re
import subprocess
import uuid
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .public_sources import catalog
from .public_suite import verify_acquisition
from .workspace import app_root, contained, read_json, sha256, timestamp, write_new

FEATURES = tuple('A' + str(i) for i in range(1, 65))
HEADER = ['year', *FEATURES, 'class']
HORIZONS = {1: 5, 2: 4, 3: 3, 4: 2, 5: 1}
SOURCE_COUNTS = {1: (7027, 271), 2: (10173, 400), 3: (10503, 495),
                 4: (9792, 515), 5: (5910, 410)}
REFERENCE_URL = 'https://archive.ics.uci.edu/static/public/365/polish%2Bcompanies%2Bbankruptcy%2Bdata.zip'
REFERENCE_FILES = {str(code) + 'year.arff' for code in HORIZONS}
SCHEMA = pa.schema([('source_row_ordinal', pa.int32()), ('source_subset_code', pa.int8()),
    ('forecast_horizon_years', pa.int8()), ('source_bankruptcy_label', pa.int8())] +
    [(name, pa.float64()) for name in FEATURES])
DIFFERENCE_SCHEMA = pa.schema([('source_row_ordinal', pa.int32()), ('source_subset_code', pa.int8()),
    ('feature', pa.string()), ('csv_value', pa.float64()), ('original_arff_value', pa.float64()),
    ('original_arff_token', pa.string()), ('matches_scientific_three_digit_half_up', pa.bool_())])


def methods():
    return {name: sha256(app_root() / 'src/credit_atlas' / name) for name in
            ('bankruptcy.py', 'public_suite.py', 'public_sources.py', 'workspace.py')}


def _number(value):
    if value == 'NaN':
        return None
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value):
        raise ValueError('Unexpected UCI365 numeric token')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('Nonfinite UCI365 feature')
    return number


def canonical_rows(path, metadata):
    data = metadata['data']
    if (data['uci_id'] != 365 or data['target_col'] != ['class']
            or [item['name'] for item in data['variables']] != HEADER):
        raise ValueError('UCI365 source metadata/schema changed')
    rows = []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != HEADER:
            raise ValueError('Unexpected UCI365 CSV schema')
        for ordinal, item in enumerate(reader, 1):
            if None in item or any(value is None for value in item.values()):
                raise ValueError('Malformed UCI365 CSV width')
            if item['year'] not in {'1', '2', '3', '4', '5'} or item['class'] not in {'0', '1'}:
                raise ValueError('Invalid UCI365 horizon or target code')
            code = int(item['year'])
            rows.append({'source_row_ordinal': ordinal, 'source_subset_code': code,
                'forecast_horizon_years': HORIZONS[code], 'source_bankruptcy_label': int(item['class']),
                **{name: _number(item[name]) for name in FEATURES}})
    if not rows:
        raise ValueError('Empty UCI365 population')
    return rows


def definitions(metadata):
    # Metadata A1..A64 map to ARFF Attr1..Attr64; definitions use X1..X64.
    text = metadata['data']['additional_info']['variable_info']
    result = []
    for line in text.splitlines():
        match = re.fullmatch(r'X(\d+)\s+(.+)', line.strip())
        if not match:
            raise ValueError('UCI365 variable definition changed')
        index = int(match[1])
        if index != len(result) + 1:
            raise ValueError('UCI365 variable definition order changed')
        result.append({'feature': 'A' + str(index), 'original_attribute': 'Attr' + str(index),
            'definition_identifier': 'X' + str(index),
            'source_definition': match[2], 'units_verified': False})
    if len(result) != 64:
        raise ValueError('UCI365 requires 64 financial definitions')
    return result


def _members(path):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if (len(members) != 5 or {item.filename for item in members} != REFERENCE_FILES
                or any(item.file_size > 32 * 1024**2 or item.flag_bits & 1 for item in members)):
            raise ValueError('Unexpected UCI365 reference archive members')
        if archive.testzip() is not None:
            raise ValueError('Invalid UCI365 reference ZIP CRC')


def acquire_reference(root):
    output = contained(root, 'data/private/polish-reference-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output / 'run-start.json', {'started_at': timestamp(), 'url': REFERENCE_URL})
    partial = output / 'original-arff.zip.partial'
    response = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
        '--connect-timeout', '20', '--max-time', '180', '--max-filesize', str(32 * 1024**2),
        '--output', str(partial), '--write-out', '%{http_code}', REFERENCE_URL], capture_output=True)
    if response.returncode != 0 or response.stdout != b'200':
        write_new(output / 'failed.json', {'completed_at': timestamp(), 'curl_code': response.returncode,
                  'http_status': response.stdout.decode('ascii', errors='replace')[:3]})
        raise RuntimeError('Official UCI365 reference download failed')
    _members(partial)
    path = output / 'original-arff.zip'
    partial.rename(path)
    write_new(output / 'receipt.json', {'reference_id': output.name, 'url': REFERENCE_URL,
        'retrieved_at': timestamp(), 'http_status': 200, 'file': path.name, 'sha256': sha256(path),
        'bytes': path.stat().st_size, 'members': sorted(REFERENCE_FILES), 'visibility': 'private',
        'rights': 'CC BY 4.0; Tomczak (2016), DOI 10.24432/C5F600', 'public_release_approved': False})
    return output.name


def verify_reference(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'polish-reference-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid Polish reference identifier')
    folder = contained(root, 'data/private/' + identifier)
    receipt = read_json(folder / 'receipt.json')
    if (receipt['reference_id'] != identifier or receipt['url'] != REFERENCE_URL
            or receipt['http_status'] != 200 or receipt['file'] != 'original-arff.zip'
            or receipt['members'] != sorted(REFERENCE_FILES) or receipt['visibility'] != 'private'
            or receipt['public_release_approved'] is not False):
        raise ValueError('UCI365 reference contract changed')
    path = contained(folder, receipt['file'])
    if sha256(path) != receipt['sha256'] or path.stat().st_size != receipt['bytes']:
        raise ValueError('UCI365 reference content changed')
    _members(path)
    return folder, receipt


def audit_reference(rows, path):
    """Reconcile labels/grain; preserve explicit proven CSV rounding differences."""
    by_code = {code: [row for row in rows if row['source_subset_code'] == code] for code in HORIZONS}
    audits, original_rows, differences = [], [], []
    with zipfile.ZipFile(path) as archive:
        for code, horizon in HORIZONS.items():
            text = archive.read(str(code) + 'year.arff').decode('utf-8-sig')
            attrs, native, in_data = [], [], False
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith('%'):
                    continue
                if line.lower() == '@data':
                    in_data = True
                    continue
                if not in_data:
                    if line.lower().startswith('@attribute'):
                        attrs.append(line.split()[1].strip("'\""))
                    elif not line.lower().startswith('@relation'):
                        raise ValueError('Unexpected ARFF declaration')
                    continue
                fields = next(csv.reader([line]))
                if len(fields) != 65 or fields[-1] not in {'0', '1'}:
                    raise ValueError('Malformed ARFF record')
                native.append(fields)
            if attrs != ['Attr' + str(i) for i in range(1, 65)] + ['class']:
                raise ValueError('Original UCI365 ARFF feature order changed')
            if len(native) != len(by_code[code]):
                raise ValueError('ARFF/CSV horizon row count mismatch')
            differing_cells, differing_ordinals = 0, set()
            for row, source in zip(by_code[code], native, strict=True):
                if row['source_bankruptcy_label'] != int(source[-1]):
                    raise ValueError('ARFF/CSV label differs')
                original = dict(row)
                for name, token in zip(FEATURES, source[:-1], strict=True):
                    value = None if token == '?' else _number(token)
                    original[name] = value
                    if row[name] == value:
                        continue
                    if value is None or row[name] is None:
                        raise ValueError('ARFF/CSV missingness differs')
                    exact = Decimal(token)
                    rounded = exact.quantize(Decimal(1).scaleb(exact.adjusted()-2), rounding=ROUND_HALF_UP)
                    if 'e' not in token.lower() or float(rounded) != row[name]:
                        raise ValueError('ARFF/CSV unexplained values differ')
                    differences.append({'source_row_ordinal': row['source_row_ordinal'],
                        'source_subset_code': code, 'feature': name, 'csv_value': row[name],
                        'original_arff_value': value, 'original_arff_token': token,
                        'matches_scientific_three_digit_half_up': True})
                    differing_cells += 1
                    differing_ordinals.add(row['source_row_ordinal'])
                original_rows.append(original)
            audits.append({'source_subset_code': code, 'forecast_horizon_years': horizon,
                'rows': len(native), 'positive': sum(int(row[-1]) for row in native),
                'label_or_missingness_differences': 0, 'unexplained_numeric_differences': 0,
                'rounded_numeric_cells': differing_cells, 'rows_with_rounded_numeric_cells': len(differing_ordinals)})
    return sorted(original_rows, key=lambda row: row['source_row_ordinal']), audits, differences


def summaries(rows):
    profiles, horizons = [], []
    fingerprints = defaultdict(Counter)
    for row in rows:
        key = tuple(None if row[name] is None else row[name].hex() for name in FEATURES)
        digest = hashlib.sha256(repr(key).encode('ascii')).hexdigest()
        fingerprints[digest][row['source_subset_code']] += 1
    for code, horizon in HORIZONS.items():
        cohort = [row for row in rows if row['source_subset_code'] == code]
        missing_cells = sum(row[name] is None for row in cohort for name in FEATURES)
        horizons.append({'source_subset_code': code, 'forecast_horizon_years': horizon,
            'rows': len(cohort), 'positive': sum(row['source_bankruptcy_label'] for row in cohort),
            'negative': sum(1-row['source_bankruptcy_label'] for row in cohort),
            'missing_cells': missing_cells, 'rows_with_missing': sum(any(row[name] is None for name in FEATURES) for row in cohort),
            'exact_feature_duplicate_excess': sum(max(0, counts[code]-1) for counts in fingerprints.values())})
        for name in FEATURES:
            values = sorted(row[name] for row in cohort if row[name] is not None)
            profiles.append({'source_subset_code': code, 'forecast_horizon_years': horizon,
                'feature': name, 'rows': len(cohort), 'known': len(values), 'missing': len(cohort)-len(values),
                'negative': sum(value < 0 for value in values), 'zero': sum(value == 0 for value in values),
                'min': min(values) if values else None, 'max': max(values) if values else None,
                'median': (values[(len(values)-1)//2] / 2 + values[len(values)//2] / 2) if values else None,
                'abs_over_1e6': sum(abs(value) > 1e6 for value in values)})
    overlap = {'exact_feature_vectors_present_in_multiple_subsets': sum(len(counts) > 1 for counts in fingerprints.values()),
               'rows_in_cross_subset_exact_vectors': sum(sum(counts.values()) for counts in fingerprints.values() if len(counts) > 1),
               'diagnostic_only_not_firm_identity': True}
    return profiles, horizons, overlap


def prepare_bankruptcy(root, suite_id, reference_id):
    root = root.resolve()
    source, batch = verify_acquisition(root, suite_id)
    ref_folder, ref = verify_reference(root, reference_id)
    selected = [next(item for item in batch['sources'] if item['source_id'] == identifier)
                for identifier in ('uci-bankruptcy', 'uci-bankruptcy-metadata')]
    if any(item['status'] != 'DOWNLOADED_AND_PROFILED' for item in selected):
        raise ValueError('UCI365 CSV and metadata required')
    source_digest, ref_digest = sha256(source / 'acquisition-complete.json'), sha256(ref_folder / 'receipt.json')
    frozen_methods = methods()
    identifier = 'bankruptcy-case-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    write_new(output / 'run-start.json', {'suite_id': suite_id, 'reference_id': reference_id,
        'source_receipt_sha256': source_digest, 'reference_receipt_sha256': ref_digest,
        'methods': frozen_methods, 'started_at': timestamp()})
    metadata = read_json(source / selected[1]['file'])
    csv_rows = canonical_rows(source / selected[0]['file'], metadata)
    cards = definitions(metadata)
    rows, audits, rounding_differences = audit_reference(csv_rows, ref_folder / ref['file'])
    for audit in audits:
        if (audit['rows'], audit['positive']) != SOURCE_COUNTS[audit['source_subset_code']]:
            raise ValueError('UCI365 documented horizon counts changed')
    if len(rows) != selected[0]['profile']['rows']:
        raise ValueError('UCI365 batch/canonical population mismatch')
    profiles, horizons, overlap = summaries(rows)
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    pq.write_table(table, output / 'financial-statements.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(csv_rows, schema=SCHEMA), output / 'csv-mirror.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(rounding_differences, schema=DIFFERENCE_SCHEMA), output / 'csv-arff-rounding.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(profiles), output / 'feature-quality.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(horizons), output / 'horizon-summary.parquet', compression='zstd')
    if not pq.read_table(output / 'financial-statements.parquet').equals(table):
        raise ValueError('UCI365 Parquet roundtrip differs')
    # A third parser checks every numeric cell independently, with SQL NULL for NaN only.
    with duckdb.connect() as db:
        native = db.sql("SELECT * FROM read_csv(?, header=true, all_varchar=true, nullstr='NaN', strict_mode=true)",
                        params=[str(source / selected[0]['file'])])
        native.create_view('native')
        projection = ('row_number() OVER ()::INTEGER AS source_row_ordinal, year::TINYINT AS source_subset_code, '
                      '(6-year::INTEGER)::TINYINT AS forecast_horizon_years, class::TINYINT AS source_bankruptcy_label, ' +
                      ', '.join('"' + name + '"::DOUBLE AS "' + name + '"' for name in FEATURES))
        db.execute('CREATE TEMP TABLE parsed AS SELECT ' + projection + ' FROM native')
        db.read_parquet(str(output / 'csv-mirror.parquet')).create_view('canonical')
        differences = db.execute('SELECT count(*) FROM ((SELECT * FROM parsed EXCEPT ALL SELECT * FROM canonical) '
                                'UNION ALL (SELECT * FROM canonical EXCEPT ALL SELECT * FROM parsed))').fetchone()[0]
    if differences:
        raise ValueError('Independent CSV/Parquet reconciliation differs')
    contract = {'version': 'uci365-original-arff-horizon-source-record-v1', 'target': 'source_binary_bankruptcy_status_at_subset_horizon',
        'horizon_mapping': {str(code): horizon for code, horizon in HORIZONS.items()},
        'row_identity': 'CSV ordinal plus source SHA256; not firm identity',
        'source_year_is_calendar_year': False, 'entity_overlap_verified': False,
        'pool_horizons_allowed': False, 'temporal_out_of_time_supported': False,
        'canonical_feature_source': 'original ARFF Attr1..Attr64; CSV mirror retained separately',
        'raw_missing_token': {'csv': 'NaN', 'arff': '?'}, 'feature_storage': 'finite IEEE754 float64; raw CSV and ARFF retained',
        'csv_arff_rounding_policy': 'Only scientific ARFF tokens whose three-significant-digit ROUND_HALF_UP equals CSV value accepted as documented representation difference; other mismatches fail',
        'csv_rounding_cause_verified': False,
        'imputation_performed': False, 'winsorization_performed': False,
        'native_ratio_definitions_corrected': False, 'bankruptcy_is_loan_default': False,
        'exclusions_from_future_predictors': ['source_row_ordinal', 'source_subset_code', 'forecast_horizon_years', 'source_bankruptcy_label'],
        'model_training_performed': False, 'feature_cards': cards,
        'warnings': ['No released firm ID or observation/publication date: entity-disjoint and OOT tests cannot be established.',
            'A29 log base and A55 currency/unit are unspecified; no unit conversion.',
            'Source A48/A49 EBITDA wording uses minus depreciation; retained literally, not silently repaired.',
            'Missing and extreme values retained. abs_over_1e6 is a diagnostic threshold, not a rejection or clipping rule.'],
        'attribution': 'Tomczak, S. (2016). Polish Companies Bankruptcy. UCI. DOI 10.24432/C5F600; CC BY 4.0.'}
    write_new(output / 'contract.json', contract)
    if (methods() != frozen_methods or sha256(source / 'acquisition-complete.json') != source_digest
            or sha256(ref_folder / 'receipt.json') != ref_digest):
        raise ValueError('UCI365 lineage changed during preparation')
    for item in selected:
        if sha256(source / item['file']) != item['sha256']:
            raise ValueError('UCI365 raw source changed during preparation')
    if sha256(ref_folder / ref['file']) != ref['sha256']:
        raise ValueError('UCI365 reference changed during preparation')
    receipt = {'case_id': identifier, 'status': 'BANKRUPTCY_CANONICAL_COMPLETE', 'completed_at': timestamp(),
        'suite_id': suite_id, 'source_receipt_sha256': source_digest, 'sources': selected,
        'reference_id': reference_id, 'reference_receipt_sha256': ref_digest, 'reference': ref,
        'methods': frozen_methods, 'rows': len(rows), 'horizons': horizons, 'overlap_diagnostics': overlap,
        'original_arff_audits': audits, 'independent_csv_differing_rows': differences,
        'csv_arff_rounded_numeric_cells': len(rounding_differences),
        'visibility': 'private', 'public_release_approved': False, 'model_training_performed': False,
        'entity_disjoint_validation_qualified': False, 'production_qualified': False,
        'files': [{'file': path.name, 'sha256': sha256(path), 'bytes': path.stat().st_size}
                  for path in sorted(output.iterdir()) if path.is_file()]}
    write_new(output / 'bankruptcy-complete.json', receipt)
    return receipt


def verify_bankruptcy(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-case-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy case identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'bankruptcy-complete.json')
    if (receipt['case_id'] != identifier or receipt['status'] != 'BANKRUPTCY_CANONICAL_COMPLETE'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or any(receipt[key] is not False for key in ('public_release_approved', 'model_training_performed',
                                                       'entity_disjoint_validation_qualified', 'production_qualified'))):
        raise ValueError('UCI365 method/qualification changed')
    if not isinstance(receipt['suite_id'], str) or not re.fullmatch(r'suite-[0-9a-f]{12}', receipt['suite_id']):
        raise ValueError('Invalid UCI365 suite identifier')
    source = contained(root, 'data/private/public-suite/' + receipt['suite_id'])
    if sha256(source / 'acquisition-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('UCI365 source receipt changed')
    batch, expected = read_json(source / 'acquisition-complete.json'), {item['source_id']: item for item in catalog()}
    if [item['source_id'] for item in receipt['sources']] != ['uci-bankruptcy', 'uci-bankruptcy-metadata']:
        raise ValueError('UCI365 selected sources changed')
    for item in receipt['sources']:
        spec = expected[item['source_id']]
        if (any(item.get(key) != value for key, value in spec.items()) or item not in batch['sources']
                or read_json(source / (item['source_id'] + '-receipt.json')) != item
                or item['status'] != 'DOWNLOADED_AND_PROFILED' or item['model_qualified'] is not False
                or item['public_release_approved'] is not False):
            raise ValueError('UCI365 per-source contract changed')
        path = contained(source, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('UCI365 raw bytes changed')
    ref_folder, ref = verify_reference(root, receipt['reference_id'])
    if ref != receipt['reference'] or sha256(ref_folder / 'receipt.json') != receipt['reference_receipt_sha256']:
        raise ValueError('UCI365 reference lineage changed')
    start = read_json(folder / 'run-start.json')
    if any(start[key] != receipt[key] for key in ('suite_id', 'reference_id', 'source_receipt_sha256',
                                                  'reference_receipt_sha256', 'methods')):
        raise ValueError('UCI365 start/completion lineage changed')
    expected_files = {'run-start.json', 'contract.json', 'financial-statements.parquet', 'csv-mirror.parquet',
                      'csv-arff-rounding.parquet', 'feature-quality.parquet', 'horizon-summary.parquet'}
    if len(receipt['files']) != 7 or {item['file'] for item in receipt['files']} != expected_files:
        raise ValueError('UCI365 output population changed')
    for item in receipt['files']:
        path = contained(folder, item['file'])
        if sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('UCI365 output bytes changed')
    if (receipt['independent_csv_differing_rows'] != 0 or len(receipt['original_arff_audits']) != 5
            or {item['source_subset_code'] for item in receipt['original_arff_audits']} != set(HORIZONS)
            or any(item['label_or_missingness_differences'] != 0 or item['unexplained_numeric_differences'] != 0
                   or (item['rows'], item['positive']) != SOURCE_COUNTS[item['source_subset_code']]
                   or item['forecast_horizon_years'] != HORIZONS[item['source_subset_code']]
                   for item in receipt['original_arff_audits'])):
        raise ValueError('UCI365 reference audit changed')
    if (receipt['csv_arff_rounded_numeric_cells'] != sum(item['rounded_numeric_cells'] for item in receipt['original_arff_audits'])
            or pq.read_metadata(folder / 'csv-arff-rounding.parquet').num_rows != receipt['csv_arff_rounded_numeric_cells']
            or pq.read_metadata(folder / 'csv-mirror.parquet').num_rows != receipt['rows']):
        raise ValueError('UCI365 CSV/ARFF representation audit changed')
    table = pq.read_table(folder / 'financial-statements.parquet')
    if table.schema != SCHEMA or table.num_rows != receipt['rows'] or table.num_rows != sum(v[0] for v in SOURCE_COUNTS.values()):
        raise ValueError('UCI365 canonical schema/count changed')
    if pq.read_table(folder / 'horizon-summary.parquet').to_pylist() != receipt['horizons']:
        raise ValueError('UCI365 horizon summary changed')
    if pq.read_metadata(folder / 'feature-quality.parquet').num_rows != 320:
        raise ValueError('UCI365 feature profile population changed')
    return folder, receipt
