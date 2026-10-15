import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas.country_audit import run_audit
from credit_atlas.country_observatory import prepare_country_case
from credit_atlas.country_views import CountryViews, build_country_view
from credit_atlas.server import handler_for
from credit_atlas.workspace import read_json, sha256
from tests.test_country_observatory import acquired


@pytest.fixture
def view(acquired):
    root, source = acquired
    case = prepare_country_case(root, source['source_id'])
    receipt = build_country_view(root, case['case_id'])
    return root, case, receipt, CountryViews(root)


def test_null_year_not_replaced_by_latest_and_aggregates_separate(view):
    _, _, receipt, service = view
    snapshot = service.view(receipt['view_id'])
    assert snapshot['rows'] == 21 and snapshot['known_rows'] == 14
    assert len(snapshot['entities']) == 2
    report = service.report(receipt['view_id'], {})
    assert report['selected_year_observation']['value'] is None
    assert report['same_year_known_entities'] == 0 and report['same_year_returned_entities'] == 1
    assert report['latest_known_profile'][0]['latest_known_value'] is None
    assert report['timeline_rows'] == 2 and report['timeline_known'] == 1
    aggregate = service.report(receipt['view_id'], {'country': 'WLD', 'universe': 'aggregates', 'year': '2025'})
    assert aggregate['selected_year_observation']['value'] == -2.5
    assert aggregate['same_year_returned_entities'] == 1
    assert aggregate['no_carryforward'] and not aggregate['model_qualified']


@pytest.mark.parametrize('query', [{'country': 'WLD'}, {'country': 'ZZZ'}, {'universe': 'all'},
    {'year': '2026'}, {'year': 2024}, {'from': '2025', 'to': '2024'}, {'indicator': 'PD'}, {'score': '1'}, {'view_id': 'other'}])
def test_invalid_or_mixed_grain_filters_rejected(view, query):
    with pytest.raises(ValueError):
        view[3].report(view[2]['view_id'], query)


def test_forged_snapshot_even_with_digest_rejected(view):
    root, _, receipt, service = view
    folder = root / 'artifacts/private' / receipt['view_id']
    snapshot = read_json(folder / 'snapshot.json'); snapshot['known_rows'] = 21
    (folder / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
    receipt['snapshot_sha256'] = sha256(folder / 'snapshot.json')
    (folder / 'view-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='differs from source'):
        service.view(receipt['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_independent_audit_reconciles_native_and_notebook(view):
    root, case, _, _ = view
    audit = run_audit(root, case['case_id'])
    assert audit['differing_rows'] == audit['duplicate_keys'] == audit['orphan_or_name_disagreement'] == 0
    assert audit['raw_native_rows'] == audit['independent_join_rows'] == 21
    assert audit['quality']['missing'] == 7 and audit['quality']['aggregate_rows'] == 7
    notebook = read_json(root / 'artifacts/private' / audit['audit_id'] / 'source-quality.ipynb')
    assert 'EXCEPT ALL' in json.dumps(notebook)


def test_local_http_export_and_filter_and_origin_guards(view):
    root, _, receipt, service = view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, country_views=service)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/country-report?view_id=' + receipt['view_id']
    try:
        with urlopen(base + endpoint) as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            assert json.load(response) == service.report(receipt['view_id'], {})
        for suffix in ('&score=1', '&year=2024&year=2025', '&country=WLD'):
            with pytest.raises(HTTPError) as error:
                urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        for headers in ({'Host': 'example.com'}, {'Origin': 'https://other.example'}):
            with pytest.raises(HTTPError) as error:
                urlopen(Request(base + endpoint, headers=headers))
            assert error.value.code == 403
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
