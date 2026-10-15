"""Actual saved-final UI checks, with final inference functions disabled."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from playwright.sync_api import expect, sync_playwright

from browser_navigation import navigate_workspace, select_task
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new

expect.set_options(timeout=60000)


def run(root):
    output = root / 'artifacts/private' / ('bankruptcy-model-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    ledger = root / 'artifacts/private/bankruptcy-holdout-access.sqlite'
    ledger_before = sha256(ledger)
    checks, errors = [], []
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with patch('credit_atlas.bankruptcy_holdout.frozen_transform', side_effect=AssertionError('Final transform forbidden')), \
             patch('credit_atlas.bankruptcy_holdout.predict_json', side_effect=AssertionError('Final predictor inference forbidden')):
            valid = [row for row in service.bankruptcy_model_views.catalog()['views'] if row['status'] == 'verified']
            identifier = valid[0]['view_id']
            expected = service.bankruptcy_model_views.view(identifier)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='msedge', headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.set_default_timeout(60000)
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                url = base + '/?view=bankruptcymodel&bankruptcymodel_view_id=' + identifier
                page.goto(url, wait_until='networkidle')
                expect(page.locator('#bankruptcy-model-final')).to_contain_text('591 statements · 41 events · 585 exact groups')
                expect(page.locator('#bankruptcy-model-final')).to_contain_text('0.962794')
                expect(page.locator('#bankruptcy-model-final')).to_contain_text('0.927076')
                expect(page.locator('#bankruptcy-model-validation')).to_contain_text('boosting_platt · selected')
                expect(page.locator('#bankruptcy-model-validation')).to_contain_text('887')
                expect(page.locator('#readiness-badges')).to_contain_text('Final access: completed')
                assert page.locator('#run-select').is_disabled()
                checks.append('Actual final support, AUC/95% interval, selected candidate, validation support and completed ledger badge')
                page.screenshot(path=str(output / 'model-desktop.png'), full_page=True)
                with page.expect_download() as info:
                    page.locator('#export-report').click()
                info.value.save_as(str(output / 'model-export.json'))
                report = read_json(output / 'model-export.json')
                assert report == expected and report['can_rescore'] is False
                assert 'source_ordinal' not in json.dumps(report) and 'mean_probability' in json.dumps(report)
                checks.append('Private aggregate export equals verified evidence, without individual probabilities or source ordinals')
                page.reload(wait_until='networkidle')
                expect(page.get_by_label('Bankruptcy model snapshot')).to_have_value(identifier)
                expect(page.locator('#bankruptcy-model-final')).to_contain_text('591 statements')
                checks.append('Snapshot survives URL reload')
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(output / 'model-mobile.png'), full_page=True)
                checks.append('390px mobile has no page overflow')
                page.set_viewport_size({'width': 1440, 'height': 1000})
                navigate_workspace(page, 'bankruptcy')
                expect(page.locator('#context-note')).to_contain_text('43,405')
                page.get_by_role('button', name='Xem model bankruptcy một năm').click()
                expect(page.locator('#bankruptcy-model-final')).to_contain_text('591 statements')
                navigate_workspace(page, 'business')
                expect(page.locator('#context-note')).to_contain_text('2,190,504')
                navigate_workspace(page, 'market')
                expect(page.locator('#context-note')).to_contain_text('46,675')
                navigate_workspace(page, 'overview')
                expect(page.locator('.metric-value').first).to_have_text('50,000')
                checks.append('Ratio-to-model link and independent SBA/P5/P2 navigation')
                page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
                page.goto(url, wait_until='networkidle')
                expect(page.locator('#bankruptcy-model-final')).to_contain_text('591 statements')
                checks.append('Model evidence remains available without mortgage runs')
                assert not errors, errors
                checks.append('No JavaScript or console errors')
                browser.close()
            assert sha256(ledger) == ledger_before
            checks.append('Ledger unchanged; final transform and prediction functions disabled throughout catalog/UI/export verification')
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(), 'view_id': identifier,
                  'checks': checks, 'browser_errors': errors, 'visibility': 'private', 'public_release_approved': False})
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
