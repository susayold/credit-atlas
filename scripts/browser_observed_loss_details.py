import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from playwright.sync_api import expect,sync_playwright
from credit_atlas.workspace import sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21';BASE='http://127.0.0.1:8770'
out=ROOT/'artifacts/private'/('observed-loss-details-browser-'+uuid4().hex[:12]);out.mkdir()
audit=json.loads((ROOT/'artifacts/private/observed-loss-source-audit-627ae17a9d01/receipt.json').read_text())
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);errors=[];checks=[];expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    response=page.request.get(BASE+'/api/observed-loss-details?run='+CASE,timeout=120000);assert response.status==200;r=response.json()
    assert r['visibility']=='private' and r['public_release_approved'] is False
    serialized=json.dumps(r).lower()
    assert not any(token in serialized for token in ['loan_id','borrower_id','ssn','disclosure_id','account_number'])
    for mode in ['signed','magnitude']:
        for key in ['mean','min','max']:assert Decimal(r[mode+'_ratio'][key+'_exact'])==Decimal(audit[mode+'_ratio'][key])
    assert r['expense_formula']['checked_rows']==audit['expense_formula_checked_rows']==374
    assert Decimal(r['expense_formula']['max_abs_residual_exact'])==Decimal(audit['max_abs_expense_residual_exact'])==0
    assert r['field_quality']['actual_loss']['negative']==17
    assert r['loss_formula']['checked_rows']==audit['loss_formula_checked_rows']==374
    assert Decimal(r['loss_formula']['max_abs_residual_exact'])==0
    assert r['expected_loss_dollars'] is None and r['selected_terminal_loans']==381
    for segment in ['all','relief','non_relief','unknown']:
        page.goto(BASE+f'/?run={CASE}&view=loss&segment={segment}&from=2020-01&to=2020-03&horizon=24&basis=balance')
        box=page.locator('#observed-loss-details');expect(box).to_be_visible()
        details=page.locator('section.card').filter(has=page.get_by_role('heading',name='Components & reconciliation',exact=True))
        money=lambda v:page.evaluate("v=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(Number(v))",v)
        assert [row.locator('td').all_text_contents() for row in details.locator('tbody tr').all()]==[[f,money(v)] for f,v in audit['signed_component_sum_exact'].items()]
        bridge=page.locator('svg[aria-label="Signed observed loss component bridge in USD"]')
        order=['removal_upb','delinquent_accrued_interest','total_expenses','net_sales_proceeds','mi_recoveries','non_mi_recoveries']
        cumulative=0;items=[]
        for f in order:
            value=float(audit['signed_component_sum_exact'][f]);start=cumulative;cumulative+=value;items.append((start,cumulative))
        items.append((0,float(audit['reported_loss_sum_exact'])))
        maximum=max(max(pair) for pair in items)*1.15
        rects=bridge.locator('rect').all();assert len(rects)==7
        for rect,(start,end) in zip(rects,items):
            expected_y=192-max(start,end)/maximum*172
            expected_h=max(1,abs(end-start)/maximum*172)
            assert abs(float(rect.get_attribute('y'))-expected_y)<1e-6
            assert abs(float(rect.get_attribute('height'))-expected_h)<1e-6
        expect(box).to_contain_text('Negative reported-loss loans17')
        expect(box).to_contain_text('Expense formula checked rows374')
        table=box.locator('table').nth(0)
        expected=[]
        for mode,label in [('signed','Signed loss / |removal UPB|'),('magnitude','Magnitude |loss| / |removal UPB|')]:
            q=r[mode+'_ratio'];expected.append([label,str(q['observations'])]+[f"{float(q[k+'_exact']):.6f}" for k in ['mean','min','max']])
        assert [row.locator('td').all_text_contents() for row in table.locator('tbody tr').all()]==expected
        expected_quality=[[f]+[format(q[k],',') for k in ['known','missing','negative','zero','positive']] for f,q in r['field_quality'].items()]
        assert [row.locator('td').all_text_contents() for row in box.locator('table').nth(1).locator('tbody tr').all()]==expected_quality
        with page.expect_download() as d:box.get_by_role('link',name='Xuất observed loss diagnostics JSON',exact=True).click()
        file=out/(segment+'-diagnostics.json');d.value.save_as(file);assert json.loads(file.read_text())==r
        with page.expect_download() as d:page.locator('#export-report').click()
        file=out/(segment+'-legacy-report.json');d.value.save_as(file);legacy=json.loads(file.read_text())
        loss=next(t for t in legacy['report']['tables'] if t['table_id']=='observed_loss_summary')
        assert loss['filters_applied']==[] and legacy['scope_notes']['loss'].startswith('Whole-sample')
        summary=loss['rows'][0]
        assert summary['terminal_loans']==381 and summary['reported_loss_loans']==374 and summary['unresolved_terminal_loans']==7
        assert abs(summary['reported_loss_sum_usd']-float(audit['reported_loss_sum_exact']))<1e-6
        checks.append({'segment':segment,'diagnostics_and_legacy_export':'PASS'})
        if segment=='all':box.screenshot(path=str(out/'desktop.png'))
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#observed-loss-details').screenshot(path=str(out/'mobile.png'))
    assert page.request.get(BASE+'/api/observed-loss-details?run='+CASE+'&segment=all').status==400
    assert page.request.get(BASE+'/api/observed-loss-details?run='+CASE,headers={'Origin':'https://example.com'}).status==403
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','scopes':checks,'source_decimal_parity':True,'field_quality_checks':len(r['field_quality'])*5*4,'mobile':True,'page_errors':errors,'ledger_unchanged':True,'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py'),'method_sha256':sha256(ROOT/'src/credit_atlas/observed_loss_details.py')},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','scopes':len(checks)}))
