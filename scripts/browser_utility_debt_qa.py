"""Utility DSCR scope, source discrepancy, export, URL, mobile and outages."""
import json,uuid
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('utility-debt-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
base='http://127.0.0.1:8770';checks=[];errors=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
expect.set_options(timeout=60000)
url=base+'/?view=sec&workspace_tab=utility-debt&sec_view_id=sec-view-913c93906c18&sec_cik=0000037996&sec_asof=2026-10-11'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url)
    summary=page.locator('#utility-debt-summary')
    expect(summary).to_contain_text('2.51x')
    expect(summary).to_contain_text('209515790')
    expect(summary).to_contain_text('East Bay Municipal Utility District')
    expect(summary).to_contain_text('Unavailable')
    expect(page.locator('#utility-legal')).to_contain_text('1.1x · parity scope')
    expect(page.locator('#utility-legal')).to_contain_text('1.6x · policy, not covenant')
    expect(page.locator('#utility-legal')).to_contain_text('March 31, 2026')
    expect(page.locator('#utility-legal')).to_contain_text('Thirty-Second')
    expect(page.locator('#utility-debt-history tbody tr')).to_have_count(5)
    expect(page.locator('#utility-dscr-driver tbody tr')).to_have_count(4)
    expect(page.locator('#utility-dscr-driver')).to_contain_text('Rational reconciliation residual')
    expect(page.locator('#utility-dscr-driver')).to_contain_text('0 / 1')
    expect(page.get_by_role('img',name='Reported parity and total fiscal-year DSCR')).to_be_visible()
    page.locator('#utility-dscr-driver').screenshot(path=str(out/'desktop-driver.png'))
    with page.expect_download() as dl:page.get_by_role('link',name='Xuất utility DSCR JSON',exact=True).click()
    dl.value.save_as(out/'water-total.json')
    exported=json.loads((out/'water-total.json').read_text())
    assert exported['dscr_driver']['reconciles_exactly'] and exported['dscr_driver']['exact_residual']['numerator']=='0'
    with urlopen(base+'/api/utility-debt-service?edition=2025&year=2025&system=water&basis=total') as response:
        assert json.loads((out/'water-total.json').read_text())==json.load(response)
    checks.append('Water total scope,source input,5-year history and exact API/export parity')
    page.get_by_label('Utility debt basis',exact=True).select_option('parity')
    expect(summary).to_contain_text('2.63x');expect(summary).to_contain_text('200370894')
    page.get_by_label('Utility system',exact=True).select_option('wastewater')
    expect(summary).to_contain_text('78505411')
    expect(page.locator('#utility-legal')).to_contain_text('April 15, 2026')
    expect(page.locator('#utility-legal')).to_contain_text('Twenty-Second')
    page.locator('#utility-legal details').filter(has=page.get_by_text('proposed default caveat · page 279',exact=True)).locator('summary').click()
    expect(page.locator('#utility-legal')).to_contain_text('shall not constitute a default')
    page.get_by_label('Utility fiscal year',exact=True).select_option('2024')
    expect(summary).to_contain_text('72374772')
    expect(page.locator('#utility-debt-checks')).to_contain_text('82.1')
    expect(page.locator('#utility-debt-checks')).to_contain_text('Source difference')
    page.reload();expect(summary).to_contain_text('72374772')
    expect(page.get_by_label('Utility debt basis',exact=True)).to_have_value('parity')
    expect(page.get_by_label('Utility system',exact=True)).to_have_value('wastewater')
    page.locator('#utility-debt-checks').screenshot(path=str(out/'desktop-checks.png'))
    checks.append('Parity scope,system/year filters,retained rounded-source mismatch and URL reload')
    page.get_by_label('Utility edition',exact=True).select_option('2024')
    expect(summary).to_contain_text('wastewater / 2024 / 2024')
    assert page.get_by_label('Utility fiscal year',exact=True).locator('option[value="2025"]').count()==0
    page.get_by_label('Utility fiscal year',exact=True).select_option('2020')
    expect(summary).to_contain_text('wastewater / 2024 / 2020')
    expect(summary).to_contain_text('Unavailable')
    expect(page.locator('#utility-dscr-driver')).to_contain_text('không có năm lịch liền trước')
    assert page.locator('#utility-dscr-driver tbody tr').count()==0
    page.get_by_label('Utility edition',exact=True).select_option('2025')
    expect(summary).to_contain_text('wastewater / 2025 / 2025')
    expect(page.locator('#utility-dscr-driver tbody tr')).to_have_count(4)
    page.locator('#utility-debt-evidence summary').click()
    expect(page.locator('#utility-debt-evidence')).to_contain_text('physical page 19')
    expect(page.locator('#utility-debt-evidence')).to_contain_text('Calculated in accordance with the Indenture')
    checks.append('Edition-specific year bounds/reset and source PDF/page/footnote evidence')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#utility-debt-summary').screenshot(path=str(out/'mobile-summary.png'))
    page.locator('#utility-dscr-driver').screenshot(path=str(out/'mobile-driver.png'))
    checks.append('Mobile exact ratios/source text have no page overflow')
    page.route('**/api/utility-debt-service?**',lambda r:r.fulfill(status=503,content_type='application/json',body='{"error":"Controlled utility outage"}'))
    page.get_by_label('Utility debt basis',exact=True).select_option('total')
    expect(page.locator('#utility-debt')).to_contain_text('Controlled utility outage')
    assert page.locator('#utility-debt-summary').count()==0
    assert page.get_by_role('link',name='Xuất utility DSCR JSON',exact=True).count()==0
    page.unroute('**/api/utility-debt-service?**')
    page.get_by_label('Utility debt basis',exact=True).select_option('parity')
    expect(summary).to_contain_text('78505411')
    checks.append('Outage removes stale results/download and filter change recovers')
    assert not errors,errors
    assert sha256(ledger)==before
    browser.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'browser_errors':errors,'ledger_unchanged':True},indent=2),encoding='utf8')
print(out);print('PASS',len(checks))
