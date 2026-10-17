"""Actual mortgage observation import, exact private exports and mobile acceptance."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
from browser_navigation import select_task

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, read_json, timestamp, write_new

expect.set_options(timeout=60000)


def run(root, web_root=None):
    output = root / 'artifacts/private' / ('exposure-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    service.exposure_convergence_views.evidence('exposure-convergence-0741003b87f4')
    identifier = 'exposure-import-57b88e00bedb'
    source = service.exposure_views.report({'import_id': identifier})
    assert source['records'] == 9698
    assert source['currencies'][0]['reported_amount_major_exact'] == '915208989.12'
    assert source['currencies'][0]['zero_amount_records'] == 141
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service, web_root=web_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(60000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            url = base + '/?view=exposure&exposure_import_id=' + identifier
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#page-title')).to_have_text('Freddie Mac Sample UPB Diagnostics')
            expect(page.locator('#freddie-sample-scope-banner')).to_contain_text('không chứng minh danh mục thuộc sở hữu bên cho vay')
            expect(page.locator('#freddie-sample-scope-banner')).to_have_attribute('role', 'note')
            expect(page.locator('#source-badge')).to_contain_text('not owned portfolio / EAD')
            checks.append('Freddie sample is explicitly labeled as raw UPB observations, not an owned portfolio/EAD')
            select_task(page, 'Tổng quan')
            expect(page.locator('#exposure-summary')).to_contain_text('9,698')
            expect(page.locator('#exposure-summary')).to_contain_text('Reported sample UPB')
            select_task(page, 'Tổng quan')
            expect(page.locator('#exposure-summary')).to_contain_text('2026-03')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('USD 915,208,989.12')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('141')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('UNAVAILABLE_NO_RISK_INPUTS')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-scope')).to_contain_text('Không có PD/LGD/EAD inputs')
            select_task(page, 'Excel')
            expect(page.locator('#exposure-excel')).to_contain_text('Nhập Excel')
            assert page.locator('#run-select').is_disabled()
            checks.append('9,698 Freddie sample observations, 141 zero UPBs, exact USD 915208989.12 and unavailable EL; no mortgage-run dependency')
            select_task(page, 'Biến động')
            expect(page.locator('#exposure-movement')).to_contain_text('106 opening-only')
            select_task(page, 'Biến động')
            expect(page.locator('#exposure-movement')).to_contain_text('USD -13,037,124.22')
            select_task(page, 'Biến động')
            expect(page.locator('#exposure-movement')).to_contain_text('2026-02 → 2026-03')
            checks.append('Paired Freddie sample snapshots: 9,698 continuing, 106 opening-only, native change and explicit no inferred exit reason')
            select_task(page, 'Scenarios')
            expect(page.locator('#exposure-scenario-scope')).to_contain_text('9,602')
            select_task(page, 'Scenarios')
            expect(page.locator('#exposure-scenario-scope')).to_contain_text('96')
            select_task(page, 'Scenarios')
            expect(page.locator('#exposure-scenario-comparison')).to_contain_text('USD 17,313,511.80')
            select_task(page, 'Scenarios')
            expect(page.locator('#exposure-scenarios')).to_contain_text('Giả định minh họa')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('UNAVAILABLE_NO_RISK_INPUTS')
            checks.append('9602 CURRENT eligible/96 excluded; illustrative scenario EL distinct from unavailable source EL')
            select_task(page, 'Scenarios')
            page.get_by_label('Exposure scenario detail').select_option('boundary_example')
            select_task(page, 'Scenarios')
            assert sum(int(value.replace(',','')) for value in page.locator('#exposure-scenario-attribution tbody tr td:last-child').all_text_contents())==9602
            select_task(page, 'Scenarios')
            assert page.locator('#exposure-scenario-attribution table').count()==1
            checks.append('Explicit LGD boundary scenario clipping counts; detail selection replaces table')
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-scope')).to_contain_text('9,602')
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-comparison')).to_contain_text('USD 23,530,061.94')
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl')).to_contain_text('chưa qualified accounting ECL')
            select_task(page, 'ECL')
            assert page.locator('#exposure-ecl-events tbody tr').count()==36
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-events tbody tr').nth(11).locator('td').last).to_have_text('YES')
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-events tbody tr').nth(12).locator('td').last).to_have_text('NO')
            checks.append('Declared research ECL scope and stage1 default-event cutoff retain all cash/recovery calculations')
            select_task(page, 'ECL')
            page.get_by_label('Exposure ECL segment').select_option('relief')
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-events tbody tr').nth(12).locator('td').last).to_have_text('YES')
            select_task(page, 'ECL')
            page.get_by_label('Exposure ECL scenario').select_option('adverse')
            select_task(page, 'ECL')
            assert page.locator('#exposure-ecl-events table').count()==1
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-events')).to_contain_text('"lag_months":12')
            checks.append('Stage2 retains month13 default; scenario/segment switches show declared recovery lag and replace table')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-scope')).to_contain_text('9,602')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-comparison')).to_contain_text('0.35')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-quantiles')).to_contain_text('40.96')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-quantiles')).to_contain_text('USD 215,933,346.47')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail')).to_contain_text('chưa qualified capital')
            select_task(page, 'Tail risk')
            assert page.locator('#exposure-tail-comparison tbody tr').count()==4
            select_task(page, 'Tail risk')
            assert page.locator('#exposure-tail-quantiles tbody tr').count()==8
            checks.append('Seeded 4,096-draw dependence/recovery sensitivity, finite 99% tail mass and assumption disclosure')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-convergence')).to_contain_text('20261011')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-convergence')).to_contain_text('6,144')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-convergence')).to_contain_text('chưa chứng nhận hội tụ')
            select_task(page, 'Review')
            expect(page.locator('#portfolio-review')).to_contain_text('Lưu portfolio review')
            select_task(page, 'Review')
            page.get_by_label('Portfolio review title').fill('QA declared research package')
            select_task(page, 'Review')
            page.get_by_label('Portfolio review owner').fill('Automated browser QA')
            select_task(page, 'Review')
            page.get_by_label('Portfolio review rationale').fill('Illustrative PD/LGD/EAD and dependence; no accounting or capital approval.')
            select_task(page, 'Review')
            page.get_by_role('button',name='Lưu portfolio review').click()
            select_task(page, 'Review')
            expect(page.locator('#portfolio-review')).to_contain_text('Đã lưu revision 1')
            select_task(page, 'Review')
            page.get_by_label('Portfolio review status').select_option('reviewed')
            select_task(page, 'Review')
            page.get_by_label('Acknowledge declared assumptions').check()
            select_task(page, 'Review')
            page.get_by_role('button',name='Lưu portfolio review').click()
            select_task(page, 'Review')
            expect(page.locator('#portfolio-review')).to_contain_text('Đã lưu revision 2')
            select_task(page, 'Review')
            with page.expect_download() as info: page.get_by_role('link',name='Xuất portfolio review').click()
            info.value.save_as(str(output/'portfolio-review-export.json'))
            review=read_json(output/'portfolio-review-export.json')
            assert review['revision']==2 and review['evidence_current'] and not review['qualification']['capital_approved']
            assert len(review['snapshots'])==4
            assert service.portfolio_reviews.report(identifier,review['id'],1)['status']=='draft'
            checks.append('Three-seed/three-draw-count diagnostics; research review creation, revision, exact export and preserved draft history')
            select_task(page, 'Excel')
            with page.expect_download(timeout=180000) as info: page.get_by_role('link',name='Xuất portfolio Excel').click()
            info.value.save_as(str(output/'portfolio-excel-export.xlsx'))
            import zipfile
            from xml.etree import ElementTree as ET
            from credit_atlas.excel_workspace import NS
            with zipfile.ZipFile(output/'portfolio-excel-export.xlsx') as workbook:
                summary=ET.fromstring(workbook.read('xl/worksheets/sheet1.xml'))
                amount=summary.find('.//s:c[@r="B7"]/s:v',NS)
                assert float(amount.text)==915208989.12
                model=ET.fromstring(workbook.read('xl/worksheets/sheet2.xml'))
                assert abs(float(model.find('.//s:c[@r="G20"]/s:v',NS).text)-17313511.79897183)<.01
                assert model.find('.//s:c[@r="G20"]/s:f',NS) is not None
            checks.append('Native XLSX report download: source amount and recalculated adverse formula parity')
            select_task(page, 'Biến động')
            page.locator('#exposure-movement').screenshot(path=str(output / 'movement-desktop.png'))
            page.screenshot(path=str(output / 'exposure-desktop.png'), full_page=True)
            page.get_by_label('Exposure currency').select_option('USD')
            page.get_by_label('Exposure dimension').select_option('source_state')
            page.get_by_role('button', name='Áp dụng phạm vi').click()
            select_task(page, 'Tổng quan')
            expect(page.locator('#exposure-bucket-detail')).to_contain_text('source_state')
            select_task(page, 'Biến động')
            expect(page.locator('#exposure-movement-groups .card-heading')).to_contain_text('source_state')
            select_task(page, 'Scenarios')
            expect(page.locator('#exposure-scenario-attribution .card-heading')).to_contain_text('source_state')
            select_task(page, 'ECL')
            expect(page.locator('#exposure-ecl-comparison')).to_contain_text('USD 23,530,061.94')
            select_task(page, 'ECL')
            with page.expect_download() as info: page.get_by_role('link',name='Xuất declared ECL study').click()
            info.value.save_as(str(output/'ecl-export.json'))
            ecl=read_json(output/'ecl-export.json')
            assert ecl==service.exposure_ecl_views.report({'ecl_id':'exposure-ecl-ba27d7207a44','source_import_id':identifier,'currency':'USD','dimension':'stage'})
            assert not ecl['contract']['accounting_compliance'] and not ecl['contract']['observed_contract_cashflows']
            assert ecl['stage_assessments']['non_relief']['stage']==1 and ecl['stage_assessments']['relief']['stage']==2
            select_task(page, 'ECL')
            page.locator('#exposure-ecl').screenshot(path=str(output/'ecl-desktop.png'))
            checks.append('Exact scoped ECL export includes scenario weights, full event curves and explicit assumption qualification')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-quantiles')).to_contain_text('40.96')
            select_task(page, 'Tail risk')
            with page.expect_download() as info: page.get_by_role('link',name='Xuất tail risk study').click()
            info.value.save_as(str(output/'tail-export.json'))
            tail=read_json(output/'tail-export.json')
            assert tail==service.exposure_tail_views.report({'tail_id':'exposure-tail-10a079f18dc9','source_import_id':identifier,'currency':'USD'})
            assert tail['global_cross_currency_total'] is None and not tail['contract']['calibrated_correlation']
            assert all(abs(sum(t['es_segment_contributions'].values())-t['es'])<1e-6 for r in tail['results'] for t in r['tails'])
            select_task(page, 'Tail risk')
            page.locator('#exposure-tail').screenshot(path=str(output/'tail-desktop.png'))
            checks.append('Private source-bound tail export parity and joint-tail segment ES conservation')
            select_task(page, 'Scenarios')
            with page.expect_download() as info: page.get_by_role('link',name='Xuất declared scenario set').click()
            info.value.save_as(str(output/'scenario-export.json'))
            scenario=read_json(output/'scenario-export.json')
            assert scenario==service.exposure_scenario_views.report({'scenario_id':'exposure-scenario-9655e30419ec','source_import_id':identifier,'currency':'USD','dimension':'source_state'})
            assert all(row['attribution_residual']['numerator']=='0' for s in scenario['scenarios'] for row in s['aggregates'])
            select_task(page, 'Scenarios')
            page.locator('#exposure-scenarios').screenshot(path=str(output/'scenario-desktop.png'))
            checks.append('Scenario filter follows confirmed dimension; exact rational/private versioned export')
            select_task(page, 'Biến động')
            expect(page.locator('#exposure-movement-transitions')).to_contain_text('USD 3,157,507.77')
            select_task(page, 'Biến động')
            expect(page.locator('#exposure-movement-transitions')).to_contain_text('CURRENT')
            select_task(page, 'Biến động')
            with page.expect_download() as info: page.get_by_role('link', name='Xuất movement bridge').click()
            info.value.save_as(str(output / 'movement-export.json'))
            movement = read_json(output / 'movement-export.json')
            assert movement == service.exposure_movement_views.report({'movement_id':'exposure-movement-dbd1ecad612e', 'closing_import_id':identifier,'dimension':'source_state','currency':'USD'})
            assert all(float(row['residual']) == 0 for row in movement['groups'])
            checks.append('Movement dimension follows confirmed scope; exact private bridge export and zero residuals')
            with page.expect_download() as info: page.locator('#export-report').click()
            info.value.save_as(str(output / 'exposure-export.json'))
            report = read_json(output / 'exposure-export.json')
            assert report == service.exposure_views.report({'import_id': identifier, 'currency': 'USD', 'dimension': 'source_state'})
            assert report['currencies'][0]['research_el_major_exact'] is None
            assert not report['public_release_approved']
            assert all(value is False for value in report['contract'].values() if type(value) is bool)
            assert 'position_id' not in report and 'source_lineage' not in report
            checks.append('Confirmed currency/dimension scope and exact private aggregate export; source IDs and paths excluded')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('Exposure currency')).to_have_value('USD')
            expect(page.get_by_label('Exposure dimension')).to_have_value('source_state')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('USD 915,208,989.12')
            checks.append('Import and confirmed scope survive URL reload')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-quantiles')).to_contain_text('40.96')
            page.set_viewport_size({'width': 390, 'height': 844})
            select_task(page, 'Review')
            expect(page.locator('#portfolio-review')).to_contain_text('Lưu portfolio review')
            select_task(page, 'Review')
            page.locator('#portfolio-review').screenshot(path=str(output/'portfolio-review-mobile.png'))
            page.screenshot(path=str(output / 'exposure-mobile.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            checks.append('390px mobile without page overflow')
            # An invalid explicit source must never fall back to a different import.
            page.goto(base + '/?view=exposure&exposure_import_id=exposure-import-000000000000', wait_until='networkidle')
            expect(page.locator('#content')).to_contain_text('Import trong URL không khả dụng')
            assert page.locator('#exposure-summary').count() == 0
            checks.append('Unavailable explicit import fails visibly without fallback')
            page.goto(url, wait_until='networkidle')
            select_task(page, 'Tổng quan')
            expect(page.locator('#exposure-summary')).to_contain_text('9,698')
            select_task(page, 'Tail risk')
            expect(page.locator('#exposure-tail-quantiles')).to_contain_text('40.96')
            assert not errors, errors
            checks.append('Valid source recovered; no JavaScript or console errors')
            select_task(page, 'Excel')
            with page.expect_download() as info: page.get_by_role('link',name='Tải mẫu Excel nhập danh mục').click()
            info.value.save_as(str(output/'input-template.xlsx'))
            select_task(page, 'Excel')
            page.get_by_label('Portfolio Excel workbook').set_input_files(str(output/'input-template.xlsx'))
            select_task(page, 'Excel')
            with page.expect_response('**/api/exposure-excel-import') as uploaded:
                page.get_by_role('button',name='Nhập Excel',exact=True).click()
            imported = uploaded.value.json()
            expect(page.get_by_label('Exposure import')).to_have_value(imported['import_id'])
            select_task(page, 'Tổng quan')
            expect(page.locator('#context-note')).to_contain_text('3 position/observation records')
            expect(page.locator('#context-note')).to_contain_text('declared_portfolio')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('USD 250,000')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('VND 1,000,000')
            select_task(page, 'Nguồn & contract')
            expect(page.locator('#exposure-currencies')).to_contain_text('UNAVAILABLE_NO_RISK_INPUTS')
            select_task(page, 'Excel')
            assert page.get_by_role('link',name='Xuất portfolio Excel').is_hidden()
            checks.append('Excel upload creates a new verified example snapshot, keeps USD/VND separate and zero/missing risk semantics')
            assert not errors,errors
            browser.close()
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(), 'import_id': identifier,
            'checks': checks, 'browser_errors': errors, 'visibility': 'private', 'public_release_approved': False})
        return {'status': 'PASS', 'checks': len(checks), 'directory': str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status': 'FAIL', 'exception_type': type(error).__name__,
            'checks_completed': checks, 'browser_errors': errors})
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def run_scope_smoke(root, web_root=None):
    """Fast UI-scope acceptance for Freddie sample UPB labels and limitations."""
    output = root / 'artifacts/private' / ('exposure-scope-browser-qa-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service, web_root=web_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            page.set_default_timeout(30000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs': []}))
            page.goto('http://127.0.0.1:' + str(server.server_port) + '/?view=exposure&exposure_import_id=exposure-import-57b88e00bedb', wait_until='networkidle')
            page.locator('#navigation [data-view="exposure"]').click()
            expect(page.locator('#page-title')).to_have_text('Freddie Mac Sample UPB Diagnostics')
            expect(page.locator('#freddie-sample-scope-banner')).to_contain_text('không chứng minh danh mục thuộc sở hữu bên cho vay')
            expect(page.locator('#freddie-sample-scope-banner')).to_have_attribute('role', 'note')
            expect(page.locator('#source-badge')).to_contain_text('not owned portfolio / EAD')
            page.screenshot(path=str(output / 'p4-scope-desktop.png'), full_page=True)
            checks.append('Title identifies the Freddie Mac 2012 sample and raw-UPB diagnostic')
            checks.append('Prominent scope banner disclaims lender ownership, borrower exposure, EAD and empirical expected loss')
            checks.append('Scope banner is exposed with the accessible note role')
            checks.append('Source badge identifies raw UPB and excludes owned-portfolio/EAD interpretation')
            page.get_by_role('tab', name='Tổng quan').click()
            expect(page.locator('#exposure-summary')).to_contain_text('Reported sample UPB')
            expect(page.locator('#context-note')).to_contain_text('Freddie Mac 2012 sample')
            checks.append('Summary metric and context bar retain the sample-UPB source label')
            checks.append('No browser JavaScript errors')
            assert not errors, errors
            browser.close()
        write_new(output / 'receipt.json', {'status': 'PASS', 'completed_at': timestamp(), 'import_id': 'exposure-import-57b88e00bedb',
            'source_namespace': 'Freddie-Mac-2012-annual-sample', 'checks': checks, 'browser_errors': errors,
            'visibility': 'private', 'public_release_approved': False})
        return {'status': 'PASS', 'checks': len(checks), 'directory': str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status': 'FAIL', 'exception_type': type(error).__name__,
            'checks_completed': checks, 'browser_errors': errors})
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    import sys
    runner = run_scope_smoke if len(sys.argv) > 1 and sys.argv[1] == '--scope-only' else run
    print(json.dumps(runner(app_root()), indent=2))
