"""Actual filing/context/ambiguity/export UI checks for SEC source data."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
from browser_navigation import navigate_workspace, select_task

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, read_json, timestamp, write_new

expect.set_options(timeout=60000)


def run(root):
    output = root / 'artifacts/private' / ('sec-browser-qa-' + uuid.uuid4().hex[:12]); output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    identifier = next(row['view_id'] for row in service.sec_views.catalog()['views'] if row['status'] == 'verified')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}); page.set_default_timeout(60000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            url = base + '/?view=sec&sec_view_id=' + identifier + '&sec_asof=2026-10-09'
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#context-note')).to_contain_text('105,441 source fact entries · 13,374 filings · 67 annual research statements')
            expect(page.locator('#sec-statement')).to_contain_text('AAPL')
            expect(page.locator('#sec-statement')).to_contain_text('2025-09-27')
            expect(page.locator('#sec-ratios .metric-value').first).to_have_text('0.8933')
            assert page.locator('#run-select').is_disabled()
            checks.append('Actual SEC source counts, AAPL filing-specific period and current ratio, P2 controls isolated')
            page.screenshot(path=str(output / 'sec-desktop.png'), full_page=True)
            page.get_by_label('SEC filing-date cutoff').fill('2020-01-01')
            page.get_by_role('button', name='Đọc filing evidence').click()
            expect(page.locator('#sec-statement')).to_contain_text('2019-09-28')
            expected = service.sec_views.report(identifier, {'asof': '2020-01-01'})
            with page.expect_download() as info:
                page.locator('#export-report').click()
            info.value.save_as(str(output / 'sec-export.json'))
            report = read_json(output / 'sec-export.json')
            assert report == expected and report['statement']['filing_date'] <= '2020-01-01'
            assert all(row['filing_date'] <= '2020-01-01' for row in report['annual_options'])
            assert not report['historical_availability_qualified'] and not report['public_release_approved']
            checks.append('Cutoff excludes later filings; exact private report equals canonical evidence, no PIT claim')
            page.get_by_label('SEC filing-date cutoff').fill('1990-01-01')
            page.get_by_role('button', name='Đọc filing evidence').click()
            expect(page.locator('#content')).to_contain_text('Không có annual statement được hỗ trợ')
            assert page.locator('#sec-statement').count() == 0
            checks.append('No eligible source statement before cutoff; no future fallback')
            page.get_by_label('SEC filing-date cutoff').fill('2026-10-09')
            page.get_by_label('SEC issuer').select_option('0000037996')
            page.get_by_role('button', name='Đọc filing evidence').click()
            expect(page.locator('#sec-statement')).to_contain_text('FORD')
            select_task(page, 'Financial statements')
            expect(page.locator('#sec-financial-fields')).to_contain_text('missing')
            select_task(page, 'Issuer overview')
            expect(page.locator('#sec-ratios .metric-value').nth(2)).to_have_text('Unavailable')
            checks.append('Actual Ford unsupported net-income tag stays missing and margin unavailable')
            page.get_by_label('SEC issuer').select_option('0001467858')
            page.get_by_role('button', name='Đọc filing evidence').click()
            expect(page.locator('#sec-statement')).to_contain_text('General Motors')
            select_task(page, 'Financial statements')
            expect(page.locator('#sec-financial-fields')).to_contain_text('ambiguous')
            select_task(page, 'Issuer overview')
            expect(page.locator('#sec-ratios .metric-value').nth(2)).to_have_text('Unavailable')
            select_task(page, 'Concept evidence')
            page.get_by_text('revenue · ambiguous', exact=False).click()
            with page.expect_download() as info:
                page.locator('#export-report').click()
            info.value.save_as(str(output / 'gm-export.json'))
            gm = read_json(output / 'gm-export.json')
            assert gm['statement']['fields']['revenue']['status'] == 'ambiguous'
            assert len({row['value_exact'] for row in gm['statement']['fields']['revenue']['evidence']}) > 1
            assert gm['statement']['ratios']['net_income_margin']['value_exact'] is None
            checks.append('Actual GM revenue conflicts preserved; no silent alias choice or ratio')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('SEC issuer')).to_have_value('0001467858')
            expect(page.get_by_label('SEC annual filing')).to_have_value(gm['statement']['accession'])
            expect(page.get_by_role('tab',name='Concept evidence',exact=True)).to_have_attribute('aria-selected','true')
            select_task(page, 'Issuer overview')
            expect(page.locator('#sec-statement')).to_contain_text('General Motors')
            checks.append('Issuer/accession/cutoff/snapshot survive URL reload')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'sec-mobile.png'), full_page=True)
            checks.append('390px mobile without page overflow')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate_workspace(page, 'country'); expect(page.locator('#context-note')).to_contain_text('122,892')
            navigate_workspace(page, 'bankruptcymodel'); expect(page.locator('#bankruptcy-model-final')).to_contain_text('591 statements')
            navigate_workspace(page, 'overview'); expect(page.locator('.metric-value').first).to_have_text('50,000')
            checks.append('Independent P4 country/P3 bankruptcy/P2 navigation')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto(url, wait_until='networkidle'); expect(page.locator('#sec-statement')).to_contain_text('AAPL')
            checks.append('SEC financial evidence independent of mortgage runs')
            assert not errors, errors; checks.append('No JavaScript/console errors')
            browser.close()
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(), 'view_id': identifier,
            'checks': checks, 'browser_errors': errors, 'visibility': 'private', 'public_release_approved': False})
        return {'status': 'PASS', 'checks': len(checks), 'directory': str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status': 'FAIL', 'exception_type': type(error).__name__, 'checks_completed': checks, 'browser_errors': errors})
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    print(json.dumps(run(app_root()), indent=2))
