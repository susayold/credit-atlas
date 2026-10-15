"""Actual World Bank country/aggregate, same-year and missing-data UI acceptance."""
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
    output = root / 'artifacts/private' / ('country-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    identifier = next(row['view_id'] for row in service.country_views.catalog()['views'] if row['status'] == 'verified')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    server.daemon_threads = True
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
            url = base + '/?view=country&country_view_id=' + identifier
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#context-note')).to_contain_text('122,892 annual source rows · 217 economies / 49 aggregates')
            expect(page.locator('#country-timeline')).to_contain_text('4.8481')
            expect(page.locator('#country-timeline')).to_contain_text('Unavailable')
            assert page.locator('#run-select').is_disabled()
            expect(page.locator('#readiness-badges')).to_contain_text('Not sovereign PD')
            checks.append('Actual source count, 217 economies/49 aggregates, VNM NPL 2024 value and missing years; P2 isolated')
            page.screenshot(path=str(output / 'country-desktop.png'), full_page=True)
            page.get_by_label('Country comparison year').fill('2025')
            page.get_by_role('button', name='Đọc country context').click()
            expect(page.locator('#country-peers .card-heading')).to_contain_text('2025')
            expect(page.locator('.metric-value').first).to_have_text('Unavailable')
            expect(page.locator('#country-profile')).to_contain_text('2024')
            checks.append('2025 NPL stays unavailable while latest-known profile explicitly retains its 2024 reference year')
            with page.expect_download() as info:
                page.locator('#export-report').click()
            info.value.save_as(str(output / 'country-export.json'))
            report = read_json(output / 'country-export.json')
            assert report['filters']['country'] == 'VNM' and report['filters']['year'] == 2025
            assert report['selected_year_observation']['value'] is None
            assert all(not row['is_aggregate'] for row in report['same_year_peers'])
            assert all(row['year'] == 2025 for row in report['same_year_peers'])
            assert report['no_carryforward'] and not report['public_release_approved']
            actual = service.country_views.report(identifier, {'country': 'VNM', 'year': '2025'})
            assert report == actual
            checks.append('Export equals canonical scoped report; null and same-year country-only peers preserved')
            page.get_by_label('Country indicator').select_option('NY.GDP.MKTP.KD.ZG')
            page.get_by_role('button', name='Đọc country context').click()
            expect(page.locator('.metric-value').first).to_have_text('8.0188')
            checks.append('GDP growth uses annual percent units and actual VNM 2025 value, not credit-ratio semantics')
            page.get_by_label('Country universe').select_option('aggregates')
            page.get_by_label('Country economy').select_option('WLD')
            page.get_by_label('Country comparison year').fill('2024')
            page.get_by_role('button', name='Đọc country context').click()
            expect(page.locator('#country-timeline .card-heading')).to_contain_text('World')
            expect(page.locator('#country-peers .card-heading')).to_contain_text('2024 · aggregates')
            with page.expect_download() as info:
                page.locator('#export-report').click()
            info.value.save_as(str(output / 'aggregate-export.json'))
            aggregate = read_json(output / 'aggregate-export.json')
            assert len(aggregate['same_year_peers']) == 49
            assert all(row['is_aggregate'] for row in aggregate['same_year_peers'])
            assert any(row['source_country_iso3'] == '' and row['country_join_basis'] == 'exact_catalog_iso2_missing_source_iso3'
                       for row in aggregate['same_year_peers'])
            checks.append('World/49 aggregate-only peers separate from economies; exact ISO2 resolution retains blank source ISO3')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('Country economy')).to_have_value('WLD')
            expect(page.get_by_label('Country indicator')).to_have_value('NY.GDP.MKTP.KD.ZG')
            expect(page.locator('#country-peers .card-heading')).to_contain_text('2024 · aggregates')
            checks.append('Universe/country/indicator/year/snapshot survive URL reload')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'country-mobile.png'), full_page=True)
            checks.append('390px mobile without page overflow')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate_workspace(page, 'bank')
            expect(page.locator('#context-note')).to_contain_text('214,809')
            navigate_workspace(page, 'bankruptcymodel')
            expect(page.locator('#bankruptcy-model-final')).to_contain_text('591 statements')
            navigate_workspace(page, 'market')
            expect(page.locator('#context-note')).to_contain_text('46,675')
            navigate_workspace(page, 'overview')
            expect(page.locator('.metric-value').first).to_have_text('50,000')
            checks.append('Independent P4 bank/P3 model/P5/P2 navigation preserves contexts')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#country-timeline')).to_contain_text('4.8481')
            checks.append('Country source explorer independent of mortgage runs')
            assert not errors, errors
            checks.append('No JavaScript/console errors')
            browser.close()
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(), 'view_id': identifier,
            'checks': checks, 'browser_errors': errors, 'visibility': 'private', 'public_release_approved': False})
        return {'status': 'PASS', 'checks': len(checks), 'directory': str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status': 'FAIL', 'exception_type': type(error).__name__,
                  'checks_completed': checks, 'browser_errors': errors})
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    print(json.dumps(run(app_root()), indent=2))
