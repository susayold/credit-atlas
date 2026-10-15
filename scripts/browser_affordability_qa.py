import json,uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import sha256
root=Path.cwd();out=root/'artifacts/private'/('affordability-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);expect.set_options(timeout=60000)
with sync_playwright() as p:
    b=p.chromium.launch(channel='msedge',headless=True);page=b.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8770/?view=retail&workspace_tab=affordability&view_id=suite-view-74e07524f6d0')
    export=page.get_by_role('button',name='Xuất affordability JSON',exact=True)
    expect(export).to_be_disabled();assert page.locator('#affordability-result').count()==0
    assert page.locator('.affordability-item').count()==0
    page.get_by_label('Affordability case reference',exact=True).fill('qa-case')
    page.get_by_label('Affordability scope reference',exact=True).fill('qa-member')
    page.get_by_label('Affordability currency',exact=True).fill('USD')
    page.get_by_label('Affordability assessment date',exact=True).fill('2026-10-12')
    for group,title,amount,period in [('gross_income','Gross income','60000','annual'),('net_income','Net income','4000','monthly'),('recurring_expenses','Recurring non-debt expenses','1500','monthly'),('debt_payments','Existing debt payments','1500','monthly'),('proposed_payments','Proposed payments','500','monthly')]:
        page.get_by_role('button',name='Thêm dòng '+title,exact=True).click()
        page.get_by_label(group+' Reference 1',exact=True).fill('qa-'+group)
        page.get_by_label(group+' Amount 1',exact=True).fill(amount)
        page.get_by_label(group+' Period 1',exact=True).select_option(period)
        page.get_by_label('Coverage '+group,exact=True).check()
    page.get_by_label('Affordability policy reference',exact=True).fill('qa-policy')
    page.get_by_label('Maximum total DTI fraction',exact=True).fill('0.4')
    page.get_by_label('Minimum monthly residual',exact=True).fill('500')
    page.get_by_role('button',name='Tính affordability',exact=True).click()
    result=page.locator('#affordability-result');expect(result).to_contain_text('WITHIN_DECLARED_LIMIT');expect(result).to_contain_text('MEETS_DECLARED_FLOOR')
    with page.expect_download() as dl:export.click()
    dl.value.save_as(out/'assessment.json');r=json.loads((out/'assessment.json').read_text())
    assert r['baseline']['gross_monthly_income']['decimal50']=='5000' and r['baseline']['total_dti_fraction']['decimal50']=='0.4'
    assert r['baseline']['monthly_residual_after_expenses_and_debt']['decimal50']=='500' and r['credit_decision'] is None
    assert not r['income_verification_qualified'] and not r['policy_confirmed']
    checks.append('Empty intake has no fictitious assessment;explicit inputs normalize correctly and private export keeps unverified status')
    pending=[];late_downloads=[]
    page.on('download',lambda d:late_downloads.append(d))
    page.route('**/api/affordability-report',lambda route:pending.append(route))
    export.click();page.wait_for_timeout(100);assert len(pending)==1
    page.get_by_label('net_income Amount 1',exact=True).fill('3000')
    pending[0].fulfill(status=200,content_type='application/json',body=json.dumps(r))
    page.wait_for_timeout(150);assert not late_downloads
    page.unroute('**/api/affordability-report')
    page.get_by_label('net_income Amount 1',exact=True).fill('3000');expect(export).to_be_disabled();assert result.count()==0
    page.get_by_role('button',name='Tính affordability',exact=True).click();expect(result).to_contain_text('BELOW_DECLARED_FLOOR')
    page.get_by_label('Enable affordability sensitivity',exact=True).check()
    page.get_by_label('Gross income reduction fraction',exact=True).fill('0.1');page.get_by_label('Net income reduction fraction',exact=True).fill('0.25');page.get_by_label('Extra monthly expense',exact=True).fill('250')
    page.get_by_role('button',name='Tính affordability',exact=True).click();expect(result).to_contain_text('EXCEEDS_DECLARED_LIMIT');expect(result).to_contain_text('-1500')
    page.locator('#affordability-result').screenshot(path=str(out/'desktop-results.png'))
    checks.append('Editing clears stale results/export;sensitivity keeps baseline and shows negative residual')
    page.get_by_label('proposed_payments Amount 1',exact=True).fill('');page.get_by_role('button',name='Tính affordability',exact=True).click()
    expect(result).to_contain_text('UNAVAILABLE')
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.locator('#affordability-result').screenshot(path=str(out/'mobile-results.png'))
    checks.append('Blank required payment propagates unavailable;mobile fits page')
    page.route('**/api/affordability-assess',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Controlled affordability outage"}'))
    page.get_by_role('button',name='Tính affordability',exact=True).click();expect(page.locator('#affordability')).to_contain_text('Controlled affordability outage');expect(export).to_be_disabled();assert result.count()==0
    page.unroute('**/api/affordability-assess');page.get_by_role('button',name='Tính affordability',exact=True).click();expect(result).to_contain_text('UNAVAILABLE')
    checks.append('Outage removes stale assessment/export and retry recovers')
    assert not errors,errors;assert sha256(ledger)==before;b.close()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'browser_errors':errors,'ledger_unchanged':True,'qa_inputs_only':True},indent=2),encoding='utf8');print(out);print('PASS',len(checks))
