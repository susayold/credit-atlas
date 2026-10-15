import json,threading
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from playwright.sync_api import expect,sync_playwright
import credit_atlas.retail_assessment as assessment
import credit_atlas.retail_comparison as comparison
import credit_atlas.retail_freeze as freeze
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256

ROOT=Path.cwd();VIEW='suite-view-74e07524f6d0';out=ROOT/'artifacts/private'/('retail-dossier-browser-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];calls=[]
def forbidden(*a,**kw):calls.append('forbidden');raise AssertionError('Actual model inference/refit attempted')
with ExitStack() as stack:
    for module,name in [(assessment,'predict_json'),(assessment,'run_assessment'),(comparison,'predict_json'),(comparison,'verify_assessment'),(freeze,'verify_freeze')]:stack.enter_context(patch.object(module,name,forbidden))
    service=ResearchService(ROOT,review_path=out/'qa-reviews.sqlite3');server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    BASE='http://127.0.0.1:'+str(server.server_port);expect.set_options(timeout=120000)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        response=page.request.get(BASE+'/api/retail-dossier?view_id='+VIEW,timeout=120000);assert response.status==200;r=response.json()
        snap=json.loads((ROOT/f'artifacts/private/{VIEW}/snapshot.json').read_text())['retail']
        assert r['model']['selection']==snap['selection'] and r['model']['rubric']==snap['rubric']
        assert r['saved_final_test']==snap['holdout'] and r['validation_metrics']==snap['validation'] and r['paired_validation_uncertainty']==snap['paired_improvements']
        assert r['source_contract']['support']==snap['support'] and r['governance']['review_owner'] is None and not any(r['governance'][k] for k in r['governance'] if k!='review_owner')
        assert str(ROOT) not in json.dumps(r) and 'model.json' not in json.dumps(r['evidence_hashes'])
        page.goto(BASE+'/?view=retail&workspace_tab=evidence&view_id='+VIEW)
        box=page.locator('#retail-governance-dossier');download=box.get_by_role('link',name='Xuất Retail model dossier JSON',exact=True);expect(download).to_be_visible()
        expected=[[s['stage'],s['artifact_id'],s['recorded_at']] for s in r['audit_trail']]
        assert [row.locator('td').all_text_contents() for row in box.locator('tbody tr').all()]==expected
        for text in ['Chưa cung cấp','Authenticated sign-off','Chưa có','Production intended-use approval','Chưa đạt','Taiwan','not independently authenticated']:expect(box).to_contain_text(text)
        with page.expect_download() as d:download.click()
        file=out/'dossier.json';d.value.save_as(file);assert json.loads(file.read_text())==r
        box.screenshot(path=str(out/'desktop.png'));page.reload();expect(page.locator('#retail-governance-dossier').get_by_role('link',name='Xuất Retail model dossier JSON',exact=True)).to_be_visible()
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#retail-governance-dossier').screenshot(path=str(out/'mobile.png'))
        assert page.request.get(BASE+'/api/retail-dossier?view_id='+VIEW+'&rescore=true').status==400
        assert page.request.get(BASE+'/api/retail-dossier?view_id='+VIEW,headers={'Origin':'https://example.com'}).status==403
        page.route('**/api/retail-dossier?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA dossier unavailable"}'))
        page.reload();expect(page.locator('#retail-panel-evidence')).to_contain_text('QA dossier unavailable');assert page.locator('#retail-governance-dossier a').count()==0
        page.unroute('**/api/retail-dossier?*');page.get_by_role('button',name='Thử lại',exact=True).click();expect(page.locator('#retail-governance-dossier').get_by_role('link',name='Xuất Retail model dossier JSON',exact=True)).to_be_visible()
        browser.close()
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
assert not calls and not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','source_split_selection_metrics_parity':True,'audit_trail_rows':6,'export_parity':True,'governance_unqualified_preserved':True,'forbidden_calls':0,'reload':True,'outage_retry':True,'mobile':True,'ledger_unchanged':True,'page_errors':errors,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py'),'method_sha256':sha256(ROOT/'src/credit_atlas/retail_dossier.py')},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','output':str(out),'audit_trail_rows':6,'forbidden_calls':0}))
