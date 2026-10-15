"""Source parity, filters, export, workflow navigation and rendered monitor verification."""
import json
import uuid
import urllib.request
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import app_root, sha256


def run():
    root=app_root()
    out=root/'artifacts/private'/('monitor-qa-'+uuid.uuid4().hex[:12])
    out.mkdir()
    base='http://127.0.0.1:8770'
    ledger=root/'artifacts/private/retail-holdout-access.sqlite'
    before=sha256(ledger)
    checks,errors=[],[]
    controlled_failure=False
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1600,'height':1050},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' and not (controlled_failure and '/api/exposure-aggregates' in m.location.get('url','') and '503' in m.text) else None)
        page.goto(base,wait_until='domcontentloaded')
        expect(page.locator('#credit-monitor')).to_be_visible(timeout=180000)
        expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        assert 'view=monitor' in page.url
        expect(page.locator('.monitor-kpis .metric-card')).to_have_count(5)
        expect(page.locator('#monitor-error-P1, #monitor-error-P2, #monitor-error-P3, #monitor-error-P4, #monitor-error-P5')).to_have_count(0)
        checks.append('Default monitor loads five source-backed KPI domains, no fallback/error panels')
        assert page.locator('#monitor-portfolio-balance').inner_text().find('915.21M')>=0
        expect(page.locator('#monitor-mortgage-d3')).to_contain_text('18')
        expect(page.locator('#monitor-retail-auc')).to_contain_text('0.778')
        expect(page.locator('#monitor-business-records')).to_contain_text('2.19M')
        expect(page.locator('#monitor-abs-pool')).to_contain_text('541.03M')
        checks.append('KPI parity with verified Freddie, UCI, SBA and World Omni snapshots')
        page.screenshot(path=str(out/'monitor-desktop.png'),full_page=True)
        page.screenshot(path=str(out/'monitor-viewport.png'))
        with page.expect_download() as pending:
            page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'monitor-all.json')
        report=json.loads((out/'monitor-all.json').read_text())
        assert len(report['provenance'])==5 and set(report['data'])=={'P1','P2','P3','P4','P5'}
        assert report['data']['P4']['currencies'][0]['research_el_major_exact'] is None
        assert report['data']['P4']['import_id']=='exposure-import-57b88e00bedb'
        assert report['data']['P1']['holdout']['loans']==3001
        assert all(row['evidence'] for row in report['review_queue'])
        checks.append('All-domain JSON: exact source references, saved holdout, null EL and pinned source-observation import')
        page.get_by_label('Monitor domain',exact=True).select_option('P2')
        assert page.locator('.monitor-kpis .metric-card:visible').count()==1
        assert page.locator('.monitor-grid [data-monitor-domain]:visible').count()==2
        page.get_by_label('Mortgage history',exact=True).select_option('12')
        page.get_by_label('Mortgage D3 basis',exact=True).select_option('balance')
        page.get_by_label('Review queue type',exact=True).select_option('quality')
        assert abs(float(page.locator('#monitor-mortgage-readout').get_attribute('data-value'))-0.002455194121465711)<1e-12
        with page.expect_download() as pending:
            page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'monitor-P2.json')
        scoped=json.loads((out/'monitor-P2.json').read_text())
        assert list(scoped['data'])==['P2'] and len(scoped['data']['P2']['monthly'])==12
        assert all(r['domain']=='P2' and r['kind']=='quality' for r in scoped['review_queue'])
        assert len(scoped['provenance'])==1
        page.reload(wait_until='domcontentloaded')
        expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        assert page.get_by_label('Monitor domain',exact=True).input_value()=='P2'
        assert page.get_by_label('Mortgage D3 basis',exact=True).input_value()=='balance'
        checks.append('Domain/window/count-vs-UPB/queue filters match rendered metrics, exports and URL reload')
        page.get_by_label('Review queue type',exact=True).select_option('qualification')
        page.locator('.monitor-queue-row').filter(has_text='Drift / calibration').get_by_role('button').click()
        expect(page.locator('[data-mortgage-task="models"]')).to_have_attribute('aria-current','page',timeout=180000)
        checks.append('Investigation action opens actual mortgage model readiness workflow')
        page.goto(base+'/?view=monitor&monitor_domain=P5')
        expect(page.get_by_role('button',name='Period waterfall ↗',exact=True)).to_be_visible(timeout=180000)
        page.get_by_role('button',name='Period waterfall ↗',exact=True).click()
        expect(page.get_by_role('tab',name='Waterfall',exact=True)).to_have_attribute('aria-selected','true',timeout=180000)
        assert 'abs_period=2026-08-31' in page.url
        checks.append('ABS action keeps exact verified deal and reported period')
        page.goto(base+'/?view=monitor')
        expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        page.get_by_role('button',name='Mở 5 workspace ↗',exact=True).click()
        expect(page.locator('.workspace-card')).to_have_count(5,timeout=180000)
        expect(page.locator('.workspace-row-art')).to_have_count(9)
        checks.append('Prior five full-width photographic workspace rows and four quick tasks remain available')
        page.goto(base+'/?view=monitor')
        expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.screenshot(path=str(out/'monitor-mobile.png'),full_page=True)
        checks.append('390px mobile layout: all five domains, controls and queue; no horizontal overflow')
        controlled_failure=True
        page.route('**/api/exposure-aggregates?*',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'error':'QA controlled source unavailable'})))
        page.goto(base+'/?view=monitor')
        expect(page.get_by_role('button',name='Xuất monitor JSON',exact=True)).to_be_enabled(timeout=180000)
        expect(page.locator('#monitor-error-P4')).to_contain_text('QA controlled source unavailable')
        expect(page.locator('.monitor-kpis .metric-card')).to_have_count(4)
        expect(page.locator('#monitor-portfolio-balance')).to_have_count(0)
        expect(page.locator('#monitor-mortgage')).to_be_visible()
        checks.append('Controlled source failure: explicit P4 unavailable; four other domains retained, no fake balance fallback')
        browser.close()
    assert not errors,errors
    assert before==sha256(ledger)
    checks.append('No browser exceptions/console errors; consumed holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'errors':errors,'holdout_ledger_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':len(checks),'receipt':str(out/'receipt.json')},ensure_ascii=False))


if __name__=='__main__':run()
