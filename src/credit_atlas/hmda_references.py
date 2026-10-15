"""Dated official display references; exact joins, never inferred lender identity."""
import csv
import copy
import io
import json
import re
import subprocess
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from .hmda_sources import YEARS, verify_source
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'hmda-reference-[0-9a-f]{12}\Z')
LIMIT = 8 * 1024**2
CONTRACT = {
    'lender_key': ['activity_year', 'lei'],
    'county_key': ['activity_year', 'county_code'],
    'reference_vintage': 'same calendar year Gazetteer; latest retrieved HMDA filer names',
    'name_is_identity': False, 'historical_availability_certified': False,
    'boundary_equivalence_certified': False, 'loan_performance_labels': False,
    'filer_counts_are_filtered_application_counts': False,
    'ambiguous_names': 'retain all candidates; no arbitrary selection or fuzzy match',
    'missing_names': 'retain source key and explicit UNMATCHED status',
}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('hmda_references', 'hmda_sources', 'workspace')}


def urls(mode='lender_and_county'):
    if mode not in ('lender_and_county', 'lender_only'): raise ValueError('Unsupported reference scope')
    result = {'api.html': 'https://ffiec.cfpb.gov/documentation/api/data-browser/'}
    for year in YEARS:
        result[f'{year}-filers.json'] = f'https://ffiec.cfpb.gov/v2/data-browser-api/view/filers?states=MD&years={year}'
        if mode == 'lender_and_county':
            result[f'{year}-counties.txt'] = f'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{year}_Gazetteer/{year}_gaz_counties_24.txt'
            result[f'{year}-gazetteer.html'] = f'https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.{year}.html'
    return result


def download(url, destination):
    if url not in urls().values() or destination.exists():
        raise ValueError('Exact official immutable reference download required')
    partial = destination.with_suffix(destination.suffix + '.partial')
    result = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
        '--compressed', '--connect-timeout', '20', '--max-time', '60', '--max-filesize', str(LIMIT),
        '--output', str(partial), '--write-out', '%{http_code}', url], capture_output=True, timeout=65)
    if result.returncode or result.stdout != b'200':
        raise RuntimeError(f'Reference HTTP failed: curl={result.returncode}, HTTP={result.stdout[:3]!r}')
    if not partial.is_file() or not 0 < partial.stat().st_size <= LIMIT:
        raise ValueError('Reference payload outside size bound')
    partial.rename(destination)
    return {'file': destination.name, 'url': url, 'http_status': 200,
            'bytes': destination.stat().st_size, 'sha256': sha256(destination), 'retrieved_at': timestamp()}


def label(names):
    names = sorted(set(names))
    return {'names': names, 'status': 'MATCHED' if len(names) == 1 else 'AMBIGUOUS' if names else 'UNMATCHED'}


def filers(path, year):
    data = read_json(path)
    if type(year) is not int or year not in YEARS or not isinstance(data.get('institutions'), list) or not data['institutions']:
        raise ValueError('Invalid filer response/year')
    result = defaultdict(list)
    for row in data['institutions']:
        if (type(row.get('period')) is not int or row['period'] != year
                or not isinstance(row.get('lei'), str) or not re.fullmatch('[A-Z0-9]{20}', row['lei'])
                or not isinstance(row.get('name'), str) or not row['name'].strip()
                or type(row.get('count')) is not int or row['count'] < 0):
            raise ValueError('Filer period/LEI/name/count mismatch')
        result[row['lei']].append(row['name'])
    return {key: label(value) for key, value in sorted(result.items())}


def counties(path, year):
    if type(year) is not int or year not in YEARS: raise ValueError('Invalid county vintage')
    reader = csv.reader(io.StringIO(path.read_text(encoding='utf-8-sig')), delimiter='|' if year == 2025 else '\t', strict=True)
    header = [value.strip() for value in next(reader, [])]
    if len(set(header)) != len(header) or not {'USPS', 'GEOID', 'NAME', 'ANSICODE'}.issubset(header):
        raise ValueError('County Gazetteer schema mismatch')
    result = {}
    for values in reader:
        if len(values) != len(header): raise ValueError('County Gazetteer row width mismatch')
        row = dict(zip(header, (value.strip() for value in values)))
        if (row['USPS'] != 'MD' or not re.fullmatch(r'24\d{3}', row['GEOID']) or not row['NAME']
                or not re.fullmatch(r'\d{8}', row['ANSICODE']) or row['GEOID'] in result):
            raise ValueError('County scope/key/name mismatch or duplicate key')
        if year == 2025 and row.get('GEOIDFQ') != '0500000US' + row['GEOID']:
            raise ValueError('County qualified GEOID mismatch')
        result[row['GEOID']] = label([row['NAME']])
    if not result: raise ValueError('Empty county reference')
    return dict(sorted(result.items()))


def project(folder, source_folder, mode='lender_and_county'):
    urls(mode)
    references = {}; coverage = []
    for year in YEARS:
        lender = filers(folder / f'{year}-filers.json', year)
        county = counties(folder / f'{year}-counties.txt', year) if mode == 'lender_and_county' else {}
        references[str(year)] = {'lender': lender, 'county': county}
        counts = {kind: Counter() for kind in ('lender', 'county')}
        gaps = {kind: Counter() for kind in counts}; keys = {kind: set() for kind in counts}; records = 0
        with (source_folder / f'{year}-MD-home-purchase-site-built.csv').open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                if row['activity_year'] != str(year): raise ValueError('Cross-year reference join')
                records += 1
                for kind, field, lookup in (('lender', 'lei', lender), ('county', 'county_code', county)):
                    key = row[field]; keys[kind].add(key)
                    status = lookup.get(key, label([]))['status']; counts[kind][status] += 1
                    if status != 'MATCHED': gaps[kind][key] += 1
        coverage.append({'year': year, 'records': records, **{
            kind: {'unique_source_keys': len(keys[kind]), 'reference_keys': len(references[str(year)][kind]),
                   'row_status_counts': dict(sorted(counts[kind].items())), 'unresolved_source_keys': dict(sorted(gaps[kind].items()))}
            for kind in counts}})
    return {'references': references, 'coverage': coverage, 'contract': copy.deepcopy(CONTRACT),
            'reference_scope': mode, 'county_names_acquired': mode == 'lender_and_county',
            'visibility': 'private', 'public_release_approved': False}


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def acquire_references(root, source_id, mode='lender_and_county'):
    expected_urls = urls(mode)
    source_folder, source = verify_source(root, source_id)
    source_digest = sha256(source_folder / 'source-complete.json')
    frozen = methods(); identifier = 'hmda-reference-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'data/private/hmda/' + identifier); folder.mkdir(parents=True, exist_ok=False)
    files = []
    try:
        for name, url in expected_urls.items():
            files.append(download(url, folder / name))
            if name.endswith('.html'):
                html = (folder / name).read_text(encoding='utf-8')
                if '<html' not in html.lower(): raise ValueError('Reference documentation is not HTML')
                if name.endswith('-gazetteer.html') and urls()[name[:4] + '-counties.txt'] not in html:
                    raise ValueError('County payload URL not linked by official year documentation')
        payload = project(folder, source_folder, mode)
        if (methods() != frozen or sha256(source_folder / 'source-complete.json') != source_digest
                or any(sha256(contained(source_folder, item['file'])) != item['sha256'] for item in source['files'])):
            raise ValueError('Methods or bound source changed during reference acquisition')
        write_new(folder / 'labels.json', payload)
        receipt = {'reference_id': identifier, 'status': 'VERIFIED_DATED_HMDA_REFERENCES' if mode == 'lender_and_county' else 'VERIFIED_DATED_HMDA_LENDER_REFERENCES',
            'reference_scope': mode,
            'completed_at': timestamp(), 'source_id': source_id, 'source_receipt_sha256': source_digest,
            'files': files, 'labels_sha256': sha256(folder / 'labels.json'), 'methods': frozen,
            'contract': copy.deepcopy(CONTRACT), 'visibility': 'private', 'public_release_approved': False}
        write_new(folder / 'reference-complete.json', receipt)
        return receipt, payload
    except Exception as error:
        write_new(folder / 'acquisition-failed.json', {'reference_id': identifier, 'completed_files': files,
            'failed_at': timestamp(), 'exception_type': type(error).__name__})
        raise


def verify_references(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier): raise ValueError('Invalid reference ID')
    folder = contained(root, 'data/private/hmda/' + identifier); receipt = read_json(folder / 'reference-complete.json')
    mode = receipt['reference_scope']; expected = urls(mode)
    status = 'VERIFIED_DATED_HMDA_REFERENCES' if mode == 'lender_and_county' else 'VERIFIED_DATED_HMDA_LENDER_REFERENCES'
    if (receipt['reference_id'] != identifier or receipt['status'] != status
            or receipt['methods'] != methods() or not same(receipt['contract'], CONTRACT)
            or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False):
        raise ValueError('Reference contract/methods changed')
    if len(receipt['files']) != len(expected) or {row['file'] for row in receipt['files']} != set(expected):
        raise ValueError('Reference files missing/duplicated')
    for item in receipt['files']:
        path = contained(folder, item['file'])
        if (item['url'] != expected[item['file']] or type(item['http_status']) is not int or item['http_status'] != 200
                or not 0 < path.stat().st_size <= LIMIT or path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']):
            raise ValueError('Reference payload/source changed')
        if item['file'].endswith('.html'):
            html = path.read_text(encoding='utf-8')
            if '<html' not in html.lower() or (item['file'].endswith('-gazetteer.html') and expected[item['file'][:4] + '-counties.txt'] not in html):
                raise ValueError('Reference documentation changed')
    source_folder, _ = verify_source(root, receipt['source_id'])
    if sha256(source_folder / 'source-complete.json') != receipt['source_receipt_sha256']:
        raise ValueError('Bound HMDA source receipt changed')
    payload = read_json(folder / 'labels.json')
    if sha256(folder / 'labels.json') != receipt['labels_sha256'] or not same(payload, project(folder, source_folder, mode)):
        raise ValueError('Reference labels/coverage differ from original source join')
    return folder, receipt, payload
