"""Real-source task/detail acceptance for Mortgage, Business, SEC and ABS."""
import json, os, uuid
from urllib.parse import urlparse,parse_qs,urlencode
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,timestamp,write_new,sha256

def run():
    root=app_root();os.environ['TEMP']=os.environ['TMP']=str(root/'.tmp')
    out=root/'artifacts/private'/('remaining-domains-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
    base='http://127.0.0.1:8770';checks=[];errors=[]
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    def get(path,params={}):
        with urlopen(base+path+'?'+urlencode(params),timeout=240) as response:return json.load(response)
    suite=get('/api/suite-view',{'view_id':'suite-view-74e07524f6d0'})
    top=max(suite['business']['aggregates']['dimensions']['program_status'],key=lambda r:r['records'])
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);page.set_default_timeout(180000);expect.set_options(timeout=180000)
        page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.goto(base+'/?view=business',wait_until='domcontentloaded')
        expect(page.locator('#business-summary')).to_contain_text('2,190,504')
        assert page.get_by_role('tab').count()==5
        page.locator('.business-status-row').first.click()
        expect(page.locator('.business-selected-cell')).to_contain_text(f"{top['records']:,}")
        assert page.get_by_label('SBA program').input_value()==top['program']
        expect(page.get_by_role('tab',name='Cohorts & outcomes',exact=True)).to_have_attribute('aria-selected','true')
        page.get_by_role('tab',name='Chất lượng',exact=True).click();expect(page.locator('#business-panel-quality table')).to_be_visible()
        page.get_by_role('tab',name='Dictionary',exact=True).click();expect(page.locator('#business-panel-dictionary')).to_contain_text('LocationID')
        page.get_by_role('tab',name='Tổng quan',exact=True).click();page.screenshot(path=str(out/'business-desktop.png'),full_page=True)
        checks.append('SBA five tasks, actual2190504 records, selected status cell/source program, quality and dictionary')
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(out/'business-mobile.png'),full_page=True)
        checks.append('390px Business status explorer and task strip do not overflow page')
        page.set_viewport_size({'width':1440,'height':1000});page.goto(base+'/?view=sec',wait_until='domcontentloaded')
        expect(page.locator('#sec-ratios')).to_be_visible();assert page.get_by_role('tab').count()==4
        page.get_by_role('tab',name='Financial statements',exact=True).click();expect(page.locator('#sec-financial-fields table')).to_be_visible()
        page.get_by_role('tab',name='Concept evidence',exact=True).click();expect(page.locator('.sec-evidence details').first).to_be_visible()
        page.locator('.sec-evidence summary').first.click();expect(page.locator('.sec-evidence details').first.locator('table')).to_be_visible()
        page.get_by_role('tab',name='Source quality',exact=True).click();expect(page.locator('#sec-quality')).to_contain_text('SEC API facts')
        page.reload(wait_until='domcontentloaded');expect(page.locator('#sec-quality')).to_be_visible()
        checks.append('SEC issuer/ratios, four tasks, exact concept evidence, quality and task/source reload')
        page.goto(base+'/?view=abs',wait_until='domcontentloaded');expect(page.locator('#abs-period-metrics')).to_be_visible();assert page.get_by_role('tab').count()==5
        page.get_by_role('tab',name='Waterfall',exact=True).click();expect(page.locator('.cashflow-step').first).to_be_visible()
        params={k:v[0] for k,v in parse_qs(urlparse(page.url).query).items()};report=get('/api/abs-period',{'view_id':params['abs_view_id'],'period':params['abs_period']})
        row=report['period']['result']['ledger'][1];page.locator('.cashflow-step').nth(1).click();expect(page.locator('#abs-step-detail')).to_contain_text(row['name'])
        def money(value):return '$'+f'{float(value):,.2f}'
        expect(page.locator('#abs-step-detail')).to_contain_text(money(row['paid']));expect(page.locator('#abs-step-detail')).to_contain_text(money(row['cash_after']))
        page.screenshot(path=str(out/'abs-waterfall-desktop.png'),full_page=True)
        page.get_by_role('tab',name='Tranches',exact=True).click();slot=report['tranches'][-1];page.get_by_label('Chọn ABS tranche').select_option(slot['slot']);expect(page.locator('#abs-tranche-detail')).to_contain_text(money(slot['ending_balance']))
        page.get_by_role('tab',name='Đối chiếu',exact=True).click();expect(page.locator('#abs-source-checks')).to_contain_text('PASS')
        page.get_by_role('tab',name='Terms & giới hạn',exact=True).click();expect(page.locator('#abs-qualification')).to_be_visible()
        page.get_by_role('tab',name='Waterfall',exact=True).click();page.get_by_label('ABS collection period').select_option(index=0);expect(page.locator('.cashflow-step').first).to_be_visible()
        assert 'workspace_tab=waterfall' in page.url
        page.reload(wait_until='domcontentloaded');expect(page.locator('#abs-step-explorer')).to_be_visible()
        checks.append('ABS five tasks, selected priority exact paid/cash, tranche detail, checks/terms and period/task reload')
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(out/'abs-waterfall-mobile.png'),full_page=True)
        checks.append('390px ABS priority explorer and detail without page overflow')
        page.set_viewport_size({'width':1440,'height':1000});page.goto(base+'/?view=overview',wait_until='domcontentloaded');expect(page.locator('.mortgage-task-link')).to_have_count(9)
        page.locator('[data-mortgage-task="transitions"]').click();expect(page.locator('.matrix-cell button').first).to_be_visible();page.locator('.matrix-cell button').first.click();expect(page.locator('.matrix-detail')).to_contain_text('Origin denominator')
        page.locator('[data-mortgage-task="lifecycle"]').click();expect(page.locator('.loan-row').first).to_be_visible();expect(page.locator('#content')).to_contain_text('Observed current UPB');page.locator('.loan-row').nth(1).click();expect(page.locator('#content')).to_contain_text('Confirmed episode events')
        expect(page.locator('.loan-row').nth(1)).to_have_attribute('aria-pressed','true')
        page.screenshot(path=str(out/'mortgage-lifecycle-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('.loan-selection-list').evaluate('(n)=>n.clientHeight<=320&&n.scrollHeight>n.clientHeight')
        page.screenshot(path=str(out/'mortgage-lifecycle-mobile.png'),full_page=True)
        checks.append('Mortgage nine actual task routes, supported transition-cell detail and selected private loan lifecycle; desktop/mobile')
        assert not errors,errors;assert sha256(ledger)==before;checks.append('No unexpected browser errors or consumed Retail holdout mutation')
        browser.close()
    write_new(out/'receipt.json',{'status':'PASS','completed_at':timestamp(),'checks':checks,'errors':errors,'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False});print(json.dumps({'status':'PASS','checks':len(checks),'directory':str(out)},indent=2))
if __name__=='__main__':run()
