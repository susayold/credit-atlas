import json
from pathlib import Path
from xml.etree import ElementTree as ET

root=Path(__file__).resolve().parents[1]
tests=root/'artifacts/private/affordability-excel-tests-20261012-final.xml'
suite=ET.parse(tests).getroot().find('testsuite')
assert int(suite.attrib['tests'])==50 and int(suite.attrib['errors'])==0 and int(suite.attrib['failures'])==0
browser='artifacts/private/affordability-excel-qa-38d197be777d/receipt.json'
r=json.loads((root/browser).read_text());assert r['status']=='PASS' and r['ledger_unchanged'] and len(r['checks'])==4 and not r['browser_errors']
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before=[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
requirement=next(r for r in data['requirements'] if r['id']=='P1.05')
entry={'checkpoint':'affordability-excel-intake-20261012','document':'docs/AFFORDABILITY_EXCEL_INTAKE_VI.md','tests':str(tests.relative_to(root)).replace('\\','/'),'browser':browser,'scope':'Bounded value-only XLSX intake,cell lineage/hash,private API,form hydration and exact DTI/residual reassessment;zero/missing/expiry/formula/precision/HTTP/browser guards','remaining':'Template workbook,actual income/obligation source documents,verification ownership,household completeness and semantic overlap review;no credit decision','full_completion_proven':False}
items=requirement.setdefault('partial_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in items):items.append(entry)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checkpoint':entry['checkpoint'],'capability_states_unchanged':True,'full_completion_proven':False}))
