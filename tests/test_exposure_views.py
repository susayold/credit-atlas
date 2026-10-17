import copy
import importlib.util
import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas.exposure_imports import import_exposures
from credit_atlas.excel_workbench import ExcelWorkbench
from credit_atlas.exposure_views import ExposureViews
from credit_atlas.server import handler_for
from credit_atlas.workspace import write_new
from tests.test_exposure_imports import metadata, rows, write_csv


@pytest.fixture
def imported(tmp_path):
    write_csv(tmp_path / 'input.csv', rows(True)); write_new(tmp_path / 'metadata.json', metadata(True))
    receipt = import_exposures(tmp_path, 'input.csv', 'metadata.json')
    return tmp_path, receipt, ExposureViews(tmp_path)


def auditor():
    path = Path(__file__).resolve().parents[1] / 'scripts/audit_exposure_import.py'
    spec = importlib.util.spec_from_file_location('exposure_auditor', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_independent_fraction_audit_and_fault_injection(imported, monkeypatch):
    root, receipt, service = imported; module = auditor()
    assert module.audit(root, receipt['import_id'])['status'] == 'PASS'
    folder, original, report = module.verify_import(root, receipt['import_id'])
    wrong = copy.deepcopy(report); wrong['currencies'][0]['research_el_major_exact'] = '999'
    monkeypatch.setattr(module, 'verify_import', lambda *args: (folder, original, wrong))
    with pytest.raises(ValueError, match='Independent exposure'): module.audit(root, receipt['import_id'])


def test_currency_filter_does_not_mix_native_totals_and_cache_is_copied(imported):
    root, receipt, service = imported; query = {'import_id': receipt['import_id'], 'currency': 'USD', 'dimension': 'segment'}
    report = service.report(query)
    assert report['records'] == 2 and len(report['currencies']) == 1
    assert report['global_cross_currency_total'] is None and report['currencies'][0]['research_el_major_exact'] == '30.000'
    report['currencies'][0]['records'] = 999
    assert service.report(query)['currencies'][0]['records'] == 2
    assert all(row['currency'] == 'USD' and row['dimension'] == 'segment' for row in report['concentrations'])
    for extra in ({'currency': 'GBP'}, {'dimension': 'pool_key'}, {'pd': '1'}):
        with pytest.raises(ValueError): service.report({**query, **extra})


def test_preserved_timestamp_corruption_rejected_after_cache_warm(imported):
    root, receipt, service = imported; service.report({'import_id': receipt['import_id']})
    path = root / 'artifacts/private' / receipt['import_id'] / 'source.csv'; stat = path.stat()
    with path.open('a') as stream: stream.write(' ')
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError, match='Frozen exposure'): service.report({'import_id': receipt['import_id']})
    assert service.catalog()['imports'][0]['status'] == 'unavailable'


def test_http_private_export_and_parameter_origin_guards(imported):
    root, receipt, service = imported
    app = SimpleNamespace(root=root, exposure_views=service)
    app.excel_workbench = ExcelWorkbench(app)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/exposure-report?import_id=' + receipt['import_id'] + '&currency=USD&dimension=region'
    try:
        with urlopen(base + '/api/exposure-imports') as response:
            assert response.headers['Cache-Control'] == 'no-store'
            catalog = json.load(response)
            assert catalog == service.catalog()
            assert catalog['imports'][0]['import_id'] == receipt['import_id']
            assert str(root) not in json.dumps(catalog)
        with pytest.raises(HTTPError) as error: urlopen(base + '/api/exposure-imports?path=other')
        assert error.value.code == 400
        with urlopen(base + endpoint) as response:
            assert response.headers['Cache-Control'] == 'no-store' and 'attachment' in response.headers['Content-Disposition']
            result = json.load(response)
            provenance = result.pop('export_provenance')
            assert provenance['visibility'] == 'private' and provenance['public_release_approved'] is False
            assert provenance['report_filters'] == {'currency': 'USD', 'dimension': 'region'}
            assert 'full verified input' in provenance['source_scope_note']
            assert provenance['source_imports'][0]['import_id'] == receipt['import_id']
            assert provenance['source_imports'][0]['receipt_sha256'] == service.evidence(receipt['import_id'])[2]
            assert result == service.report({'import_id': receipt['import_id'], 'currency': 'USD', 'dimension': 'region'})
            assert 'position_id' not in json.dumps(result) and str(root) not in json.dumps(result)
            assert str(root) not in json.dumps(provenance)
        for suffix in ('&pd=1', '&currency=VND', '&dimension=position_id'):
            with pytest.raises(HTTPError) as error: urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error: urlopen(Request(base + endpoint, headers={'Origin':'https://other.example'}))
        assert error.value.code == 403
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
