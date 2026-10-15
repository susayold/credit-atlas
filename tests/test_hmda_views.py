import json
import os
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas import hmda_views
from credit_atlas.hmda_applications import build_case
from credit_atlas.hmda_sources import acquire_hmda_source
from credit_atlas.server import handler_for
from credit_atlas.workspace import read_json, sha256
from tests.test_hmda_sources import fake_network
from tests import test_hmda_sources as fixtures
from credit_atlas.hmda_applications import DIMENSIONS


@pytest.fixture
def view(tmp_path, fake_network, monkeypatch):
    fields = sorted(set(fixtures.header()) | set(DIMENSIONS))
    actual = [name for name in fields if not name.startswith('extra_')]
    actual += ['extra_' + str(i) for i in range(99 - len(actual))]
    monkeypatch.setattr(fixtures, 'header', lambda: actual)
    original = fixtures.records
    def records(year):
        rows = original(year)
        rows[0].update(lei='A' * 20, county_code='24031', loan_type='1')
        rows[1].update(lei='B' * 20, county_code='24033', loan_type='2', debt_to_income_ratio='45')
        return rows
    monkeypatch.setattr(fixtures, 'records', records)
    src = acquire_hmda_source(tmp_path); case = build_case(tmp_path, src['source_id'])
    receipt = hmda_views.build_hmda_view(tmp_path, case['case_id'])
    return tmp_path, src, case, receipt, hmda_views.HmdaViews(tmp_path)


def test_source_scope_default_year_exact_amounts_denominator_and_no_rows(view):
    root, _, _, receipt, service = view
    report = service.report(receipt['view_id'], {})
    assert report['filters']['year'] == '2025' and report['summary']['records'] == 2
    assert report['summary']['public_amount_sum_usd'] == '20000.00'
    assert report['summary']['decision_denominator'] == 2 and report['summary']['descriptive_denial_rate'] == '0.5'
    assert len(report['summary']['actions']) == 8 and len(report['timeline']) == 3
    assert all(row['records'] == 2 for row in report['timeline'])
    assert all(value is False for value in report['qualification'].values())
    assert str(root) not in json.dumps(report) and 'public_row_fingerprint' not in json.dumps(report)
    assert 'source_rows' not in report and report['public_release_approved'] is False


def test_intersection_of_lender_county_product_dti_filters_not_single_mart(view):
    _, _, _, receipt, service = view
    query = {'year': '2024', 'lei': 'B' * 20, 'county': '24033', 'loan_type': '2', 'dti': '45', 'dimension': 'lender'}
    report = service.report(receipt['view_id'], query)
    assert report['summary']['records'] == 1 and report['summary']['denied_numerator'] == 1
    assert report['summary']['public_amount_sum_usd'] == '15000.00'
    assert report['breakdown'][0]['bucket'] == 'B' * 20
    assert all(row['records'] == 1 for row in report['timeline'])
    empty = service.report(receipt['view_id'], {**query, 'county': '24031'})
    assert empty['summary']['records'] == 0 and empty['summary']['descriptive_denial_rate'] is None
    assert empty['breakdown'] == [] and empty['status'] == 'NO_SOURCE_RECORDS_FOR_FILTERS'
    assert all(row['descriptive_denial_rate'] is None for row in empty['timeline'])


@pytest.mark.parametrize('query', [{'year': '2026'}, {'year': ''}, {'county': 'unknown'}, {'lei': '../x'},
    {'loan_type': '99'}, {'dti': '0'}, {'dimension': 'pd'}, {'pd': '1'}, {'view_id': 'other'}])
def test_invalid_year_filters_and_score_fields_rejected(view, query):
    with pytest.raises(ValueError): view[4].report(view[3]['view_id'], query)


def test_full_source_rederivation_once_per_service_with_every_read_hash_guard(view, monkeypatch):
    _, _, _, receipt, service = view
    original = hmda_views.verify_case; calls = []
    def verified(root, identifier):
        calls.append(identifier); return original(root, identifier)
    monkeypatch.setattr(hmda_views, 'verify_case', verified)
    service.report(receipt['view_id'], {}); service.report(receipt['view_id'], {'year': '2023'})
    service.catalog(); assert len(calls) == 1


def test_source_mutation_with_preserved_timestamp_invalidates_warm_cache(view):
    root, src, _, receipt, service = view
    service.view(receipt['view_id'])
    path = root / 'data/private/hmda' / src['source_id'] / '2024-MD-home-purchase-site-built.csv'
    stat = path.stat(); content = path.read_text(); path.write_text(content.replace('5000.0', '9000.0'), encoding='utf-8')
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError, match='Frozen HMDA'): service.report(receipt['view_id'], {})
    assert service.catalog()['views'][0]['status'] == 'unavailable'


@pytest.mark.parametrize('field', ['records', 'qualification'])
def test_forged_snapshot_with_updated_hash_not_trusted(view, field):
    root, _, _, receipt, service = view
    folder = root / 'artifacts/private' / receipt['view_id']; snapshot = read_json(folder / 'snapshot.json')
    if field == 'records': snapshot['records'] += 1
    else: snapshot['qualification']['default_pd'] = 0
    (folder / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
    receipt['snapshot_sha256'] = sha256(folder / 'snapshot.json')
    (folder / 'view-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='differs from'): service.view(receipt['view_id'])


def test_http_private_scoped_export_and_parameter_origin_guards(view):
    root, _, _, receipt, service = view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, hmda_views=service)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/hmda-report?view_id=' + receipt['view_id'] + '&year=2024&county=24033'
    try:
        with urlopen(base + endpoint) as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            assert json.load(response)['summary']['records'] == 1
        for suffix in ('&pd=1', '&year=2023', '&county=other'):
            with pytest.raises(HTTPError) as error: urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + endpoint, headers={'Origin': 'https://other.example'}))
        assert error.value.code == 403
        with pytest.raises(HTTPError) as error:
            urlopen(base + '/api/hmda-view?view_id=' + receipt['view_id'] + '&year=2024')
        assert error.value.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
