"""Bounded official HMDA static-browser acquisition; public LAR is not loan performance."""
import csv
import json
import re
import subprocess
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .workspace import contained, read_json, sha256, timestamp, write_new

YEARS = (2023, 2024, 2025)
FILTERS = {'states': 'MD', 'loan_purposes': '1', 'construction_methods': '1'}
BASE = 'https://ffiec.cfpb.gov'
DOCS = {
    'api.html': '/documentation/api/data-browser/',
    'dataset-faq.html': '/documentation/tools/data-browser/data-browser-faq',
    'public-fields.html': '/documentation/publications/loan-level-datasets/lar-data-fields',
    'modified-lar.html': '/documentation/publications/modified-lar/modified-lar-schema',
}
PATTERN = re.compile(r'hmda-source-[0-9a-f]{12}\Z')
REQUIRED = {'activity_year', 'lei', 'state_code', 'construction_method', 'loan_purpose',
    'action_taken', 'loan_amount', 'loan_to_value_ratio', 'income', 'debt_to_income_ratio',
    'interest_rate', 'property_value', 'applicant_age', 'denial_reason-1', 'derived_race', 'derived_sex'}
PROFILE_FIELDS = ('income', 'debt_to_income_ratio', 'loan_to_value_ratio', 'interest_rate',
                  'property_value', 'applicant_age', 'denial_reason-1')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('hmda_sources', 'workspace')}


def endpoint(year, kind):
    if type(year) is not int or year not in YEARS or kind not in ('csv', 'aggregations'):
        raise ValueError('Unsupported bounded HMDA request')
    return BASE + '/v2/data-browser-api/view/' + kind + '?' + urlencode({'years': str(year), **FILTERS})


def allowed_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'ffiec.cfpb.gov' or parsed.port is not None
            or parsed.username or parsed.password or parsed.fragment):
        return False
    return (url in {BASE + path for path in DOCS.values()}
            or url in {endpoint(year, kind) for year in YEARS for kind in ('csv', 'aggregations')})


def download(url, destination):
    if not allowed_url(url) or destination.exists():
        raise ValueError('Official bounded immutable HMDA download required')
    partial = destination.with_suffix(destination.suffix + '.partial')
    headers = destination.with_suffix(destination.suffix + '.headers.partial')
    trace = []; served_url = url
    for hop in range(2):
        response = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
            '--compressed', '--connect-timeout', '20', '--max-time', '180', '--max-filesize', str(64 * 1024**2),
            '--dump-header', str(headers), '--output', str(partial), '--write-out', '%{http_code}', served_url],
            capture_output=True, timeout=185)
        text = headers.read_text(encoding='utf-8') if headers.exists() else ''
        status = int(response.stdout) if response.stdout.isdigit() else 0
        trace.append({'url': served_url, 'status': status, 'headers': text})
        if response.returncode:
            raise RuntimeError(f'HMDA HTTP failed: curl={response.returncode}, HTTP={status}')
        if status == 200:
            break
        if status in (301, 302) and hop == 0:
            locations = re.findall(r'^Location:\s*(\S+)\s*$', text, re.I | re.M)
            if len(locations) != 1 or not cache_redirect(url, locations[0]):
                raise ValueError('HMDA redirect outside official matching-year CSV cache')
            served_url = locations[0]
        else:
            raise RuntimeError(f'HMDA HTTP failed: HTTP={status}')
    if trace[-1]['status'] != 200:
        raise ValueError('HMDA cached response did not complete')
    if not partial.is_file() or not 0 < partial.stat().st_size <= 64 * 1024**2:
        raise ValueError('Invalid HMDA response size')
    partial.rename(destination)
    headers.unlink()
    return {'file': destination.name, 'url': url, 'served_url': served_url, 'http_trace': trace,
            'bytes': destination.stat().st_size, 'sha256': sha256(destination), 'retrieved_at': timestamp()}


def cache_redirect(original, target):
    """One observed official redirect only; no arbitrary S3/credentialed URL following."""
    if original not in {endpoint(year, 'csv') for year in YEARS}:
        return False
    year = re.search(r'years=(\d{4})', original)[1]
    return bool(re.fullmatch(r'https://files\.ffiec\.cfpb\.gov/data-browser/datasets/' + year
        + r'/filtered-queries/(?:one-year|snapshot|three-year)/[0-9a-f]{32}\.csv', target))


def aggregate(path):
    data = json.loads(path.read_text(encoding='utf-8'), parse_float=Decimal)
    expected = {'state': 'MD', 'loan_purposes': '1', 'construction_methods': '1'}
    if data.get('parameters') != expected or not isinstance(data.get('aggregations'), list) or len(data['aggregations']) != 1:
        raise ValueError('Unexpected HMDA aggregation parameters/grain')
    row = data['aggregations'][0]
    if (type(row.get('count')) is not int or row['count'] <= 0
            or row.get('loan_purposes') != '1' or row.get('construction_methods') != '1'
            or isinstance(row.get('sum'), bool) or not isinstance(row.get('sum'), (int, Decimal))):
        raise ValueError('Unexpected HMDA aggregation count/amount')
    amount = Decimal(row['sum'])
    if not amount.is_finite() or amount <= 0:
        raise ValueError('Invalid HMDA aggregated amount')
    return {'records': row['count'], 'reported_public_loan_amount_sum_usd': str(amount)}


def profile(path, year):
    if type(year) is not int or year not in YEARS:
        raise ValueError('Unsupported HMDA source year')
    count = 0; amount = Decimal(0); actions = Counter(); reporters = set()
    categories = {field: Counter() for field in PROFILE_FIELDS}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        if len(header) != 99 or len(set(header)) != len(header) or not REQUIRED.issubset(header):
            raise ValueError('HMDA public 99-field header mismatch')
        for values in reader:
            if len(values) != len(header):
                raise ValueError('HMDA truncated/extra-width row')
            row = dict(zip(header, values))
            if (row['activity_year'] != str(year) or row['state_code'] != 'MD'
                    or row['loan_purpose'] != '1' or row['construction_method'] != '1'
                    or row['action_taken'] not in tuple(str(i) for i in range(1, 9))
                    or not re.fullmatch(r'[A-Z0-9]{20}', row['lei'])):
                raise ValueError('HMDA record scope/code/LEI mismatch')
            try:
                loan_amount = Decimal(row['loan_amount'])
            except InvalidOperation as error:
                raise ValueError('Invalid HMDA public loan amount') from error
            if not loan_amount.is_finite() or loan_amount <= 0 or loan_amount != loan_amount.to_integral_value():
                raise ValueError('Nonpositive/noninteger HMDA public amount')
            amount += loan_amount; count += 1; actions[row['action_taken']] += 1; reporters.add(row['lei'])
            for field in PROFILE_FIELDS:
                value = row[field]
                status = ('SOURCE_BLANK' if value == '' else 'NOT_APPLICABLE' if value == 'NA'
                          else 'EXEMPT' if value == 'Exempt' or (field == 'denial_reason-1' and value == '1111') else
                          'AGE_NOT_APPLICABLE' if field == 'applicant_age' and value == '8888' else 'REPORTED')
                categories[field][status] += 1
    if not count:
        raise ValueError('Empty HMDA CSV')
    return {'year': year, 'records': count, 'header': header, 'reporters': len(reporters),
        'reported_public_loan_amount_sum_usd': str(amount), 'actions': dict(sorted(actions.items())),
        'field_status_counts': {field: dict(sorted(counts.items())) for field, counts in categories.items()}}


def reconciles(profiled, aggregated):
    return (profiled['records'] == aggregated['records']
            and Decimal(profiled['reported_public_loan_amount_sum_usd']) == Decimal(aggregated['reported_public_loan_amount_sum_usd']))


def acquire_hmda_source(root):
    root = root.resolve()
    if root.drive.upper() != 'D:':
        raise ValueError('D: workspace required')
    identifier = 'hmda-source-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'data/private/hmda/' + identifier); folder.mkdir(parents=True)
    frozen = methods()
    write_new(folder / 'acquisition-start.json', {'source_id': identifier, 'started_at': timestamp(),
        'years': list(YEARS), 'filters': FILTERS, 'methods': frozen, 'request_mode': 'sequential credential-free HTTPS'})
    files, profiles = [], []
    try:
        for name, path in DOCS.items():
            item = download(BASE + path, folder / name)
            if '<html' not in (folder / name).read_text(encoding='utf-8').lower():
                raise ValueError('HMDA documentation is not HTML')
            files.append(item)
        for year in YEARS:
            before = f'{year}-aggregate-before.json'; after = f'{year}-aggregate-after.json'; csv_name = f'{year}-MD-home-purchase-site-built.csv'
            files.append(download(endpoint(year, 'aggregations'), folder / before))
            expected = aggregate(folder / before)
            files.append(download(endpoint(year, 'csv'), folder / csv_name))
            profiled = profile(folder / csv_name, year)
            files.append(download(endpoint(year, 'aggregations'), folder / after))
            if not reconciles(profiled, expected) or not reconciles(profiled, aggregate(folder / after)):
                raise ValueError('HMDA CSV count/amount differs from before/after source aggregation')
            if profiles and profiled['header'] != profiles[0]['header']:
                raise ValueError('HMDA cross-year public schema drift')
            profiles.append(profiled)
        if frozen != methods():
            raise ValueError('HMDA acquisition methods changed')
        receipt = {'source_id': identifier, 'status': 'VERIFIED_SCOPED_HMDA_SOURCE',
            'completed_at': timestamp(), 'years': list(YEARS), 'filters': FILTERS, 'files': files,
            'profiles': profiles, 'methods': frozen, 'visibility': 'private', 'public_release_approved': False,
            'qualification': {'loan_performance_labels': False, 'historical_availability': False,
                              'national_representativeness': False, 'borrower_linkage': False},
            'limitations': ['Maryland/home-purchase/site-built subset; not all HMDA or nationally representative.',
                'Browser uses latest static release for each year; observation year is not availability vintage.',
                'Public LAR privacy modifications suppress IDs and coarsen amounts/ages/DTI; duplicate public rows may be distinct loans.',
                'Action outcomes are origination/application/purchase/preapproval statuses, not delinquency/default PD.',
                'Raw header loan_to_value_ratio differs from current public dictionary combined_loan_to_value_ratio; no silent semantic rename.',
                'No Freddie identity join, credit score values or independent compliance/causal conclusions.']}
        write_new(folder / 'source-complete.json', receipt)
        return receipt
    except Exception as error:
        write_new(folder / 'acquisition-failed.json', {'source_id': identifier, 'failed_at': timestamp(),
            'exception_type': type(error).__name__, 'completed_files': files})
        raise


def verify_source(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
        raise ValueError('Invalid HMDA source ID')
    folder = contained(root, 'data/private/hmda/' + identifier)
    receipt = read_json(folder / 'source-complete.json')
    if (receipt['source_id'] != identifier or receipt['status'] != 'VERIFIED_SCOPED_HMDA_SOURCE'
            or receipt['methods'] != methods() or receipt['years'] != list(YEARS) or receipt['filters'] != FILTERS
            or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
            or any(value is not False for value in receipt['qualification'].values())):
        raise ValueError('HMDA source contract changed')
    expected_names = set(DOCS) | {f'{year}-aggregate-{when}.json' for year in YEARS for when in ('before', 'after')} | {
        f'{year}-MD-home-purchase-site-built.csv' for year in YEARS}
    if len(receipt['files']) != len(expected_names) or {row['file'] for row in receipt['files']} != expected_names:
        raise ValueError('HMDA required files missing/duplicated')
    for item in receipt['files']:
        path = contained(folder, item['file'])
        name = item['file']
        if name in DOCS:
            expected_url = BASE + DOCS[name]
        else:
            expected_url = endpoint(int(name[:4]), 'csv' if name.endswith('.csv') else 'aggregations')
        if item['url'] != expected_url or sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('HMDA file/source identity changed')
        trace = item['http_trace']
        if (not isinstance(trace, list) or len(trace) not in (1, 2) or trace[0]['url'] != expected_url
                or trace[-1]['status'] != 200 or type(trace[-1]['status']) is not int
                or trace[-1]['url'] != item['served_url']):
            raise ValueError('HMDA HTTP trace changed')
        if len(trace) == 2 and (type(trace[0]['status']) is not int or trace[0]['status'] not in (301, 302)
                or not cache_redirect(expected_url, item['served_url'])
                or re.findall(r'^Location:\s*(\S+)\s*$', trace[0]['headers'], re.I | re.M) != [item['served_url']]):
            raise ValueError('HMDA cached redirect trace changed')
    actual = []
    for year in YEARS:
        current = profile(folder / f'{year}-MD-home-purchase-site-built.csv', year)
        if not all(reconciles(current, aggregate(folder / f'{year}-aggregate-{when}.json')) for when in ('before', 'after')):
            raise ValueError('HMDA source reconciliation changed')
        actual.append(current)
    if actual != receipt['profiles']:
        raise ValueError('HMDA source profile differs from original CSV')
    return folder, receipt
