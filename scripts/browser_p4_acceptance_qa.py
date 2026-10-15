"""P4 intake/reconciliation/bridge acceptance; isolates review database."""
import json,threading,uuid,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright,expect
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import sha256
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tests.test_excel_workspace import mutated,NS,TEMPLATE
from browser_navigation import select_task
expect.set_options(timeout=180000)

root=Path.cwd();out=root/'artifacts/private'/('p4-acceptance-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
service=ResearchService(root,review_path=out/'reviews.sqlite3')
print('Verifying saved P4 scenario/ECL/tail evidence before browser timing',flush=True)
service.exposure_scenario_views.catalog('exposure-import-57b88e00bedb')
service.exposure_ecl_views.catalog('exposure-import-57b88e00bedb')
service.exposure_tail_views.catalog('exposure-import-57b88e00bedb')
print('Saved evidence verified; browser checks starting',flush=True)
server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(service));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
server.daemon_threads=True
base='http://127.0.0.1:'+str(server.server_port);identifier='exposure-import-57b88e00bedb'
errors=[];checks=[];downloads=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
def api(path,q):
    with urlopen(base+path+'?'+urlencode(q)) as r:
        assert r.headers['Cache-Control']=='no-store';return json.load(r)
try:
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('download',lambda d:downloads.append(d.suggested_filename))
        page.goto(base+'/?view=exposure&exposure_import_id='+identifier)
        select_task(page,'Tổng quan');expect(page.locator('#exposure-summary')).to_contain_text('9,698',timeout=180000)
        expect(page.locator('#exposure-bucket-detail')).to_contain_text('không phải borrower identity')
        page.get_by_role('button',name='Review bucket →',exact=True).click()
        expect(page.get_by_label('Portfolio review title')).to_have_value(__import__('re').compile('Concentration review'))
        expect(page.get_by_label('Portfolio review rationale')).to_have_value(__import__('re').compile('Source amount không phải EAD'))
        checks.append('Real source overview/concentration/bucket→review draft preserves source grain and amount-vs-EAD scope')
        select_task(page,'Nguồn & contract');expect(page.locator('#exposure-currencies')).to_contain_text('UNAVAILABLE_NO_RISK_INPUTS')
        with page.expect_download() as dl:page.locator('#export-report').click()
        dl.value.save_as(out/'inventory.json')
        q={'import_id':identifier,'currency':'all','dimension':'region'}
        r=api('/api/exposure-report',q);downloaded=json.loads((out/'inventory.json').read_text(encoding='utf-8'))
        assert downloaded==r
        assert r['global_cross_currency_total'] is None and not r['contract']['amount_is_ead']
        assert r['currencies'][0]['research_el_major_exact'] is None
        checks.append('Private inventory export/API parity; missing risk stays null; no FX total; reported amount not EAD')
        assert len(downloads)==1,downloads
        page.route('**/api/exposure-report*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Synthetic P4 inventory report outage"}'))
        page.locator('#export-report').click();expect(page.locator('#notice.error')).to_contain_text('Synthetic P4 inventory report outage');assert len(downloads)==1,downloads
        page.unroute('**/api/exposure-report*');checks.append('P4 inventory HTTP 503 is visible and creates no fake download')
        select_task(page,'Biến động');expect(page.locator('#exposure-movement')).to_contain_text('106 opening-only',timeout=180000)
        expect(page.locator('#exposure-movement')).to_contain_text('không phải FX P&L')
        with page.expect_download() as dl:page.get_by_role('link',name='Xuất movement bridge',exact=True).click()
        dl.value.save_as(out/'movement.json')
        q={'movement_id':'exposure-movement-dbd1ecad612e','closing_import_id':identifier,'dimension':'region','currency':'all'}
        r=api('/api/exposure-movement-report',q);assert json.loads((out/'movement.json').read_text(encoding='utf-8'))==r
        assert not r['contract']['exit_reason_inferred'] and all(x['residual']=='0.00' or float(x['residual'])==0 for x in r['groups'])
        page.locator('#exposure-movement').screenshot(path=str(out/'movement-desktop.png'))
        checks.append('Source bridge/UI/API/export: explicit no inferred payoff/default, native-currency migration and retained residual')
        page.route('**/api/exposure-movement-report*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Synthetic P4 movement export outage"}'))
        page.get_by_role('link',name='Xuất movement bridge',exact=True).click();expect(page.locator('#notice.error')).to_contain_text('Synthetic P4 movement export outage');assert len(downloads)==2,downloads
        page.unroute('**/api/exposure-movement-report*');assert len(downloads)==2,downloads;checks.append('P4 movement export HTTP 503 is visible and creates no fake download')
        select_task(page,'Excel')
        invalid=out/'unsafe-numeric.xlsx'
        invalid.write_bytes(mutated('G2',lambda c:setattr(c.find('s:v',NS),'text','100000000000000.000000000000001')))
        imports_before=set(root.glob('artifacts/private/exposure-import-*'))
        page.get_by_label('Portfolio Excel workbook').set_input_files(str(invalid))
        page.get_by_role('button',name='Nhập Excel',exact=True).click()
        expect(page.locator('#exposure-excel')).to_contain_text('15 significant digits',timeout=180000)
        assert set(root.glob('artifacts/private/exposure-import-*'))==imports_before
        checks.append('Unsafe 30-significant-digit numeric XLSX rejected through browser/POST without creating import')
        page.get_by_label('Portfolio Excel workbook').set_input_files(str(TEMPLATE))
        page.get_by_role('button',name='Nhập Excel',exact=True).click()
        expect(page.locator('#context-note')).to_contain_text('3 position/observation records',timeout=180000)
        new_id=page.get_by_label('Exposure import',exact=True).input_value()
        r=api('/api/exposure-report',{'import_id':new_id,'currency':'all','dimension':'region'})
        assert r['global_cross_currency_total'] is None
        assert {x['currency']:x['reported_amount_major_exact'] for x in r['currencies']}=={'USD':'250000','VND':'1000000'}
        assert all(x['research_el_major_exact'] is None for x in r['currencies'])
        select_task(page,'Nguồn & contract');expect(page.locator('#exposure-currencies')).to_contain_text('VND 1,000,000')
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.locator('#exposure-currencies').screenshot(path=str(out/'intake-mobile.png'))
        assert not errors and sha256(ledger)==before
        checks.append('Valid EXAMPLE template upload→verified import; currencies/zero/null retained; mobile; frozen ledger unchanged')
        browser.close()
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'example_import_id':new_id,'ledger_unchanged':True,'desktop_excel_execution_tested':False},indent=2),encoding='utf8')
    print(out)
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)
