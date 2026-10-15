"""Compare every maturity bucket with acquired SEC companyfacts, then UI scope."""
import json
import uuid
from decimal import Decimal,localcontext
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256
from credit_atlas.sec_sources import verify_source


def audit(root,r):
    folder,receipt=verify_source(root,r['source_id']);file=next(x for x in receipt['files'] if x['kind']=='companyfacts' and x['cik']==r['filters']['cik'])
    raw=json.loads((folder/file['file']).read_text(encoding='utf-8'),parse_float=Decimal);s=r['statement'];supported=[]
    for b in r['buckets']:
        f=b['field'];observations=raw['facts'].get('us-gaap',{}).get(f['concept'],{}).get('units',{}).get('USD',[])
        selected=[x for x in observations if x.get('accn')==s['accession'] and x.get('end')==s['report_date'] and x.get('filed')==s['filing_date'] and x.get('form')==s['form'] and x.get('start') is None]
        signatures={Decimal(str(x['val'])) for x in selected};status='missing' if not selected else 'ambiguous' if len(signatures)!=1 else 'supported'
        assert f['status']==status and len(f['evidence'])==len(selected)
        if status=='supported':assert Decimal(f['value_exact'])==Decimal(str(selected[0]['val']));supported.append(Decimal(f['value_exact']))
        for e in f['evidence']:
            source=observations[e['source_ordinal']];assert Decimal(e['value_exact'])==Decimal(str(source['val'])) and source['accn']==e['accession'] and source['end']==e['end_date']
    summary=r['summary'];assert summary['supported_buckets']==len(supported)
    if len(supported)==6 and min(supported)>=0:
        total=sum(supported);assert Decimal(summary['disclosed_schedule_total_exact'])==total
        if total>0:
            with localcontext() as ctx:
                ctx.prec=80
                for b in r['buckets']:assert Decimal(b['share_of_disclosed_schedule_exact'])==Decimal(b['field']['value_exact'])/total
                assert Decimal(summary['first_three_years_share_exact'])==sum(supported[:3])/total
        else:assert summary['first_three_years_share_exact'] is None
    else:assert summary['disclosed_schedule_total_exact'] is None and summary['first_three_years_share_exact'] is None
    assert not any(r['qualification'].values())
    return len(supported)


def run():
    root=app_root();out=root/'artifacts/private'/('sec-debt-qa-'+uuid.uuid4().hex[:12]);out.mkdir();errors=[];checks=[];support={}
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        base='http://127.0.0.1:8770/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_asof=2026-10-10&workspace_tab=debt&sec_cik='
        for cik,ticker in [('0000320193','AAPL'),('0000789019','MSFT'),('0000037996','F'),('0001467858','GM')]:
            page.goto(base+cik);link=page.get_by_role('link',name='Xuất maturity JSON',exact=True);expect(link).to_be_visible(timeout=180000)
            expect(page.locator('#sec-debt-buckets tbody tr')).to_have_count(6)
            with page.expect_download() as pending:link.click()
            path=out/(ticker+'.json');pending.value.save_as(path);r=json.loads(path.read_text(encoding='utf-8'));support[ticker]=audit(root,r)
            if ticker in ['F','GM']:assert r['summary']['supported_buckets']==0 and r['summary']['disclosed_schedule_total_exact'] is None
            if ticker=='MSFT':assert r['buckets'][1]['field']['value_exact']=='0' and r['buckets'][1]['field']['status']=='supported'
        checks.append('Four issuers: actual UI exports, all six buckets/candidates independently reconciled to raw SEC, complete/partial/zero distinctions')
        page.goto(base+'0000320193');expect(page.get_by_role('link',name='Xuất maturity JSON')).to_be_visible(timeout=180000)
        page.locator('#sec-debt').screenshot(path=str(out/'debt-desktop.png'))
        page.get_by_label('SEC debt maturity scope',exact=True).select_option('debt_and_capital_lease')
        expect(page.get_by_role('link',name='Xuất maturity JSON')).to_have_attribute('href',__import__('re').compile('debt_scope=debt_and_capital_lease'),timeout=180000)
        with page.expect_download() as pending:page.get_by_role('link',name='Xuất maturity JSON').click()
        path=out/'AAPL-lease.json';pending.value.save_as(path);r=json.loads(path.read_text(encoding='utf-8'));audit(root,r);assert r['filters']['debt_scope']=='debt_and_capital_lease'
        page.reload();expect(page.get_by_label('SEC debt maturity scope',exact=True)).to_have_value('debt_and_capital_lease',timeout=180000)
        page.set_viewport_size({'width':390,'height':844});expect(page.locator('#sec-debt-buckets')).to_be_visible(timeout=180000);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'debt-mobile.png'))
        checks.append('Explicit family selection, no debt/lease fallback, URL/reload and mobile no page overflow')
        page.route('**/api/sec-debt?**',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA maturity outage"}'))
        page.get_by_label('SEC debt maturity scope',exact=True).select_option('debt_only');expect(page.locator('#sec-debt')).to_contain_text('QA maturity outage',timeout=30000);expect(page.get_by_role('link',name='Xuất maturity JSON')).to_have_count(0)
        page.unroute('**/api/sec-debt?**');page.get_by_label('SEC debt maturity scope',exact=True).select_option('debt_and_capital_lease');expect(page.get_by_role('link',name='Xuất maturity JSON')).to_be_visible(timeout=180000)
        checks.append('Source outage removes stale export and selection recovers')
        browser.close()
    assert not errors and sha256(ledger)==before;checks.append('No browser exceptions; frozen holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'supported_buckets':support,'errors':errors},indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','receipt':str(out/'receipt.json'),'support':support}))


if __name__=='__main__':run()
