import json
import os
import threading
import uuid
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new


def run(root):
    output = root / 'artifacts/private' / ('retail-explanations-browser-qa-' + uuid.uuid4().hex[:12]); output.mkdir()
    os.environ['TEMP'] = os.environ['TMP'] = str(root / '.tmp')
    print('Creating isolated QA service', flush=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service)); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    study = 'retail-explanations-84b3ac3bab6e'; ledger = root / 'artifacts/private/retail-holdout-access.sqlite'; before = sha256(ledger)
    errors = []; checks = []; expect.set_options(timeout=240000)
    try:
        # Full source/model replay remains mandatory; cache it before UI navigation.
        service.retail_explanation_views.evidence(study)
        print('Actual explanation source replay verified', flush=True)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width':1440,'height':1000}); page.set_default_timeout(240000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs':[]}))
            page.goto(base + '/?view=retail&view_id=suite-view-74e07524f6d0&retail_policy_id=retail-policy-bd4b8623de28&workspace_tab=explanations', wait_until='domcontentloaded', timeout=300000)
            print('Page DOM loaded; waiting for verified model data', flush=True)
            panel = page.locator('#retail-explanations'); expect(panel).to_contain_text('4,499 validation clients')
            expect(page.get_by_label('Retail explanation study', exact=True)).to_have_value(study)
            expect(page.locator('#retail-explanation-global tbody tr')).to_have_count(4)
            assert 'Trạng thái trả nợ' in page.locator('#retail-explanation-global tbody tr').first.inner_text()
            checks.append('Actual frozen validation study, all four whole-cohort permutation groups and strongest repayment-status reliance')
            print('Global validation report checked', flush=True)
            expect(page.get_by_label('Retail explanation case', exact=True).locator('option')).to_have_count(12)
            page.get_by_label('Retail explanation case', exact=True).select_option('validation_case_12')
            expect(page.locator('#retail-explanation-local')).to_contain_text('validation_case_12')
            expect(page.locator('#retail-explanation-local table').nth(1).locator('tbody tr')).to_have_count(4)
            checks.append('Twelve ranked validation cases; selected case changes all four probability-point contributions')
            print('Local validation case checked', flush=True)
            with page.expect_download(timeout=240000) as download:
                page.get_by_role('link', name='Xuất giải thích đang xem', exact=True).click()
            download.value.save_as(str(output / 'export.json')); report = read_json(output / 'export.json')
            assert report['explanations_id'] == study and report['filters']['case'] == 'validation_case_12'
            assert len(report['local_explanations']) == 1 and len(report['global_permutation']) == 4
            assert 'source_client_id' not in json.dumps(report) and not any(report['qualification'].values())
            local = report['local_explanations'][0]
            assert abs(local['reference_probability'] + sum(r['probability_contribution'] for r in local['contributions']) - local['predicted_probability']) < 1e-12
            checks.append('Selected-case private export matches visible scope, reconstructs prediction and excludes original IDs/reference records')
            print('Private selected-case export checked', flush=True)
            panel.screenshot(path=str(output / 'desktop.png'))
            page.set_viewport_size({'width':390,'height':844}); assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            link = page.get_by_role('link', name='Xuất giải thích đang xem', exact=True)
            layout = link.evaluate("node=>{const style=getComputedStyle(node),rect=node.getBoundingClientRect();return {display:style.display,white_space:style.whiteSpace,left:rect.left,right:rect.right,width:rect.width,viewport:innerWidth};}")
            # A direct flex child blockifies inline-flex to computed display:flex.
            assert layout['display'] in ('flex','inline-flex') and layout['white_space']=='nowrap' and layout['left']>=0 and layout['right']<=layout['viewport'], layout
            panel.screenshot(path=str(output / 'mobile.png'))
            checks.append('Desktop and 390px mobile without page overflow; export label stays together')
            assert sha256(ledger) == before and not errors, errors
            checks.append('Consumed holdout ledger unchanged and no unexpected JS/console errors')
            browser.close()
        write_new(output / 'receipt.json', {'status':'PASS','completed_at':timestamp(),'checks':checks,'explanations_id':study,
                                           'holdout_ledger_unchanged':True,'mobile_export_layout':layout,'cold_replay_before_navigation':True,'browser_errors':errors,'visibility':'private','public_release_approved':False})
        return {'status':'PASS','checks':len(checks),'directory':str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status':'FAIL','type':type(error).__name__,'message':str(error),'checks_completed':checks,'browser_errors':errors}); raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__': print(json.dumps(run(app_root()), indent=2))
