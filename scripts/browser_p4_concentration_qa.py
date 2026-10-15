"""Actual inventory meters/search/sort/detail plus synthetic zero denominator."""
from pathlib import Path
from uuid import uuid4
import json
from playwright.sync_api import sync_playwright,expect
from urllib.request import urlopen
from urllib.parse import urlencode
from credit_atlas.workspace import read_json,sha256,write_new
from credit_atlas.exposure_imports import aggregate
from browser_navigation import select_task

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'artifacts/private'/('p4-concentration-browser-'+uuid4().hex[:12]);out.mkdir();base='http://127.0.0.1:8770'
source='exposure-import-57b88e00bedb';template=read_json(ROOT/'artifacts/private/p4-acceptance-qa-b6a5a8af88d0/receipt.json')['example_import_id']
ledgers=[ROOT/'artifacts/private'/name for name in ['retail-holdout-access.sqlite','bankruptcy-holdout-access.sqlite']]
before={str(p.relative_to(ROOT)):sha256(p) for p in ledgers};errors=[];scopes=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1050})
    page.on('pageerror',lambda e:errors.append(str(e)))
    for identifier in [source,template]:
        for dimension in ['region','segment','source_state','representation']:
            query={'import_id':identifier,'currency':'all','dimension':dimension}
            with urlopen(base+'/api/exposure-report?'+urlencode(query),timeout=120) as response:report=json.load(response)
            page.goto(base+'/?view=exposure&workspace_tab=overview&exposure_import_id='+identifier+'&exposure_currency=all&exposure_dimension='+dimension)
            expect(page.locator('#exposure-concentration')).to_be_visible(timeout=180000)
            select_task(page,'Tổng quan');panel=page.locator('#exposure-concentration')
            for currency in [c['currency'] for c in report['currencies']]:
                page.get_by_label('Concentration chart currency',exact=True).select_option(currency)
                group=[r for r in report['concentrations'] if r['currency']==currency]
                page.get_by_label('Concentration sort',exact=True).select_option('records')
                buttons=panel.locator('.concentration-row');actual=[b.get_attribute('data-bucket') for b in buttons.all()]
                expected=[r['bucket'] for r in sorted(group,key=lambda r:-r['records'])[:12]];assert actual==expected
                for b in buttons.all():
                    r=next(row for row in group if row['bucket']==b.get_attribute('data-bucket'))
                    if r['amount_share'] is None:assert b.locator('meter').count()==0
                    else:assert abs(float(b.locator('meter').get_attribute('value'))-float(r['amount_share']))<1e-15
                selected=group[0];page.get_by_label('Tìm concentration bucket',exact=True).fill(selected['bucket'])
                page.get_by_role('button',name='Đọc bucket '+selected['bucket'],exact=True).click()
                expect(page.locator('#exposure-bucket-detail .bucket-name')).to_have_text(selected['bucket'])
                expect(page.locator('#exposure-bucket-detail')).to_contain_text('không phải borrower identity')
                page.get_by_label('Tìm concentration bucket',exact=True).fill('NO_SUCH_QA_BUCKET')
                expect(panel).to_contain_text('Không có bucket phù hợp.')
                expect(page.get_by_role('button',name='Review bucket →',exact=True)).to_be_disabled()
                page.get_by_label('Tìm concentration bucket',exact=True).fill('')
                scopes.append({'import_id':identifier,'currency':currency,'dimension':dimension,'buckets':len(group)})
    metadata=read_json(ROOT/'artifacts/private'/source/'metadata.json');metadata['source_namespace']='Synthetic-zero-denominator-QA';metadata['source_description']='Synthetic browser fixture only'
    zero=aggregate([{'currency':'USD','reported_amount_major_exact':'0','research_el_major_exact':None,
        'region':'ZERO_BUCKET','segment':'QA','source_state':'CURRENT','representation':'DIRECT_ASSET'}],metadata)
    zero['filters']={'currency':'USD','dimension':'region'};zero['concentrations']=[r for r in zero['concentrations'] if r['dimension']=='region']
    assert zero['concentrations'][0]['amount_share'] is None
    page.evaluate('''r=>{const mount=document.createElement('section');mount.id='qa-zero-denominator';mount.className='task-panel';document.querySelector('#content').append(mount);portfolioOverview(mount,r,()=>{});}''',zero)
    fixture=page.locator('#qa-zero-denominator');expect(fixture.locator('.concentration-row')).to_contain_text('Unavailable')
    assert fixture.locator('.concentration-row meter').count()==0
    expect(fixture.locator('.bucket-balance')).to_contain_text('USD 0')
    expect(fixture.locator('#exposure-bucket-detail')).to_contain_text('Unavailable')
    fixture.screenshot(path=str(out/'zero-share.png'))
    page.evaluate("document.querySelector('#qa-zero-denominator').remove()")
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#exposure-concentration').screenshot(path=str(out/'concentration-mobile.png'))
    browser.close()
assert not errors and all(sha256(ROOT/p)==h for p,h in before.items())
write_new(out/'receipt.json',{'status':'PASS','scopes':scopes,'zero_denominator_ui_fixture':True,
    'fixture_backend_import_tested':False,'page_errors':errors,'protected_sha256_unchanged':before,
    'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'method_sha256':sha256(Path(__file__)),
    'scope':'Actual source/example inventory UI meter/sort/search/detail per currency and four dimensions; synthetic zero widget exercises unavailable share, not an actual upload.'})
print(out)
