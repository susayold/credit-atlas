import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import app_root,sha256,timestamp,write_new,read_json

def run(root):
    output=root/'artifacts/private'/('retail-subgroups-browser-qa-'+uuid.uuid4().hex[:12]);output.mkdir()
    service=ResearchService(root,review_path=output/'qa-reviews.sqlite3');server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)
    policy='retail-policy-bd4b8623de28';study='retail-subgroups-3cf671cf3152';ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];checks=[]
    expect.set_options(timeout=240000)
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(240000)
            page.on('pageerror',lambda error:errors.append(str(error)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
            page.route('**/api/runs',lambda route:route.fulfill(json={'runs':[]}))
            page.goto(base+'/?view=retail&view_id=suite-view-74e07524f6d0&retail_policy_id='+policy,wait_until='networkidle',timeout=300000)
            panel=page.locator('#retail-subgroups');expect(panel).to_contain_text('4,499 validation clients')
            expect(page.get_by_label('Retail subgroup study',exact=True)).to_have_value(study)
            assert page.locator('#retail-subgroup-results tbody tr').count()==2
            checks.append('Actual source-bound validation subgroup study; SEX source codes and no mortgage dependency')
            page.get_by_label('Retail subgroup dimension',exact=True).select_option('education')
            expect(page.locator('#retail-subgroup-results tbody tr')).to_have_count(7)
            expect(panel).to_contain_text('INSUFFICIENT_RECORDS');expect(panel).to_contain_text('Unavailable')
            assert sum(int(t.replace(',','')) for t in page.locator('#retail-subgroup-results tbody tr td:nth-child(2)').all_text_contents())==4499
            checks.append('Seven education source categories retained; small-group metrics unavailable and records reconcile')
            with page.expect_download(timeout=240000) as download:page.get_by_role('link',name='Xuất subgroup đã kiểm tra',exact=True).click()
            download.value.save_as(str(output/'export.json'));report=read_json(output/'export.json')
            assert report['filters']['dimension']=='education' and report['assumptions']['policy_id']==policy and report['subgroups_id']==study
            assert len(report['groups'])==7 and not any(report['qualification'].values()) and 'source_client_id' not in str(report)
            checks.append('Private aggregate export matches source, policy, study and selected dimension')
            page.get_by_label('Retail subgroup dimension',exact=True).select_option('age_band')
            expect(page.locator('#retail-subgroup-results tbody tr')).to_have_count(4)
            page.locator('#retail-subgroups').screenshot(path=str(output/'desktop.png'))
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#retail-subgroups').screenshot(path=str(output/'mobile.png'))
            checks.append('Four declared age bands, desktop and 390px mobile without page overflow')
            assert sha256(ledger)==before and not errors,errors
            checks.append('Actual consumed holdout ledger unchanged; no unexpected JS/console errors')
            browser.close()
        write_new(output/'receipt.json',{'status':'PASS','completed_at':timestamp(),'checks':checks,'browser_errors':errors,'subgroups_id':study,'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
        return {'status':'PASS','checks':len(checks),'directory':str(output)}
    except Exception as error:write_new(output/'failed.json',{'status':'FAIL','type':type(error).__name__,'checks_completed':checks,'browser_errors':errors});raise
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
if __name__=='__main__':print(json.dumps(run(app_root()),indent=2))
