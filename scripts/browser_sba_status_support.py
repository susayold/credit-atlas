"""Check selected status drill-down and source-program/bucket denominators."""
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import read_json, sha256, write_new

root = Path.cwd();base = 'http://127.0.0.1:8770';view = 'suite-view-74e07524f6d0'
source = root/'artifacts/private/business-sba-21c568f10f7d/aggregates.json'
marts = read_json(source)['dimensions'];out = root/'artifacts/private'/('sba-status-support-browser-'+uuid4().hex[:12]);out.mkdir()
errors = [];ledger = root/'artifacts/private/retail-holdout-access.sqlite';before = sha256(ledger)
expect.set_options(timeout=120000);shares = 0
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge',headless=True)
    page = browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/?view=business&workspace_tab=overview&view_id='+view)
    button = page.locator('#business-status-explorer .business-status-row').first
    expect(button).to_be_visible();button.click()
    detail = page.locator('.business-selected-cell');expect(detail).to_be_visible()
    selected = max(marts['program_status'],key=lambda r:r['records'])
    expect(detail).to_contain_text(selected['program']+' · '+selected['status'])
    expect(detail).to_contain_text(format(selected['records'],','))
    expect(page.get_by_label('SBA program',exact=True)).to_have_value(selected['program'])
    expect(page.get_by_label('SBA dimension',exact=True)).to_have_value('program_status')
    detail.screenshot(path=str(out/'selected-status.png'))
    for dimension in ['program_status','project_state','naics_two_digit','approval_fiscal_year']:
        page.get_by_label('SBA dimension',exact=True).select_option(dimension)
        assert page.locator('.business-selected-cell').count() == 0
        for program in ['7A','504']:
            page.get_by_label('SBA program',exact=True).select_option(program)
            rows = [r for r in marts[dimension] if r['program'] == program]
            totals = {}
            for r in rows:totals[r['bucket']] = totals.get(r['bucket'],0) + r['records']
            actual = [r.locator('td').all_text_contents() for r in page.locator('#business-panel-cohorts table tbody tr').all()]
            assert len(actual) == len(rows)
            for a,r in zip(actual,rows):
                share = (Decimal(r['records']) * 100 / Decimal(totals[r['bucket']])).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
                assert a[:4] == [r['program'],r['bucket'],r['status'],format(r['records'],',')]
                assert a[4] == str(share)+'%'
                shares += 1
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.screenshot(path=str(out/'cohorts-mobile.png'));browser.close()
assert not errors and sha256(ledger) == before
write_new(out/'receipt.json',{'status':'PASS','snapshot_share_cells_checked':shares,
    'program_dimension_scopes':8,'selected_status_drilldown':True,'filter_change_clears_detail':True,
    'mobile':True,'ledger_unchanged':True,'page_errors':errors,'source_sha256':sha256(source),
    'app_js_sha256':sha256(root/'apps/web/app.js'),'server_sha256':sha256(root/'src/credit_atlas/server.py'),
    'method_sha256':sha256(Path(__file__))})
print(out)
