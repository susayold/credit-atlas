import json,uuid
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('absee-dictionary-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';errors=[];checks=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/?view=abs&workspace_tab=absee-dictionary')
    panel=page.locator('#absee-dictionary')
    expect(panel).to_contain_text('62 / 62 trường',timeout=180000)
    expect(panel).to_contain_text('chưa xác minh XSD/giá trị mirror')
    search=page.get_by_role('searchbox',name='Tìm trường ABS-EE')
    search.fill('currentDelinquencyStatus');expect(panel).to_contain_text('1 / 62 trường')
    panel.locator('details summary').click();expect(panel).to_contain_text('number of days')
    expect(panel).to_contain_text('3(f)(25)')
    panel.screenshot(path=str(out/'desktop.png'))
    checks.append('Dictionary62fields, search/expanded source definition, edition and qualification visible')
    with page.expect_download() as dl:page.get_by_role('button',name='Xuất ABS-EE dictionary JSON',exact=True).click()
    dl.value.save_as(out/'export.json')
    with urlopen(base+'/api/absee-dictionary') as response:
        r=json.load(response);assert json.loads((out/'export.json').read_text())==r
        assert response.headers['Cache-Control']=='no-store'
    assert r['observed_fields']==62
    assert all(r[k] is False for k in ['xsd_verified','mirror_fidelity_verified','model_ready','raw_filing_xml_acquired','current_rule_verified'])
    for x in r['fields']:
        assert x['mapping_status']=='ANALYST_PROPOSED_CORRESPONDENCE_NOT_XSD_VERIFIED'
        assert x['source_url'].startswith('https://www.govinfo.gov/')
    checks.append('Scoped export/API62field parity, no-store and all gates remain false')
    search.fill('zeroBalanceCode');expect(panel).to_contain_text('1 / 62 trường')
    panel.locator('details summary').click();expect(panel).to_contain_text('Periods without column')
    search.fill('no-such-field');expect(panel).to_contain_text('0 / 62 trường')
    page.reload();expect(panel).to_contain_text('62 / 62 trường',timeout=180000)
    search.fill('reportingPeriodBeginningLoanBalanceAmount')
    panel.locator('details summary').click()
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    panel.screenshot(path=str(out/'mobile.png'))
    checks.append('Missing schema coverage, empty search, reload and long field name mobile layout')
    page.route('**/api/absee-dictionary',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled definition outage"}'))
    page.reload();expect(page.locator('#abs-panel-absee-dictionary')).to_contain_text('Controlled definition outage',timeout=180000)
    assert page.get_by_role('button',name='Xuất ABS-EE dictionary JSON',exact=True).count()==0
    page.unroute('**/api/absee-dictionary');page.get_by_role('button',name='Thử lại',exact=True).click()
    expect(panel).to_contain_text('62 / 62 trường',timeout=30000)
    checks.append('Outage clears stale definition/export and explicit retry recovers')
    try:urlopen(base+'/api/absee-dictionary?default_code=3');raise AssertionError('Unexpected filter accepted')
    except HTTPError as e:assert e.code==400
    assert not errors and before==sha256(ledger);checks.append('Unexpected filter rejected; no browser errors; frozen ledger unchanged')
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'ledger_unchanged':True},indent=2),encoding='utf8')
print(out)
