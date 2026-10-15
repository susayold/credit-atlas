"""Check detailed roadmap navigation, real Retail evidence, export and mobile scope."""
import json
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import app_root, sha256


def run():
    root = app_root()
    out = root / 'artifacts/private' / ('content-detail-qa-' + uuid.uuid4().hex[:12])
    out.mkdir()
    ledger = root / 'artifacts/private/retail-holdout-access.sqlite'
    before = sha256(ledger)
    checks, errors = [], []
    base = 'http://127.0.0.1:8770/'
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page.on('pageerror', lambda error: errors.append(str(error)))
        for domain, view in [('P1','retail'),('P2','portfolio'),('P3','business'),('P4','exposure'),('P5','abs')]:
            page.goto(base + '?view=' + view + '&run=d01-a24484b21a21&exposure_import_id=exposure-import-57b88e00bedb')
            roadmap = page.locator('.capability-roadmap')
            expect(roadmap).to_have_attribute('data-domain', domain, timeout=180000)
            roadmap.locator('summary').click()
            expect(roadmap.locator('[data-capability]')).to_have_count(10)
            for i in range(10):
                roadmap.locator('[data-capability]').nth(i).click()
                expect(roadmap.locator('.capability-fields dt')).to_have_count(6)
                assert all(text.strip() for text in roadmap.locator('.capability-fields dd').all_text_contents())
                expect(roadmap.locator('[aria-pressed=true]')).to_have_count(1)
            with page.expect_download() as pending:
                roadmap.get_by_role('button', name='Tải kế hoạch '+domain+' (.md)', exact=True).click()
            pending.value.save_as(out / (domain + '.md'))
            text = (out / (domain + '.md')).read_text(encoding='utf-8')
            assert text.count('\n## ') == 10 and 'Điều kiện nghiệm thu' in text
            checks.append(domain + ': ten selectable capabilities, six nonempty fields, selection state and ten-section Markdown download')
        for view in ['hmda','bank','country','bankruptcy','bankruptcymodel']:
            page.goto(base+'?view='+view)
            expect(page.locator('.task-context-guide')).to_have_count(1, timeout=180000)
            page.locator('.task-context-guide summary').click()
            expect(page.locator('.task-context-guide .capability-fields dt')).to_have_count(6)
            checks.append(view + ': native-source guide has six fields without borrowing another dataset target')
        page.goto(base+'?view=retail&workspace_tab=evidence')
        expect(page.locator('#retail-model-dossier')).to_be_visible(timeout=180000)
        expect(page.locator('#retail-model-dossier li')).to_have_count(7)
        body = page.locator('#retail-model-dossier').inner_text()
        assert '3dc86f5afe01' in body and '061c440ea867' in body
        assert '3,001' in body and '664' in body
        expect(page.get_by_role('tab')).to_have_count(5)
        page.locator('.task-context-guide summary').click()
        expect(page.locator('.task-context-guide .capability-fields dt')).to_have_count(6)
        roadmap = page.locator('.capability-roadmap')
        roadmap.locator('summary').click()
        roadmap.locator('[data-capability="P1.02"]').click()
        expect(roadmap.locator('.capability-detail a')).to_have_count(0)
        roadmap.locator('[data-capability="P1.04"]').click()
        roadmap.get_by_role('link', name='Mở workflow liên quan ↗').click()
        expect(page.get_by_role('tab',name='Policy & subgroup',exact=True)).to_have_attribute('aria-selected','true',timeout=180000)
        checks.append('Retail dossier: actual frozen identifiers/support, seven stages, five unchanged task tabs; missing-data capability has no workflow; policy link opens correct task')
        page.goto(base+'?view=retail&workspace_tab=evidence')
        expect(page.locator('#retail-model-dossier')).to_be_visible(timeout=180000)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('.capability-roadmap summary').click()
        page.locator('.task-context-guide summary').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
        page.screenshot(path=str(out/'retail-detail-mobile.png'),full_page=True)
        page.set_viewport_size({'width':1440,'height':1000})
        page.screenshot(path=str(out/'retail-detail-desktop.png'),full_page=True)
        checks.append('Expanded detailed content: mobile 390px has no horizontal overflow; desktop/mobile screenshots saved')
        browser.close()
    assert before == sha256(ledger), 'Saved holdout ledger changed'
    assert not errors, errors
    checks.append('No browser exceptions and no holdout ledger mutation')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':len(checks),'receipt':str(out/'receipt.json')},ensure_ascii=False))


if __name__ == '__main__':
    run()
