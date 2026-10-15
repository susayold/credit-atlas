"""Actual-source horizon, precision and ratio UI acceptance."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright

from browser_navigation import navigate_workspace, select_task
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new


def run(root):
    output = root / 'artifacts/private' / ('bankruptcy-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    valid = [row for row in service.bankruptcy_views.catalog()['views'] if row['status'] == 'verified']
    if not valid:
        raise ValueError('Real bankruptcy snapshot required')
    identifier = valid[0]['view_id']
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(30000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.goto(base + '/?view=bankruptcy&bankruptcy_view_id=' + identifier, wait_until='networkidle')
            expect(page.locator('#context-note')).to_contain_text('43,405')
            expect(page.locator('#content')).to_contain_text('Horizon 1 năm · 5,910 selected statements · 410 source label=1')
            expect(page.locator('#readiness-badges')).to_contain_text('2,092 CSV precision differences')
            assert page.locator('#run-select').is_disabled() and not page.locator('#segment-select').is_visible()
            checks.append('actual 43405-statement/five-horizon source and 2092 precision differences; P2 controls isolated')
            page.screenshot(path=str(output / 'bankruptcy-desktop.png'), full_page=True)
            page.get_by_label('Bankruptcy forecast horizon').select_option('4')
            page.get_by_label('Bankruptcy financial feature').select_option('A55')
            page.get_by_role('button', name='Đọc ratio profile').click()
            expect(page.locator('#content')).to_contain_text('Horizon 4 năm · 10,173 selected statements · 400 source label=1')
            expect(page.locator('#content')).to_contain_text('A55 · working capital')
            expect(page.locator('#content')).to_contain_text('652 CSV/ARFF rounded cells')
            checks.append('four-year target maps to subset code2; A55 original definition and selected-horizon precision audit')
            with page.expect_download() as download_info:
                page.locator('#export-report').click()
            download_info.value.save_as(str(output / 'bankruptcy-export.json'))
            report = json.loads((output / 'bankruptcy-export.json').read_text(encoding='utf-8'))
            assert report['filters'] == {'horizon': 4, 'feature': 'A55'}
            assert report['horizon_summary']['source_subset_code'] == 2 and len(report['feature_quality']) == 64
            assert report['precision_audit']['rounded_numeric_cells'] == 652
            assert report['public_release_approved'] is False and report['contract']['entity_overlap_verified'] is False
            # Independently read the actual canonical selected-horizon ratios to reconcile UI export extrema.
            import pyarrow.parquet as pq
            facts = pq.read_table(root / 'artifacts/private' / report['case_id'] / 'financial-statements.parquet',
                                  columns=['source_subset_code', 'A55']).to_pylist()
            values = [row['A55'] for row in facts if row['source_subset_code'] == 2 and row['A55'] is not None]
            assert report['selected_feature']['min'] == min(values) and report['selected_feature']['max'] == max(values)
            checks.append('private scoped export matches canonical original-ARFF extrema and 64-feature population')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('Bankruptcy forecast horizon')).to_have_value('4')
            expect(page.get_by_label('Bankruptcy financial feature')).to_have_value('A55')
            expect(page.locator('#content')).to_contain_text('10,173 selected statements')
            checks.append('horizon/feature/snapshot survive URL reload')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'bankruptcy-mobile.png'))
            checks.append('390px mobile without page overflow')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate_workspace(page, 'market')
            expect(page.locator('#context-note')).to_contain_text('46,675')
            navigate_workspace(page, 'business')
            expect(page.locator('#context-note')).to_contain_text('2,190,504')
            navigate_workspace(page, 'overview')
            expect(page.locator('.metric-value').first).to_have_text('50,000')
            checks.append('navigation to verified P5/SBA/P2 retains independent contexts')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto(base + '/?view=bankruptcy&bankruptcy_view_id=' + identifier, wait_until='networkidle')
            expect(page.locator('#content')).to_contain_text('5,910 selected statements')
            checks.append('ratio workbench independent of mortgage runs')
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
