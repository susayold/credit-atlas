"""Actual six-segment archive API/UI/export, outage and scope checks."""
import json
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import sha256

root = Path.cwd();base = 'http://127.0.0.1:8770';view = 'suite-view-74e07524f6d0'
out = root / 'artifacts/private' / ('sba-archive-browser-' + uuid4().hex[:12]);out.mkdir()
ledger = root / 'artifacts/private/retail-holdout-access.sqlite';before = sha256(ledger)
errors = [];checks = [];expect.set_options(timeout=120000)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1450, 'height':1000}, accept_downloads=True)
    page.on('pageerror', lambda e: errors.append(str(e)))
    response = page.request.get(base + '/api/business-archive?view_id=' + view, timeout=120000)
    assert response.status == 200, response.text()
    report = response.json()
    assert report['records'] == 2174502 and not any(report['qualified'].values())
    assert len(report['segments']) == 6 and report['borrower_rows_included'] is False
    page.goto(base + '/?view=business&workspace_tab=evidence&view_id=' + view)
    box = page.locator('#business-historical-archive')
    link = box.get_by_role('link', name='Xuất SBA historical archive JSON', exact=True)
    expect(link).to_be_visible()
    rows = [r.locator('td').all_text_contents() for r in box.locator('table').nth(0).locator('tbody tr').all()]
    assert rows == [[p['program'],format(p['records'],','),p['amount_scope'],p['amounts']['GrossApproval']['sum_exact'],format(p['amounts']['GrossApproval']['known_records'],',')+' / '+format(p['amounts']['GrossApproval']['blank_records'],','),p['amounts']['GrossChargeOffAmount']['sum_exact']] for p in report['programs']]
    statuses = [r.locator('td').all_text_contents() for r in box.locator('table').nth(1).locator('tbody tr').all()]
    assert statuses == [[p['program'],s['raw'] or 'Missing',format(s['records'],',')] for p in report['programs'] for s in p['source_status_counts']]
    assert box.locator('table').nth(2).locator('tbody tr').count() == 6
    expect(box).to_contain_text('subprogram')
    checks.append('Six actual source segments,program totals,raw statuses and exact decimals match API')
    with page.expect_download() as d: link.click()
    d.value.save_as(out / 'archive.json')
    assert json.loads((out / 'archive.json').read_text()) == report
    checks.append('Download is exact private API report;qualifications remain false')
    box.screenshot(path=str(out / 'desktop.png'))
    page.reload();expect(page.locator('#business-historical-archive a')).to_be_visible()
    page.get_by_role('tab', name='Tổng quan', exact=True).click()
    expect(page.locator('#business-summary')).to_contain_text('2,190,504')
    page.get_by_role('tab', name='Nguồn & giới hạn', exact=True).click()
    expect(page.locator('#business-historical-archive a')).to_be_visible()
    checks.append('Reload/tab navigation retains separate March archive and original June case')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#business-historical-archive').screenshot(path=str(out / 'mobile.png'))
    checks.append('Mobile table containers do not cause page overflow')
    assert page.request.get(base + '/api/business-archive?view_id=' + view + '&program=7A').status == 400
    assert page.request.get(base + '/api/business-archive?view_id=' + view, headers={'Origin':'https://outside.example'}).status == 403
    page.route('**/api/business-archive?*', lambda route: route.fulfill(status=503, content_type='application/json', body='{"error":"QA archive unavailable"}'))
    page.reload();expect(page.locator('#business-panel-evidence')).to_contain_text('QA archive unavailable')
    assert page.locator('#business-historical-archive a').count() == 0
    page.unroute('**/api/business-archive?*')
    page.get_by_role('button', name='Thử lại', exact=True).click()
    expect(page.locator('#business-historical-archive a')).to_be_visible()
    checks.append('Unsupported filters/cross-origin rejected;outage hides report and retry restores verified data')
    browser.close()
assert not errors and sha256(ledger) == before
(out / 'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'page_errors':errors,
    'ledger_unchanged':True,'records':report['records'],'app_js_sha256':sha256(root/'apps/web/app.js'),
    'server_sha256':sha256(root/'src/credit_atlas/server.py'),'method_sha256':sha256(root/'src/credit_atlas/business_archive.py'),
    'report_sha256':sha256(out/'archive.json')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','checks':len(checks)}))
