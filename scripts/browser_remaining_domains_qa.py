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
        expect(page.locator('#sec-ratios')).to_be_visible();assert page.get_by_role('tab').count()==13
        sec_tasks=[('Payment rules','#sec-note-rules'),('Note cashflows','#sec-note-schedule'),('Utility DSCR','#utility-debt'),('Facilities & covenant','#sec-facilities'),('Issuer filings','#sec-events'),('Debt maturities','#sec-debt'),('Interest coverage','#sec-coverage'),('Corporate memo','#corporate-memos'),('Annual trends','#sec-trend'),('Financial statements','#sec-financial-fields'),('Concept evidence','.sec-evidence'),('Source quality','#sec-quality')]
        for label,selector in sec_tasks:
            page.get_by_role('tab',name=label,exact=True).click();expect(page.locator(selector).first).to_be_visible()
        page.get_by_role('tab',name='Financial statements',exact=True).click();expect(page.locator('#sec-financial-fields table')).to_be_visible()
        page.get_by_role('tab',name='Concept evidence',exact=True).click();expect(page.locator('.sec-evidence details').first).to_be_visible()
        page.locator('.sec-evidence summary').first.click();expect(page.locator('.sec-evidence details').first.locator('table')).to_be_visible()
        page.get_by_role('tab',name='Source quality',exact=True).click();expect(page.locator('#sec-quality')).to_contain_text('SEC API facts')
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(out/'sec-quality-mobile.png'),full_page=True)
        checks.append('SEC 13 tasks, issuer ratios, payment/cashflow rules, utility DSCR, facilities, filings, debt, coverage, memo, annual trends, statement/concept evidence and source quality render')
        checks.append('390px SEC task strip and source-quality tables do not overflow')
        page.set_viewport_size({'width':1440,'height':1000});page.reload(wait_until='domcontentloaded');expect(page.locator('#sec-quality')).to_be_visible()
        checks.append('SEC selected task and source snapshot survive reload')
        page.goto(base+'/?view=abs',wait_until='domcontentloaded');expect(page.locator('#abs-period-metrics')).to_be_visible();assert page.get_by_role('tab').count()==10
        abs_tasks=[('Tổng quan','#abs-panel-overview'),('Waterfall','#abs-step-explorer'),('Tranches','#abs-tranche-detail'),('Đối chiếu','#abs-source-checks'),('Static pool','#abs-panel-pool-history'),('Managed pool','#abs-panel-managed-pool'),('ABS-EE coverage','#abs-panel-absee-profile'),('Định nghĩa ABS-EE','#abs-panel-absee-dictionary'),('SOFR nguồn','#abs-benchmark'),('Terms & giới hạn','#abs-qualification')]
        for label,selector in abs_tasks:
            page.get_by_role('tab',name=label,exact=True).click();expect(page.locator(selector).first).to_be_visible()
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
        checks.append('ABS ten tasks render: reported waterfall, tranches, source checks, static/managed pools, ABS-EE profile/dictionary, SOFR and terms')
        checks.append('ABS selected priority exact paid/cash, tranche detail and period/task reload')
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
        export_page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);export_page.set_default_timeout(180000)
        export_page.on('pageerror',lambda e:errors.append(str(e)));export_page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'status of 503 (Service Unavailable)' not in m.text else None)
        fake_downloads=[];export_page.on('download',lambda d:fake_downloads.append(d.suggested_filename))
        def reject_export(url,ready,route,error,trigger,label):
            export_page.goto(base+url,wait_until='domcontentloaded');expect(export_page.locator(ready)).to_be_visible()
            export_page.route(route,lambda r:r.fulfill(status=503,content_type='application/json',body=json.dumps({'error':error})))
            trigger();expect(export_page.locator('#notice.error')).to_contain_text(error);assert fake_downloads==[]
            export_page.unroute(route);checks.append(label)
        reject_export('/?view=retail&view_id=suite-view-74e07524f6d0&workspace_tab=evidence','a[download][href^="/api/retail-dossier-report"]','**/api/retail-dossier-report*','Synthetic Retail dossier export outage',lambda:export_page.get_by_role('link',name='Xuất Retail model dossier JSON').click(),'Retail model dossier 503 is visible and creates no fake download')
        reject_export('/?view=business','#business-summary','**/api/business-report*','Synthetic SBA report outage',lambda:export_page.locator('#export-report').click(),'SBA aggregate report 503 is visible and creates no fake download')
        reject_export('/?view=abs','#abs-period-metrics','**/api/abs-report*','Synthetic ABS report outage',lambda:export_page.locator('#export-report').click(),'ABS period report 503 is visible and creates no fake download')
        reject_export('/?view=country&workspace_tab=macro','#country-timeline','**/api/country-report*','Synthetic World Bank report outage',lambda:export_page.locator('#export-report').click(),'World Bank country report 503 is visible and creates no fake download')
        reject_export('/?view=country&workspace_tab=sovereign','#sovereign-controls','**/api/sovereign-defaults-report*','Synthetic sovereign report outage',lambda:export_page.locator('#export-report').click(),'Sovereign default report 503 is visible and creates no fake download')
        export_page.close()
        checks.append('Retail, SBA, ABS, World Bank and sovereign export failures tested against their selected real workspaces')
        assert not errors,errors;assert sha256(ledger)==before;checks.append('No unexpected browser errors or consumed Retail holdout mutation')
        browser.close()
    write_new(out/'receipt.json',{'status':'PASS','completed_at':timestamp(),'checks':checks,'errors':errors,'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False});print(json.dumps({'status':'PASS','checks':len(checks),'directory':str(out)},indent=2))
if __name__=='__main__':run()
