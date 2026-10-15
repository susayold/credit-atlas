import json
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('mortgage-provenance-browser-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
errors=[];checks=[];expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    response=page.request.get(BASE+'/api/mortgage-provenance?run='+CASE,timeout=120000)
    assert response.status==200
    r=response.json()
    foundation=json.loads((ROOT/f'artifacts/private/{CASE}/foundation-complete.json').read_text())
    receipt_path=ROOT/f'vendor/credit_risk_strategy_lab/data/private/raw/{foundation["raw_sha256"]}.receipt.json'
    raw=json.loads(receipt_path.read_text())
    assert r['source_use_receipt_sha256']==sha256(receipt_path)==foundation['source_use_receipt_sha256']
    assert r['receipt_received_at']==raw['received_at'] and r['release_confirmation']==raw['release_confirmation']
    assert r['publisher_publication_at'] is None and r['publisher_release_authenticated'] is False
    assert str(ROOT) not in json.dumps(r) and 'original_filename' not in r
    for segment in ['all','relief','non_relief','unknown']:
        page.goto(BASE+f'/?run={CASE}&view=sources&segment={segment}')
        box=page.locator('#mortgage-provenance');expect(box).to_be_visible()
        for text in ['Supplied annual source','Chưa xác thực','Publisher publication date',raw['received_at'],raw['release_confirmation'],'not the whole mortgage market']:
            expect(box).to_contain_text(text)
        assert 'Official annual sample' not in box.inner_text()
        with page.expect_download() as d:box.get_by_role('link',name='Xuất mortgage provenance JSON',exact=True).click()
        file=out/(segment+'-provenance.json');d.value.save_as(file)
        assert json.loads(file.read_text())==r
        checks.append({'segment':segment,'status':'PASS'})
        if segment=='all':box.screenshot(path=str(out/'desktop.png'))
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#mortgage-provenance').screenshot(path=str(out/'mobile.png'))
    for url in ['/api/mortgage-provenance','/api/mortgage-provenance?run='+CASE+'&segment=all','/api/mortgage-provenance?run=../private','/api/mortgage-provenance?run='+CASE+'&run='+CASE]:
        assert page.request.get(BASE+url).status==400
    assert page.request.get(BASE+'/api/mortgage-provenance?run='+CASE,headers={'Origin':'https://example.com'}).status==403
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','scopes':checks,'mobile_no_overflow':True,'source_receipt_parity':True,'invalid_query_checks':4,'cross_origin_rejected':True,'page_errors':errors,'ledger_unchanged':True,'source_receipt_sha256':sha256(receipt_path),'method_sha256':sha256(ROOT/'src/credit_atlas/mortgage_provenance.py'),'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks)}))
