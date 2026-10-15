import copy
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from credit_atlas import bankruptcy_model_views as module
from credit_atlas.server import handler_for
from credit_atlas.workspace import read_json, sha256, write_new


@pytest.fixture
def model_view(tmp_path, monkeypatch):
    root = tmp_path
    private = root / 'artifacts/private'
    for name in ('evaluation', 'freeze', 'study', 'assessment', 'case'):
        (private / name).mkdir(parents=True)
    evaluated = {'freeze_id': 'freeze', 'study_id': 'study', 'candidate': 'boosting_platt'}
    metrics = {'statements': 10, 'events': 2, 'roc_auc': .8, 'average_precision': .7,
               'brier_score': .1, 'log_loss': .3, 'reliability_bins': []}
    # Extra private fields must not pass through the aggregate whitelist.
    metrics['source_ordinal'] = [1, 2]
    write_new(private / 'evaluation/evaluation-complete.json', evaluated)
    write_new(private / 'freeze/freeze-complete.json', {'assessment_id': 'assessment'})
    write_new(private / 'study/study-complete.json', {'case_id': 'case', 'study_id': 'study', 'horizon': 1,
              'support': {'final_test': {'rows': 10, 'positive': 2, 'negative': 8, 'exact_feature_groups': 10}}})
    write_new(private / 'assessment/validation-metrics.json', {'boosting_platt': metrics})
    write_new(private / 'freeze/protocol.json', {'selection': {}, 'transform': {}, 'fixed_models': {}, 'calibration': {}})
    write_new(private / 'case/contract.json', {'warnings': ['Research only'], 'attribution': 'UCI'})
    monkeypatch.setattr(module, 'verify_holdout', lambda path, identifier: (
        private / 'evaluation', copy.deepcopy(evaluated), copy.deepcopy(metrics),
        {'exact_feature_groups': 10, 'intervals': {}, 'valid_replicates': 1000}))
    receipt = module.build_model_view(root, 'evaluation')
    return root, receipt, module.BankruptcyModelViews(root)


def test_projection_privacy_and_catalog(model_view):
    root, receipt, service = model_view
    result = service.view(receipt['view_id'])
    assert result['final']['events'] == 2
    assert 'source_ordinal' not in json.dumps(result) and str(root) not in json.dumps(result)
    assert result['can_rescore'] is False and result['production_qualified'] is False
    assert result['final_access_status'] == 'completed'
    assert service.catalog()['views'][0]['status'] == 'verified'


def test_forged_metrics_with_updated_digest_rejected(model_view):
    root, receipt, service = model_view
    folder = root / 'artifacts/private' / receipt['view_id']
    data = read_json(folder / 'snapshot.json')
    data['final']['roc_auc'] = 1
    (folder / 'snapshot.json').write_text(json.dumps(data), encoding='utf-8')
    receipt['snapshot_sha256'] = sha256(folder / 'snapshot.json')
    (folder / 'view-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError, match='differ from saved'):
        service.view(receipt['view_id'])
    assert service.catalog()['views'][0]['status'] == 'unavailable'


def test_upstream_method_change_rejected(model_view, monkeypatch):
    _, receipt, service = model_view
    monkeypatch.setattr(module, 'methods', lambda: {'changed': 'method'})
    with pytest.raises(ValueError, match='method/qualification'):
        service.view(receipt['view_id'])


@pytest.mark.parametrize('identifier', ['../evaluation', 'bankruptcy-model-view-bad', '', None])
def test_invalid_identifier(model_view, identifier):
    with pytest.raises(ValueError, match='identifier'):
        model_view[2].view(identifier)


def test_http_aggregate_export_rejects_inference_and_cross_origin(model_view):
    root, receipt, service = model_view
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(SimpleNamespace(root=root, bankruptcy_model_views=service)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    endpoint = '/api/bankruptcy-model-report?view_id=' + receipt['view_id']
    try:
        with urlopen(base + endpoint) as response:
            assert 'attachment' in response.headers['Content-Disposition']
            assert response.headers['Cache-Control'] == 'no-store'
            assert json.load(response) == service.view(receipt['view_id'])
        for suffix in ('&score=1', '&horizon=2', '&view_id=other'):
            with pytest.raises(HTTPError) as error:
                urlopen(base + endpoint + suffix)
            assert error.value.code == 400
        with pytest.raises(HTTPError) as error:
            urlopen(base + '/api/bankruptcy-model-views?score=1')
        assert error.value.code == 400
        for headers in ({'Origin': 'https://other.example'}, {'Host': 'other.example'}):
            with pytest.raises(HTTPError) as error:
                urlopen(Request(base + endpoint, headers=headers))
            assert error.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
