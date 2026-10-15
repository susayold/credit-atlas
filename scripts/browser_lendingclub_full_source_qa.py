import json,uuid
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('lendingclub-full-source-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';checks=[];errors=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
expect.set_options(timeout=60000)
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/?view=retail&workspace_tab=lendingclub-full&view_id=suite-view-74e07524f6d0')
    summary=page.locator('#lendingclub-full-summary');expect(summary).to_contain_text('2260701');expect(summary).to_contain_text('2260668')
    expect(summary).to_contain_text('funded month');expect(summary).to_contain_text('Unavailable')
    expect(page.locator('#lendingclub-temporal')).to_contain_text('1519965')
    expect(page.locator('#lendingclub-temporal')).to_contain_text('2019-03')
    expect(page.locator('#lendingclub-temporal')).to_contain_text('2019-04')
    expect(page.locator('#lendingclub-temporal')).to_contain_text('2019-05')
    expect(page.locator('#lendingclub-temporal')).to_contain_text('PD12 labels / maturity qualification')
    page.locator('#lendingclub-temporal').screenshot(path=str(out/'desktop-temporal.png'))
    expect(page.locator('#lendingclub-full-quality tbody tr')).to_have_count(151)
    with page.expect_download() as dl:page.get_by_role('link',name='Xuất full LendingClub JSON',exact=True).click()
    dl.value.save_as(out/'accepted.json')
    with urlopen(base+'/api/lendingclub-full-source?kind=accepted&from=2007-06&to=2018-12&category=all') as response:assert json.loads((out/'accepted.json').read_text())==json.load(response)
    checks.append('Accepted raw/dated records,151quality rows,unqualified rate/PD and exact API/export parity')
    page.get_by_label('Full LendingClub category',exact=True).select_option('Current')
    expect(summary).to_contain_text('878317')
    page.get_by_label('Full LendingClub category',exact=True).select_option('__missing__')
    expect(summary).to_contain_text('Selected dated records0')
    assert page.locator('#lendingclub-full-cohorts tbody tr').count()==0
    page.get_by_label('Full LendingClub source',exact=True).select_option('rejected')
    page.get_by_label('Full LendingClub from',exact=True).fill('2007-05');page.get_by_label('Full LendingClub from',exact=True).dispatch_event('change')
    expect(summary).to_contain_text('27648741');expect(summary).to_contain_text('application day')
    expect(page.locator('#lendingclub-temporal')).to_contain_text('does not apply to rejected applications')
    assert page.locator('#lendingclub-temporal tbody tr').count()==0
    expect(page.locator('#lendingclub-full-quality tbody tr')).to_have_count(9)
    expect(page.locator('#lendingclub-full-quality')).to_contain_text('18497630')
    expect(page.get_by_label('Full LendingClub category',exact=True)).to_have_value('all')
    assert page.get_by_label('Full LendingClub category',exact=True).locator('option[value="Current"]').count()==0
    page.get_by_label('Full LendingClub category',exact=True).select_option('2.0');expect(summary).to_contain_text('88129')
    page.reload();expect(summary).to_contain_text('88129');expect(page.get_by_label('Full LendingClub source',exact=True)).to_have_value('rejected')
    page.locator('#lendingclub-full-summary').screenshot(path=str(out/'desktop-summary.png'))
    checks.append('Current/missing dated scopes,rejected grain/score missingness,category reset and URL reload')
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#lendingclub-full-summary').screenshot(path=str(out/'mobile-summary.png'))
    checks.append('Mobile scope/missing controls fit page')
    page.route('**/api/lendingclub-full-source?**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Controlled full-source outage"}'))
    page.get_by_label('Full LendingClub category',exact=True).select_option('all')
    expect(page.locator('#lendingclub-full-source')).to_contain_text('Controlled full-source outage')
    assert page.locator('#lendingclub-full-summary').count()==0
    assert page.get_by_role('link',name='Xuất full LendingClub JSON',exact=True).count()==0
    page.unroute('**/api/lendingclub-full-source?**');page.get_by_label('Full LendingClub category',exact=True).select_option('2.0')
    expect(summary).to_contain_text('88129')
    checks.append('Outage clears stale results/export and filter change recovers')
    assert not errors,errors;assert sha256(ledger)==before;b.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'browser_errors':errors,'ledger_unchanged':True},indent=2),encoding='utf8');print(out);print('PASS',len(checks))
