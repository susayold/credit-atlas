"""Verify the redesigned MVP against live local source-backed workspaces."""
import json
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import app_root, timestamp, write_new, sha256


def run():
    root = app_root()
    out = root / 'artifacts/private' / ('mvp-ux-qa-' + uuid.uuid4().hex[:12])
    out.mkdir()
    checks, errors = [], []
    ledger = root / 'artifacts/private/retail-holdout-access.sqlite'
    before = sha256(ledger)
    base = 'http://127.0.0.1:8770'
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text+' '+m.location.get('url','')) if m.type == 'error' else None)
        failed_requests = []
        page.on('requestfailed', lambda request: failed_requests.append({'url':request.url,'failure':request.failure}))
        page.goto(base+'/?view=suite', wait_until='domcontentloaded')
        expect(page.locator('.workspace-card')).to_have_count(5, timeout=180000)
        expect(page.locator('.workspace-row-art')).to_have_count(9)
        page.locator('.workspace-row-art').evaluate_all('(images)=>images.forEach(i=>i.loading="eager")')
        page.wait_for_function('()=>Array.from(document.querySelectorAll(".workspace-row-art")).every(i=>i.complete&&i.naturalWidth>1000)')
        assert page.locator('.workspace-card').evaluate_all('(rows)=>rows.every((r,i)=>r.getBoundingClientRect().width>=r.parentElement.clientWidth-2&&(i===0||r.getBoundingClientRect().top>=rows[i-1].getBoundingClientRect().bottom))')
        assert page.locator('.home-task-card').evaluate_all('(rows)=>rows.every((r,i)=>r.getBoundingClientRect().width>=r.parentElement.clientWidth-2&&(i===0||r.getBoundingClientRect().top>=rows[i-1].getBoundingClientRect().bottom))')
        assert 'view=suite' in page.url
        assert page.locator('.workspace-card').evaluate_all('(a)=>new Set(a.map(x=>x.href)).size') == 5
        checks.append('Workspace catalog: five photographic workspace rows and four task rows, each full-width on a separate line; nine real background images and five distinct routes')
        page.screenshot(path=str(out / 'home-desktop.png'), full_page=True)
        page.locator('.atlas-evidence-details summary').click()
        page.get_by_label('Lọc source theo workspace').select_option('P3')
        assert page.locator('#content tbody tr').count() == 14
        checks.append('Source catalog filter preserves actual P3 evidence and module denominators')
        page.locator('[data-home-task="exposure-excel"]').click()
        expect(page.locator('#exposure-excel')).to_be_visible(timeout=180000)
        expect(page.get_by_role('tab',name='Excel',exact=True)).to_have_attribute('aria-selected','true',timeout=180000)
        assert 'workspace_tab=excel' in page.url and 'exposure-import-57b88e00bedb' in page.url
        page.goto(base+'/?view=suite',wait_until='domcontentloaded')
        expect(page.locator('.workspace-card')).to_have_count(5,timeout=180000)
        expect(page.locator('.home-task-card')).to_have_count(4)
        checks.append('Homepage task launcher opens exact Excel/source directly, with four real task entries')
        for domain, view, marker in (
            ('P4', 'exposure', '#exposure-summary'),
            ('P3', 'business', '#business-summary'),
            ('P2', 'overview', '.hero-card'),
            ('P5', 'abs', '#abs-period-metrics'),
            ('P1', 'retail', '#retail-model-summary'),
        ):
            page.locator('[data-view="suite"]').click()
            expect(page.locator('.workspace-card')).to_have_count(5, timeout=180000)
            page.locator('[data-workspace="' + domain + '"]').click()
            expect(page.locator(marker).first).to_be_visible(timeout=240000)
            assert ('view=' + view) in page.url
            assert page.locator('[data-view="' + view + '"]').get_attribute('aria-current') == 'page'
            assert page.locator('[data-view="' + view + '"]').evaluate('(n)=>n.closest("details").open')
            if domain == 'P4':
                expect(page.locator('#exposure-summary')).to_contain_text('9,698')
                expect(page.locator('#exposure-summary')).to_contain_text('915,208,989.12')
                assert 'exposure-import-57b88e00bedb' in page.url
                page.screenshot(path=str(out / 'portfolio-desktop.png'), full_page=False)
                page.get_by_role('tab',name='Excel',exact=True).click()
                expect(page.locator('#exposure-excel')).to_be_visible()
                page.get_by_role('tab',name='Nguồn & contract',exact=True).click()
                expect(page.locator('#exposure-currencies')).to_contain_text('915,208,989.12')
                page.get_by_role('tab',name='Tổng quan',exact=True).click()
            if domain == 'P1':
                expect(page.locator('#retail-model-summary')).to_contain_text('3,001')
                page.screenshot(path=str(out / 'retail-desktop.png'), full_page=False)
            checks.append(domain + ': launchpad opens actual data workspace, selected route and grouped navigation')
            print('Verified ' + domain, flush=True)
        page.locator('[data-view="suite"]').click()
        expect(page.locator('.workspace-card')).to_have_count(5, timeout=180000)
        assert not page.locator('.atlas-evidence-details').get_attribute('open')
        page.set_viewport_size({'width': 390, 'height': 844})
        assert not page.locator('#navigation').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out / 'home-mobile.png'), full_page=True)
        page.screenshot(path=str(out / 'home-mobile-viewport.png'))
        page.get_by_role('button', name='Mở menu workspace').click()
        expect(page.locator('#navigation')).to_be_visible()
        assert page.locator('#menu-toggle').get_attribute('aria-expanded') == 'true'
        page.locator('.nav-group summary').filter(has_text='P4 / PORTFOLIO').click()
        page.locator('[data-view="exposure"]').click()
        expect(page.locator('#exposure-summary')).to_be_visible(timeout=180000)
        assert not page.locator('#navigation').is_visible()
        assert page.locator('#menu-toggle').get_attribute('aria-expanded') == 'false'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out / 'portfolio-mobile.png'), full_page=True)
        page.get_by_role('tab',name='Excel',exact=True).click()
        expect(page.locator('#exposure-excel')).to_be_visible()
        checks.append('390px mobile: no page overflow, menu expands and route selection closes it; Excel remains accessible')
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('#exposure-excel')).to_be_visible(timeout=180000)
        assert 'view=exposure' in page.url
        checks.append('Selected Portfolio route survives reload')
        page.get_by_role('button',name='Tìm chức năng',exact=True).click()
        expect(page.locator('#command-dialog')).to_be_visible()
        page.get_by_label('Tìm workspace hoặc tác vụ').fill('NO_SUCH_TASK_999')
        expect(page.locator('#command-results')).to_contain_text('Không có tác vụ phù hợp')
        page.keyboard.press('Escape')
        expect(page.locator('#command-dialog')).not_to_be_visible()
        page.keyboard.press('Control+k')
        page.get_by_label('Tìm workspace hoặc tác vụ').fill('So sánh model validation')
        page.keyboard.press('Enter')
        expect(page.locator('#retail-panel-validation')).to_contain_text('Paired validation uncertainty',timeout=180000)
        assert 'view=retail' in page.url and 'workspace_tab=validation' in page.url
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        checks.append('Mobile global task search: empty state, Escape, CtrlK and Enter route to actual Retail validation')
        page.set_viewport_size({'width':1440,'height':1000})
        page.goto(base+'/?view=market&workspace_tab=bond',wait_until='domcontentloaded')
        expect(page.locator('#market-panel-bond')).to_contain_text('Price per 100 face',timeout=180000)
        expect(page.locator('#market-panel-bond')).to_contain_text('100.000000')
        page.get_by_role('tab',name='Market context',exact=True).click()
        expect(page.locator('#market-panel-series svg')).to_be_visible()
        page.get_by_role('tab',name='Nguồn & limits',exact=True).click()
        expect(page.locator('#market-panel-evidence')).to_contain_text('Source & use limits')
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('#market-panel-evidence')).to_be_visible(timeout=180000)
        checks.append('Market native-series/bond/source tasks: assumed par bond, actual chart and exact task reload')
        assert sha256(ledger) == before
        if errors:
            write_new(out/'failed.json',{'status':'FAIL','browser_errors':errors,'failed_requests':failed_requests,'checks_completed':checks})
        assert not errors, errors
        checks.append('No unexpected browser errors; consumed holdout ledger unchanged')
        context.close()
        browser.close()
    receipt = {'status': 'PASS', 'completed_at': timestamp(), 'checks': checks,
               'browser_errors': errors, 'holdout_ledger_unchanged': True,
               'visibility': 'private', 'public_release_approved': False}
    write_new(out / 'receipt.json', receipt)
    print(json.dumps({'status': 'PASS', 'checks': len(checks), 'directory': str(out)}, indent=2))


if __name__ == '__main__':
    run()
