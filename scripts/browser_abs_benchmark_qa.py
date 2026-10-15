import json,uuid
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

root=Path.cwd();out=root/'artifacts/private'/('abs-benchmark-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';checks=[];errors=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with urlopen(base+'/api/abs-views') as response:view=next(x['view_id'] for x in json.load(response)['views'] if x['status']=='verified')
def api(**query):
    with urlopen(base+'/api/abs-benchmark?'+urlencode({'view_id':view,**query})) as response:
        assert response.headers['Cache-Control']=='no-store';return json.load(response)
all_report=api();assert all_report['summary']['periods']==20 and all_report['summary']['rate_precision_matches']==20
assert all_report['summary']['base_interest_matches']==20
for query in [{'period':'2030-01-31'},{'fixing':'2025-01-27'}]:
    try:api(**query);raise AssertionError('Invalid query accepted')
    except HTTPError as e:assert e.code==400
checks.append('20-period API, scoped guards, precision/interest comparison and no-store')
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1400,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    url=base+'/?view=abs&workspace_tab=benchmark&abs_view_id='+view+'&abs_period=2025-09-30'
    page.goto(url);expect(page.locator('#abs-benchmark')).to_contain_text('4E-18',timeout=180000)
    with page.expect_download() as dl:page.get_by_role('button',name='Xuất SOFR evidence JSON',exact=True).click()
    dl.value.save_as(out/'export.json');assert json.loads((out/'export.json').read_text())==api(period='2025-09-30')
    page.locator('#abs-benchmark').screenshot(path=str(out/'desktop.png'))
    checks.append('Selected period UI/private JSON parity, raw binary delta and current-vintage limitations')
    page.get_by_label('ABS collection period',exact=True).select_option('2025-01-31')
    expect(page.locator('#abs-benchmark')).to_contain_text('2025-01-27',timeout=180000)
    expect(page.locator('#abs-benchmark')).to_contain_text('$285,201.28')
    checks.append('Period switch recomputes initial adjustment date and source-backed interest')
    page.reload();expect(page.locator('#abs-benchmark')).to_contain_text('2025-01-27',timeout=180000)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#abs-benchmark').screenshot(path=str(out/'mobile.png'));checks.append('Deep-link reload and mobile layout')
    page.route('**/api/abs-benchmark?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled benchmark outage"}'))
    page.reload();expect(page.locator('#abs-panel-benchmark')).to_contain_text('Controlled benchmark outage',timeout=180000)
    assert page.get_by_role('button',name='Xuất SOFR evidence JSON',exact=True).count()==0
    page.unroute('**/api/abs-benchmark?**');page.reload();expect(page.locator('#abs-benchmark')).to_contain_text('2025-01-27',timeout=180000)
    checks.append('Outage removes stale values/export; reload recovers')
    assert not errors and before==sha256(ledger);checks.append('No browser errors; frozen holdout ledger unchanged')
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'summary':all_report['summary'],'ledger_unchanged':True},indent=2),encoding='utf-8')
print(out);print(checks)
