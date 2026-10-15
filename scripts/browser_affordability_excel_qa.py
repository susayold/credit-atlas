"""Synthetic workbook upload QA; no fabricated customer/source records."""
import importlib.util
import json
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import sha256

root=Path.cwd();out=root/'artifacts/private'/('affordability-excel-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
spec=importlib.util.spec_from_file_location('qa_fixture',root/'tests/test_affordability_excel.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);checks=[];errors=[]
expect.set_options(timeout=60000)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8770/?view=retail&workspace_tab=affordability&view_id=suite-view-74e07524f6d0')
    link=page.get_by_role('link',name='Tải mẫu affordability Excel',exact=True)
    try: expect(link).to_be_visible()
    except Exception:
        page.screenshot(path=str(out/'failure.png'),full_page=True)
        (out/'failure.json').write_text(json.dumps({'page_errors':errors,'body':page.locator('body').inner_text()},ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    with page.expect_download() as d:link.click()
    d.value.save_as(out/'blank-template.xlsx')
    assert sha256(out/'blank-template.xlsx')==sha256(root/'apps/excel/templates/CreditAtlas-Affordability-Input.xlsx')
    checks.append('App template download matches pinned blank workbook bytes')
    file=page.get_by_label('Affordability Excel file',exact=True)
    file.set_input_files(str(root/'artifacts/private/affordability-template-roundtrip-20261012/qa-filled.xlsx'))
    result=page.locator('#affordability-result');expect(result).to_contain_text('WITHIN_DECLARED_LIMIT');expect(result).to_contain_text('MEETS_DECLARED_FLOOR')
    expect(page.get_by_label('gross_income Amount 1',exact=True)).to_have_value('60000')
    page.get_by_text('Excel original source cells',exact=True).click()
    expect(page.locator('#affordability')).to_contain_text('C2')
    with page.expect_download() as d: page.get_by_role('button',name='Xuất affordability JSON',exact=True).click()
    d.value.save_as(out/'assessment.json');r=json.loads((out/'assessment.json').read_text())
    assert r['baseline']['total_dti_fraction']['decimal50']=='0.4' and r['baseline']['monthly_residual_after_expenses_and_debt']['decimal50']=='500'
    assert r['credit_decision'] is None and not r['income_verification_qualified']
    checks.append('Excel import hydrates explicit form,source cell trace and assessment/export arithmetic parity')
    page.get_by_label('net_income Amount 1',exact=True).fill('3000')
    expect(page.get_by_role('button',name='Xuất affordability JSON',exact=True)).to_be_disabled()
    assert result.count()==0
    page.get_by_role('button',name='Tính affordability',exact=True).click();expect(result).to_contain_text('BELOW_DECLARED_FLOOR')
    checks.append('Editing imported amount clears old assessment/export and recomputes current form')
    file.set_input_files({'name':'missing-qa.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':fixture.fixture_workbook(missing=True)})
    expect(page.get_by_label('proposed_payments Amount 2',exact=True)).to_have_value('')
    expect(result).to_contain_text('UNAVAILABLE')
    page.locator('#affordability').screenshot(path=str(out/'desktop.png'))
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'mobile.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    checks.append('Missing Excel payment stays unavailable and mobile page fits')
    file.set_input_files({'name':'formula-qa.xlsx','mimeType':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','buffer':fixture.fixture_workbook(formula=True)})
    expect(page.locator('#affordability')).to_contain_text('Invalid affordability intake')
    expect(page.get_by_role('button',name='Xuất affordability JSON',exact=True)).to_be_disabled()
    assert result.count()==0
    checks.append('Rejected formula upload clears stale assessment/export without fake completion')
    browser.close()
assert not errors and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'browser_errors':errors,'ledger_unchanged':True,'qa_inputs_only':True},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'checks':len(checks),'status':'PASS'}))
