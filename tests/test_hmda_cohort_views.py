import copy
import importlib.util
import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from credit_atlas.hmda_cohort_views import HmdaCohortViews
from credit_atlas.hmda_views import HmdaViews
from credit_atlas.server import handler_for
from tests.test_hmda_cohorts import built
from tests.test_hmda_sources import fake_network


def auditor():
    path = Path(__file__).resolve().parents[1] / 'scripts/audit_hmda_cohorts.py'
    spec = importlib.util.spec_from_file_location('cohort_auditor', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_independent_raw_csv_cohort_audit(built):
    root, receipt = built; result = auditor().audit(root, receipt['cohort_id'])
    assert result['status'] == 'PASS' and len(result['checks']) == 70


def test_independent_auditor_rejects_wrong_standardized_fraction(built, monkeypatch):
    root, receipt = built; module = auditor(); folder, original, payload = module.verify_cohorts(root, receipt['cohort_id'])
    wrong = copy.deepcopy(payload)
    wrong['cohorts'][0]['comparison']['years'][0]['full_reference_standardized_rate']['numerator'] = '999'
    monkeypatch.setattr(module, 'verify_cohorts', lambda *args: (folder, original, wrong))
    with pytest.raises(ValueError, match='Independent cohort'): module.audit(root, receipt['cohort_id'])


def test_private_report_bound_to_case_and_hot_byte_guards(built):
    root, receipt = built; service = HmdaCohortViews(root, HmdaViews(root))
    query = {'cohort_id': receipt['cohort_id'], 'case_id': receipt['case_id'], 'cohort': 'all_source'}
    result = service.report(query)
    assert result['cohort']['years'][0]['records'] == 2
    assert result['contract']['default_pd'] is False and result['public_release_approved'] is False
    result['cohort']['years'][0]['records'] = 999
    assert service.report(query)['cohort']['years'][0]['records'] == 2
    with pytest.raises(ValueError, match='another HMDA case'): service.report({**query, 'case_id': 'hmda-case-' + '1' * 12})
    path = root / 'artifacts/private' / receipt['cohort_id'] / 'coverage.json'; stat = path.stat()
    with path.open('a') as stream: stream.write(' ')
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError, match='Frozen cohort'): service.report(query)


def test_cohort_export_http_exact_scope_and_extra_filter_guards(built):
    root, receipt = built; service = HmdaCohortViews(root, HmdaViews(root))
    web = root / 'apps/web'; web.mkdir(parents=True)
    (web / 'index.html').write_text('<html>Workspace page</html>', encoding='utf-8')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, hmda_cohort_views=service)))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    query = {'cohort_id': receipt['cohort_id'], 'case_id': receipt['case_id'], 'cohort': 'all_source'}
    endpoint = '/api/hmda-cohort-report?' + '&'.join(key + '=' + value for key, value in query.items())
    try:
        for count in (17, 32):
            with urlopen(base + '/?' + '&'.join(f'field{i}=value' for i in range(count))) as response:
                assert response.status == 200 and b'Workspace page' in response.read()
        for path, count in [('/', 33), ('/api/health', 17)]:
            with pytest.raises(HTTPError) as error: urlopen(base + path + '?' + '&'.join(f'field{i}=value' for i in range(count)))
            assert error.value.code == 400
        with urlopen(base + endpoint) as response:
            assert response.headers['Cache-Control'] == 'no-store' and 'attachment' in response.headers['Content-Disposition']
            result = json.load(response); assert result == service.report(query)
            assert str(root) not in json.dumps(result)
        for extra in ('&year=2025', '&lei=all', '&cohort=unknown'):
            with pytest.raises(HTTPError) as error: urlopen(base + endpoint + extra)
            assert error.value.code == 400
    finally: server.shutdown(); server.server_close(); thread.join(timeout=5)
