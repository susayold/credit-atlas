"""Reconcile coverage UI exports directly against acquired SEC companyfacts."""
import json
import uuid
from datetime import date
from decimal import Decimal, localcontext
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import app_root, sha256
from credit_atlas.sec_sources import verify_source


def audit(root, report):
    folder, receipt = verify_source(root, report['source_id'])
    item = next(x for x in receipt['files'] if x['kind']=='companyfacts' and x['cik']==report['filters']['cik'])
    raw = json.loads((folder/item['file']).read_text(encoding='utf-8'), parse_float=Decimal)
    supported = 0
    for period in report['periods']:
        for field in period['fields'].values():
            observations = raw['facts'].get('us-gaap',{}).get(field['concept'],{}).get('units',{}).get('USD',[])
            selected = [x for x in observations if x.get('accn')==period['accession'] and x.get('end')==period['report_date'] and x.get('filed')==period['filing_date'] and x.get('form')=='10-K' and x.get('start') and 330<=(date.fromisoformat(x['end'])-date.fromisoformat(x['start'])).days+1<=400]
            signatures={(x['start'],x['end'],Decimal(str(x['val']))) for x in selected}
            status='missing' if not selected else 'ambiguous' if len(signatures)!=1 else 'supported'
            assert field['status']==status and len(field['evidence'])==len(selected)
            if status=='supported': assert Decimal(field['value_exact'])==Decimal(str(selected[0]['val']))
            for evidence in field['evidence']:
                x=observations[evidence['source_ordinal']]
                assert (x['start'],x['end'],x['accn'],Decimal(str(x['val'])))==(evidence['start_date'],evidence['end_date'],evidence['accession'],Decimal(evidence['value_exact']))
        for name,numerator in [('operating_income_coverage','operating_income'),('reported_ocf_coverage','operating_cashflow')]:
            ratio=period['ratios'][name]
            if ratio['status']=='supported':
                with localcontext() as context:
                    context.prec=60
                    assert Decimal(ratio['value_exact'])==Decimal(period['fields'][numerator]['value_exact'])/Decimal(period['fields']['interest_expense']['value_exact'])
                supported+=1
            else: assert ratio['value_exact'] is None
    assert not any(report['qualification'].values())
    return supported


def run():
    root=app_root();out=root/'artifacts/private'/('sec-coverage-qa-'+uuid.uuid4().hex[:12]);out.mkdir();errors=[];checks=[];counts={}
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True)
        page.on('pageerror',lambda e:errors.append(str(e)))
        base='http://127.0.0.1:8770/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_asof=2026-10-10&workspace_tab=coverage&sec_cik='
        for cik,ticker in [('0000320193','AAPL'),('0000789019','MSFT'),('0000037996','F'),('0001467858','GM')]:
            page.goto(base+cik)
            link=page.get_by_role('link',name='Xuất SEC coverage JSON',exact=True)
            expect(link).to_be_visible(timeout=180000)
            with page.expect_download() as pending:link.click()
            path=out/(ticker+'.json');pending.value.save_as(path)
            report=json.loads(path.read_text(encoding='utf-8'));counts[ticker]=audit(root,report)
            expect(page.locator('#sec-coverage-periods tbody tr')).to_have_count(5)
            if ticker=='F':assert Decimal(report['periods'][-1]['ratios']['operating_income_coverage']['value_exact'])<0
            if ticker in ['AAPL','GM']:assert report['periods'][-1]['fields']['interest_expense']['status']=='missing'
        checks.append('Four issuer UI downloads: all field candidates independently reconciled to raw SEC observations; exact ratios, negative Ford and missing expense retained')
        page.goto(base+'0000789019');expect(page.get_by_role('link',name='Xuất SEC coverage JSON')).to_be_visible(timeout=180000)
        page.get_by_label('SEC interest concept',exact=True).select_option('InterestExpense')
        expect(page.get_by_role('link',name='Xuất SEC coverage JSON')).to_have_attribute('href',__import__('re').compile('interest_concept=InterestExpense&'),timeout=180000)
        with page.expect_download() as pending:page.get_by_role('link',name='Xuất SEC coverage JSON').click()
        pending.value.save_as(out/'MSFT-explicit.json');audit(root,json.loads((out/'MSFT-explicit.json').read_text(encoding='utf-8')))
        page.get_by_label('SEC coverage periods',exact=True).select_option('3');expect(page.locator('#sec-coverage-periods tbody tr')).to_have_count(3,timeout=180000)
        page.reload();expect(page.locator('#sec-coverage-periods tbody tr')).to_have_count(3,timeout=180000);expect(page.get_by_label('SEC interest concept',exact=True)).to_have_value('InterestExpense')
        page.locator('#sec-coverage').screenshot(path=str(out/'coverage-desktop.png'))
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'coverage-mobile.png'))
        checks.append('Explicit concept/3-period selector, persisted URL/reload and mobile no page overflow')
        page.route('**/api/sec-coverage?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA outage"}'))
        page.get_by_label('SEC coverage periods',exact=True).select_option('5');expect(page.locator('#sec-coverage')).to_contain_text('QA outage',timeout=180000);expect(page.get_by_role('link',name='Xuất SEC coverage JSON')).to_have_count(0)
        page.unroute('**/api/sec-coverage?**');page.get_by_label('SEC coverage periods',exact=True).select_option('10');expect(page.get_by_role('link',name='Xuất SEC coverage JSON')).to_be_visible(timeout=180000)
        checks.append('Controlled API outage removes stale export; subsequent selection recovers')
        browser.close()
    assert not errors,errors;assert sha256(ledger)==before
    checks.append('No browser exceptions; frozen retail holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'supported_ratio_counts':counts,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','receipt':str(out/'receipt.json'),'counts':counts}))


if __name__=='__main__':run()
