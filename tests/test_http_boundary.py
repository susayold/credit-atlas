"""Exercise the real HTTP handler with synthetic evidence and isolated reviews."""
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from credit_atlas.reviews import Reviews
from credit_atlas.server import handler_for
from credit_atlas.service import EvidenceChanged


@pytest.fixture
def http_app(tmp_path):
    class SyntheticSuiteViews:
        def catalog(self):
            return {"views": [{"view_id": "suite-view-aaaaaaaaaaaa", "status": "verified"}], "visibility": "private"}

        def view(self, identifier):
            if identifier != "suite-view-aaaaaaaaaaaa":
                raise ValueError("PRIVATE PATH MUST NOT LEAK")
            return {"view_id": identifier, "visibility": "private", "public_release_approved": False,
                    "retail": {"holdout": {"loans": 100}}, "business": {"business_id": "business-sba-bbbbbbbbbbbb",
                    "receipt_sha256": "a" * 64, "aggregates": {"dimensions": {"program_status": [
                        {"program": "7A", "bucket": "all", "records": 9}, {"program": "504", "bucket": "all", "records": 3}]},
                        "amount_scope": {"7A": "total loan", "504": "SBA/CDC component"}, "limitations": []}, "quality": {}, "contract": {}}}

    class SyntheticService:
        root = tmp_path
        reviews = Reviews(tmp_path / "private/reviews.sqlite3")
        suite_views = SyntheticSuiteViews()
        sec_views = object()  # Coverage HTTP test supplies the calculation separately.

        def case(self, identifier):
            if identifier == "changed":
                raise EvidenceChanged("PRIVATE PATH MUST NOT LEAK")
            if identifier != "synthetic":
                raise KeyError("PRIVATE PATH MUST NOT LEAK")
            return {}

        def snapshot(self, identifier):
            self.case(identifier)
            return {"case_id": identifier, "source_kind": "SYNTHETIC-QA"}

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SyntheticService()))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    def request(path, method="GET", body=None, headers=None):
        # Full LendingClub requests verify ~650MB compressed source bytes.
        # Keep the ordinary boundary timeout while allowing that actual hash IO.
        timeout=30 if path.startswith('/api/lendingclub-full-source') else 5
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=timeout)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        connection.close()
        return result

    yield request, server.server_port
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)


def test_loopback_origin_and_no_store_headers(http_app):
    request, _ = http_app
    status, headers, _ = request("/api/health")
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert request("/api/health", headers={"Host": "evil.example"})[0] == 403
    assert request("/api/health", headers={"Origin": "https://evil.example"})[0] == 403
    assert request("/api/health", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403


def test_affordability_origin_validation_and_private_export(http_app):
    p={'case_ref':'qa-http','as_of':'2026-10-12','currency':'USD','scope':'individual','scope_ref':'qa-member','members':1,
       'coverage':{k:True for k in ['gross_income','net_income','recurring_expenses','debt_payments','proposed_payments']},
       'policy':{'policy_ref':'qa-policy','max_total_dti_fraction':'0.4','min_monthly_residual':'500'}}
    for group,amount in [('gross_income','5000'),('net_income','4000'),('recurring_expenses','1500'),('debt_payments','1500'),('proposed_payments','500')]:
        p[group]=[{'ref':group,'amount':amount,'period':'monthly','evidence_ref':None,'valid_through':None}]
    request,port=http_app;body=json.dumps(p)
    headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{port}','X-CreditAtlas-Client':'local'}
    status,response,data=request('/api/affordability-assess','POST',body,headers)
    assert status==200 and response['Cache-Control']=='no-store'
    r=json.loads(data);assert r['baseline']['total_dti_fraction']['decimal50']=='0.4' and r['credit_decision'] is None
    status,response,data=request('/api/affordability-report','POST',body,headers)
    assert status==200 and 'private-affordability.json' in response['Content-Disposition'] and json.loads(data)==r
    assert request('/api/affordability-assess','POST',body,{'Content-Type':'application/json','Origin':'https://evil.example'})[0]==403
    assert request('/api/affordability-assess','POST',json.dumps({'gross_income':'secret'}),headers)[0]==400
    assert request('/api/affordability-assess','POST',body,{'Content-Type':'text/plain','Origin':headers['Origin'],'X-CreditAtlas-Client':'local'})[0]==415


def test_full_lendingclub_source_private_http_and_export(http_app,monkeypatch):
    from pathlib import Path
    from credit_atlas import lendingclub_full_source
    original=lendingclub_full_source.report;root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(lendingclub_full_source,'report',lambda _,q:original(root,q))
    request,_=http_app
    status,headers,data=request('/api/lendingclub-full-source?category=Current')
    assert status==200 and headers['Cache-Control']=='no-store'
    r=json.loads(data);assert r['selected_records']==878317 and r['approval_rate'] is None
    status,headers,data=request('/api/lendingclub-full-source-report?kind=rejected')
    assert status==200 and 'private-LendingClub-full-source.json' in headers['Content-Disposition']
    assert json.loads(data)['source_records']==27648741
    assert request('/api/lendingclub-full-source?kind=rejected&category=Current')[0]==400


def test_lendingclub_source_private_http_and_export(http_app,monkeypatch):
    from pathlib import Path
    from credit_atlas import lendingclub_source
    original=lendingclub_source.report;root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(lendingclub_source,'report',lambda _,q:original(root,q))
    request,_=http_app
    status,headers,data=request('/api/lendingclub-source?from=2020-01&status=Charged%20Off')
    assert status==200 and headers['Cache-Control']=='no-store'
    r=json.loads(data);assert r['selected_records']<r['window_all_status_records']
    status,headers,data=request('/api/lendingclub-source-report?field=dti')
    assert status==200 and 'private-LendingClub-source.json' in headers['Content-Disposition']
    assert json.loads(data)['selected_field']['missing']==1204
    assert request('/api/lendingclub-source?status=Current')[0]==400


def test_utility_debt_report_http_and_export(http_app,monkeypatch):
    from pathlib import Path
    from credit_atlas import utility_debt_service
    original=utility_debt_service.report
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(utility_debt_service,'report',lambda _,q:original(root,q))
    request,_=http_app
    status,headers,data=request('/api/utility-debt-service?system=water&basis=total')
    assert status==200 and headers['Cache-Control']=='no-store'
    result=json.loads(data)
    assert result['reported_dscr']=='2.51' and result['compliance'] is None
    status,headers,data=request('/api/utility-debt-service-report?system=wastewater&year=2024')
    assert status==200 and 'private-utility-debt-service.json' in headers['Content-Disposition']
    assert json.loads(data)['selected']['values']['net_revenues']=='72374772'
    assert request('/api/utility-debt-service?year=2026')[0]==400
    status,headers,data=request('/api/utility-debt-service',method='HEAD')
    assert status==200 and data==b''


def test_sovereign_source_report_http_export_and_invalid_scope(http_app,monkeypatch):
    from pathlib import Path
    from credit_atlas import sovereign_defaults
    original=sovereign_defaults.report
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(sovereign_defaults,'report',lambda _,q:original(root,q))
    request,_=http_app
    status,headers,data=request('/api/sovereign-defaults?entity=VNM&year=2025')
    assert status==200 and headers['Cache-Control']=='no-store'
    result=json.loads(data)
    assert result['actual_exact']=='36' and result['reference_year_header']['provisional']
    status,headers,data=request('/api/sovereign-defaults-report?year=2024')
    assert status==200 and 'CreditAtlas-private-sovereign-defaults.json' in headers['Content-Disposition']
    assert json.loads(data)['edition_revision_same_year_exact']=='82335.31'
    assert request('/api/sovereign-defaults?year=2026')[0]==400
    assert request('/api/sovereign-defaults?year=2025&year=2024')[0]==400
    assert request('/api/sovereign-defaults?metric=PD')[0]==400
    assert request('/api/sovereign-defaults',headers={'Origin':'https://evil.example'})[0]==403
    status,_,data=request('/api/sovereign-defaults',method='HEAD')
    assert status==200 and data==b''


def test_kpi_workbook_http_guards_and_binary_attachment(http_app,monkeypatch):
    request,port=http_app
    headers={'Origin':f'http://127.0.0.1:{port}','X-CreditAtlas-Client':'local','Content-Type':'application/json'}
    assert request('/api/kpi-workbook','POST','{}',{'Content-Type':'application/json'})[0]==403
    assert request('/api/kpi-workbook','POST','{}',{**headers,'Origin':'https://evil.example'})[0]==403
    assert request('/api/kpi-workbook','POST','{}',{**headers,'Content-Type':'text/plain'})[0]==415
    assert request('/api/kpi-workbook','POST','{}',headers)[0]==400
    from credit_atlas import kpi_workbook
    monkeypatch.setattr(kpi_workbook,'export_workbook',lambda *args:b'PK-test-workbook')
    status,response,body=request('/api/kpi-workbook','POST','{}',headers)
    assert status==200 and body==b'PK-test-workbook'
    assert 'spreadsheetml.sheet' in response['Content-Type'] and response['Cache-Control']=='no-store'
    assert 'CreditAtlas-KPI.xlsx' in response['Content-Disposition']


def test_corporate_memo_http_guards_and_routes(http_app,monkeypatch):
    request,port=http_app
    headers={'Origin':f'http://127.0.0.1:{port}','X-CreditAtlas-Client':'local','Content-Type':'application/json'}
    assert request('/api/corporate-memos','POST','{}',{'Content-Type':'application/json'})[0]==403
    assert request('/api/corporate-memos','POST','{}',headers)[0]==400
    path='/api/corporate-memos?view_id=sec-view-aaaaaaaaaaaa&cik=0000320193'
    assert json.loads(request(path)[2])['memos']==[]
    assert request(path+'&asof=2026-01-01')[0]==400
    assert request('/api/corporate-memo?id=../private')[0]==400
    assert request('/api/corporate-memo?id='+'a'*32)[0]==404
    from credit_atlas.corporate_memos import CorporateMemos
    monkeypatch.setattr(CorporateMemos,'report',lambda *args:{'memo':{'id':'a'*32},'history':[]})
    status,response,_=request('/api/corporate-memo-report?id='+'a'*32)
    assert status==200 and response['Cache-Control']=='no-store' and 'corporate-memo.json' in response['Content-Disposition']


def test_sec_coverage_http_guards_and_attachment(http_app,monkeypatch):
    request,_=http_app
    from credit_atlas import sec_coverage
    monkeypatch.setattr(sec_coverage,'report',lambda *args:{'periods':[],'visibility':'private'})
    status,headers,body=request('/api/sec-coverage-report?view_id=sec-view-aaaaaaaaaaaa&asof=2026-10-10')
    assert status==200 and headers['Cache-Control']=='no-store' and 'SEC-coverage.json' in headers['Content-Disposition']
    assert json.loads(body)['visibility']=='private'
    assert request('/api/sec-coverage',headers={'Origin':'https://evil.example'})[0]==403


def test_sec_workbook_http_guards_and_binary(http_app,monkeypatch):
    request,port=http_app
    headers={'Origin':f'http://127.0.0.1:{port}','X-CreditAtlas-Client':'local','Content-Type':'application/json'}
    assert request('/api/sec-workbook','POST','{}',{'Content-Type':'application/json'})[0]==403
    assert request('/api/sec-workbook','POST','{}',{**headers,'Origin':'https://evil.example'})[0]==403
    assert request('/api/sec-workbook','POST','{}',{**headers,'Content-Type':'text/plain'})[0]==415
    assert request('/api/sec-workbook','POST','{}',headers)[0]==400
    from credit_atlas import sec_workbook
    monkeypatch.setattr(sec_workbook,'export_workbook',lambda *args:b'PK-SEC-workbook')
    status,response,body=request('/api/sec-workbook','POST','{}',headers)
    assert status==200 and body==b'PK-SEC-workbook'
    assert response['Cache-Control']=='no-store' and 'CreditAtlas-SEC.xlsx' in response['Content-Disposition']
    assert 'spreadsheetml.sheet' in response['Content-Type']


def test_sec_debt_http_guards_and_attachment(http_app,monkeypatch):
    request,_=http_app
    from credit_atlas import sec_debt
    monkeypatch.setattr(sec_debt,'report',lambda *args:{'buckets':[],'visibility':'private'})
    status,headers,body=request('/api/sec-debt-report?view_id=sec-view-aaaaaaaaaaaa')
    assert status==200 and headers['Cache-Control']=='no-store'
    assert 'SEC-maturities.json' in headers['Content-Disposition'] and b'private' in body
    assert request('/api/sec-debt',headers={'Origin':'https://evil.example'})[0]==403


def test_affordability_excel_upload_boundary(http_app,monkeypatch):
    request,port=http_app
    route='/api/affordability-excel-import'
    headers={'Origin':f'http://127.0.0.1:{port}','X-CreditAtlas-Client':'local','Content-Type':'application/json'}
    assert request(route,'POST','{}',{'Content-Type':'application/json'})[0]==403
    assert request(route,'POST','{}',{**headers,'Origin':'https://evil.example'})[0]==403
    assert request(route,'POST','{}',{**headers,'Content-Type':'text/plain'})[0]==415
    assert request(route,'POST','{}',headers)[0]==400
    bad={'filename':'private.xlsx','content_base64':'!!private-sensitive-content!!'}
    status,_,body=request(route,'POST',json.dumps(bad),headers)
    assert status==400 and b'private-sensitive-content' not in body
    from credit_atlas import affordability_excel
    monkeypatch.setattr(affordability_excel,'import_upload',lambda payload:{'status':'QA_ROUTING_ONLY','source_documents_verified':False})
    status,response,body=request(route,'POST','{}',headers)
    assert status==200 and response['Cache-Control']=='no-store' and not json.loads(body)['source_documents_verified']


def test_affordability_template_http_boundary(http_app,monkeypatch):
    request,_=http_app
    from credit_atlas import affordability_excel
    monkeypatch.setattr(affordability_excel,'template_bytes',lambda root:b'PK-QA-template')
    route='/api/affordability-excel-template'
    status,headers,body=request(route)
    assert status==200 and body==b'PK-QA-template' and headers['Cache-Control']=='no-store'
    assert 'CreditAtlas-Affordability-Input.xlsx' in headers['Content-Disposition']
    assert request(route+'?unknown=1')[0]==400
    assert request(route,headers={'Origin':'https://evil.example'})[0]==403


def test_fannie_samples_scope_and_private_export(http_app,monkeypatch):
    from pathlib import Path
    from credit_atlas import fannie_samples
    original=fannie_samples.report;root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(fannie_samples,'report',lambda _,q:original(root,q))
    request,_=http_app
    route='/api/fannie-samples'
    status,_,data=request(route+'?family=multifamily')
    assert status==200 and json.loads(data)['summary']['source_rows']==258
    status,headers,exported=request('/api/fannie-samples-report?family=multifamily')
    assert status==200 and data==exported and headers['Cache-Control']=='no-store'
    assert 'private-Fannie-samples.json' in headers['Content-Disposition']
    assert request(route+'?loan_id=private')[0]==400
    assert request(route,headers={'Origin':'https://evil.example'})[0]==403


def test_sec_debt_workbook_http_guards_and_binary(http_app,monkeypatch):
    request,port=http_app
    headers={'Origin':f'http://127.0.0.1:{port}','X-CreditAtlas-Client':'local','Content-Type':'application/json'}
    route='/api/sec-debt-workbook'
    assert request(route,'POST','{}',{'Content-Type':'application/json'})[0]==403
    assert request(route,'POST','{}',{**headers,'Origin':'https://evil.example'})[0]==403
    assert request(route,'POST','{}',{**headers,'Content-Type':'text/plain'})[0]==415
    assert request(route,'POST','{}',headers)[0]==400
    from credit_atlas import sec_debt_workbook
    monkeypatch.setattr(sec_debt_workbook,'export_workbook',lambda *args:b'PK-maturity-workbook')
    status,response,body=request(route,'POST','{}',headers)
    assert status==200 and body==b'PK-maturity-workbook'
    assert response['Cache-Control']=='no-store' and 'CreditAtlas-Maturities.xlsx' in response['Content-Disposition']


def test_suite_routes_return_aggregate_snapshot_and_private_attachment(http_app):
    request, _ = http_app
    assert json.loads(request("/api/suite-views")[2])["views"][0]["status"] == "verified"
    path = "/api/suite-view?view_id=suite-view-aaaaaaaaaaaa"
    status, _, body = request(path)
    assert status == 200 and json.loads(body)["retail"]["holdout"]["loans"] == 100
    status, headers, exported = request("/api/suite-report?view_id=suite-view-aaaaaaaaaaaa")
    assert status == 200 and exported == body
    assert "private-aggregates.json" in headers["Content-Disposition"]
    assert headers["Cache-Control"] == "no-store"


def test_suite_routes_reject_cross_origin_and_invalid_snapshot_identifiers(http_app):
    request, _ = http_app
    assert request("/api/suite-views", headers={"Origin": "https://evil.example"})[0] == 403
    assert request("/api/suite-report?view_id=suite-view-aaaaaaaaaaaa", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    status, _, body = request("/api/suite-view?view_id=../../private")
    assert status == 400 and b"PRIVATE PATH" not in body


def test_scoped_business_attachment_and_unknown_row_filters(http_app):
    # Boundary checks exercise the real projector; cold scientific dependency
    # imports are not part of this synthetic five-second socket assertion.
    from credit_atlas.suite_snapshot import business_report
    request, _ = http_app
    status, headers, body = request("/api/business-report?view_id=suite-view-aaaaaaaaaaaa&program=504")
    assert status == 200 and "private-business-aggregates.json" in headers["Content-Disposition"]
    report = json.loads(body)
    assert report["selected_record_count"] == 3 and all(r["program"] == "504" for r in report["rows"])
    assert report["quality_scope"].startswith("whole_source")
    assert request("/api/business-report?view_id=suite-view-aaaaaaaaaaaa&loan_key=raw")[0] == 400
    assert request("/api/business-report?view_id=suite-view-aaaaaaaaaaaa", headers={"Origin": "https://evil.example"})[0] == 403


def test_private_file_routes_and_duplicate_query_are_not_served(http_app):
    request, _ = http_app
    assert request("/artifacts/private/reviews.sqlite3")[0] == 404
    assert request("/../workspace.local.json")[0] == 404
    assert request("/api/snapshot?run=synthetic&run=changed")[0] == 400


def test_changed_or_missing_evidence_does_not_leak_internal_diagnostic(http_app):
    request, _ = http_app
    for run, expected in [("changed", 503), ("missing", 404)]:
        status, _, data = request("/api/snapshot?run=" + run)
        assert status == expected
        assert b"PRIVATE PATH" not in data


def test_finding_requires_same_origin_json_and_revision_context(http_app):
    request, port = http_app
    payload = {"case_id": "synthetic", "title": "SYNTHETIC-QA", "body": "example",
               "view": "portfolio", "filters": {"segment": "relief"},
               "evidence_refs": ["portfolio_monthly"]}
    body = json.dumps(payload)
    headers = {"Origin": "http://127.0.0.1:" + str(port), "X-CreditAtlas-Client": "local",
               "Content-Type": "application/json"}
    assert request("/api/findings", "POST", body, {"Content-Type": "application/json"})[0] == 403
    assert request("/api/findings", "POST", body, {**headers, "Content-Type": "text/plain"})[0] == 415
    status, _, data = request("/api/findings", "POST", body, headers)
    assert status == 201
    record = json.loads(data)
    stale = {**payload, "id": record["id"], "revision": 0}
    assert request("/api/findings", "POST", json.dumps(stale), headers)[0] == 409
    invalid = {**payload, "filters": {"loan_id": "source-private-id"}}
    assert request("/api/findings", "POST", json.dumps(invalid), headers)[0] == 400


def test_abs_surveillance_public_release_and_excel_routes(http_app):
    request, _ = http_app
    status, headers, body = request("/api/absee-surveillance")
    assert status == 200 and headers["Cache-Control"] == "no-store"
    release = json.loads(body)
    assert release["period_count"] == 103
    assert release["deal_count"] == 3
    assert release["exception_period_count"] == 86
    assert release["cross_deal_recovery_residual_total"] is None
    assert request("/api/absee-surveillance?deal_id=NISSAN-2024-B")[0] == 400

    status, headers, body = request("/api/absee-surveillance-report")
    assert status == 200 and "CreditAtlas-ABS-Surveillance-Release.json" in headers["Content-Disposition"]
    assert json.loads(body)["recovery_exception_period_count"] == 83

    status, headers, body = request("/downloads/abs-surveillance-exceptions.xlsx")
    assert status == 200
    assert headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "CreditAtlas-ABS-Surveillance-Exceptions.xlsx" in headers["Content-Disposition"]
    assert body[:2] == b"PK"
    assert request("/downloads/abs-surveillance-exceptions.xlsx?deal_id=NISSAN-2024-B")[0] == 400
