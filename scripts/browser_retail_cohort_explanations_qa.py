import json
import os
import threading
import uuid
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new
import pyarrow.parquet as pq


def run(root):
    output=root/'artifacts/private'/('retail-cohort-browser-qa-'+uuid.uuid4().hex[:12]);output.mkdir()
    os.environ['TEMP']=os.environ['TMP']=str(root/'.tmp')
    service=ResearchService(root,review_path=output/'qa-reviews.sqlite3')
    cohort='retail-cohort-explanations-02487bb9d1a2';parent='retail-explanations-84b3ac3bab6e'
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];checks=[]
    print('Verifying all4499 source-bound explanations before UI navigation',flush=True)
    service.retail_cohort_explanation_views.evidence(cohort)
    private=pq.read_table(root/'artifacts/private'/cohort/'private-client-explanations.parquet').to_pylist()
    minimum=next(r for r in private if r['score_rank']==1)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port);expect.set_options(timeout=300000)
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(300000)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            page.route('**/api/runs',lambda route:route.fulfill(json={'runs':[]}))
            url=base+'/?view=retail&view_id=suite-view-74e07524f6d0&retail_policy_id=retail-policy-bd4b8623de28&retail_explanations_id='+parent+'&retail_cohort_id='+cohort
            page.goto(url,wait_until='domcontentloaded',timeout=300000)
            panel=page.locator('#retail-cohort-explanations');clients=page.locator('#retail-explanation-clients tbody tr');detail=page.locator('#retail-cohort-client')
            expect(panel).to_contain_text('4,499 hồ sơ toàn cohort');expect(clients).to_have_count(20)
            expect(clients.first.locator('td').nth(1)).to_have_text('4,499')
            expect(detail).to_contain_text('rank 4,499 / 4,499')
            checks.append('All4499 actual validation clients available; first20 score-ranked clients and four-group cohort distribution')
            print('Initial whole-cohort UI verified',flush=True)
            page.get_by_role('button',name='Trang sau',exact=True).click()
            expect(clients.first.locator('td').nth(1)).to_have_text('4,479')
            chosen=clients.nth(9).locator('td').nth(2).inner_text();clients.nth(9).get_by_role('button',name='Giải thích',exact=True).click()
            expect(detail).to_contain_text(chosen);expect(detail).to_contain_text('rank 4,470 / 4,499')
            checks.append('Second page and rank4470 client outside original12 examples; no subset fallback')
            with page.expect_download(timeout=120000) as download:page.get_by_role('link',name='Xuất giải thích hồ sơ',exact=True).click()
            download.value.save_as(str(output/'export.json'));report=read_json(output/'export.json')
            assert report['cohort_id']==cohort and report['explanations_id']==parent and report['client']['client_token']==chosen and report['client']['score_rank']==4470
            assert report['records']==4499 and len(report['global_group_contributions'])==4 and 'source_client_id' not in json.dumps(report) and 'background_source_ids' not in json.dumps(report)
            row=report['client'];assert abs(row['reference_probability']+sum(g['probability_contribution'] for g in row['contributions'])-row['predicted_probability'])<1e-12
            assert chosen in page.url and cohort in page.url
            checks.append('Selected client export matches source/version/scope, reconstructs prediction and excludes original IDs/reference rows')
            page.reload(wait_until='domcontentloaded',timeout=300000);expect(detail).to_contain_text(chosen);expect(clients).to_have_count(1)
            checks.append('URL reload restores exact client and cohort/explanation source binding')
            search=page.get_by_label('Retail explanation client token',exact=True);search.fill(minimum['client_token']);page.get_by_role('button',name='Tìm token',exact=True).click()
            expect(clients).to_have_count(1);expect(detail).to_contain_text('rank 1 / 4,499')
            checks.append('Exact-token search reaches lowest-score client across complete validation population')
            search.fill('client-'+'f'*24);page.get_by_role('button',name='Tìm token',exact=True).click()
            expect(panel).to_contain_text('Không tìm thấy token trong cohort này');expect(page.get_by_role('link',name='Xuất giải thích hồ sơ',exact=True)).to_be_hidden()
            assert detail.inner_text()==''
            checks.append('Unknown valid token produces no client/prediction/export; no fallback')
            search.fill('');page.get_by_role('button',name='Tìm token',exact=True).click();expect(clients).to_have_count(20);expect(detail).to_contain_text('rank 4,499 / 4,499')
            panel.screenshot(path=str(output/'desktop.png'));page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            action=clients.nth(1).get_by_role('button',name='Giải thích',exact=True)
            rect=action.bounding_box();assert rect and rect['x']>=0 and rect['x']+rect['width']<=390
            action.click();expect(detail).to_contain_text('rank 4,498 / 4,499')
            panel.screenshot(path=str(output/'mobile.png'))
            checks.append('Desktop and390px mobile without page overflow; client action visible and operable before horizontal scrolling')
            assert sha256(ledger)==before and not errors,errors
            checks.append('Consumed holdout ledger unchanged; no unexpected JS/console errors')
            browser.close()
        write_new(output/'receipt.json',{'status':'PASS','completed_at':timestamp(),'checks':checks,'cohort_id':cohort,'browser_errors':errors,
                                         'holdout_ledger_unchanged':True,'saved_audited_consistency_before_navigation':True,'model_inference_rerun':False,'visibility':'private','public_release_approved':False})
        return {'status':'PASS','checks':len(checks),'directory':str(output)}
    except Exception as error:
        write_new(output/'failed.json',{'status':'FAIL','type':type(error).__name__,'message':str(error),'checks_completed':checks,'browser_errors':errors});raise
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':print(json.dumps(run(app_root()),indent=2))
