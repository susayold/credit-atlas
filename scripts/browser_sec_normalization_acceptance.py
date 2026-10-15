"""Four issuer field evidence UI and exhaustive67annual report parity."""
import json
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();base='http://127.0.0.1:8770';view='sec-view-b92d9914f1dc'
case=root/'artifacts/private/sec-case-33077fe45722';statements=read_json(case/'annual-statements.json')
out=root/'artifacts/private'/('sec-normalization-browser-'+uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];checks=[]
expect.set_options(timeout=120000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    for s in statements:
        query={'view_id':view,'cik':s['cik'],'accession':s['accession'],'asof':'2026-10-14'}
        r=page.request.get(base+'/api/sec-report?'+urlencode(query),timeout=120000)
        assert r.status==200,(query,r.status,r.text())
        assert r.json()['statement']==s and not r.json()['historical_availability_qualified']
    checks.append('All67annual statements including536field states/candidate evidence match private HTTP report')
    for cik in ['0000320193','0000789019','0000037996','0001467858']:
        page.goto(base+'/?'+urlencode({'view':'sec','workspace_tab':'statements','sec_view_id':view,'sec_cik':cik,'sec_asof':'2026-10-14'}))
        box=page.locator('#sec-financial-fields');expect(box).to_be_visible()
        s=max((s for s in statements if s['cik']==cik),key=lambda s:(s['filing_date'],s['accession']))
        rows=[r.locator('td').all_text_contents() for r in box.locator('table tbody tr').all()]
        expected=[[name,v['status'],v['value_exact'] if v['value_exact'] is not None else 'Unavailable',v['start_date'] or 'Instant / unavailable',v['end_date'],format(len(v['evidence']),',')] for name,v in s['fields'].items()]
        assert rows==expected,(cik,rows[:2],expected[:2])
        with page.expect_download() as d:page.locator('#export-report').click()
        path=out/(cik+'.json');d.value.save_as(path);assert read_json(path)['statement']==s
    checks.append('Fourissuer latest8field rows each,missing/ambiguous states and downloaded exact evidence match saved source')
    page.reload();expect(page.get_by_label('SEC issuer')).to_have_value('0001467858')
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.screenshot(path=str(out/'mobile.png'))
    checks.append('Issuer/accession/cutoff reload and mobile without page overflow')
    page.get_by_label('SEC filing-date cutoff').fill('1990-01-01')
    page.get_by_role('button',name='Đọc filing evidence',exact=True).click()
    expect(page.locator('#content')).to_contain_text('Không có supported annual statement')
    assert page.locator('#sec-financial-fields').count()==0
    checks.append('Noeligible cutoff retains absence;no future fallback')
    assert page.request.get(base+'/api/sec-report?'+urlencode({'view_id':view,'cik':'0001467858','accession':'0000320193-25-000079','asof':'1990-01-01'})).status==400
    assert page.request.get(base+'/api/sec-report?view_id='+view,headers={'Origin':'https://outside.example'}).status==403
    browser.close()
assert not errors and sha256(ledger)==before
write_new(out/'receipt.json',{'status':'PASS','checks':checks,'annual_reports_checked':67,'latest_ui_fields_checked':32,
    'ledger_unchanged':True,'page_errors':errors,'app_js_sha256':sha256(root/'apps/web/app.js'),
    'server_sha256':sha256(root/'src/credit_atlas/server.py'),'method_sha256':sha256(Path(__file__)),
    'case_receipt_sha256':sha256(case/'case-complete.json')})
print(json.dumps({'output':str(out),'status':'PASS'}))
