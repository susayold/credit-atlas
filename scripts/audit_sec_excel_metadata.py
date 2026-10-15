"""Independent completeness/metadata/summary checks for all36 Excel captures."""
import json,zipfile
from collections import Counter
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET
from credit_atlas.workspace import read_json,sha256,write_new

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def cells(path):
    result=[]
    with zipfile.ZipFile(path) as z:
        shared=[''.join(t.text or '' for t in n.iter('{'+NS['s']+'}t')) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
        for name in ['sheet1','sheet2']:
            table={}
            for c in ET.fromstring(z.read('xl/worksheets/'+name+'.xml')).findall('.//s:sheetData/s:row/s:c',NS):
                v=c.findtext('s:v',None,NS);kind=c.get('t','n')
                if v is None:continue
                if kind=='s':v=shared[int(v)]
                elif kind=='inlineStr':v=''.join(t.text or '' for t in c.findall('s:is//s:t',NS))
                elif kind=='d':v=v[:10]
                elif kind=='n':v=Decimal(v)
                table[c.attrib['r']]=v
            result.append(table)
    return result

def vector(accession,period,label,v,filing_date,form,url):
    concepts=list(dict.fromkeys(e['taxonomy']+':'+e['concept'] for e in v['evidence']))
    return [label,accession,period,v['value_exact'] or 'Unavailable',v['status'],v['start_date'] or 'Instant / unavailable',
            v['end_date'],v['unit'],', '.join(concepts) or 'Unavailable',filing_date,form,url,v['evidence'],
            'Excel floating point; exact text retained' if v['status']=='supported' else 'No numeric input']

root=Path.cwd();manifest=root/'artifacts/private/sec-workbook-scope-audit-1133f2bb3c7b/receipt.json'
receipt=read_json(manifest);assert receipt['status']=='PASS';checked=[]
for scope in receipt['scopes']:
    path=root/scope['workbook'];capture=root/scope['capture']
    assert sha256(path)==scope['sha256'] and sha256(capture)==scope['capture_sha256']
    doc=read_json(capture);t=doc['trend'];c=doc['coverage'];a,f=cells(path)
    assert a['B4']==t['filters']['cik'] and a['D4']==t['filters']['asof'] and a['F4']==Decimal(t['filters']['years'])
    assert a['B5']==c['filters']['interest_concept'] and a['B8']==t['periods'][-1]['report_date']
    allowed={};summaries={}
    def include(s,label,v):
        key=(s['accession'],label,json.dumps(v,sort_keys=True))
        allowed[key]=vector(s['accession'],s['report_date'],label,v,s['filing_date'],s['form'],s['filing_url'])
    for p in t['periods']:
        for key,definition in t['ratio_definitions'].items():
            s=p['statement'];prior=p['baseline_statement'];r=s['ratios'][key] if s else None
            old=prior['ratios'][key] if prior else None
            for selected,value in [(s,r),(prior,old)]:
                if selected:
                    for field in [value['numerator'],value['denominator']]:include(selected,field,selected['fields'][field])
            summaries[definition['label']]=(r['value_exact'] if r else None,old['value_exact'] if old else None,
                p['comparisons'].get(key,{}).get('absolute_delta_exact'),definition['unit'])
    for p in c['periods']:
        s={'accession':p['accession'],'report_date':p['report_date'],'filing_date':p['filing_date'],'form':'10-K',
           'filing_url':f"https://www.sec.gov/Archives/edgar/data/{int(c['filters']['cik'])}/{p['accession']}-index.html"}
        for field,label in [('operating_income','operating_income'),('operating_cashflow','operating_cashflow'),
            ('interest_expense','selected_interest_expense'),('interest_paid','interest_paid'),('interest_paid_net','interest_paid_net')]:
            if field in p['fields']:include(s,label,p['fields'][field])
        for key,label in [('operating_income_coverage','Operating income / selected expense'),('reported_ocf_coverage','Reported OCF / selected expense')]:
            summaries[label]=(p['ratios'][key]['value_exact'],None,None,'times')
    expected=Counter(json.dumps(v,sort_keys=True) for v in allowed.values());actual=Counter();fact_rows=0
    for row in range(6,10000):
        if f.get('A'+str(row)) not in {v[0] for v in allowed.values()}:break
        vals=[f.get(chr(65+i)+str(row)) for i in range(15)]
        evidence=json.loads(vals[13]);sig=vals[:3]+vals[4:13]+[evidence,vals[14]]
        actual[json.dumps(sig,sort_keys=True)]+=1
        if vals[5]=='supported':assert isinstance(vals[3],Decimal) and abs(vals[3]-Decimal(vals[4]))<=Decimal('0.001')
        else:assert vals[3]==vals[4]=='Unavailable'
        fact_rows+=1
    assert actual==expected,'Facts metadata/candidate set differs from captured source fields'
    for row,(label,(value,baseline,delta,unit)) in enumerate(summaries.items(),10):
        assert a['A'+str(row)]==label
        for col,exact in [('B',value),('C',baseline),('D',None if delta is None else str(Decimal(delta)*(100 if unit=='share' else 1)))]:
            stored=a[col+str(row)]
            if exact is None:assert stored=='Unavailable'
            else:assert isinstance(stored,Decimal) and abs(stored-Decimal(exact))<Decimal('1e-10')
    metadata=dict((f['A'+str(row)],f['B'+str(row)]) for row in range(fact_rows+8,fact_rows+8+11))
    expected_meta={'Source ID':t['source_id'],'Case ID':t['case_id'],**c['source_capture'],
        'Trend method SHA256':t['method_source_sha256'],'Coverage method SHA256':c['method_source_sha256'],
        'Scope rules':t['selection_rule'],'Comparison rules':t['comparison_rule'],'Expense rule':c['concept_rule']}
    assert metadata==expected_meta
    assert f['B4']==f"https://data.sec.gov/api/xbrl/companyfacts/CIK{t['filters']['cik']}.json"
    checked.append({'workbook':scope['workbook'],'facts_rows_checked':fact_rows,'metadata_entries':len(metadata),'summary_cells':18})
out=root/'artifacts/private'/('sec-excel-metadata-audit-'+uuid4().hex[:12])
write_new(out/'receipt.json',{'status':'PASS','books':checked,'source_receipt_sha256':sha256(manifest),
    'method_sha256':sha256(Path(__file__)),'full_completion_proven':False})
print(out)
