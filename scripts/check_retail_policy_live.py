"""Live API parity and mobile layout of the actual source-bound policy study."""
import json
import uuid
from time import perf_counter
from urllib.parse import urlencode
from urllib.request import urlopen
from playwright.sync_api import expect,sync_playwright
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new

def run(root):
    output=root/'artifacts/private'/('retail-policy-live-'+uuid.uuid4().hex[:12]);output.mkdir()
    base='http://127.0.0.1:8770';policy='retail-policy-bd4b8623de28';freeze='retail-freeze-3dc86f5afe01';view='suite-view-74e07524f6d0'
    source=read_json(root/'artifacts/private'/policy/'report.json'); ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with urlopen(base+'/api/retail-policies?'+urlencode({'freeze_id':freeze}),timeout=240) as response:
        catalog=json.load(response);assert any(r['policy_id']==policy for r in catalog['policies'])
    query={'policy_id':policy,'freeze_id':freeze}
    timings=[]
    for _ in range(2):
        start=perf_counter()
        with urlopen(base+'/api/retail-policy-report?'+urlencode(query),timeout=240) as response:
            result=json.load(response);assert 'no-store' in response.headers['Cache-Control']
            assert result==source|{'policy_id':policy,'visibility':'private','public_release_approved':False}
        timings.append(perf_counter()-start)
    errors=[];expect.set_options(timeout=120000)
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':390,'height':844});page.set_default_timeout(120000)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
        page.route('**/api/runs',lambda route:route.fulfill(json={'runs':[]}))
        page.goto(base+'/?view=retail&view_id='+view+'&retail_policy_id='+policy,wait_until='networkidle',timeout=240000)
        expect(page.locator('#retail-policy')).to_contain_text('4,499 validation clients / 995 events')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        link=page.get_by_role('link',name='Xuất policy đã lưu',exact=True)
        assert link.evaluate("node=>getComputedStyle(node).display==='inline-flex' && getComputedStyle(node).whiteSpace==='nowrap'")
        page.locator('#retail-policy').screenshot(path=str(output/'mobile.png'))
        assert not errors,errors;browser.close()
    assert sha256(ledger)==before
    write_new(output/'receipt.json',{'status':'PASS','completed_at':timestamp(),'policy_id':policy,'api_parity':True,
        'cached_report_seconds':timings,'native_mobile_layout':True,'holdout_ledger_unchanged':True,'browser_errors':errors,
        'visibility':'private','public_release_approved':False})
    return {'status':'PASS','directory':str(output),'cached_report_seconds':timings}

if __name__=='__main__': print(json.dumps(run(app_root()),indent=2))
