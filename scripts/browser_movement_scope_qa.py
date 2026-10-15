"""All actual native-currency/dimension scopes, exports and outage UI guards."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from uuid import uuid4
import json
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import read_json,sha256,write_new
from browser_navigation import select_task

ROOT=Path(__file__).resolve().parents[1];base='http://127.0.0.1:8770'
movement='exposure-movement-dbd1ecad612e';folder=ROOT/'artifacts/private'/movement
receipt=read_json(folder/'movement-complete.json');report=read_json(folder/'report.json')
assert sha256(folder/'report.json')==receipt['report_sha256']
assert all(sha256(ROOT/p)==h for p,h in receipt['inputs_sha256'].items())
out=ROOT/'artifacts/private'/('movement-scope-browser-'+uuid4().hex[:12]);out.mkdir();scopes=[];errors=[]
protected=[ROOT/'artifacts/private'/n for n in ['retail-holdout-access.sqlite','bankruptcy-holdout-access.sqlite']]
before={str(p.relative_to(ROOT)):sha256(p) for p in protected}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True)
    page.on('pageerror',lambda e:errors.append(str(e)))
    for currency in ['all',*[r['currency'] for r in report['currencies']]]:
        for dimension in ['region','segment','source_state','representation']:
            query={'movement_id':movement,'closing_import_id':receipt['closing_import_id'],'currency':currency,'dimension':dimension}
            with urlopen(base+'/api/exposure-movement-report?'+urlencode(query),timeout=120) as response:
                assert 'attachment;' in response.headers['Content-Disposition'] and response.headers['Cache-Control']=='no-store';expected=json.load(response)
            assert expected['identity_counts']==report['identity_counts'] and expected['identity_counts_scope']=='Whole pair, independent of currency filter'
            assert expected['currencies']==[r for r in report['currencies'] if currency in ['all',r['currency']]]
            for key in ['groups','transitions']:
                assert expected[key]==[r for r in report[key] if r['dimension']==dimension and currency in ['all',r['currency']]]
            assert expected['global_cross_currency_total'] is None and all(not v for v in expected['contract'].values() if isinstance(v,bool))
            page.goto(base+'/?view=exposure&workspace_tab=movement&exposure_import_id='+receipt['closing_import_id']+'&exposure_currency='+currency+'&exposure_dimension='+dimension)
            expect(page.get_by_role('link',name='Xuất movement bridge',exact=True)).to_be_visible(timeout=180000)
            select_task(page,'Biến động')
            panel=page.locator('#exposure-movement')
            expect(panel).to_contain_text('106 opening-only')
            expect(panel).to_contain_text('không phải FX P&L')
            expect(page.locator('#exposure-movement-groups tbody tr')).to_have_count(len(expected['groups']))
            with page.expect_download() as d:page.get_by_role('link',name='Xuất movement bridge',exact=True).click()
            export=out/(currency+'-'+dimension+'.json');d.value.save_as(export);assert read_json(export)==expected
            scopes.append({'currency':currency,'dimension':dimension,'group_rows':len(expected['groups']),'transition_rows':len(expected['transitions']),'export':export.name,'sha256':sha256(export)})
    panel.screenshot(path=str(out/'movement-desktop.png'))
    page.reload();expect(page.get_by_role('link',name='Xuất movement bridge',exact=True)).to_be_visible(timeout=180000)
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    panel.screenshot(path=str(out/'movement-mobile.png'))
    page.route('**/api/exposure-movement?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA movement outage"}'))
    page.get_by_label('Exposure movement pair',exact=True).dispatch_event('change')
    expect(panel).to_contain_text('QA movement outage',timeout=30000)
    expect(page.get_by_role('link',name='Xuất movement bridge',exact=True)).to_have_count(0)
    page.unroute('**/api/exposure-movement?**')
    page.get_by_label('Exposure movement pair',exact=True).dispatch_event('change')
    expect(page.get_by_role('link',name='Xuất movement bridge',exact=True)).to_be_visible(timeout=180000)
    browser.close()
for change in [{'closing_import_id':receipt['opening_import_id']},{'currency':'GBP'},{'dimension':'loan_id'},{'pd':'1'}]:
    query={'movement_id':movement,'closing_import_id':receipt['closing_import_id'],**change}
    try:
        with urlopen(base+'/api/exposure-movement-report?'+urlencode(query),timeout=120):raise AssertionError('Invalid bridge scope accepted')
    except HTTPError as e:assert e.code==400
assert not errors and all(sha256(ROOT/p)==h for p,h in before.items())
write_new(out/'receipt.json',{'status':'PASS','scopes':scopes,'outage_recovery':True,'reload_mobile':True,'page_errors':errors,
    'protected_sha256_unchanged':before,'method_sha256':sha256(Path(__file__)),
    'movement_receipt_sha256':sha256(folder/'movement-complete.json'),'source_report_sha256':sha256(folder/'report.json'),
    'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'view_method_sha256':sha256(ROOT/'src/credit_atlas/exposure_movement_views.py')})
print(out)
