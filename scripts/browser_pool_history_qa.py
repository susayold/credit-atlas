import json,uuid
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

root=Path.cwd();out=root/'artifacts/private'/('pool-history-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';checks=[];errors=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    url=base+'/?view=abs&workspace_tab=pool-history&pool_metric=loss&pool_deal=WOART+2025-A'
    page.goto(url);expect(page.locator('#pool-history')).to_contain_text('1,998',timeout=180000)
    expect(page.locator('#pool-history')).to_contain_text('1,362')
    with page.expect_download() as dl:page.get_by_role('button',name='Xuất static pool JSON',exact=True).click()
    dl.value.save_as(out/'export.json')
    with urlopen(base+'/api/pool-history?'+urlencode({'metric':'loss','deal':'WOART 2025-A'})) as response:
        assert json.loads((out/'export.json').read_text())==json.load(response)
        assert response.headers['Cache-Control']=='no-store'
    page.locator('#pool-history').screenshot(path=str(out/'desktop.png'))
    checks.append('21 cohorts/1998 populated/1362 missing cells in UI, scoped API/JSON parity')
    page.get_by_label('Static pool metric',exact=True).select_option('delinquency')
    expect(page.locator('#pool-history')).to_contain_text('61+ day delinquency share',timeout=180000)
    page.get_by_label('Static pool deal',exact=True).select_option('WOART 2026-B')
    expect(page.locator('#pool-history')).to_contain_text('WOART 2026-B · 61+',timeout=180000)
    page.reload();expect(page.locator('#pool-history')).to_contain_text('WOART 2026-B · 61+',timeout=180000)
    assert page.get_by_label('Static pool metric',exact=True).input_value()=='delinquency'
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#pool-history').screenshot(path=str(out/'mobile.png'))
    checks.append('Metric/cohort switch, URL reload and mobile preserve filters without source blank fill')
    page.route('**/api/pool-history?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled pool outage"}'))
    page.reload();expect(page.locator('#abs-panel-pool-history')).to_contain_text('Controlled pool outage',timeout=180000)
    assert page.get_by_role('button',name='Xuất static pool JSON',exact=True).count()==0
    page.unroute('**/api/pool-history?**');page.reload();expect(page.locator('#pool-history')).to_contain_text('WOART 2026-B · 61+',timeout=180000)
    checks.append('Source outage clears values/export; reload recovers')
    assert not errors and before==sha256(ledger);checks.append('No browser errors; frozen holdout ledger unchanged')
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'ledger_unchanged':True},indent=2),encoding='utf8')
print(out);print(checks)
