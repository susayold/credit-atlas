"""Actual scoped HMDA intersections, unavailable rates, private exports and UI QA."""
import argparse
import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

import duckdb
from playwright.sync_api import expect, sync_playwright

from browser_navigation import navigate_workspace, select_task
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new

expect.set_options(timeout=60000)


def run(root, web_root=None):
    root = root.resolve()
    web_root = (web_root or (Path(__file__).resolve().parents[1] / 'apps' / 'web')).resolve()
    if root.drive.upper() != 'D:':
        raise ValueError('Private HMDA browser QA data must remain on D:')
    output = root / 'artifacts/private' / ('hmda-browser-qa-' + uuid.uuid4().hex[:12]); output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / 'qa-reviews.sqlite3')
    identifier = next(row['view_id'] for row in service.hmda_views.catalog()['views'] if row['status'] == 'verified')
    snapshot = service.hmda_views.view(identifier)
    reference_id = next(row['reference_id'] for row in service.hmda_reference_views.catalog(snapshot['source_id'])['references'] if row['status'] == 'verified')
    names = service.hmda_reference_views.reference(reference_id, snapshot['source_id'])
    cohort_id = next(row['cohort_id'] for row in service.hmda_cohort_views.catalog(snapshot['case_id'])['cohorts'] if row['status'] == 'verified')
    path = root / 'artifacts/private' / snapshot['case_id'] / 'applications.parquet'
    connection = duckdb.connect(); connection.from_parquet(str(path)).create_view('applications')
    lender = connection.execute("SELECT lei,count(*) n FROM applications WHERE activity_year=2024 AND county_code='24031' AND loan_type='2' AND dti_public_category='45' GROUP BY 1 ORDER BY n DESC,lei LIMIT 1").fetchone()[0]
    seen = set(connection.execute('SELECT DISTINCT county_code,loan_type,dti_public_category FROM applications WHERE activity_year=2024 AND lei=?', [lender]).fetchall())
    impossible = next((county, loan, dti) for county in snapshot['options']['county'] for loan in snapshot['options']['loan_type'] for dti in snapshot['options']['dti'] if (county,loan,dti) not in seen)
    connection.close()
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(service, web_root=web_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port); checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000}); page.set_default_timeout(60000)
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
            url = base + '/?view=hmda&hmda_panel=legacy&hmda_view_id=' + identifier
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#context-note')).to_contain_text('347,056 public records · 99 fields')
            expect(page.locator('#hmda-summary .metric-value').nth(0)).to_have_text('117,817')
            expect(page.locator('#hmda-summary .metric-value').nth(1)).to_have_text('72,103')
            expect(page.locator('#hmda-summary .metric-value').nth(2)).to_have_text('10.0495%')
            assert page.locator('#run-select').is_disabled()
            assert page.locator('#hmda-actions tbody tr').count() == 8
            expect(page.locator('#hmda-actions tbody tr').nth(5)).to_contain_text('27,009')
            checks.append('Actual 2025 records/denominator/rate; purchased loans separate, eight source action categories, mortgage controls isolated')
            expect(page.locator('#hmda-reference-coverage')).to_contain_text('439')
            expect(page.get_by_label('HMDA dated name reference')).to_have_value(reference_id)
            missing = next(iter(names['coverage'][-1]['lender']['unresolved_source_keys']))
            expect(page.get_by_label('HMDA lender LEI').locator('option[value="' + missing + '"]')).to_contain_text('Chưa có tên')
            checks.append('Explicit source-bound reference receipt, actual 2025 unmatched label and whole-year coverage')
            expect(page.locator('#hmda-cohort-totals tbody tr').nth(2)).to_contain_text('100,934')
            expect(page.locator('#hmda-cohort-totals tbody tr').nth(2)).to_contain_text('60,070')
            expect(page.locator('#hmda-cohort-fixed tbody tr').nth(2)).to_contain_text('8.6183%')
            expect(page.locator('#hmda-cohort-comparison')).to_contain_text('không áp dụng lender/county/product/DTI filters')
            assert page.locator('#hmda-cohort-attrition tbody tr').count() == 15
            checks.append('Actual strict principal/1-4/first-lien/closed/non-reverse cohort counts, rates and ordered exclusions')
            page.get_by_label('HMDA comparison cohort').select_option('all_source')
            expect(page.locator('#hmda-cohort-fixed tbody tr').nth(1)).to_contain_text('INCOMPLETE_SUPPORT')
            expect(page.locator('#hmda-cohort-fixed tbody tr').nth(1).locator('td').nth(2)).to_have_text('Unavailable')
            expect(page.locator('#hmda-cohort-common tbody tr').nth(2)).to_contain_text('9.9361%')
            checks.append('Actual incomplete full support stays unavailable; common subset weighted rate is separately labeled')
            cohort_query = {'cohort_id':cohort_id,'case_id':snapshot['case_id'],'cohort':'all_source'}
            with page.expect_download() as info: page.get_by_role('button',name='Xuất cohort comparison').click()
            info.value.save_as(str(output/'hmda-cohort-export.json'))
            assert read_json(output/'hmda-cohort-export.json') == service.hmda_cohort_views.report(cohort_query)
            checks.append('Exact private cohort export includes support, rational weights, source counts and attrition')
            page.screenshot(path=str(output/'hmda-cohort-desktop.png'),full_page=True)
            page.screenshot(path=str(output / 'hmda-desktop.png'), full_page=True)
            chosen = {'year':'2024','lei':lender,'county':'24031','loan_type':'2','dti':'45','dimension':'lender'}
            for key, label in [('year','activity year'),('lei','lender LEI'),('county','county FIPS'),('loan_type','loan type'),('dti','DTI category'),('dimension','breakdown dimension')]:
                page.get_by_label('HMDA ' + label).select_option(chosen[key])
            expect(page.get_by_label('HMDA lender LEI').locator('option[value="' + lender + '"]')).to_contain_text(names['references']['2024']['lender'][lender]['names'][0])
            checks.append('Year change refreshes lender option names using exact 2024 reference')
            expected = service.hmda_reference_views.report(reference_id, {'view_id': identifier, **chosen})
            page.get_by_role('button', name='Đọc HMDA aggregates').click()
            expect(page.locator('#hmda-summary .metric-value').first).to_have_text(f"{expected['summary']['records']:,}")
            expect(page.locator('#hmda-breakdown')).to_contain_text(lender)
            assert expected['summary']['records'] > 0
            checks.append('Actual lender/county/FHA/public-DTI/year intersection, no marginal-mart approximation')
            expect(page.locator('#hmda-cohort-totals tbody tr').nth(2)).to_contain_text('117,817')
            checks.append('Whole-source comparison remains separate from intersecting top-panel filters')

            with page.expect_download() as info: page.locator('#export-report').click()
            info.value.save_as(str(output / 'hmda-filtered-export.json'))
            exported = read_json(output / 'hmda-filtered-export.json')
            assert exported == expected and exported['public_release_approved'] is False
            assert all(value is False for value in exported['qualification'].values())
            assert str(root) not in json.dumps(exported) and 'public_row_fingerprint' not in json.dumps(exported)
            checks.append('Exact private aggregate export equals verified query, no row identities/raw paths/default claim')
            page.reload(wait_until='networkidle')
            expect(page.get_by_label('HMDA lender LEI')).to_have_value(lender)
            expect(page.get_by_label('HMDA county FIPS')).to_have_value('24031')
            expect(page.get_by_label('HMDA DTI category')).to_have_value('45')
            expect(page.locator('#hmda-summary .metric-value').first).to_have_text(f"{expected['summary']['records']:,}")
            checks.append('Snapshot/year/lender/county/product/DTI/dimension survive URL reload')
            expect(page.get_by_label('HMDA comparison cohort')).to_have_value('all_source')
            expect(page.get_by_label('HMDA cohort receipt')).to_have_value(cohort_id)
            expect(page.locator('#hmda-cohort-fixed tbody tr').nth(1)).to_contain_text('INCOMPLETE_SUPPORT')
            checks.append('Cohort receipt/preset survive URL reload without becoming the top-panel filter scope')

            for key, label, value in [('county','county FIPS',impossible[0]),('loan_type','loan type',impossible[1]),('dti','DTI category',impossible[2])]:
                page.get_by_label('HMDA ' + label).select_option(value)
            page.get_by_role('button', name='Đọc HMDA aggregates').click()
            expect(page.locator('#hmda-summary .metric-value').first).to_have_text('0')
            expect(page.locator('#hmda-summary .metric-value').nth(2)).to_have_text('Unavailable')
            expect(page.locator('#content')).to_contain_text('Không có source records cho tổ hợp bộ lọc này')
            assert page.locator('#hmda-breakdown tbody tr').count() == 0
            checks.append('Known source categories with empty intersection return no records and unavailable rate, no fabricated fallback')
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#hmda-scope')).to_contain_text('450 public-equality groups')
            expect(page.locator('#hmda-scope')).to_contain_text('682 beyond-first rows retained')
            assert all(text.strip() == 'NO' for text in page.locator('#hmda-scope tbody td:nth-child(2)').all_text_contents())
            assert page.locator('#hmda-timeline svg path').evaluate_all('(paths)=>paths.length===1&&paths.every(p=>getComputedStyle(p).stroke!=="none")')
            checks.append('Whole-case duplicates scope explicit, false qualifications visible and rate chart styled')
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            expect(page.locator('#hmda-cohort-common')).to_be_visible()
            page.screenshot(path=str(output / 'hmda-mobile.png'), full_page=True)
            checks.append('390px mobile without page overflow, controls and financial tables contained')
            page.set_viewport_size({'width':1440,'height':1000})
            navigate_workspace(page, 'abs'); select_task(page, 'Waterfall')
            page.get_by_text('Toàn bộ ledger & allocations', exact=True).click()
            expect(page.locator('#abs-ledger')).to_contain_text('regular_principal')
            navigate_workspace(page, 'sec'); expect(page.locator('#sec-statement')).to_contain_text('AAPL')
            navigate_workspace(page, 'overview'); expect(page.locator('.metric-value').first).to_have_text('50,000')
            checks.append('P5 ABS/P3 SEC/P2 mortgage navigation remains operational')
            page.route('**/api/runs', lambda route: route.fulfill(json={'runs':[]}))
            page.goto(url, wait_until='networkidle'); expect(page.locator('#hmda-summary .metric-value').first).to_have_text('117,817')
            checks.append('HMDA evidence independent of mortgage run availability')
            assert not errors, errors; checks.append('No JavaScript/console errors')
            browser.close()
        write_new(output / 'receipt.json', {'status':'PASS','completed_at':timestamp(),'view_id':identifier,'reference_id':reference_id,'cohort_id':cohort_id,
            'checks':checks,'browser_errors':errors,'methods':{name:sha256(root/name) for name in
                ('apps/web/app.js','apps/web/style.css','src/credit_atlas/hmda_views.py','src/credit_atlas/hmda_cohorts.py','src/credit_atlas/hmda_cohort_views.py','src/credit_atlas/server.py')},
            'visibility':'private','public_release_approved':False})
        return {'status':'PASS','checks':len(checks),'directory':str(output)}
    except Exception as error:
        write_new(output / 'failed.json', {'status':'FAIL','exception_type':type(error).__name__,'checks_completed':checks,'browser_errors':errors})
        raise
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=app_root(), help='Private data root on D: (defaults to the checkout root)')
    parser.add_argument('--web-root', type=Path, default=Path(__file__).resolve().parents[1] / 'apps' / 'web', help='UI checkout to serve')
    args = parser.parse_args()
    print(json.dumps(run(args.root, args.web_root), indent=2))
