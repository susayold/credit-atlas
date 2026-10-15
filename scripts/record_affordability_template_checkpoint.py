import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.affordability_excel import template_bytes,TEMPLATE_SHA256

root=Path(__file__).resolve().parents[1]
tests='artifacts/private/affordability-template-tests-20261012-final.xml'
s=ET.parse(root/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==53 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
browser='artifacts/private/affordability-excel-qa-5db4d5f8f7f8/receipt.json'
b=json.loads((root/browser).read_text());assert b['status']=='PASS' and len(b['checks'])==5 and b['ledger_unchanged'] and not b['browser_errors']
native='artifacts/private/native-excel-qa-affordability-c541484f16e5/receipt.json'
n=json.loads((root/native).read_text());assert n['status']=='PASS' and n['cells_checked']==38 and n['originals_unchanged'] and n['copies_not_saved']
audit='artifacts/private/affordability-template-roundtrip-20261012/audit.json'
a=json.loads((root/audit).read_text());assert a['status']=='PASS' and len(a['checks'])==2
assert template_bytes(root)
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before=[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
entry={'checkpoint':'affordability-excel-template-20261012','document':'docs/AFFORDABILITY_EXCEL_INTAKE_VI.md','tests':tests,'browser':browser,'native':native,'audit':audit,'template_sha256':TEMPLATE_SHA256,'scope':'Blank guided XLSX template,native validation definitions,hash-guarded download route,Artifact Tool roundtrip,source-cell/form/export parity and native Excel read-only 38-cell checks','remaining':'Actual income/debt documents,verification ownership,household completeness and semantic obligation overlap review;full native dropdown interaction not exercised','full_completion_proven':False}
r=next(r for r in data['requirements'] if r['id']=='P1.05');items=r.setdefault('partial_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in items):items.append(entry)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checkpoint':entry['checkpoint'],'states_unchanged':True,'full_completion_proven':False}))
