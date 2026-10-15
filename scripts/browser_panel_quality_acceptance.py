import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('panel-quality-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[]
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    monitor=page.request.get(BASE+'/api/monitoring?run='+CASE,timeout=120000).json()
    for segment in ['all','relief','non_relief','unknown']:
        page.goto(BASE+f'/?run={CASE}&view=sources&segment={segment}&basis=count&horizon=12&transition_year=all')
        box=page.locator('section.card').filter(has=page.get_by_role('heading',name='Quality monitoring & investigation',exact=True))
        expect(box).to_be_visible()
        expected=[[r['check'],format(r['value'],','),r['status'],r['action']] for r in monitor['integrity_checks']]
        assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(0).locator('tbody tr').all()]==expected
        expected=[[r['field'],r['status'],f"{r['missing_share']*100:.2f}%"] for r in monitor['field_availability']]
        assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(1).locator('tbody tr').all()]==expected
        expect(box).to_contain_text('Calibration/drift alerts: unavailable')
        expect(page.locator('#content')).to_contain_text('Delinquency codes là categories')
        with page.expect_download() as d:page.locator('#export-report').click()
        file=out/(segment+'-report.json');d.value.save_as(file);report=json.loads(file.read_text())
        quality=report['supplemental_evidence']['quality_monitoring']
        assert quality['integrity_checks']==monitor['integrity_checks'] and quality['field_availability']==monitor['field_availability']
        assert quality['filters_applied']==[] and quality['scope']=='whole_frozen_sample'
        assert quality['model_monitoring']['calibration_alert'] is None and quality['model_monitoring']['drift_alert'] is None
        checks.append({'segment':segment,'whole_source_quality_unchanged':True,'status':'PASS'})
        if segment=='all':box.screenshot(path=str(out/'quality-desktop.png'))
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'quality-mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','requirement':'P2.02','scopes':checks,'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks)}))
