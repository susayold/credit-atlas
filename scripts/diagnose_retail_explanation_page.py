"""Read a separate browser page on an already-running QA server."""
import json
import os
import uuid
import argparse
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

root = Path('D:/data/Codex/credit-atlas')
parser = argparse.ArgumentParser()
parser.add_argument('--base-url', required=True)
args = parser.parse_args()
parsed = urlparse(args.base_url)
if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
    parser.error('Use a local HTTP QA server base URL')
output = root / 'artifacts/private' / ('retail-page-diagnostic-' + uuid.uuid4().hex[:12]); output.mkdir()
os.environ['TEMP'] = os.environ['TMP'] = str(root / '.tmp')
errors = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
    try:
        page.goto(args.base_url.rstrip('/') + '/?view=retail&view_id=suite-view-74e07524f6d0&retail_policy_id=retail-policy-bd4b8623de28', wait_until='domcontentloaded', timeout=30000)
        print('DOMContentLoaded', flush=True)
        expect(page.locator('#retail-explanation-global')).to_contain_text('4,499 validation clients', timeout=90000)
        print('Global report loaded', flush=True)
        page.get_by_label('Retail explanation case', exact=True).select_option('validation_case_12')
        expect(page.locator('#retail-explanation-local')).to_contain_text('validation_case_12')
        print('Local case selected', flush=True)
        with page.expect_download(timeout=30000) as download:
            page.get_by_role('button', name='Xuất giải thích đang xem', exact=True).click()
        download.value.save_as(str(output / 'export.json'))
        print('Private export saved', flush=True)
        result = {'panel': page.locator('#retail-explanations').inner_text(), 'errors': errors}
    except Exception as error:
        result = {'exception': str(error), 'errors': errors, 'body': page.locator('body').inner_text(timeout=10000)[-5000:]}
    (output / 'diagnostic.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    page.screenshot(path=str(output / 'page.png'))
    browser.close()
print(json.dumps({'directory': str(output), **result}, ensure_ascii=False))
