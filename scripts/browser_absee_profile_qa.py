import json,uuid
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('absee-profile-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';errors=[];checks=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/?view=abs&workspace_tab=absee-profile')
    expect(page.locator('#absee-profile')).to_contain_text('488,219',timeout=180000)
    expect(page.locator('#absee-profile')).to_contain_text('giá trị chưa đối chiếu XML gốc')
    with page.expect_download() as dl:page.get_by_role('button',name='Xuất ABS-EE coverage JSON',exact=True).click()
    dl.value.save_as(out/'export.json')
    with urlopen(base+'/api/absee-profile') as response:
        r=json.load(response);assert json.loads((out/'export.json').read_text())==r
        assert response.headers['Cache-Control']=='no-store'
    assert r['model_ready'] is False and r['source_value_fidelity_verified'] is False
    d=page.locator('#absee-profile details').first;d.locator('summary').click()
    expect(d).to_contain_text('assetNumber');expect(d).to_contain_text('currentDelinquencyStatus')
    page.locator('#absee-profile').screenshot(path=str(out/'desktop.png'))
    checks.append('Coverage/qualification/raw schema visible, API/export parity, no-store')
    page.reload();expect(page.locator('#absee-profile')).to_contain_text('488,219',timeout=180000)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#absee-profile').screenshot(path=str(out/'mobile.png'))
    checks.append('Reload/mobile, gaps preserved')
    page.route('**/api/absee-profile',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled mirror outage"}'))
    page.reload();expect(page.locator('#abs-panel-absee-profile')).to_contain_text('Controlled mirror outage',timeout=180000)
    assert page.get_by_role('button',name='Xuất ABS-EE coverage JSON',exact=True).count()==0
    page.unroute('**/api/absee-profile');page.reload();expect(page.locator('#absee-profile')).to_contain_text('488,219',timeout=180000)
    checks.append('Source outage clears values/export; reload recovery')
    assert not errors and before==sha256(ledger);checks.append('No browser errors; frozen ledger unchanged')
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'ledger_unchanged':True},indent=2),encoding='utf8')
print(out)
