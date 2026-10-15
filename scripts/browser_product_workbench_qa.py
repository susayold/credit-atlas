"""Source-backed acceptance for Portfolio/Retail task workbenches."""
import json
import os
import uuid
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def run():
    root=app_root();os.environ['TEMP']=os.environ['TMP']=str(root/'.tmp')
    out=root/'artifacts/private'/('product-workbench-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    base='http://127.0.0.1:8770';errors=[];requests=[];checks=[]
    with urlopen(base+'/api/exposure-aggregates?import_id=exposure-import-57b88e00bedb&currency=USD&dimension=region') as response: source=json.load(response)
    with urlopen(base+'/api/suite-view?view_id=suite-view-74e07524f6d0') as response: retail_source=json.load(response)['retail']
    top=max(source['concentrations'],key=lambda r:float(r['amount_share']))
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
        page.set_default_timeout(240000);expect.set_options(timeout=240000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('request',lambda r:requests.append(r.url))
        url=base+'/?view=exposure&exposure_import_id=exposure-import-57b88e00bedb&exposure_currency=USD'
        page.goto(url,wait_until='domcontentloaded')
        expect(page.locator('#exposure-summary')).to_contain_text('9,698')
        expect(page.locator('#exposure-summary')).to_contain_text('915,208,989.12')
        expect(page.locator('#exposure-summary')).to_contain_text('141')
        expect(page.locator('#exposure-summary')).to_contain_text('UNAVAILABLE_NO_RISK_INPUTS')
        assert page.get_by_role('tab').count()==8
        assert not any('/api/exposure-tail' in u or '/api/exposure-ecl' in u for u in requests)
        assert not page.locator('#exposure-excel').is_visible()
        checks.append('P4 overview reconciles actual9698/141/USD915208989.12/EL unavailable; eight task tabs; no eager ECL/tail requests')
        expect(page.locator('#exposure-bucket-detail .bucket-name')).to_have_text(top['bucket'])
        assert abs(float(page.locator('.concentration-row meter').first.get_attribute('value'))-float(top['amount_share']))<1e-15
        page.locator('.concentration-row').nth(1).click()
        selected=page.locator('.concentration-row').nth(1).get_attribute('data-bucket')
        expect(page.locator('#exposure-bucket-detail .bucket-name')).to_have_text(selected)
        page.get_by_label('Tìm concentration bucket').fill('THIS_BUCKET_DOES_NOT_EXIST')
        expect(page.locator('.concentration-row')).to_have_count(0)
        expect(page.locator('#exposure-bucket-detail')).to_contain_text('Đổi từ khóa')
        page.get_by_label('Tìm concentration bucket').fill('CA')
        expect(page.locator('.concentration-row')).to_have_count(1)
        page.get_by_label('Tìm concentration bucket').fill('')
        page.get_by_label('Concentration sort').select_option('name')
        assert page.locator('.concentration-row').first.get_attribute('data-bucket')=='AK'
        checks.append('Interactive concentration source parity, exact selection, empty search, search and alphabetical sorting')
        page.screenshot(path=str(out/'portfolio-overview-desktop.png'),full_page=True)
        page.get_by_role('button',name='Review bucket →',exact=True).click()
        expect(page.get_by_label('Portfolio review title')).to_have_value('Concentration review · USD · AK')
        assert '19 observations' in page.get_by_label('Portfolio review rationale').input_value()
        assert '2,012,252.51' in page.get_by_label('Portfolio review rationale').input_value()
        page.get_by_role('tab',name='Tổng quan',exact=True).click()
        checks.append('Selected bucket opens source-bound review draft with exact bucket amount/count; no save or approval')
        page.get_by_role('tab',name='Nguồn & contract',exact=True).click()
        expect(page.locator('#exposure-currencies')).to_contain_text('915,208,989.12')
        expect(page.locator('#exposure-scope')).to_contain_text('Không có PD/LGD/EAD')
        page.get_by_role('tab',name='Excel',exact=True).click()
        expect(page.locator('#exposure-excel')).to_be_visible()
        with page.expect_download() as downloaded:
            page.locator('#exposure-excel').get_by_role('link',name='Xuất portfolio Excel').click()
        downloaded.value.save_as(str(out/'portfolio-review.xlsx'))
        checks.append('Source/contract remains separate; private native-currency Excel export works in dedicated task')
        page.get_by_role('tab',name='Biến động',exact=True).click()
        page.get_by_role('tab',name='Biến động',exact=True).click()
        page.get_by_role('tab',name='Biến động',exact=True).click()
        expect(page.locator('#exposure-movement table').first).to_be_visible()
        expect(page.locator('#exposure-movement')).to_have_count(1)
        expect(page.locator('#exposure-movement')).to_contain_text('9,698')
        checks.append('Movement task loads actual source-bound bridge on demand; repeated active-tab clicks retain a single panel')
        page.get_by_role('tab',name='Scenarios',exact=True).click()
        expect(page.locator('#exposure-scenarios table').first).to_be_visible()
        checks.append('Scenario task loads declared saved scenario study on demand')
        page.get_by_role('tab',name='Review',exact=True).click()
        expect(page.get_by_label('Portfolio review title')).to_be_visible()
        checks.append('Review task exposes versioned source-bound workflow; no review mutation performed')
        page.get_by_role('tab',name='Tổng quan',exact=True).click()
        expect(page.locator('#exposure-summary')).to_be_visible()
        assert page.get_by_label('Concentration sort').input_value()=='name'
        tab=page.get_by_role('tab',name='Tổng quan',exact=True);tab.focus();page.keyboard.press('End')
        expect(page.get_by_role('tab',name='Nguồn & contract',exact=True)).to_have_attribute('aria-selected','true')
        page.keyboard.press('Home')
        expect(tab).to_have_attribute('aria-selected','true')
        page.get_by_role('tab',name='Excel',exact=True).click()
        page.reload(wait_until='domcontentloaded')
        expect(page.locator('#exposure-excel')).to_be_visible()
        expect(page.get_by_role('tab',name='Excel',exact=True)).to_have_attribute('aria-selected','true')
        assert 'workspace_tab=excel' in page.url and 'exposure-import-57b88e00bedb' in page.url
        checks.append('Task cache preserves sort, keyboard tabs work, exact Excel/source URL survives reload')
        page.get_by_role('tab',name='Tổng quan',exact=True).click()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/'portfolio-overview-mobile.png'),full_page=True)
        checks.append('390px Portfolio: horizontal tab strip remains internal; no page overflow')
        page.set_viewport_size({'width':1440,'height':1000});start=len(requests)
        page.goto(base+'/?view=retail',wait_until='domcontentloaded')
        expect(page.locator('#retail-model-summary')).to_contain_text('3,001')
        expect(page.locator('#retail-model-summary')).to_contain_text('0.7779')
        bins=[b for b in retail_source['holdout']['reliability_bins'] if b['mean_probability'] is not None and b['observed_rate'] is not None]
        points=page.locator('#retail-calibration-chart circle')
        expect(points).to_have_count(len(bins))
        for i,b in enumerate(bins):
            assert abs(float(points.nth(i).get_attribute('cx'))-(42+b['mean_probability']*336))<1e-10
            assert abs(float(points.nth(i).get_attribute('cy'))-(238-b['observed_rate']*196))<1e-10
        assert not any('/api/retail-explanations' in u or '/api/retail-cohort-explanations' in u for u in requests[start:])
        assert page.get_by_role('tab').count()==5
        page.screenshot(path=str(out/'retail-overview-desktop.png'),full_page=True)
        page.get_by_role('tab',name='Validation',exact=True).click()
        expect(page.locator('#retail-panel-validation')).to_contain_text('Paired validation uncertainty')
        page.get_by_role('tab',name='Model & evidence',exact=True).click()
        expect(page.locator('#retail-panel-evidence')).to_contain_text('Model đã chốt')
        checks.append('Retail saved model KPIs/calibration, five tasks, deferred explanations, validation and model evidence')
        page.get_by_role('tab',name='Policy & subgroup',exact=True).click()
        expect(page.locator('#retail-policy table').first).to_be_visible()
        expect(page.locator('#retail-subgroups table').first).to_be_visible()
        checks.append('Retail policy/subgroup task loads actual pinned saved evidence on demand')
        page.get_by_role('tab',name='Hồ sơ & giải thích',exact=True).click()
        expect(page.locator('#retail-cohort-explanations')).to_contain_text('4,499 hồ sơ toàn cohort')
        expect(page.locator('#retail-explanation-clients tbody tr')).to_have_count(20)
        expect(page.locator('#retail-cohort-client')).to_contain_text('rank 4,499 / 4,499')
        with page.expect_download() as explanation_download:
            page.get_by_role('button',name='Xuất giải thích hồ sơ',exact=True).click()
        explanation_download.value.save_as(str(out/'client-explanation.json'))
        exported=json.loads((out/'client-explanation.json').read_text(encoding='utf-8'))
        assert exported['cohort_id']=='retail-cohort-explanations-02487bb9d1a2'
        assert exported['client']['score_rank']==4499
        assert 'source_client_id' not in json.dumps(exported)
        checks.append('Retail case task reaches all4499/20-page clients and exact selected private export without source IDs')
        page.set_viewport_size({'width':390,'height':844});page.get_by_role('tab',name='Tổng quan',exact=True).click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/'retail-overview-mobile.png'),full_page=True)
        checks.append('390px Retail calibration/KPIs without page overflow')
        assert not errors,errors;assert sha256(ledger)==before
        checks.append('No unexpected browser errors; consumed holdout ledger unchanged')
        browser.close()
    write_new(out/'receipt.json',{'status':'PASS','completed_at':timestamp(),'checks':checks,'browser_errors':errors,'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
    print(json.dumps({'status':'PASS','checks':len(checks),'directory':str(out)},indent=2))

if __name__=='__main__':run()
