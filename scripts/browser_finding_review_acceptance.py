"""Real frozen evidence, isolated QA database/server; no user findings changed."""
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import expect,sync_playwright
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import contained,sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21'
out=ROOT/'artifacts/private'/('finding-review-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
main=ROOT/'artifacts/private/reviews.sqlite3';main_before=sha256(main)
manifest=json.loads((ROOT/f'artifacts/private/{CASE}/case-complete.json').read_text())
files=[(contained(ROOT,i['path']),i['sha256']) for i in manifest['verified_inputs']]+[(ROOT/f'artifacts/private/{CASE}'/f,h) for f,h in manifest['outputs_sha256'].items()]
service=ResearchService(ROOT,review_path=out/'qa-reviews.sqlite3')
server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
BASE='http://127.0.0.1:'+str(server.server_port);errors=[];checks=[];expect.set_options(timeout=60000)
try:
 with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    http_errors=[]
    page.on('response',lambda r:http_errors.append({'path':r.url.split('?')[0].replace(BASE,''),'status':r.status}) if r.status>=400 else None)
    for view in ['overview','sources','portfolio','vintage','transitions','lifecycle','models','loss','evidence']:
        page.goto(BASE+f'/?run={CASE}&view={view}&segment=relief&basis=balance&horizon=24&from=2020-01&to=2020-03&transition_year=2020')
        add=page.get_by_role('button',name='+ Lưu finding từ view này',exact=True)
        try:expect(add).to_be_visible()
        except AssertionError:
            page.screenshot(path=str(out/'failure.png'),full_page=True)
            (out/'failure.json').write_text(json.dumps({'view':view,'http_errors':http_errors,'page_errors':errors,'page_text':page.locator('body').inner_text()},ensure_ascii=False,indent=2),encoding='utf-8')
            raise
        add.click()
        title='QA synthetic '+view
        page.locator('#finding-title').fill(title);page.locator('#finding-body').fill('<script>window.QA_INJECTED=true</script> Scope QA only')
        expect(page.locator('#finding-dialog')).to_contain_text('không phải phê duyệt tín dụng')
        page.locator('#save-finding').click();expect(page.locator('#finding-dialog')).not_to_be_visible()
        records=page.request.get(BASE+'/api/findings?run='+CASE).json()['findings'];record=next(r for r in records if r['title']==title)
        assert record['view']==view
        assert {k:v for k,v in record['filters'].items() if k!='loan_key'}=={'segment':'relief','basis':'balance','horizon':'24','from':'2020-01','to':'2020-03','transition_year':'2020'}
        if record['filters'].get('loan_key'):
            assert view=='lifecycle' and service.loans(CASE,{'q':record['filters']['loan_key'],'limit':'1'})['total_matching']==1
        checks.append({'view':view,'saved_scope':'PASS','id':record['id']})
    token=service.loans(CASE,{'segment':'relief','limit':'1'})['rows'][0]['loan_key']
    payload={'case_id':CASE,'title':'QA explicit loan context','body':'QA pseudonymous timeline scope','view':'lifecycle','status':'draft','filters':{'segment':'relief','basis':'count','horizon':'12','loan_key':token},'evidence_refs':['loan_timeline','episode_events']}
    response=page.request.post(BASE+'/api/findings',data=payload,headers={'Origin':BASE,'X-CreditAtlas-Client':'local'});assert response.status==201
    loan_record=response.json()
    exported=page.request.get(BASE+'/api/finding-report?run='+CASE+'&id='+loan_record['id']).json()
    assert exported['view_evidence']['loan_timeline']==service.timeline(CASE,token)
    assert exported['finding']['filters']['loan_key']==token
    assert 'loan_id' not in json.dumps(exported['view_evidence']['loan_timeline'])
    page.goto(BASE+f'/?run={CASE}&view=evidence&segment=all')
    target=page.locator('.finding-card').filter(has=page.get_by_role('heading',name='QA synthetic portfolio',exact=True));expect(target).to_be_visible()
    assert page.evaluate('window.QA_INJECTED===true') is False
    for status,revision in [('reviewed',2),('archived',3),('draft',4)]:
        target.get_by_role('button',name='Sửa / review',exact=True).click();page.locator('#finding-status').select_option(status);page.locator('#finding-body').fill('QA '+status+' revision '+str(revision));page.locator('#save-finding').click();expect(page.locator('#finding-dialog')).not_to_be_visible();expect(target).to_contain_text('revision '+str(revision))
    target.get_by_role('button',name='Xem history',exact=True).click();expect(target.locator('.history-block')).to_be_visible()
    record=next(r for r in service.reviews.list(CASE) if r['title']=='QA synthetic portfolio');identifier=record['id']
    for revision in range(1,5):
        with page.expect_download() as d:target.locator('.history-block').get_by_role('link',name='Xuất finding r'+str(revision),exact=True).click()
        file=out/('revision-'+str(revision)+'.json');d.value.save_as(file);r=json.loads(file.read_text())
        assert r['finding']==service.reviews.history(CASE,identifier)[revision-1]['record']
        assert len(r['history'])==revision and r['aggregate_evidence']['filter_context']==record['filters']
        assert r['bank_credit_approval'] is False and r['authenticated_reviewer_identity'] is False
        assert r['aggregate_evidence']['lineage']['case_receipt_sha256']==sha256(ROOT/f'artifacts/private/{CASE}/case-complete.json')
    # External concurrent edit must make the stale open form fail with409.
    target.get_by_role('button',name='Sửa / review',exact=True).click()
    service.reviews.save(CASE,{**record,'revision':4,'body':'Concurrent QA update'},identifier)
    page.locator('#finding-body').fill('Stale update');page.locator('#save-finding').click();expect(page.locator('#finding-error')).to_contain_text('Finding changed')
    assert len(service.reviews.history(CASE,identifier))==5
    page.locator('#cancel-finding').click()
    # Modal-open context is kept even if application state changes programmatically.
    page.goto(BASE+f'/?run={CASE}&view=portfolio&segment=relief&basis=count')
    page.get_by_role('button',name='+ Lưu finding từ view này',exact=True).click()
    page.locator('#finding-title').fill('QA modal context');page.locator('#finding-body').fill('QA context freeze')
    page.evaluate("state.view='loss';state.segment='non_relief';state.run='d01-000000000000'")
    page.locator('#save-finding').click();expect(page.locator('#finding-dialog')).not_to_be_visible()
    ctx=next(r for r in service.reviews.list(CASE) if r['title']=='QA modal context');assert ctx['view']=='portfolio' and ctx['filters']['segment']=='relief'
    for case in checks:
        q=page.request.get(BASE+'/api/finding-report?run='+CASE+'&id='+case['id']);assert q.status==200
        r=q.json()
        if case['view']=='loss':assert r['view_evidence']['observed_loss_details']['expense_formula']['checked_rows']==374
        if case['view']=='sources':assert r['view_evidence']['source_provenance']['publisher_publication_at'] is None
    assert page.request.get(BASE+'/api/finding-report?run='+CASE+'&id='+identifier+'&revision=0').status==400
    assert page.request.get(BASE+'/api/finding-report?run='+CASE+'&id='+identifier+'&revision=99').status==404
    assert page.request.get(BASE+'/api/finding-report?run='+CASE+'&id='+identifier,headers={'Origin':'https://example.com'}).status==403
    page.goto(BASE+f'/?run={CASE}&view=evidence');page.set_viewport_size({'width':390,'height':844})
    expect(page.get_by_role('heading',name='QA synthetic portfolio',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('.finding-card').filter(has=page.get_by_role('heading',name='QA synthetic portfolio',exact=True)).screenshot(path=str(out/'review-mobile.png'))
    browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
assert not errors and sha256(ledger)==before and sha256(main)==main_before
for path,expected in files:assert sha256(path)==expected
(out/'receipt.json').write_text(json.dumps({'status':'PASS','view_scopes':checks,'historical_exports':4,'loan_timeline_export_parity':True,'status_revisions':['draft','reviewed','archived','draft'],'conflict_rejected':True,'modal_context_preserved':True,'text_injection_not_executed':True,'source_file_entries_unchanged':len(files),'user_reviews_unchanged':True,'ledger_unchanged':True,'mobile':True,'page_errors':errors,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py'),'method_sha256':sha256(ROOT/'src/credit_atlas/finding_reports.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','view_scopes':len(checks),'historical_exports':4}))
