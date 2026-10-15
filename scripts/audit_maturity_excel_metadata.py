"""Every maturity source/definition/date/capture cell vs immutable report."""
import json,zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET
from uuid import uuid4
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();manifest=root/'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json';m=read_json(manifest)
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};checked=[]
for s in m['scopes']:
 path=root/s['workbook'];capture=root/s['capture'];assert sha256(path)==s['sha256'] and sha256(capture)==s['capture_sha256']
 r=read_json(capture);tables=[]
 with zipfile.ZipFile(path) as z:
  for name in ['sheet1','sheet2']:
   cells={}
   for c in ET.fromstring(z.read('xl/worksheets/'+name+'.xml')).findall('.//s:sheetData/s:row/s:c',ns):
    v=c.findtext('s:v',None,ns)
    if v is None:continue
    kind=c.get('t','n');cells[c.get('r')]=v[:10] if kind=='d' else Decimal(v) if kind=='n' else v
   tables.append(cells)
 a,f=tables
 assert [a[k] for k in ['B4','D4','B5','D5','B6']]==[r['filters']['cik'],r['filters']['asof'],r['statement']['accession'],r['statement']['report_date'],r['filters']['debt_scope']]
 for i,b in enumerate(r['buckets']):
  row=i+6;field=b['field'];vector=[f[chr(65+j)+str(row)] for j in range(12)]
  expected=[b['bucket'],field['concept'],Decimal(field['value_exact']) if field['status']=='supported' else 'Unavailable',
   field['value_exact'] if field['value_exact'] is not None else 'Unavailable',field['status'],field['end_date'],
   r['statement']['filing_date'],r['statement']['accession'],field['evidence'],b['definition']['label'] or 'Not supplied',
   b['definition']['description'] or 'Not supplied',r['statement']['filing_url']]
  vector[8]=json.loads(vector[8]);assert vector==expected
  assert a['A'+str(i+9)]==b['label'] and a['E'+str(i+9)]==expected[3]
  assert a['F'+str(i+9)]==(b['share_of_disclosed_schedule_exact'] or 'Unavailable')
 metadata={f['A'+str(i)]:f['B'+str(i)] for i in range(14,22)}
 assert metadata=={'Source ID':r['source_id'],'Case ID':r['case_id'],'Method SHA256':r['method_source_sha256'],**r['source_capture'],'Selection rule':r['selection_rule']}
 assert f['B4']==f"https://data.sec.gov/api/xbrl/companyfacts/CIK{r['filters']['cik']}.json"
 assert a['B16']==r['summary']['supported_buckets'] and a['B20']==r['summary']['status']
 checked.append({'workbook':s['workbook'],'facts_rows':6,'metadata_entries':8,'family':r['filters']['debt_scope']})
out=root/'artifacts/private'/('maturity-excel-metadata-'+uuid4().hex[:12])
write_new(out/'receipt.json',{'status':'PASS','books':checked,'source_receipt_sha256':sha256(manifest),'method_sha256':sha256(Path(__file__))})
print(out)
