import csv
import json
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest

from credit_atlas import hmda_sources as hmda
from credit_atlas.workspace import read_json, sha256, timestamp


def header():
    fields = sorted(hmda.REQUIRED)
    return fields + ['extra_' + str(i) for i in range(99 - len(fields))]


def records(year):
    first = dict.fromkeys(header(), 'NA')
    first.update({'activity_year': str(year), 'lei': 'A' * 20, 'state_code': 'MD',
        'loan_purpose': '1', 'construction_method': '1', 'action_taken': '1',
        'loan_amount': '5000.0', 'applicant_age': '8888', 'income': '0', 'interest_rate': 'Exempt',
        'debt_to_income_ratio': '30%-<36%', 'denial_reason-1': '10'})
    second = {**first, 'action_taken': '3', 'loan_amount': '15000.0', 'applicant_age': '35-44'}
    return [first, second]


def write_csv(path, year, rows=None, fields=None):
    fields = header() if fields is None else fields
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows(records(year) if rows is None else rows)


def aggregation(count=2, amount=20000):
    return {'parameters': {'state': 'MD', 'loan_purposes': '1', 'construction_methods': '1'},
        'aggregations': [{'count': count, 'sum': amount, 'loan_purposes': '1', 'construction_methods': '1'}]}


@pytest.fixture
def fake_network(monkeypatch):
    def download(url, destination):
        if destination.name in hmda.DOCS:
            destination.write_text('<html><body>Official field documentation</body></html>', encoding='utf-8')
        elif destination.suffix == '.csv':
            write_csv(destination, int(parse_qs(urlsplit(url).query)['years'][0]))
        else:
            destination.write_text(json.dumps(aggregation()), encoding='utf-8')
        return {'url': url, 'served_url': url, 'http_trace': [{'url': url, 'status': 200, 'headers': ''}],
                'file': destination.name, 'bytes': destination.stat().st_size,
                'sha256': sha256(destination), 'retrieved_at': timestamp()}
    monkeypatch.setattr(hmda, 'download', download)
    return download


def test_acquisition_and_reverification_preserve_public_status_scope(tmp_path, fake_network):
    receipt = hmda.acquire_hmda_source(tmp_path)
    folder, verified = hmda.verify_source(tmp_path, receipt['source_id'])
    assert verified == receipt and len(receipt['files']) == 13
    profile = receipt['profiles'][0]
    assert profile['records'] == 2 and profile['reported_public_loan_amount_sum_usd'] == '20000.0'
    assert profile['field_status_counts']['income'] == {'REPORTED': 2}  # real zero remains zero
    assert profile['field_status_counts']['interest_rate'] == {'EXEMPT': 2}
    assert profile['field_status_counts']['applicant_age'] == {'AGE_NOT_APPLICABLE': 1, 'REPORTED': 1}
    assert all(value is False for value in receipt['qualification'].values())
    assert folder.is_relative_to(tmp_path)


@pytest.mark.parametrize('url', ['https://ffiec.cfpb.gov.evil.example/v2/data-browser-api/view/csv',
    'http://ffiec.cfpb.gov/documentation/api/data-browser/',
    'https://user:pass@ffiec.cfpb.gov/documentation/api/data-browser/',
    'https://ffiec.cfpb.gov:443/documentation/api/data-browser/',
    hmda.endpoint(2024, 'csv') + '&actions_taken=1', hmda.endpoint(2024, 'csv') + '#x'])
def test_unbounded_or_credentialed_url_rejected(tmp_path, url):
    with pytest.raises(ValueError, match='Official bounded'):
        hmda.download(url, tmp_path / 'never-downloaded.csv')


@pytest.mark.parametrize('field,value', [('activity_year', '2025'), ('state_code', 'VA'),
    ('loan_purpose', '31'), ('construction_method', '2'), ('action_taken', '0'),
    ('lei', '123'), ('loan_amount', 'NaN'), ('loan_amount', '-1'), ('loan_amount', '123.45')])
def test_out_of_scope_codes_and_invalid_amounts_fail(tmp_path, field, value):
    rows = records(2024); rows[0][field] = value
    path = tmp_path / 'invalid.csv'; write_csv(path, 2024, rows)
    with pytest.raises(ValueError): hmda.profile(path, 2024)


def test_public_duplicate_rows_retained_and_scientific_aggregate_exact(tmp_path):
    path = tmp_path / 'duplicate.csv'; row = records(2024)[0]
    write_csv(path, 2024, [row, row])
    profiled = hmda.profile(path, 2024)
    assert profiled['records'] == 2 and Decimal(profiled['reported_public_loan_amount_sum_usd']) == 10000
    agg_path = tmp_path / 'aggregate.json'; agg_path.write_text(json.dumps(aggregation(amount=1e4)))
    assert hmda.reconciles(profiled, hmda.aggregate(agg_path))


def test_numeric_income_1111_is_value_not_categorical_exemption(tmp_path):
    row = records(2024)[0]; row['income'] = '1111'; row['denial_reason-1'] = '1111'
    path = tmp_path / 'field-specific.csv'; write_csv(path, 2024, [row])
    counts = hmda.profile(path, 2024)['field_status_counts']
    assert counts['income'] == {'REPORTED': 1}
    assert counts['denial_reason-1'] == {'EXEMPT': 1}


def test_width_header_and_empty_payload_rejected(tmp_path):
    path = tmp_path / 'empty.csv'; write_csv(path, 2024, [])
    with pytest.raises(ValueError, match='Empty'): hmda.profile(path, 2024)
    write_csv(path, 2024)
    with path.open('a') as stream: stream.write('truncated,row\n')
    with pytest.raises(ValueError, match='width'): hmda.profile(path, 2024)
    path.write_text('<html>error</html>')
    with pytest.raises(ValueError, match='header'): hmda.profile(path, 2024)


def test_before_after_count_amount_difference_cannot_complete(tmp_path, monkeypatch, fake_network):
    def changed(url, destination):
        item = fake_network(url, destination)
        if destination.name.endswith('aggregate-after.json'):
            destination.write_text(json.dumps(aggregation(count=3)))
            item.update(bytes=destination.stat().st_size, sha256=sha256(destination))
        return item
    monkeypatch.setattr(hmda, 'download', changed)
    with pytest.raises(ValueError, match='differs'): hmda.acquire_hmda_source(tmp_path)
    assert not list(tmp_path.rglob('source-complete.json'))
    assert len(list(tmp_path.rglob('acquisition-failed.json'))) == 1


def test_changed_csv_cannot_pass_with_updated_file_digest(tmp_path, fake_network):
    receipt = hmda.acquire_hmda_source(tmp_path)
    folder = tmp_path / 'data/private/hmda' / receipt['source_id']
    name = '2024-MD-home-purchase-site-built.csv'
    rows = records(2024); rows[0]['action_taken'] = '6'; write_csv(folder / name, 2024, rows)
    item = next(row for row in receipt['files'] if row['file'] == name)
    item.update(bytes=(folder / name).stat().st_size, sha256=sha256(folder / name))
    (folder / 'source-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='profile differs'): hmda.verify_source(tmp_path, receipt['source_id'])


def test_boolean_count_and_scope_mismatch_aggregate_rejected(tmp_path):
    path = tmp_path / 'aggregate.json'
    path.write_text(json.dumps(aggregation(count=True)))
    with pytest.raises(ValueError): hmda.aggregate(path)
    data = aggregation(); data['parameters']['state'] = 'CA'; path.write_text(json.dumps(data))
    with pytest.raises(ValueError): hmda.aggregate(path)


def test_only_matching_year_official_cache_redirect_allowed():
    target = 'https://files.ffiec.cfpb.gov/data-browser/datasets/2024/filtered-queries/one-year/' + 'a' * 32 + '.csv'
    assert hmda.cache_redirect(hmda.endpoint(2024, 'csv'), target)
    assert not hmda.cache_redirect(hmda.endpoint(2025, 'csv'), target)
    assert not hmda.cache_redirect(hmda.endpoint(2024, 'aggregations'), target)
    assert not hmda.cache_redirect(hmda.endpoint(2024, 'csv'), target.replace('files.ffiec.cfpb.gov', 'evil.example'))
    assert not hmda.cache_redirect(hmda.endpoint(2024, 'csv'), target + '?credentials=1')
