"""Verify re-entry while a real saved-policy response is delayed."""
import json
import os
import time
import uuid
from urllib.request import urlopen
from playwright.sync_api import expect, sync_playwright
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def run():
    root = app_root()
    os.environ['TEMP'] = os.environ['TMP'] = str(root / '.tmp')
    output = root / 'artifacts/private' / ('task-race-qa-' + uuid.uuid4().hex[:12])
    output.mkdir()
    base = 'http://127.0.0.1:8770'
    ledger = root / 'artifacts/private/retail-holdout-access.sqlite'
    before = sha256(ledger)
    with urlopen(base + '/api/retail-policies?freeze_id=retail-freeze-3dc86f5afe01', timeout=240) as response:
        actual_catalog = json.load(response)
    calls, errors = [], []
    expect.set_options(timeout=180000)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        def delayed_catalog(route):
            calls.append(route.request.url)
            if len(calls) == 1:
                # Browser timers still execute while the Python callback waits.
                time.sleep(0.75)
            route.fulfill(json=actual_catalog)
        page.route('**/api/retail-policies?*', delayed_catalog)
        page.goto(base + '/?view=retail&workspace_tab=overview', wait_until='domcontentloaded')
        expect(page.locator('#retail-model-summary')).to_be_visible()
        page.evaluate('''() => {
            document.querySelector('#retail-tab-policy').click();
            setTimeout(() => document.querySelector('#retail-tab-overview').click(), 50);
            setTimeout(() => document.querySelector('#retail-tab-policy').click(), 100);
        }''')
        expect(page.locator('#retail-policy')).to_contain_text('4,499', timeout=180000)
        expect(page.locator('#retail-subgroups')).to_contain_text('4,499', timeout=180000)
        page.wait_for_timeout(1500)  # Allow the discarded build's saved-data callbacks to settle.
        assert len(calls) == 2, calls
        expect(page.locator('#retail-policy')).to_have_count(1)
        expect(page.get_by_label('Accept dưới probability', exact=True)).to_have_count(1)
        expect(page.get_by_role('tab', name='Policy & subgroup', exact=True)).to_have_attribute('aria-selected', 'true')
        assert 'workspace_tab=policy' in page.url
        page.get_by_role('button', name='Tìm chức năng', exact=True).click()
        page.get_by_label('Tìm workspace hoặc tác vụ').fill('DOC ECL')
        expect(page.locator('#command-results')).to_contain_text('Đọc ECL study')
        page.keyboard.press('Escape')
        assert not errors, errors
        assert sha256(ledger) == before
        page.screenshot(path=str(output / 'policy-after-race.png'))
        browser.close()
    write_new(output / 'receipt.json', {
        'status': 'PASS', 'completed_at': timestamp(),
        'checks': ['Delayed real saved-policy catalog; leave and re-enter task while initial request is pending',
                   'Discarded build cannot duplicate visible controls or overwrite selected task/source context',
                   'Vietnamese uppercase/accent-free search finds Đọc ECL study',
                   'No page errors or consumed holdout mutation'],
        'catalog_requests': len(calls), 'holdout_ledger_unchanged': True,
        'visibility': 'private', 'public_release_approved': False})
    print(json.dumps({'status': 'PASS', 'checks': 4, 'directory': str(output)}, indent=2))


if __name__ == '__main__':
    run()
