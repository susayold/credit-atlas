import json,uuid
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256

root=Path.cwd();out=root/'artifacts/private'/('managed-pool-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';checks=[];errors=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    url=base+'/?view=abs&workspace_tab=managed-pool'
    page.goto(url);expect(page.locator('#managed-pool')).to_contain_text('105',timeout=180000)
    expect(page.locator('#managed-pool')).to_contain_text('publisher duration unspecified')
    expect(page.locator('#managed-pool')).to_contain_text('2026-06-30')
    with page.expect_download() as dl:page.get_by_role('button',name='Xuất Managed pool JSON',exact=True).click()
    dl.value.save_as(out/'export.json')
    with urlopen(base+'/api/managed-pool') as response:
        r=json.load(response);assert json.loads((out/'export.json').read_text())==r
        assert response.headers['Cache-Control']=='no-store'
    assert len(r['periods'])==7 and r['field_count']==30
    rows=page.locator('#managed-pool .atlas-evidence-details').first
    rows.locator('summary').click()
    expect(rows).to_contain_text('14941646.66041')
    expect(rows).to_contain_text('-28736.804530000092')
    expect(rows).to_contain_text('USD_thousands')
    page.locator('#managed-pool').screenshot(path=str(out/'desktop.png'))
    checks.append('7 periods/30 fields/105 checks; raw signed recovery/units visible; API/JSON parity/no-store')
    page.reload();expect(page.locator('#managed-pool')).to_contain_text('105',timeout=180000)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#managed-pool').screenshot(path=str(out/'mobile.png'))
    checks.append('Deep-link reload/mobile; source duration caveat visible')
    page.route('**/api/managed-pool',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled managed outage"}'))
    page.reload();expect(page.locator('#abs-panel-managed-pool')).to_contain_text('Controlled managed outage',timeout=180000)
    assert page.get_by_role('button',name='Xuất Managed pool JSON',exact=True).count()==0
    page.unroute('**/api/managed-pool');page.reload();expect(page.locator('#managed-pool')).to_contain_text('105',timeout=180000)
    checks.append('Outage clears values/export; reload recovery')
    assert not errors and before==sha256(ledger)
    checks.append('No browser errors; frozen ledger unchanged')
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'ledger_unchanged':True},indent=2),encoding='utf8')
print(out);print(checks)
