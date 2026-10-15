"""Audit saved XLSX formulas/caches independently and exercise actual UI export."""
import json
import re
import uuid
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from credit_atlas.workspace import app_root,sha256

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def audit(path,doc,require_missing_guard=False):
    with zipfile.ZipFile(path) as z:
        cells=[]
        for name in ['sheet1','sheet2']:
            table={}
            for c in ET.fromstring(z.read('xl/worksheets/'+name+'.xml')).findall('.//m:c',NS):
                v=c.find('m:v',NS);f=c.find('m:f',NS)
                table[c.attrib['r']]={'type':c.get('t'),'value':v.text if v is not None else None,'formula':f.text if f is not None else None}
            cells.append(table)
        a,facts=cells
        assert a['B4']['type']=='str' and a['B4']['value']==doc['trend']['filters']['cik']
        expected={}
        for p in doc['trend']['periods']:
            for key,definition in doc['trend']['ratio_definitions'].items():
                expected[(p['report_date'],definition['label'])]=(p['statement']['ratios'][key]['value_exact'] if p['statement'] else None,p['comparisons'].get(key,{}).get('absolute_delta_exact'))
        for p in doc['coverage']['periods']:
            for key,label in [('operating_income_coverage','Operating income / selected expense'),('reported_ocf_coverage','Reported OCF / selected expense')]:expected[(p['report_date'],label)]=(p['ratios'][key]['value_exact'],None)
        rows=4*len(doc['trend']['periods'])+2*len(doc['coverage']['periods']);numeric=0;bridges=0
        for row in range(19,19+rows):
            # XLSX stores real dates as serials; metric name and chronological grouping establish expected row.
            label=a['B'+str(row)]['value'];matching=[v for (date,name),v in expected.items() if name==label]
            index=sum(a['B'+str(i)]['value']==label for i in range(19,row));actual,delta=matching[index]
            for column,exact in [('I',actual),('K',delta)]:
                cell=a[column+str(row)];assert cell['formula']
                if exact is None:assert cell['type']=='str' and cell['value']=='Unavailable'
                else:assert cell['type']=='n' and abs(Decimal(cell['value'])-Decimal(exact))<Decimal('1e-10');numeric+=1
            inputs=[]
            for column in ['E','F','G','H']:
                cell=a[column+str(row)]
                if cell['formula']:
                    guarded=re.fullmatch(r'''IF\(ISNUMBER\('Facts'!D([0-9]+)\),'Facts'!D\1,"Unavailable"\)''',cell['formula'])
                    ref=guarded or re.fullmatch("'Facts'!D([0-9]+)",cell['formula']);assert ref
                    if require_missing_guard:assert guarded, 'New exports must preserve missing numeric sources'
                    source=facts['D'+ref[1]];exact=facts['E'+ref[1]]
                    assert exact['type']=='str'
                    if source['type']=='n':
                        assert abs(Decimal(source['value'])-Decimal(exact['value']))<=Decimal('0.001')
                        inputs.append(Fraction(Decimal(exact['value'])))
                    else:inputs.append(None)
                else:assert cell['value']=='Unavailable';inputs.append(None)
            if delta is not None:
                n1,d1,n0,d0=inputs;ne=n1/d0-n0/d0;de=n1/d1-n1/d0
                for column,value in [('L',ne),('M',de),('U',n1/d0)]:assert abs(Fraction(Decimal(a[column+str(row)]['value']))-value)<Fraction(1,10**10)
                assert abs(Decimal(a['N'+str(row)]['value']))<Decimal('1e-10');bridges+=1
            else:assert a['L'+str(row)]['value']==a['M'+str(row)]['value']=='Unavailable'
        for table in cells:
            assert not any(c['type']=='e' for c in table.values())
        assert len(ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets',NS))==2
    return {'rows':rows,'numeric_results':numeric,'bridges':bridges,'formulas':sum(bool(c['formula']) for c in a.values())}


def run():
    root=app_root();out=root/'artifacts/private'/('sec-workbook-qa-'+uuid.uuid4().hex[:12]);out.mkdir();errors=[];checks=[]
    doc=json.loads((root/'artifacts/private/sec-workbook-review.json').read_text(encoding='utf-8'))
    metrics=audit(root/'outputs/sec-analysis-20261010/CreditAtlas-SEC.xlsx',doc)
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1450,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8770/?view=sec&sec_view_id=sec-view-b92d9914f1dc&sec_cik=0000789019&sec_asof=2026-10-10&workspace_tab=trends&sec_trend_years=5')
        button=page.get_by_role('button',name='Xuất SEC Excel',exact=True);expect(button).to_be_visible(timeout=180000)
        previous=set(root.glob('artifacts/private/sec-workbook-*'))
        with page.expect_download(timeout=180000) as pending:button.click()
        pending.value.save_as(out/'ui-export.xlsx')
        created=[x for x in set(root.glob('artifacts/private/sec-workbook-*'))-previous if x.is_dir()]
        assert len(created)==1
        captured=json.loads((created[0]/'report.json').read_text(encoding='utf-8'))
        assert captured['trend']['filters']==doc['trend']['filters'];assert captured['coverage']['filters']==doc['coverage']['filters']
        ui_metrics=audit(out/'ui-export.xlsx',captured,require_missing_guard=True);assert ui_metrics==metrics
        checks.append('Actual UI POST/download: server-derived scope and saved formula/cached-value/source-text parity')
        page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        page.route('**/api/sec-workbook',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"QA workbook outage"}'))
        button.click();expect(page.locator('#sec-trend')).to_contain_text('QA workbook outage',timeout=30000);expect(button).to_be_enabled()
        page.unroute('**/api/sec-workbook');browser.close()
        checks.append('Mobile no horizontal page overflow; export failure shown and button restored')
    assert not errors and sha256(ledger)==before;checks.append('No browser exceptions and frozen holdout ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'audit':metrics,'errors':errors},indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','receipt':str(out/'receipt.json'),'audit':metrics}))


if __name__=='__main__':run()
