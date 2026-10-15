import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas.sec_audit import run_audit
from credit_atlas.sec_financials import prepare_sec_case
from credit_atlas.sec_views import SecViews, build_sec_view
from credit_atlas.server import handler_for
from credit_atlas.workspace import read_json, sha256
from tests.test_sec_financials import ACC, acquired


@pytest.fixture
def view(acquired):
    root, source = acquired
    case = prepare_sec_case(root, source['source_id'])
    receipt = build_sec_view(root, case['case_id'])
    return root, case, receipt, SecViews(root)


def test_exact_filing_identity_cutoff_and_no_future_fallback(view):
    root, _, receipt, service = view
    report = service.report(receipt['view_id'], {'asof': '2026-02-01'})
    assert report['statement']['accession'] == ACC
    assert report['statement']['ratios']['current_ratio']['value_exact'] == '1'
    assert not report['historical_availability_qualified'] and not report['model_qualified']
    assert str(root) not in json.dumps(report)
    older = service.report(receipt['view_id'], {'asof': '2026-01-31'})
    assert older['statement'] is None and older['annual_options'] == []
    assert older['status'] == 'NO_SOURCE_STATEMENT_AS_OF'
    with pytest.raises(ValueError, match='not available'):
        service.report(receipt['view_id'], {'asof': '2026-01-31', 'accession': ACC})


@pytest.mark.parametrize('query', [{'cik': 'other'}, {'asof': '2026-02-30'}, {'asof': '2026'},
                                 {'accession': '../other'}, {'pd': '1'}, {'view_id': 'other'}])
def test_invalid_filters_rejected(view, query):
    with pytest.raises(ValueError):
        view[3].report(view[2]['view_id'], query)


def test_forged_view_with_updated_hash_rejected(view):
    root, _, receipt, service = view
    folder = root / 'artifacts/private' / receipt['view_id']
    snapshot = read_json(folder / 'snapshot.json'); snapshot['fact_entries'] += 1
    (folder / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
    receipt['snapshot_sha256'] = sha256(folder / 'snapshot.json')
    (folder / 'view-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='differs from source'):
        service.view(receipt['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_independent_raw_and_exact_arithmetic_audit(view):
    root, case, _, _ = view
    audit = run_audit(root, case['case_id'])
    assert audit['differing_rows'] == {'facts': 0, 'filings': 0}
    assert audit['exact_supported_ratio_checks'] == 16
    assert audit['raw_fact_entries'] == 32


def test_local_http_export_extra_query_and_origin_guards(view):
    root, _, receipt, service = view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, sec_views=service)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/sec-report?view_id=' + receipt['view_id'] + '&asof=2026-02-01'
    try:
        with urlopen(base + endpoint) as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            assert json.load(response) == service.report(receipt['view_id'], {'asof': '2026-02-01'})
        for suffix in ('&pd=1', '&asof=2026-02-02', '&cik=other'):
            with pytest.raises(HTTPError) as error:
                urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + endpoint, headers={'Origin': 'https://other.example'}))
        assert error.value.code == 403
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
