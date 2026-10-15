"""Actual SEC trend UI/export parity and independent ratio arithmetic."""
import json
import uuid
from decimal import Decimal,localcontext
from fractions import Fraction
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256


def audit(r):
    periods=r['periods'];assert len(periods)<=int(r['filters']['years'])
    assert [p['report_date'] for p in periods]==sorted(p['report_date'] for p in periods)
    checks=0
    for p in periods:
        for f in p['filings']:assert f['filing_date']<=r['filters']['asof']
        s=p['statement'];prior=p['baseline_statement']
        if not s:continue
        assert s['form']=='10-K' and s['cik']==r['filters']['cik']
        for key,ratio in s['ratios'].items():
            c=p['comparisons'][key]
            if ratio['status']=='supported':
                n,d=(s['fields'][ratio[k]] for k in ['numerator','denominator'])
                assert n['status']==d['status']=='supported' and n['unit']==d['unit']=='USD'
                with localcontext() as ctx:
                    ctx.prec=60;assert Decimal(ratio['value_exact'])==Decimal(n['value_exact'])/Decimal(d['value_exact'])
                checks+=1
            else:assert ratio['value_exact'] is None
            if c['status']=='COMPARABLE':
                assert prior and c['baseline_accession']==prior['accession']
                with localcontext() as ctx:
                    ctx.prec=60;x,y=Decimal(ratio['value_exact']),Decimal(prior['ratios'][key]['value_exact'])
                    assert Decimal(c['absolute_delta_exact'])==x-y
                    if y>0:assert Decimal(c['relative_delta_exact'])==(x-y)/y
                    else:assert c['relative_delta_exact'] is None
            else:assert c['absolute_delta_exact'] is None
            b=c['driver_bridge']
            if b['status']=='SUPPORTED':
                n0=Fraction(prior['fields'][ratio['numerator']]['value_exact']);d0=Fraction(prior['fields'][ratio['denominator']]['value_exact'])
                n1=Fraction(s['fields'][ratio['numerator']]['value_exact']);d1=Fraction(s['fields'][ratio['denominator']]['value_exact'])
                for field,exact in [('numerator_effect_exact',n1/d0-n0/d0),('denominator_effect_exact',n1/d1-n1/d0),('total_change_exact',n1/d1-n0/d0)]:
                    assert abs(Fraction(b[field])-exact)<Fraction(1,10**55)
                assert abs(Decimal(b['rounding_residual_exact']))<Decimal('1e-55')
            else:assert b['numerator_effect_exact'] is None and b['denominator_effect_exact'] is None
    assert not any(r['qualification'].values());return checks


def run():
    root=app_root();out=root/'artifacts/private'/('sec-trends-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[];base='http://127.0.0.1:8770'
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);supported=0
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1500,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        for cik,ticker in [('0000320193','AAPL'),('0000789019','MSFT'),('0000037996','F'),('0001467858','GM')]:
            url=base+'/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_cik='+cik+'&sec_asof=2026-10-10&workspace_tab=trends&sec_trend_years=5'
            page.goto(url);expect(page.locator('#sec-trend-periods')).to_be_visible(timeout=180000)
            expect(page.locator('.sec-trend-ratio')).to_have_count(4)
            with page.expect_download(timeout=180000) as pending:page.get_by_role('link',name='Xuất SEC trend JSON',exact=True).click()
            pending.value.save_as(out/(ticker+'.json'));r=json.loads((out/(ticker+'.json')).read_text(encoding='utf-8'));supported+=audit(r)
            assert len(r['periods'])==5 and page.locator('#sec-trend-periods tbody tr').count()==5
            assert page.locator('.sec-trend-ratio tbody tr').count()==20
            expect(page.locator('#sec-ratio-drivers [data-driver-ratio]')).to_have_count(4)
            assert page.locator('#sec-ratio-drivers tbody tr').count()==20
            for key in r['ratio_definitions']:
                rows=page.locator('#sec-ratio-drivers [data-driver-ratio="'+key+'"] tbody tr')
                for i,period in enumerate(r['periods']):
                    b=period['comparisons'].get(key,{}).get('driver_bridge',{})
                    assert rows.nth(i).locator('td').last.inner_text()==b.get('status',period['selection_status'])
            assert page.locator('#sec-trend').inner_text().find('DSCR')>=0
            checks.append(ticker+' five-period UI/private export, exact inputs/ratios/deltas, rational driver bridge and cutoff scope')
        page.get_by_label('SEC trend periods',exact=True).select_option('3');expect(page.locator('#sec-trend-periods tbody tr')).to_have_count(3,timeout=180000)
        page.reload();expect(page.get_by_label('SEC trend periods',exact=True)).to_have_value('3',timeout=180000);expect(page.locator('#sec-trend-periods tbody tr')).to_have_count(3,timeout=180000)
        page.locator('#sec-trend').screenshot(path=str(out/'trend-desktop.png'))
        page.set_viewport_size({'width':390,'height':844});page.locator('#sec-trend').scroll_into_view_if_needed();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'trend-mobile.png'))
        # Controlled endpoint outage keeps a usable retry selector and exposes unavailable.
        page.route('**/api/sec-trend?*',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA trend source unavailable"}'))
        page.get_by_label('SEC trend periods',exact=True).select_option('10');expect(page.locator('#sec-trend')).to_contain_text('QA trend source unavailable',timeout=180000);assert page.get_by_role('link',name='Xuất SEC trend JSON',exact=True).count()==0
        page.unroute('**/api/sec-trend?*');page.get_by_label('SEC trend periods',exact=True).select_option('5');expect(page.locator('#sec-trend-periods tbody tr')).to_have_count(5,timeout=180000)
        checks.append('Period selector/reload, mobile layout and explicit source outage/recovery')
        browser.close()
    query='/api/sec-trend?view_id=sec-view-b92d9914f1dc&cik=0000320193&asof=1900-01-01&years=3'
    assert json.load(urlopen(base+query))['periods']==[]
    assert not errors and before==sha256(ledger);checks.append('Pre-source cutoff empty, no browser errors and holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'supported_ratio_checks':supported,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':len(checks),'supported_ratio_checks':supported,'receipt':str(out/'receipt.json')}))


if __name__=='__main__':run()
