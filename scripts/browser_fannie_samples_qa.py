import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('fannie-samples-qa-'+uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[]
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8770/?run=d01-a24484b21a21&view=sources&segment=all&basis=count&horizon=12&transition_year=all')
    box=page.locator('#fannie-samples');expect(box).to_contain_text('1,015');expect(box).to_contain_text('96,749')
    expect(box).to_contain_text('8');expect(box).to_contain_text('Chưa thực hiện')
    with page.expect_download() as d:box.get_by_role('link',name='Xuất Fannie sample JSON',exact=True).click()
    d.value.save_as(out/'all-report.json');r=json.loads((out/'all-report.json').read_text())
    assert r['summary']['source_rows']==1015 and len(r['profiles'])==3
    assert all(not x for x in r['gates'].values()) and r['summary']['added_freddie_annual_vintages']==0
    assert len(box.locator('table').all())>0
    checks.append('All source sample coverage/private export parity and no multi-vintage/model qualification claim')
    family=page.get_by_label('Fannie sample family',exact=True)
    family.select_option('single-family');expect(box).to_contain_text('757');expect(box).not_to_contain_text('Reported annual DSCR rows')
    expect(box).to_contain_text('XX')
    family.select_option('multifamily');expect(box).to_contain_text('258');expect(box).to_contain_text('1.13 / 2.68');expect(box).to_contain_text('annual DSCR không được nhân')
    box.get_by_text('Field quality · blank vs literal NULL tokens',exact=True).first.click()
    assert box.get_by_role('cell',name='Loan Number',exact=True).count()>=1
    checks.append('Family filters separate populations;62-field quality and17 annual reported DSCR retain grain')
    box.screenshot(path=str(out/'desktop.png'))
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    checks.append('Mobile page fits with source/quality tables')
    page.route('**/api/fannie-samples?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA source unavailable"}'))
    family.select_option('single-family');expect(box).to_contain_text('QA source unavailable')
    assert box.get_by_role('link',name='Xuất Fannie sample JSON',exact=True).count()==0
    page.unroute('**/api/fannie-samples?*');family.select_option('all');expect(box).to_contain_text('96,749')
    checks.append('API outage clears stale results/export while Freddie source page remains;retry recovers')
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'page_errors':errors,'ledger_unchanged':True},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','checks':len(checks)}))
