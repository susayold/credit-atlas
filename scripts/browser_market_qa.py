"""Actual-source P5 native-market and assumed-bond workflow acceptance."""
import csv
import json
import re
import threading
import uuid
from datetime import date
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
from browser_navigation import navigate_workspace, select_task

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new

expect.set_options(timeout=60000)


def run(root):
    output = root / 'artifacts/private' / ('market-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    valid = [row for row in service.market_views.catalog()['views'] if row['status'] == 'verified']
    if not valid:
        raise ValueError('Real market snapshot required')
    identifier = valid[0]['view_id']
    snapshot = service.market_views.view(identifier)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors, checks = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page.set_default_timeout(30000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.goto(base + '/?view=market&market_view_id=' + identifier, wait_until='networkidle')
            expect(page.locator('#active-module')).to_have_text('P5')
            expect(page.locator('#context-note')).to_contain_text('46,675')
            expect(page.locator('#readiness-badges')).to_contain_text('994 historical values quarantined')
            expect(page.locator('#content')).to_contain_text('Ngày cuối có đủ ba kỳ hạn: 2026-10-06')
            expect(page.locator('#content')).to_contain_text('4.79 / 5.27 / 5.64')
            checks.append('actual 46675-observation/five-series context and same-date Treasury values')
            for name in ('run-select', 'segment-select', 'basis-select'):
                assert page.locator('#' + name).is_disabled()
            assert not page.locator('#content').get_by_text('Lưu finding từ view này').count()
            checks.append('P5 mortgage controls and finding namespace isolated')
            select_task(page, 'Bond scenarios')
            expect(page.locator('#market-panel-bond')).to_contain_text('100.000000')
            expect(page.locator('#content')).to_contain_text('Assumption-only')
            checks.append('default fixed-coupon/coupon-date scenario prices at par with declared assumptions')
            select_task(page, 'Market context')
            page.get_by_label('Market series', exact=True).select_option('BAMLC0A0CM')
            page.get_by_label('Market from date', exact=True).fill('2026-05-29')
            page.get_by_label('Market to date', exact=True).fill('2026-06-02')
            page.get_by_role('button', name='Đọc market observations', exact=True).click()
            query = {'view_id': identifier, 'series': 'BAMLC0A0CM', 'from': '2026-05-29', 'to': '2026-06-02'}
            expected = service.market_views.report(identifier, query)
            expect(page.locator('#content')).to_contain_text(f"{expected['native_rows']} selected native rows")
            assert any(row['observation_date'] == '2026-05-31' for row in expected['rows'])
            expect(page.locator('#content')).to_contain_text('2026-05-31')
            checks.append('native OAS month-end Sunday retained by date/series selection')
            with page.expect_download() as info:
                page.locator('#export-report').click()
            info.value.save_as(str(output / 'market-export.json'))
            actual = json.loads((output / 'market-export.json').read_text(encoding='utf-8'))
            assert actual == expected and actual['public_release_approved'] is False
            assert 'internal use only' in actual['profile']['rights']
            # Compare selected downloaded output to raw CSV independently of serving methods.
            raw = root / 'data/private/public-suite/suite-619b1ee9aa8c/fred-bamlc0a0cm.csv'
            with raw.open() as stream:
                native = [row for row in csv.DictReader(stream) if query['from'] <= row['observation_date'] <= query['to']]
            assert [(row['observation_date'], row['source_value']) for row in actual['rows']] == [(row['observation_date'], row['BAMLC0A0CM']) for row in native]
            checks.append('private selected series export matches snapshot and raw CSV, with source rights')
            page.screenshot(path=str(output / 'market-desktop.png'))
            page.locator('.card').filter(has_text='Native series explorer').screenshot(path=str(output / 'market-native-desktop.png'))
            # Test the actual historical discontinuation on calendar-scaled SVG,
            # not just the source adapter's absence of imputed observations.
            page.get_by_label('Market series', exact=True).select_option('DGS30')
            page.get_by_label('Market from date', exact=True).fill('2001-01-01')
            page.get_by_label('Market to date', exact=True).fill('2007-01-01')
            page.get_by_role('button', name='Đọc market observations', exact=True).click()
            historical = service.market_views.report(identifier, {'view_id': identifier, 'series': 'DGS30', 'from': '2001-01-01', 'to': '2007-01-01'})
            expect(page.locator('#content')).to_contain_text(f"{historical['native_rows']:,} selected native rows")
            history_rows = historical['rows']
            middle = date(2004, 1, 1)
            before = [row for row in history_rows if row['value_percent'] is not None and date.fromisoformat(row['observation_date']) < middle]
            after = [row for row in history_rows if row['value_percent'] is not None and date.fromisoformat(row['observation_date']) > middle]
            assert before[-1]['observation_date'] == '2002-02-15' and after[0]['observation_date'] == '2006-02-09'
            assert historical['quarantined_rows'] == 994
            flagged = [row for row in history_rows if row['documented_discontinuation_conflict']]
            assert all(row['source_value_percent'] is not None and row['value_percent'] is None for row in flagged)
            first_date, last_date = (date.fromisoformat(history_rows[i]['observation_date']) for i in (0, -1))
            middle_x = 48 + (middle - first_date).days / (last_date - first_date).days * (680 - 48 - 18)
            path = page.locator('svg[aria-label="Native market observations in percent"] path').get_attribute('d')
            styling = page.locator('svg[aria-label="Native market observations in percent"] path').evaluate(
                '(element)=>({fill:getComputedStyle(element).fill,stroke:getComputedStyle(element).stroke})')
            assert styling['fill'] == 'none' and styling['stroke'] != 'none'
            previous_x = None
            for command, x, y in re.findall(r'([ML])([-0-9.e+]+),([-0-9.e+]+)', path):
                current_x = float(x)
                if command == 'L' and previous_x is not None:
                    assert not previous_x < middle_x < current_x, 'Chart connects across source discontinuation'
                previous_x = current_x
            page.locator('.card').filter(has_text='Native series explorer').screenshot(path=str(output / 'dgs30-discontinuation.png'))
            checks.append('994 documentation-conflict source values preserved but quarantined from calendar-scaled curve')
            page.get_by_label('Market series', exact=True).select_option('BAMLC0A0CM')
            page.get_by_label('Market from date', exact=True).fill(query['from'])
            page.get_by_label('Market to date', exact=True).fill(query['to'])
            page.get_by_role('button', name='Đọc market observations', exact=True).click()
            expect(page.locator('#content')).to_contain_text(f"{expected['native_rows']} selected native rows")
            select_task(page, 'Bond scenarios')
            page.get_by_label('Assumed yield percent', exact=True).fill('7')
            page.get_by_role('button', name='Tính bond scenario', exact=True).click()
            with page.expect_download() as info:
                page.get_by_role('button', name='Xuất bond scenario riêng tư', exact=True).click()
            info.value.save_as(str(output / 'bond-export.json'))
            bond = json.loads((output / 'bond-export.json').read_text(encoding='utf-8'))
            expected_price = 2.5 * (1 - 1.035**(-20)) / .035 + 100 * 1.035**(-20)
            assert abs(bond['price_usd'] - expected_price) < 1e-10
            assert bond['terms']['yield_percent'] == '7' and bond['market_calibrated'] is False
            assert bond['source_market_series_used_for_pricing'] is False
            page.locator('.card').filter(has_text='Fixed-coupon bond scenario').screenshot(path=str(output / 'bond-desktop.png'))
            checks.append('7-percent-yield scenario matches independent annuity price; no market calibration claim')
            assert bond['bump_validation']['duration_abs_residual'] < 2e-6
            assert sum(row['principal_usd'] for row in bond['schedule']) == 100
            checks.append('export retains cash flows, coupon-date conventions and analytical/bump parity')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('Assumed yield percent')).to_have_value('7')
            select_task(page, 'Market context')
            expect(page.get_by_label('Market series')).to_have_value('BAMLC0A0CM')
            expect(page.get_by_label('Market from date')).to_have_value('2026-05-29')
            select_task(page, 'Bond scenarios')
            expect(page.get_by_label('Assumed yield percent')).to_have_value('7')
            checks.append('market date/series and bond assumptions survive URL reload')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'market-mobile.png'))
            checks.append('390px P5 mobile without page overflow')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate_workspace(page, 'bank')
            expect(page.locator('#content')).to_contain_text('4,313 selected bank reports')
            navigate_workspace(page, 'overview')
            expect(page.locator('.metric-value').first).to_have_text('50,000', timeout=30000)
            assert not page.locator('#segment-select').is_disabled()
            checks.append('P5 navigation back to actual independent P4/P2 contexts')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto(base + '/?view=market&market_view_id=' + identifier, wait_until='networkidle')
            expect(page.locator('#context-note')).to_contain_text('46,675')
            select_task(page, 'Bond scenarios')
            expect(page.locator('#content')).to_contain_text('100.000000')
            checks.append('P5 usable without mortgage or retail runs')
            assert not errors, errors
            checks.append('no browser JavaScript/console errors')
            browser.close()
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(),
            'view_id': identifier, 'checks': checks, 'browser_errors': errors,
            'visibility': 'private', 'public_release_approved': False})
        return {'status': 'PASS', 'checks': len(checks), 'directory': str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status': 'FAIL', 'exception_type': type(error).__name__,
                   'checks_completed': checks, 'browser_errors': errors})
        raise
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__ == '__main__':
    print(json.dumps(run(app_root()), indent=2))
