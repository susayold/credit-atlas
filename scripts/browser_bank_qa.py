"""Actual-source P4 browser acceptance, scoped export and navigation regression."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright

from credit_atlas.bank_views import bank_report
from browser_navigation import navigate_workspace, select_task
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new


def run(root):
    output = root / 'artifacts/private' / ('bank-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    valid = [row for row in service.bank_views.catalog()['views'] if row['status'] == 'verified']
    if not valid:
        raise ValueError('Actual verified bank view required')
    identifier = valid[0]['view_id']
    snapshot = service.bank_views.view(identifier)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f'http://127.0.0.1:{server.server_port}'
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page.set_default_timeout(30000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.goto(base + '/?view=bank&bank_view_id=' + identifier, wait_until='networkidle')
            expect(page.locator('#active-module')).to_have_text('P4')
            expect(page.locator('#context-note')).to_contain_text('214,809')
            expect(page.locator('#context-note')).to_contain_text('42 quarters')
            expect(page.locator('#content')).to_contain_text('4,313 selected bank reports')
            checks.append('actual 214809-record/42-quarter panel and latest 4313-report cohort')
            for name in ['run-select', 'segment-select', 'basis-select']:
                assert page.locator('#' + name).is_disabled()
            assert not page.locator('#content').get_by_text('Lưu finding từ view này').count()
            checks.append('P4 disables mortgage controls and does not write findings under P2')
            page.get_by_label('Bank reporting quarter', exact=True).select_option('2020-06-30')
            page.get_by_label('Bank asset peer', exact=True).select_option('1bn_to_10bn')
            query = {'view_id': identifier, 'quarter': '2020-06-30', 'peer': '1bn_to_10bn'}
            expected = bank_report(snapshot, query)
            expect(page.locator('#content')).to_contain_text(f"{expected['selected_record_count']:,} selected bank reports")
            expect(page.locator('#content')).to_contain_text('Quality · toàn quý đã chọn')
            checks.append('quarter/peer filters reconcile actual support; quality retains whole-quarter scope')
            with page.expect_download() as info:
                page.locator('#export-report').click()
            info.value.save_as(str(output / 'bank-export.json'))
            actual = json.loads((output / 'bank-export.json').read_text(encoding='utf-8'))
            assert actual == expected
            assert actual['rows'][0]['reported_assets_usd_thousands'] == expected['rows'][0]['reported_assets_usd_thousands']
            assert actual['public_release_approved'] is False and actual['model_qualified'] is False
            assert str(root) not in json.dumps(actual)
            checks.append('private selected export exactly matches verified scope, exact money strings and limits')
            page.screenshot(path=str(output / 'bank-desktop.png'))
            page.get_by_label('FDIC certificate', exact=True).fill('628')
            page.get_by_role('button', name='Đọc institution', exact=True).click()
            timeline = service.bank_views.timeline(identifier, '628')
            expect(page.locator('#content')).to_contain_text(f"CERT 628 · {len(timeline['rows'])} observed quarters")
            expect(page.locator('#content')).to_contain_text(timeline['rows'][-1]['name'])
            assert len(timeline['rows']) == 42
            checks.append('real CERT628 42-quarter institution timeline independent of dashboard peer')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('Bank reporting quarter')).to_have_value('2020-06-30')
            expect(page.get_by_label('Bank asset peer')).to_have_value('1bn_to_10bn')
            expect(page.get_by_label('FDIC certificate')).to_have_value('628')
            expect(page.locator('#content')).to_contain_text('CERT 628 · 42 observed quarters')
            checks.append('bank snapshot/quarter/peer/certificate URL state survives reload')
            page.get_by_label('Bank reporting quarter').select_option('2016-03-31')
            expect(page.locator('#content')).to_contain_text('Quý đầu tiên chưa có preceding quarter')
            checks.append('first quarter has explicit unavailable adjacent change rather than zero')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / 'bank-mobile.png'))
            checks.append('390px P4 mobile without page horizontal overflow')
            page.set_viewport_size({'width': 1440, 'height': 1000})
            navigate_workspace(page, 'retail')
            # A cold retail catalog verifies its ~1GB acquisition plus frozen
            # model lineage before serving. The ordinary 5s assertion timeout
            # is shorter than that legitimate cold verification path.
            expect(page.locator('#retail-model-summary')).to_contain_text('3,001', timeout=60000)
            navigate_workspace(page, 'business')
            expect(page.locator('#content')).to_contain_text('2,190,504')
            navigate_workspace(page, 'overview')
            expect(page.locator('.metric-value').first).to_have_text('50,000')
            assert not page.locator('#segment-select').is_disabled()
            checks.append('P4 navigation back to actual P1/P3/P2 with independent cases')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto(base + '/?view=bank&bank_view_id=' + identifier, wait_until='networkidle')
            expect(page.locator('#content')).to_contain_text('4,313 selected bank reports')
            checks.append('bank app remains usable without mortgage runs or retail snapshot dependency')
            assert not errors, errors
            checks.append('no JavaScript or console errors')
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
