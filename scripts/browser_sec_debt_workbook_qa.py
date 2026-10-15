"""Saved XLSX independent arithmetic and actual maturity UI download."""
import json
import uuid
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal
from fractions import Fraction
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256
try:
    from scripts.browser_sec_debt_qa import audit as raw_audit
except ModuleNotFoundError as error:
    if error.name != 'scripts':raise
    from browser_sec_debt_qa import audit as raw_audit

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def audit(path,r):
    with zipfile.ZipFile(path) as z:
        tables=[]
        for name in ['sheet1','sheet2']:
            table={}
            for c in ET.fromstring(z.read('xl/worksheets/'+name+'.xml')).findall('.//m:c',NS):
                v=c.find('m:v',NS);f=c.find('m:f',NS)
                table[c.get('r')]={'type':c.get('t'),'value':v.text if v is not None else None,'formula':f.text if f is not None else None}
            tables.append(table)
        main,facts=tables;assert main['B4']['type']=='str' and main['B4']['value']==r['filters']['cik']
        assert main['B5']['value']==r['statement']['accession'] and main['B6']['value']==r['filters']['debt_scope']
        values=[]
        for i,b in enumerate(r['buckets']):
            row=i+9;src=i+6;f=b['field'];cell=main['B'+str(row)]
            assert "'Facts'!C"+str(src) in cell['formula'] and 'ISNUMBER' in cell['formula']
            assert facts['D'+str(src)]['type']=='str' and facts['D'+str(src)]['value']==(f['value_exact'] or 'Unavailable')
            assert facts['E'+str(src)]['value']==f['status']
            assert json.loads(facts['I'+str(src)]['value'])==f['evidence']
            if f['status']=='supported':
                assert cell['type']=='n' and Decimal(cell['value'])==Decimal(f['value_exact']);values.append(Fraction(f['value_exact']))
            else:assert cell['type']=='str' and cell['value']=='Unavailable'
            share=main['D'+str(row)];assert share['formula'] and '$B$18' in share['formula']
            if b['share_of_disclosed_schedule_exact'] is None:assert share['value']=='Unavailable'
            else:assert abs(Fraction(share['value'])-Fraction(b['share_of_disclosed_schedule_exact']))<Fraction(1,10**12)
        for cell,exact in [('B17',r['summary']['supported_subtotal_exact']),('B18',r['summary']['disclosed_schedule_total_exact']),('B19',r['summary']['first_three_years_share_exact'])]:
            assert main[cell]['formula']
            if exact is None:assert main[cell]['value']=='Unavailable'
            else:assert abs(Fraction(main[cell]['value'])-Fraction(exact))<Fraction(1,10**12)
        assert main['B20']['value']==r['summary']['status']
        if len(values)==6 and min(values)>=0:assert Fraction(main['B18']['value'])==sum(values)
        assert not any(cell['type']=='e' for table in tables for cell in table.values())
        return {'supported_buckets':len(values),'formulas':sum(bool(c['formula']) for c in main.values()),'status':main['B20']['value']}


def run():
    root=app_root();out=root/'artifacts/private'/('sec-debt-xlsx-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[];results={}
    doc=json.loads((root/'artifacts/private/sec-debt-workbook-review.json').read_text(encoding='utf-8'))
    audit(root/'outputs/sec-maturities-20261010/CreditAtlas-Maturities.xlsx',doc)
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1050},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        for cik,scope,label in [('0000320193','debt_only','AAPL'),('0000789019','debt_only','MSFT'),('0000320193','debt_and_capital_lease','AAPL-lease')]:
            page.goto('http://127.0.0.1:8770/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_asof=2026-10-10&workspace_tab=debt&sec_cik='+cik+'&sec_debt_scope='+scope)
            button=page.get_by_role('button',name='Xuất maturity Excel',exact=True);expect(button).to_be_visible(timeout=180000)
            previous=set(root.glob('artifacts/private/sec-debt-workbook-*'))
            with page.expect_download(timeout=180000) as pending:button.click()
            path=out/(label+'.xlsx');pending.value.save_as(path)
            created=[x for x in set(root.glob('artifacts/private/sec-debt-workbook-*'))-previous if x.is_dir()];assert len(created)==1
            captured=json.loads((created[0]/'report.json').read_text(encoding='utf-8'))
            assert captured['filters']['cik']==cik and captured['filters']['debt_scope']==scope
            raw_audit(root,captured);results[label]=audit(path,captured)
            if label=='MSFT':assert captured['buckets'][1]['field']['value_exact']=='0'
            if label=='AAPL-lease':assert captured['summary']['disclosed_schedule_total_exact'] is None
            checks.append(label+' actual UI scope/source capture, raw SEC reconciliation and saved XLSX formulas/caches/exact text')
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.route('**/api/sec-debt-workbook',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA maturity Excel outage"}'))
        button.click();expect(page.locator('#sec-debt')).to_contain_text('QA maturity Excel outage',timeout=30000);expect(button).to_be_enabled();page.unroute('**/api/sec-debt-workbook')
        # Changing the family removes/recreates the export control; no duplicate buttons.
        page.get_by_label('SEC debt maturity scope',exact=True).select_option('debt_only');expect(page.get_by_role('button',name='Xuất maturity Excel')).to_have_count(1,timeout=180000)
        page.locator('#sec-debt').scroll_into_view_if_needed();page.screenshot(path=str(out/'mobile.png'))
        checks.append('Mobile/export failure recovery and one scoped export control after selection change');browser.close()
    assert not errors and sha256(ledger)==before;checks.append('No browser exceptions; frozen holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'results':results,'errors':errors},indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','receipt':str(out/'receipt.json'),'results':results}))


if __name__=='__main__':run()
