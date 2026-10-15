"""World Bank annual source observations: countries/economies and aggregates kept apart.

Latest revised WDI snapshots, not historical publication vintages or sovereign PD.
"""
from __future__ import annotations

import math
import re
import subprocess
import uuid
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pyarrow as pa
import pyarrow.parquet as pq

from .workspace import contained, read_json, sha256, timestamp, write_new

START, END = 1960, 2025
INDICATORS = {
    'FB.AST.NPER.ZS': ('Bank nonperforming loans', 'percent of total gross loans'),
    'FB.BNK.CAPA.ZS': ('Bank capital to assets', 'percent of total assets; source capital definition'),
    'FS.AST.PRVT.GD.ZS': ('Domestic credit to private sector', 'percent of GDP; financial corporations'),
    'FD.AST.PRVT.GD.ZS': ('Domestic credit to private sector by banks', 'percent of GDP; banks'),
    'DT.DOD.DECT.GN.ZS': ('External debt stocks', 'percent of GNI; external debt, not government debt only'),
    'NY.GDP.MKTP.KD.ZG': ('Real GDP growth', 'annual percent change'),
    'FP.CPI.TOTL.ZG': ('Consumer price inflation', 'annual percent change'),
}
PATTERN = re.compile(r'country-(?:source|case)-[0-9a-f]{12}\Z')
SCHEMA = pa.schema([
    ('indicator_id', pa.string()), ('country_code', pa.string()), ('country_iso2', pa.string()),
    ('country_name', pa.string()), ('is_aggregate', pa.bool_()), ('region', pa.string()),
    ('income_group_current', pa.string()), ('year', pa.int16()), ('value', pa.float64()),
    ('source_unit', pa.string()), ('declared_unit', pa.string()), ('obs_status', pa.string()),
    ('source_decimal', pa.int16()), ('footnote', pa.string()), ('source_lastupdated', pa.string()),
    ('source_country_iso3', pa.string()), ('source_country_name', pa.string()), ('country_join_basis', pa.string()),
])


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('country_observatory', 'workspace')}


def _download(url, destination):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in {'api.worldbank.org', 'databank.worldbank.org'}
            or parsed.username or parsed.password or parsed.port is not None):
        raise ValueError('Official credential-free World Bank HTTPS required')
    if destination.exists():
        raise ValueError('Immutable download exists')
    partial = destination.with_suffix(destination.suffix + '.partial')
    result = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
        '--connect-timeout', '20', '--max-time', '120', '--max-filesize', str(32 * 1024**2),
        '--output', str(partial), '--write-out', '%{http_code}', url], capture_output=True, timeout=125)
    if result.returncode or result.stdout != b'200':
        raise RuntimeError(f'World Bank HTTP failed: curl={result.returncode}, HTTP={result.stdout[:3]!r}')
    if not partial.is_file() or not 0 < partial.stat().st_size <= 32 * 1024**2:
        raise ValueError('Invalid World Bank download size')
    partial.rename(destination)
    return {'url': url, 'file': destination.name, 'sha256': sha256(destination),
            'bytes': destination.stat().st_size, 'retrieved_at': timestamp()}


def page_payload(payload):
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[0], dict) or not isinstance(payload[1], list):
        raise ValueError('Invalid World Bank paginated response')
    meta, rows = payload
    def integer(key):
        value = meta[key]
        if isinstance(value, bool) or not re.fullmatch(r'\d+', str(value)):
            raise ValueError('Invalid pagination integer')
        return int(value)
    page, pages, total, size = (integer(key) for key in ('page', 'pages', 'total', 'per_page'))
    if not (size > 0 and total > 0 and pages == (total + size - 1) // size and 1 <= page <= pages):
        raise ValueError('Inconsistent World Bank pagination')
    expected = min(size, total - (page - 1) * size)
    if len(rows) != expected or any(not isinstance(row, dict) for row in rows):
        raise ValueError('Incomplete World Bank page')
    return meta, rows


def collect_pages(payloads):
    if not payloads:
        raise ValueError('No source pages')
    parsed = [page_payload(payload) for payload in payloads]
    first = parsed[0][0]
    if int(first['page']) != 1 or len(parsed) != int(first['pages']):
        raise ValueError('Missing source pages')
    for index, (meta, _) in enumerate(parsed, 1):
        if int(meta['page']) != index or any(meta.get(key) != first.get(key) for key in
                                             ('pages', 'total', 'per_page', 'sourceid', 'lastupdated')):
            raise ValueError('Source pagination/version changed')
    rows = [row for _, page in parsed for row in page]
    if len(rows) != int(first['total']):
        raise ValueError('Source total not reconciled')
    return first, rows


def _pages(folder, path, query, prefix, receipts):
    query = {**query, 'format': 'json', 'per_page': 20000, 'page': 1}
    url = 'https://api.worldbank.org/v2/' + path + '?' + urlencode(query)
    first_file = folder / (prefix + '-page-1.json')
    first_receipt = _download(url, first_file)
    meta, _ = page_payload(read_json(first_file))
    receipts.append({**first_receipt, 'group': prefix, 'page': 1})
    paths = [first_file]
    for page in range(2, int(meta['pages']) + 1):
        query['page'] = page
        path = folder / (prefix + f'-page-{page}.json')
        receipts.append({**_download('https://api.worldbank.org/v2/' + urlsplit(url).path.removeprefix('/v2/')
                                    + '?' + urlencode(query), path), 'group': prefix, 'page': page})
        paths.append(path)
    collect_pages([read_json(path) for path in paths])


def acquire_country_source(root):
    root = root.resolve()
    if root.drive.upper() != 'D:':
        raise ValueError('D: workspace required')
    identifier = 'country-source-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'data/private/country-observatory/' + identifier)
    folder.mkdir(parents=True)
    frozen_methods = methods()
    write_new(folder / 'acquisition-start.json', {'source_id': identifier, 'started_at': timestamp(),
              'years': [START, END], 'indicators': list(INDICATORS), 'methods': frozen_methods})
    receipts = []
    try:
        _pages(folder, 'country', {}, 'countries', receipts)
        for indicator in INDICATORS:
            _pages(folder, 'indicator/' + indicator, {'source': 2}, indicator + '-metadata', receipts)
            _pages(folder, 'country/all/indicator/' + indicator,
                   {'date': f'{START}:{END}', 'source': 2, 'footnote': 'y'}, indicator + '-data', receipts)
            glossary = 'https://databank.worldbank.org/metadataglossary/world-development-indicators/series/' + indicator
            receipts.append({**_download(glossary, folder / (indicator + '-glossary.html')), 'group': indicator + '-glossary'})
            print(indicator + ': HTTP pages and glossary saved', flush=True)
        if methods() != frozen_methods:
            raise ValueError('Acquisition methods changed')
        receipt = {'source_id': identifier, 'status': 'WORLD_BANK_SOURCE_COMPLETE', 'completed_at': timestamp(),
            'methods': frozen_methods, 'years': [START, END], 'indicators': list(INDICATORS), 'files': receipts,
            'visibility': 'private', 'public_release_approved': False}
        write_new(folder / 'acquisition-complete.json', receipt)
        return receipt
    except Exception as error:
        write_new(folder / 'acquisition-failed.json', {'status': 'FAILED', 'exception_type': type(error).__name__,
                  'completed_files': receipts, 'failed_at': timestamp()})
        raise


def verify_source(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier) or not identifier.startswith('country-source-'):
        raise ValueError('Invalid country-source identifier')
    folder = contained(root, 'data/private/country-observatory/' + identifier)
    receipt = read_json(folder / 'acquisition-complete.json')
    if (receipt['source_id'] != identifier or receipt['status'] != 'WORLD_BANK_SOURCE_COMPLETE'
            or receipt['methods'] != methods() or receipt['years'] != [START, END]
            or receipt['indicators'] != list(INDICATORS) or receipt['public_release_approved'] is not False):
        raise ValueError('Country source/method contract changed')
    names = set()
    for item in receipt['files']:
        path = contained(folder, item['file'])
        if path.parent != folder or path.name in names or sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Country source bytes changed')
        names.add(path.name)
    return folder, receipt


def _read_group(folder, receipt, group):
    selected = [item for item in receipt['files'] if item['group'] == group]
    selected.sort(key=lambda item: item['page'])
    return collect_pages([read_json(folder / item['file']) for item in selected])


def derive_source(folder, receipt):
    _, definitions = _read_group(folder, receipt, 'countries')
    countries = {}
    for item in definitions:
        code = item['id']
        if not isinstance(code, str) or not re.fullmatch(r'[A-Z0-9]{3}', code) or code in countries:
            raise ValueError('Invalid/duplicate World Bank country code')
        for field in ('iso2Code', 'name'):
            if not isinstance(item[field], str) or not item[field]:
                raise ValueError('Country definition missing')
        aggregate = item['region']['id'] == 'NA' and item['region']['value'] == 'Aggregates'
        if (item['region']['id'] == 'NA') != aggregate:
            raise ValueError('Unknown country/aggregate classification')
        countries[code] = item
    iso2_catalog = {}
    for country in countries.values():
        if country['iso2Code'] in iso2_catalog:
            raise ValueError('Ambiguous catalog ISO2 code')
        iso2_catalog[country['iso2Code']] = country
    facts, metadata, coverage = [], {}, []
    for indicator, (_, unit) in INDICATORS.items():
        _, definitions = _read_group(folder, receipt, indicator + '-metadata')
        if len(definitions) != 1 or definitions[0]['id'] != indicator or definitions[0]['source']['id'] != '2':
            raise ValueError('Indicator definition/source mismatch')
        metadata[indicator] = definitions[0]
        meta, rows = _read_group(folder, receipt, indicator + '-data')
        if str(meta['sourceid']) != '2' or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', meta['lastupdated']):
            raise ValueError('Indicator source vintage missing')
        keys = set()
        for item in rows:
            code = item['countryiso3code']
            if not isinstance(code, str):
                raise ValueError('Invalid source ISO3 code')
            country = countries.get(code) if code else iso2_catalog.get(item['country']['id'])
            if (country is None or item['country']['id'] != country['iso2Code']
                    or item['country']['value'].strip() != country['name'].strip() or item['indicator']['id'] != indicator):
                raise ValueError('Country/indicator join mismatch')
            resolved_code = country['id']
            if not isinstance(item['date'], str) or not re.fullmatch(r'\d{4}', item['date']):
                raise ValueError('Annual year required')
            year = int(item['date'])
            key = (resolved_code, year)
            if not START <= year <= END or key in keys:
                raise ValueError('Duplicate/out-of-range indicator-country-year')
            keys.add(key)
            value = item['value']
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError('Invalid numeric observation')
            if type(item['decimal']) is not int or not 0 <= item['decimal'] <= 18:
                raise ValueError('Invalid source precision declaration')
            if any(not isinstance(item.get(field), str) for field in ('unit', 'obs_status', 'footnote')):
                raise ValueError('Missing source observation annotations')
            facts.append({'indicator_id': indicator, 'country_code': resolved_code, 'country_iso2': country['iso2Code'],
                'country_name': country['name'], 'is_aggregate': country['region']['id'] == 'NA',
                'region': country['region']['value'], 'income_group_current': country['incomeLevel']['value'],
                'year': year, 'value': None if value is None else float(value), 'source_unit': item['unit'],
                'declared_unit': unit, 'obs_status': item['obs_status'], 'source_decimal': item['decimal'],
                'footnote': item['footnote'], 'source_lastupdated': meta['lastupdated'],
                'source_country_iso3': code, 'source_country_name': item['country']['value'],
                'country_join_basis': 'source_iso3' if code else 'exact_catalog_iso2_missing_source_iso3'})
        selected = [row for row in facts if row['indicator_id'] == indicator]
        for is_aggregate in (False, True):
            subset = [row for row in selected if row['is_aggregate'] == is_aggregate]
            known = [row for row in subset if row['value'] is not None]
            coverage.append({'indicator_id': indicator, 'is_aggregate': is_aggregate, 'rows': len(subset),
                'entities_returned': len({row['country_code'] for row in subset}), 'known_rows': len(known),
                'missing_rows': len(subset) - len(known), 'known_entities': len({row['country_code'] for row in known}),
                'first_known_year': min((row['year'] for row in known), default=None),
                'last_known_year': max((row['year'] for row in known), default=None),
                'source_lastupdated': meta['lastupdated']})
    return facts, countries, metadata, coverage


def prepare_country_case(root, identifier):
    source, receipt = verify_source(root, identifier)
    frozen_methods = methods()
    facts, countries, metadata, coverage = derive_source(source, receipt)
    case_id = 'country-case-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'artifacts/private/' + case_id)
    folder.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(facts, schema=SCHEMA), folder / 'observations.parquet')
    write_new(folder / 'countries.json', countries)
    write_new(folder / 'indicators.json', metadata)
    write_new(folder / 'coverage.json', coverage)
    write_new(folder / 'contract.json', {'grain': 'indicator x World Bank economy/aggregate code x annual reference year',
        'years': [START, END], 'indicators': {code: {'label': label, 'unit': unit} for code, (label, unit) in INDICATORS.items()},
        'country_classification': 'current API region.id=NA/region.value=Aggregates; not historical classification',
        'country_join': 'Source ISO3 when present; blank ISO3 resolves only by unique exact catalog ISO2 plus whitespace-trim-equivalent name. Original codes/names retained.',
        'null_policy': 'Source null retained; absent API entity-year not synthesized or forward-filled',
        'time_scope': 'Latest revised source snapshot; reference year is not publication/availability year',
        'warnings': ['Country/economy coverage differs by indicator; missing is not zero or safe.',
            'Income/region groups are current metadata, not historical classifications.',
            'Ratios cannot be summed; cross-country methodology/consolidation differ, especially IMF FSI.',
            'Financial corporations/private credit differs from banks-only credit.',
            'External debt includes public and private borrowers; not sovereign government debt only.',
            'No sovereign PD/rating, causal stress response, regulatory capital compliance or vintage backtest.'],
        'source_url': 'https://data.worldbank.org', 'rights': 'Source glossary license; attribution required; derivatives stay private'})
    verify_source(root, identifier)
    if methods() != frozen_methods:
        raise ValueError('Country adapter methods changed')
    completed = {'case_id': case_id, 'source_id': identifier, 'status': 'COUNTRY_DESCRIPTIVE_READY',
        'completed_at': timestamp(), 'methods': frozen_methods, 'source_receipt_sha256': sha256(source / 'acquisition-complete.json'),
        'rows': len(facts), 'source_country_catalog_entries': len(countries),
        'source_country_catalog_aggregates': sum(item['region']['id'] == 'NA' for item in countries.values()),
        'visibility': 'private', 'public_release_approved': False, 'model_qualified': False,
        'files': {name: sha256(folder / name) for name in
                  ('observations.parquet', 'countries.json', 'indicators.json', 'coverage.json', 'contract.json')}}
    write_new(folder / 'case-complete.json', completed)
    return completed


def verify_case(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier) or not identifier.startswith('country-case-'):
        raise ValueError('Invalid country-case identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'case-complete.json')
    if receipt['case_id'] != identifier or receipt['methods'] != methods() or receipt['status'] != 'COUNTRY_DESCRIPTIVE_READY':
        raise ValueError('Country case methods/receipt changed')
    source, acquired = verify_source(root, receipt['source_id'])
    if sha256(source / 'acquisition-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('Source receipt changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('Country canonical bytes changed')
    facts, countries, metadata, coverage = derive_source(source, acquired)
    actual = pq.read_table(folder / 'observations.parquet')
    if (actual.schema != SCHEMA or actual.to_pylist() != facts or receipt['rows'] != len(facts)
            or read_json(folder / 'countries.json') != countries or read_json(folder / 'indicators.json') != metadata
            or read_json(folder / 'coverage.json') != coverage):
        raise ValueError('Country canonical projection differs from raw source')
    return folder, receipt
