"""Actual issuer period, waterfall, exact-export and responsive UI acceptance."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
from browser_navigation import navigate_workspace, select_task

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new

expect.set_options(timeout=60000)


def run(root):
    output = root / 'artifacts/private' / ('abs-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    identifier = next(row['view_id'] for row in service.abs_views.catalog()['views'] if row['status'] == 'verified')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(60000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            url = base + '/?view=abs&abs_view_id=' + identifier + '&abs_period=2025-01-31'
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#context-note')).to_contain_text('20 kỳ báo cáo · 720 đối chiếu nguồn')
            expect(page.locator('#abs-period-metrics')).to_contain_text('payment 2025-02-18')
            expect(page.locator('#abs-period-metrics')).to_contain_text('$44,964,910.32')
            assert page.locator('#run-select').is_disabled()
            select_task(page, 'Waterfall')
            page.get_by_text('Toàn bộ ledger & allocations', exact=True).click()
            assert page.locator('#abs-ledger tbody tr').count() == 11
            select_task(page, 'Tranches')
            assert page.locator('#abs-tranches tbody tr').count() == 7
            select_task(page, 'Đối chiếu')
            assert page.locator('#abs-source-checks tbody tr').count() == 36
            checks.append('Actual first source period, distinct payment date, 11 priorities, 7 tranches, 36 source comparisons')
            select_task(page, 'Waterfall')
            row = page.locator('#abs-ledger tbody tr').filter(has_text='regular_principal')
            expect(row).to_contain_text('$10,704,708.94')
            expect(row).to_contain_text('$6,321,560.55')
            expect(row).to_contain_text('$4,383,148.39')
            expect(page.locator('#abs-ledger')).to_contain_text('Không cộng chúng thành credit loss')
            checks.append('Actual regular-principal due/paid/unfunded separated; gap is not labelled as credit loss')
            details = page.locator('#abs-allocations details').filter(has_text='second_priority_principal')
            details.locator('summary').click()
            expect(details.locator('tbody tr').first).to_contain_text('A-1')
            expect(details.locator('tbody tr').first).to_contain_text('$17,567,895.22')
            expect(details.locator('tbody tr').nth(5)).to_contain_text('B')
            expect(details.locator('tbody tr').nth(5)).to_contain_text('$0.00')
            checks.append('Second-priority funded principal actually pays A-1, not B; per-stage tranche evidence visible')
            select_task(page, 'Terms & giới hạn')
            expect(page.locator('#abs-qualification')).to_contain_text('Reviewer total fees due')
            assert all(text.strip() == 'NO' for text in page.locator('#abs-qualification tbody td:nth-child(2)').all_text_contents())
            expect(page.locator('#abs-terms')).to_contain_text('4.411%')
            select_task(page, 'Tổng quan')
            assert page.locator('#abs-history svg path').count() == 2
            assert page.locator('#abs-history svg path').evaluate_all('(paths)=>paths.every(p=>getComputedStyle(p).stroke!=="none"&&p.getAttribute("d").length>0)')
            checks.append('Unverified qualifications explicit; both pool/note curves have visible strokes')
            page.screenshot(path=str(output / 'abs-desktop.png'), full_page=True)
            with page.expect_download() as info: page.locator('#export-report').click()
            info.value.save_as(str(output / 'abs-export.json'))
            exported = read_json(output / 'abs-export.json')
            assert exported == service.abs_views.report(identifier, {'period': '2025-01-31'})
            assert exported['public_release_approved'] is False
            assert all(value is False for value in exported['qualification'].values())
            assert str(root) not in json.dumps(exported)
            checks.append('Private exact period export equals reverified source projection, no raw filesystem paths')
            def check_source_download(task, button, filename):
                select_task(page, task)
                with page.expect_download() as info:
                    page.get_by_role('button', name=button, exact=True).click()
                path = output / filename; info.value.save_as(str(path)); report = read_json(path)
                assert report['visibility'] == 'private' and report['public_release_approved'] is False
                assert str(root) not in json.dumps(report)
                checks.append(task + ' specialized source export is valid private JSON without raw local paths')
            check_source_download('ABS-EE coverage', 'Xuất ABS-EE coverage JSON', 'absee-profile-export.json')
            check_source_download('Định nghĩa ABS-EE', 'Xuất ABS-EE dictionary JSON', 'absee-dictionary-export.json')
            check_source_download('Managed pool', 'Xuất Managed pool JSON', 'managed-pool-export.json')
            check_source_download('Static pool', 'Xuất static pool JSON', 'static-pool-export.json')
            check_source_download('SOFR nguồn', 'Xuất SOFR evidence JSON', 'abs-benchmark-export.json')
            failed_downloads = []; error_page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            error_page.set_default_timeout(60000); error_page.on('pageerror', lambda error: errors.append(str(error)))
            error_page.on('download', lambda download: failed_downloads.append(download.suggested_filename))
            error_exports = [
                ('absee-profile', 'ABS-EE coverage', 'Xuất ABS-EE coverage JSON', '**/api/absee-profile-report*'),
                ('absee-dictionary', 'Định nghĩa ABS-EE', 'Xuất ABS-EE dictionary JSON', '**/api/absee-dictionary-report*'),
                ('managed-pool', 'Managed pool', 'Xuất Managed pool JSON', '**/api/managed-pool-report*'),
                ('pool-history', 'Static pool', 'Xuất static pool JSON', '**/api/pool-history-report*'),
                ('benchmark', 'SOFR nguồn', 'Xuất SOFR evidence JSON', '**/api/abs-benchmark-report*'),
            ]
            for tab, task, button, pattern in error_exports:
                error_page.goto(base + '/?view=abs&abs_view_id=' + identifier + '&abs_period=2025-01-31&workspace_tab=' + tab, wait_until='networkidle')
                expect(error_page.get_by_role('button', name=button, exact=True)).to_be_visible()
                error_page.route(pattern, lambda route: route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'Synthetic ABS source attachment outage'})))
                error_page.get_by_role('button', name=button, exact=True).click()
                expect(error_page.locator('#notice.error')).to_contain_text('Synthetic ABS source attachment outage')
                assert failed_downloads == []
                error_page.unroute(pattern)
                checks.append(task + ' HTTP 503 is visible and creates no fake source attachment')
            error_page.close()
            select_task(page, 'Tổng quan')
            page.get_by_label('ABS collection period').select_option('2025-12-31')
            expect(page.locator('#abs-period-metrics')).to_contain_text('payment 2026-01-15')
            expect(page.locator('#export-report')).to_be_enabled()
            with page.expect_download() as info: page.locator('#export-report').click()
            info.value.save_as(str(output / 'abs-year-boundary-export.json'))
            boundary = read_json(output / 'abs-year-boundary-export.json')
            assert boundary['period']['inputs']['reviewer_ytd_year'] == 2026
            checks.append('Collection/payment year boundary uses payment calendar year for reviewer YTD')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('ABS collection period')).to_have_value('2025-12-31')
            expect(page.locator('#abs-period-metrics')).to_contain_text('payment 2026-01-15')
            checks.append('ABS snapshot and selected collection period survive URL reload')
            page.get_by_label('ABS collection period').select_option('2026-08-31')
            expect(page.locator('#abs-period-metrics')).to_contain_text('Kỳ 2026-08-31')
            expected = service.abs_views.report(identifier, {'period': '2026-08-31'})
            select_task(page, 'Tranches')
            expect(page.locator('#abs-tranches tbody tr').first).to_contain_text('$0.00')
            assert expected['tranches'][0]['ending_balance'] == '0.00'
            checks.append('Later observed period with A-1 paid off, without extrapolated future periods')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'abs-mobile.png'), full_page=True)
            checks.append('390px mobile without page overflow; wide financial tables scroll within their cards')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate_workspace(page, 'market')
            expect(page.locator('#page-title')).to_have_text('Market Context & Bond Scenario Lab')
            navigate_workspace(page, 'sec'); expect(page.locator('#sec-statement')).to_contain_text('AAPL')
            navigate_workspace(page, 'overview'); expect(page.locator('.metric-value').first).to_have_text('50,000')
            checks.append('P5 market/P3 issuer/P2 mortgage navigation remains operational')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto(url + '&workspace_tab=waterfall', wait_until='networkidle')
            page.get_by_text('Toàn bộ ledger & allocations', exact=True).click()
            expect(page.locator('#abs-ledger')).to_contain_text('regular_principal')
            checks.append('ABS source workflow independent of mortgage run availability')
            assert not errors, errors; checks.append('No JavaScript/console errors')
            browser.close()
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(), 'view_id': identifier,
            'checks': checks, 'browser_errors': errors, 'methods': {name: sha256(root / name)
                for name in ('apps/web/app.js', 'apps/web/style.css', 'src/credit_atlas/abs_views.py', 'src/credit_atlas/server.py')},
            'visibility': 'private', 'public_release_approved': False})
        return {'status': 'PASS', 'checks': len(checks), 'directory': str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status': 'FAIL', 'exception_type': type(error).__name__,
            'checks_completed': checks, 'browser_errors': errors})
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    print(json.dumps(run(app_root()), indent=2))
