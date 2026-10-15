import json,urllib.request
from pathlib import Path
from credit_atlas.kpi_workbook import validate_report
from browser_kpi_workbook_qa import audit
out=Path('artifacts/private/kpi-inspector-qa-9479d922c579');r=json.loads((out/'monitor.json').read_text());report={k:r[k] for k in ['schema_version','read_at','filters','kpi_analysis']};validate_report(report)
req=urllib.request.Request('http://127.0.0.1:8770/api/kpi-workbook',data=json.dumps(report).encode(),headers={'Content-Type':'application/json','X-CreditAtlas-Client':'local','Origin':'http://127.0.0.1:8770'},method='POST')
with urllib.request.urlopen(req,timeout=200) as response:
 assert 'no-store' in response.headers['Cache-Control'];data=response.read()
target=out/'KPI-inspector-regression.xlsx';target.write_bytes(data);result=audit(target,report);(out/'excel-regression.json').write_text(json.dumps({'status':'PASS','audit':result,'no_store':True},indent=2));print(json.dumps({'status':'PASS','audit':result,'bytes':len(data)}))
