"""Real saved-validation policy workflow, source-scoped export and mobile QA."""
import json
import threading
import uuid
import shutil
from http.server import ThreadingHTTPServer
from playwright.sync_api import expect,sync_playwright
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new
from credit_atlas.retail_policy_views import RetailPolicyViews

def run(root):
    output=root/'artifacts/private'/('retail-policy-browser-qa-'+uuid.uuid4().hex[:12]); output.mkdir()
    service=ResearchService(root,review_path=output/'qa-reviews.sqlite3')
    view='suite-view-74e07524f6d0'; policy='retail-policy-bd4b8623de28'; freeze='retail-freeze-3dc86f5afe01'
    storage=output/'qa-policies';storage.mkdir()
    shutil.copytree(root/'artifacts/private'/policy,storage/policy)
    service.retail_policy_views=RetailPolicyViews(root,storage_root=storage)
    service.suite_views.view(view)
    ledger=root/'artifacts/private/retail-holdout-access.sqlite'; before=sha256(ledger)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service)); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    base='http://127.0.0.1:'+str(server.server_port); errors=[];checks=[];expected_http_errors=[]
    expect.set_options(timeout=120000)
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(120000)
            page.on('pageerror',lambda error:errors.append(str(error)))
            def console(message):
                if message.type!='error': return
                location=message.location.get('url','')
                if '400' in message.text and location.startswith(base+'/api/retail-policy-preview?') and 'lower_threshold=0.8' in location:
                    expected_http_errors.append({'status':400,'route':'retail-policy-preview'})
                else: errors.append(message.text)
            page.on('console',console)
            page.route('**/api/runs',lambda route:route.fulfill(json={'runs':[]}))
            url=base+'/?view=retail&view_id='+view+'&retail_policy_id='+policy
            page.goto(url,wait_until='networkidle',timeout=180000)
            panel=page.locator('#retail-policy')
            expect(panel).to_contain_text('4,499 validation clients / 995 events')
            expect(page.locator('#retail-policy-comparison')).to_contain_text('2,277')
            expect(page.locator('#retail-policy-comparison')).to_contain_text('overflow 1,677')
            expect(page.locator('#retail-policy-actions')).to_contain_text('Detail: lower_thresholds')
            assert page.locator('#run-select').is_disabled()
            checks.append('Real frozen boosting/raw validation cohort; declared threshold/cost cases and capacity overflow')
            page.locator('#retail-policy').screenshot(path=str(output/'policy-desktop.png'))
            save=page.get_by_role('button',name='Lưu policy version',exact=True)
            assert save.is_disabled()
            page.get_by_label('Review capacity · trống nếu chưa biết',exact=True).fill('3000')
            page.get_by_role('button',name='Tính thử policy',exact=True).click()
            expect(panel).to_contain_text('UNSAVED preview')
            expect(save).to_be_enabled()
            row=page.locator('#retail-policy-comparison tbody tr').last
            expect(row).to_contain_text('2,277'); expect(row.locator('td').nth(4)).to_have_text('NO')
            checks.append('Changed capacity recalculates declared preview; no source/model/holdout override')
            page.get_by_label('accept · event cost',exact=True).fill('12')
            assert save.is_disabled()
            page.get_by_role('button',name='Tính thử policy',exact=True).click()
            expect(save).to_be_enabled(); save.click()
            expect(page.get_by_label('Retail policy version',exact=True)).not_to_have_value(policy)
            saved_id=page.get_by_label('Retail policy version',exact=True).input_value()
            expect(panel).to_contain_text('Saved version')
            checks.append('Editing assumptions disables save until recomputed; explicit save creates distinct immutable version')
            with page.expect_download(timeout=180000) as download: page.get_by_role('link',name='Xuất policy đã lưu',exact=True).click()
            download.value.save_as(str(output/'policy-export.json')); exported=read_json(output/'policy-export.json')
            assert exported['policy_id']==saved_id and exported['freeze_id']==freeze and exported['records']==4499
            assert exported['assumptions']['review_capacity']==3000 and exported['assumptions']['cost_matrix']['accept']['event']=='12'
            assert not any(exported['qualification'].values()) and 'source_client_id' not in str(exported)
            checks.append('Saved export matches confirmed cost/capacity, source and model; aggregate-only private contract')
            page.reload(wait_until='networkidle',timeout=180000)
            expect(page.get_by_label('Retail policy version',exact=True)).to_have_value(saved_id)
            expect(page.get_by_label('accept · event cost',exact=True)).to_have_value('12')
            checks.append('URL and reload restore saved policy version')
            page.get_by_label('Accept dưới probability',exact=True).fill('0.8')
            with page.expect_response(lambda response:'/api/retail-policy-preview?' in response.url and response.status==400,timeout=180000):
                page.get_by_role('button',name='Tính thử policy',exact=True).click()
            expect(panel).to_contain_text('Invalid request or evidence contract'); assert save.is_disabled()
            checks.append('Reversed thresholds fail visibly; previous study remains intact')
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            panel.screenshot(path=str(output/'policy-mobile.png'))
            checks.append('390px controls/tables without page overflow')
            page.goto(base+'/?view=retail&view_id='+view+'&retail_policy_id=retail-policy-000000000000',wait_until='networkidle',timeout=180000)
            expect(page.locator('#retail-policy')).to_contain_text('Policy trong URL không thuộc frozen model')
            assert page.locator('#retail-policy-comparison').count()==0
            checks.append('Invalid explicit policy has no fallback to unrelated study')
            assert sha256(ledger)==before and not errors,errors
            checks.append('Actual consumed holdout ledger unchanged; no JavaScript/console errors')
            browser.close()
        write_new(output/'receipt.json',{'status':'PASS','completed_at':timestamp(),'policy_id':policy,'saved_qa_policy_id':saved_id,
            'checks':checks,'browser_errors':errors,'expected_invalid_request_console_errors':expected_http_errors,'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
        return {'status':'PASS','checks':len(checks),'directory':str(output)}
    except Exception as error:
        write_new(output/'failed.json',{'status':'FAIL','exception_type':type(error).__name__,'checks_completed':checks,'browser_errors':errors});raise
    finally: server.shutdown();server.server_close();thread.join(timeout=5)

if __name__=='__main__': print(json.dumps(run(app_root()),indent=2))
