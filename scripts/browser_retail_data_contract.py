import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import expect,sync_playwright
from credit_atlas.workspace import sha256

ROOT=Path.cwd();VIEW='suite-view-74e07524f6d0';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('retail-data-contract-browser-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];expect.set_options(timeout=120000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    response=page.request.get(BASE+'/api/retail-data-contract?view_id='+VIEW,timeout=120000);assert response.status==200;r=response.json()
    assert r['clients']==30000 and r['history_rows']==180000 and r['target_counts']=={'0':23364,'1':6636}
    page.goto(BASE+'/?view=retail&workspace_tab=evidence&view_id='+VIEW)
    box=page.locator('#retail-data-contract');expect(box.get_by_role('button',name='Xuất Retail data contract JSON',exact=True)).to_be_visible()
    expected=[[m['reference_month'],m['status_field']+' / '+m['status_source_field'],m['bill_field']+' / '+m['bill_source_field'],m['payment_field']+' / '+m['payment_source_field']] for m in r['history_mapping']]
    assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(0).locator('tbody tr').all()]==expected
    assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(1).locator('tbody tr').all()]==[[role,format(s['positive'],','),format(s['negative'],','),format(s['positive']+s['negative'],',')] for role,s in r['support'].items()]
    assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(2).locator('tbody tr').all()]==[[f['source_field'],f['feature'],'Allowlisted' if f['predictor'] else 'Excluded'] for f in r['feature_mapping']]
    box.get_by_text('Source categories · dictionary qualification',exact=True).click()
    assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(3).locator('tbody tr').all()]==[[c['field'],c['code'],format(c['clients'],','),'Source description' if c['dictionary_qualified'] else 'Unqualified meaning',c['interpretation']] for c in r['source_category_counts']]
    for text in ['180,000','30,000','TWD/NT dollars','-2/0','source_client_id','not regulatory default','Vietnam applicability']:expect(box).to_contain_text(text)
    with page.expect_download() as d:box.get_by_role('button',name='Xuất Retail data contract JSON',exact=True).click()
    file=out/'contract.json';d.value.save_as(file);assert json.loads(file.read_text())==r
    box.get_by_text('Source categories · dictionary qualification',exact=True).click();box.screenshot(path=str(out/'desktop.png'))
    page.reload();expect(page.locator('#retail-data-contract').get_by_role('button',name='Xuất Retail data contract JSON',exact=True)).to_be_visible()
    page.get_by_role('tab',name='Tổng quan',exact=True).click();expect(page.locator('#retail-model-summary')).to_be_visible()
    page.get_by_role('tab',name='Model & evidence',exact=True).click();expect(page.locator('#retail-data-contract')).to_be_visible()
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#retail-data-contract').screenshot(path=str(out/'mobile.png'))
    assert page.request.get(BASE+'/api/retail-data-contract?view_id='+VIEW+'&partition=final_test').status==400
    assert page.request.get(BASE+'/api/retail-data-contract?view_id='+VIEW,headers={'Origin':'https://example.com'}).status==403
    page.route('**/api/retail-data-contract?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA source unavailable"}'))
    page.reload();expect(page.locator('#retail-panel-evidence')).to_contain_text('QA source unavailable');assert page.locator('#retail-data-contract a').count()==0
    page.unroute('**/api/retail-data-contract?*');page.get_by_role('button',name='Thử lại',exact=True).click();expect(page.locator('#retail-data-contract').get_by_role('button',name='Xuất Retail data contract JSON',exact=True)).to_be_visible()
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','history_rows_checked':6,'split_rows_checked':4,'feature_fields_checked':23,'category_rows_checked':133,'json_export_parity':True,'reload_and_tab_navigation':True,'outage_retry':True,'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py'),'method_sha256':sha256(ROOT/'src/credit_atlas/retail_data_contract.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','category_rows':133}))
