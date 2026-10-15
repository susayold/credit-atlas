"""Current SBA scope/quality/dictionary and all program/dimension export checks."""
import json
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import read_json, sha256, write_new

root = Path.cwd();base = 'http://127.0.0.1:8770';view = 'suite-view-74e07524f6d0'
case = root/'artifacts/private/business-sba-21c568f10f7d'
aggregates = read_json(case/'aggregates.json');quality = read_json(case/'quality.json');dictionary = read_json(case/'dictionary.json')
out = root/'artifacts/private'/('sba-june-browser-acceptance-'+uuid4().hex[:12]);out.mkdir()
ledger = root/'artifacts/private/retail-holdout-access.sqlite';before = sha256(ledger);errors = [];checks = []
expect.set_options(timeout=120000)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge',headless=True)
    page = browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'/?view=business&workspace_tab=cohorts&view_id='+view)
    expect(page.get_by_label('SBA program',exact=True)).to_be_visible()
    combinations = 0
    for program in ['all','7A','504']:
        page.get_by_label('SBA program',exact=True).select_option(program)
        for dimension, population in aggregates['dimensions'].items():
            page.get_by_label('SBA dimension',exact=True).select_option(dimension)
            expected = [r for r in population if program == 'all' or r['program'] == program]
            panel = page.locator('#business-panel-cohorts')
            expect(panel).to_contain_text(f'{sum(r["records"] for r in expected):,} selected source records')
            displayed = [r.locator('td').all_text_contents()[:4] for r in panel.locator('table tbody tr').all()]
            assert displayed == [[r['program'],r['bucket'],r['status'],format(r['records'],',')] for r in expected]
            query = {'view_id':view,'program':program,'dimension':dimension,'bucket':'all'}
            response = page.request.get(base+'/api/business-report?'+urlencode(query),timeout=120000)
            assert response.status == 200, (query, response.status, response.text())
            report = response.json();assert report['rows'] == expected and report['quality'] == quality
            assert report['quality_scope'] == 'whole_source_all_six_segments_not_filtered_by_aggregate_controls'
            assert report['contract']['amounts_are_current_exposure'] is False and report['fixed_horizon_default_target_qualified'] is False
            with page.expect_download() as d:page.locator('#export-report').click()
            path = out/f'{program}-{dimension}.json';d.value.save_as(path)
            assert read_json(path) == report
            # A specific nonempty bucket additionally checks scoped support and denominator filtering.
            bucket = next(r['bucket'] for r in expected)
            if bucket != 'all':
                page.get_by_label('SBA bucket',exact=True).select_option(bucket)
                selected = [r for r in expected if r['bucket'] == bucket]
                expect(panel).to_contain_text(f'{sum(r["records"] for r in selected):,} selected source records')
                scoped = page.request.get(base+'/api/business-report?'+urlencode({**query,'bucket':bucket})).json()
                assert scoped['rows'] == selected
            combinations += 1
    checks.append('12program/dimension whole-scope UI/API/download exact-row parities plus9selected buckets')
    page.reload();expect(page.get_by_label('SBA program',exact=True)).to_have_value('504')
    expect(page.get_by_label('SBA dimension',exact=True)).to_have_value('naics_two_digit')
    checks.append('Scoped program/dimension/bucket restored by URL reload')
    page.get_by_role('tab',name='Chất lượng',exact=True).click()
    panel = page.locator('#business-panel-quality')
    actual = [r.locator('td').all_text_contents() for r in panel.locator('table tbody tr').all()]
    assert actual == [[id,format(q['retained_rows'],','),format(q['exact_duplicate_excess_rows'],','),format(q['flags']['event_date_after_snapshot'],','),format(q['flags']['disbursement_before_approval'],','),format(q['flags']['charged_off_missing_date'],','),format(q['flags']['chargeoff_exceeds_approval'],',')] for id,q in quality.items()]
    checks.append('All6source quality rows match retained/duplicate/date/outcome flags')
    page.get_by_role('tab',name='Dictionary',exact=True).click()
    box = page.locator('#business-source-dictionary')
    actual = [r.locator('td').all_text_contents() for r in box.locator('table tbody tr').all()]
    # HTTP JSON sorts object keys;list entries and source cell coordinates remain exact.
    assert actual == [[p,e['field'],e['definition'],e['sheet']+' · '+e['field_cell']+' / '+e['definition_cell']] for p,entries in sorted(dictionary.items()) for e in entries]
    assert len(actual) == 81
    box.screenshot(path=str(out/'dictionary-desktop.png'))
    checks.append('All81dictionary definitions and162source cell coordinates rendered exactly')
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.screenshot(path=str(out/'mobile.png'))
    page.get_by_role('tab',name='Nguồn & giới hạn',exact=True).click()
    expect(page.locator('#business-historical-archive a')).to_be_visible()
    checks.append('Mobile no page overflow;separate March archive still loads')
    for extra in [{'program':'bad'},{'dimension':'bad'},{'bucket':'missing-bucket'},{'loan_id':'1'}]:
        assert page.request.get(base+'/api/business-report?'+urlencode({'view_id':view,**extra})).status == 400
    assert page.request.get(base+'/api/business-report?view_id='+view,headers={'Origin':'https://outside.example'}).status == 403
    checks.append('Invalid scope/raw-loan filter and cross-origin blocked')
    browser.close()
assert not errors and sha256(ledger) == before
write_new(out/'receipt.json',{'status':'PASS','checks':checks,'program_dimension_combinations':combinations,
    'dictionary_fields_checked':81,'quality_source_rows_checked':6,'ledger_unchanged':True,'page_errors':errors,
    'app_js_sha256':sha256(root/'apps/web/app.js'),'server_sha256':sha256(root/'src/credit_atlas/server.py'),
    'business_receipt_sha256':sha256(case/'business-complete.json'),'method_sha256':sha256(Path(__file__))})
print(json.dumps({'output':str(out),'status':'PASS','checks':len(checks)}))
