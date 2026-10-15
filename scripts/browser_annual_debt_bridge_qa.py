"""Actual bridge UI/export, scope isolation, outage and loopback boundary."""
import json
from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import sha256

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'artifacts/private' / ('annual-debt-bridge-qa-' + uuid4().hex[:12])
out.mkdir()
ledger = ROOT / 'artifacts/private/retail-holdout-access.sqlite'
before = sha256(ledger)
base = 'http://127.0.0.1:8770/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_asof=2026-10-15&workspace_tab=debt&sec_cik='
errors = []
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1450, 'height': 1050}, accept_downloads=True)
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(base + '0000320193')
    link = page.get_by_role('link', name='Xuất annual debt bridge JSON', exact=True)
    expect(link).to_be_visible(timeout=180000)
    box = page.locator('#sec-annual-debt-bridge')
    expect(box.locator('tbody tr')).to_have_count(2)
    with page.expect_download() as pending:
        link.click()
    path = out / 'apple-annual-debt.json'
    pending.value.save_as(path)
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['status'] == 'VERIFIED_ANNUAL_DEBT_BRIDGE'
    assert data['source']['accession'] == '0000320193-25-000079'
    assert data['first_year_principal_minus_current_carrying_usd_exact'] == '43000000'
    for b in data['bridges']:
        assert int(b['principal_usd_exact']) + int(b['discount_and_costs_usd_exact']) + int(b['hedge_fair_value_adjustment_usd_exact']) == int(b['carrying_usd_exact'])
        assert int(b['current_carrying_usd_exact']) + int(b['noncurrent_carrying_usd_exact']) == int(b['carrying_usd_exact'])
    assert not any(data['qualification'].values())
    box.screenshot(path=str(out / 'bridge-desktop.png'))
    checks.append('Actual Apple UI/download: source identity, two independent integer bridges, 43m basis difference, unqualified actual-payment flags')
    page.get_by_label('SEC debt maturity scope', exact=True).select_option('debt_and_capital_lease')
    expect(box).to_contain_text('Chưa có bảng annual debt gốc', timeout=180000)
    expect(link).to_have_count(0)
    page.reload()
    expect(page.get_by_label('SEC debt maturity scope', exact=True)).to_have_value('debt_and_capital_lease', timeout=180000)
    expect(box).to_contain_text('Chưa có bảng annual debt gốc', timeout=180000)
    page.goto(base + '0000789019')
    expect(box).to_contain_text('Chưa có bảng annual debt gốc', timeout=180000)
    expect(link).to_have_count(0)
    page.goto(base.replace('2026-10-15', '2025-10-30') + '0000320193')
    expect(box).to_contain_text('Chưa có bảng annual debt gốc', timeout=180000)
    expect(link).to_have_count(0)
    checks.append('Family/reload, issuer and pre-filing cutoff never reuse Apple bridge')
    page.goto(base + '0000320193')
    expect(link).to_be_visible(timeout=180000)
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    box.screenshot(path=str(out / 'bridge-mobile.png'))
    page.route('**/api/sec-annual-debt-bridge?**', lambda route: route.fulfill(status=503, content_type='application/json', body='{"error":"QA annual bridge outage"}'))
    page.get_by_label('SEC debt maturity scope', exact=True).select_option('debt_and_capital_lease')
    expect(box).to_contain_text('QA annual bridge outage', timeout=180000)
    expect(link).to_have_count(0)
    expect(page.get_by_role('link', name='Xuất maturity JSON', exact=True)).to_be_visible()
    page.unroute('**/api/sec-annual-debt-bridge?**')
    page.get_by_label('SEC debt maturity scope', exact=True).select_option('debt_only')
    expect(link).to_be_visible(timeout=180000)
    checks.append('Mobile no page overflow; bridge outage removes stale bridge export while maturity export remains; recovery')
    browser.close()
api = 'http://127.0.0.1:8770/api/sec-annual-debt-bridge?view_id=sec-view-b92d9914f1dc&cik=0000320193&asof=2026-10-15&debt_scope=debt_only'
for suffix, headers, code in [('', {'Origin': 'https://invalid.example'}, 403), ('&unexpected=1', {}, 400), ('&cik=0000789019', {}, 400)]:
    try:
        with urlopen(Request(api + suffix, headers=headers), timeout=120):
            raise AssertionError('Invalid request accepted')
    except HTTPError as exc:
        assert exc.code == code
checks.append('Actual HTTP rejects cross-origin, unknown filters and duplicate query fields')
assert not errors and sha256(ledger) == before
(out / 'receipt.json').write_text(json.dumps({'status': 'PASS', 'checks': checks, 'errors': errors,
    'ledger_unchanged': True, 'export_sha256': sha256(path),
    'methods_sha256': {str(p.relative_to(ROOT)): sha256(p) for p in [Path(__file__), ROOT / 'src/credit_atlas/annual_debt_bridge.py', ROOT / 'src/credit_atlas/server.py', ROOT / 'apps/web/app.js']}}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(out)
