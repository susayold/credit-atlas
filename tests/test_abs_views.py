import copy
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas import abs_views
from credit_atlas.abs_waterfall import run
from credit_atlas.server import handler_for
from credit_atlas.workspace import read_json, sha256
from tests.test_abs_waterfall import inputs


@pytest.fixture
def view(tmp_path, monkeypatch):
    identifier = 'abs-waterfall-' + '1' * 12
    first = inputs(available_funds='5.00', ending_pool='95.00', input_basis='CONDITIONAL_REPORTED_REPLAY')
    second = inputs(available_funds='7.00', ending_pool='88.00', payment_date='2025-03-17',
                    input_basis='CONDITIONAL_REPORTED_REPLAY')
    second['beginning_balances']['A-1'] = '95.00'
    replay = {'waterfall_id': identifier, 'case_id': 'abs-case-' + '2' * 12,
        'terms_id': 'abs-terms-' + '3' * 12, 'status': 'CONDITIONAL_REPORTED_REPLAY_RECONCILED',
        'failed_checks': 0, 'qualification': {'full_contractual_waterfall': False},
        'conditional_assumptions': ['Zero reviewer fees assumed'], 'public_release_approved': False,
        'periods': [{'collection_end': end, 'inputs': i, 'result': run(i)}
                   for end, i in [('2025-01-31', first), ('2025-02-28', second)]],
        'checks': [{'collection_end': end, 'check': 'cash', 'expected': '0.00', 'reported': '0.00',
                    'delta': '0.00', 'tolerance': '0.00', 'pass': True}
                   for end in ('2025-01-31', '2025-02-28')]}
    folder = tmp_path / 'artifacts/private' / identifier
    folder.mkdir(parents=True)
    (folder / 'waterfall-complete.json').write_text(json.dumps(replay), encoding='utf-8')
    monkeypatch.setattr(abs_views, 'verify_replay', lambda root, waterfall: copy.deepcopy(replay))
    receipt = abs_views.build_abs_view(tmp_path, identifier)
    return tmp_path, receipt, abs_views.AbsViews(tmp_path), replay


def test_exact_period_payment_dates_allocations_and_private_export(view):
    root, receipt, service, _ = view
    report = service.report(receipt['view_id'], {'period': '2025-01-31'})
    assert report['period']['inputs']['payment_date'] == '2025-02-18'
    assert report['tranches'][0]['principal_paid'] == '5.00'
    assert report['tranches'][0]['ending_balance'] == '95.00'
    assert report['source_checks'][0]['collection_end'] == '2025-01-31'
    assert report['qualification']['full_contractual_waterfall'] is False
    assert str(root) not in json.dumps(report)
    assert service.report(receipt['view_id'], {})['filters']['period'] == '2025-02-28'
    assert service.catalog()['views'][0]['status'] == 'verified'


@pytest.mark.parametrize('query', [{'period': '2026-01-31'}, {'period': '2025-01'}, {'period': ''},
                                 {'period': None}, {'pd': '1'}, {'view_id': '../other'}, {'regime': 'ACCELERATED'}])
def test_unsupported_period_and_scenario_filters_rejected(view, query):
    with pytest.raises(ValueError):
        view[2].report(view[1]['view_id'], query)


@pytest.mark.parametrize('change', ['money', 'qualification_type'])
def test_modified_projection_rejected_even_with_updated_digest(view, change):
    root, receipt, service, _ = view
    folder = root / 'artifacts/private' / receipt['view_id']
    snapshot = read_json(folder / 'snapshot.json')
    if change == 'money':
        snapshot['period_options'][0]['available_funds'] = '999.00'
    else:
        snapshot['qualification']['full_contractual_waterfall'] = 0
    (folder / 'snapshot.json').write_text(json.dumps(snapshot), encoding='utf-8')
    receipt['snapshot_sha256'] = sha256(folder / 'snapshot.json')
    (folder / 'view-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='differs from source'):
        service.view(receipt['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_source_receipt_change_invalidates_view(view):
    root, receipt, service, replay = view
    path = root / 'artifacts/private' / replay['waterfall_id'] / 'waterfall-complete.json'
    path.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='differs from source'):
        service.view(receipt['view_id'])


@pytest.mark.parametrize('flag,value', [('public_release_approved', 0), ('failed_checks', False), ('pass', 1)])
def test_type_confused_source_flags_rejected(view, flag, value):
    _, receipt, service, replay = view
    if flag == 'pass': replay['checks'][0]['pass'] = value
    else: replay[flag] = value
    with pytest.raises(ValueError, match='not qualified'):
        service.view(receipt['view_id'])


def test_http_period_export_filters_and_origin_guards(view):
    root, receipt, service, _ = view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, abs_views=service)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/abs-report?view_id=' + receipt['view_id'] + '&period=2025-01-31'
    try:
        with urlopen(base + endpoint) as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            assert json.load(response)['period']['inputs']['payment_date'] == '2025-02-18'
        for suffix in ('&pd=1', '&period=2025-02-28'):
            with pytest.raises(HTTPError) as error: urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(Request(base + endpoint, headers={'Origin': 'https://other.example'}))
        assert error.value.code == 403
        with urlopen(base + '/api/abs-period?view_id=' + receipt['view_id'] + '&period=2025-01-31') as response:
            assert response.headers['Content-Disposition'] is None
        with pytest.raises(HTTPError) as error:
            urlopen(base + '/api/abs-view?view_id=' + receipt['view_id'] + '&period=2025-01-31')
        assert error.value.code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
