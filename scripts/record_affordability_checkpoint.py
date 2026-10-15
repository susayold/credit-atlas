"""Record intake/calculation delivery without substituting verified data."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
tests='artifacts/private/affordability-http-tests-20261012-final.xml';suite=ET.parse(root/tests).getroot().find('testsuite')
assert suite.attrib['tests']=='34' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
entry={'checkpoint':'affordability-intake-engine-api-20261012','document':'docs/AFFORDABILITY_INTAKE_VI.md','tests':tests,
    'scope':'Explicit gross/net/expenses/debt/proposed/household/currency/date intake,exact period normalization,DTI/residual/declared policy/sensitivity,missing-zero-expiry/coverage/duplicate guards and private same-originPOST/export',
    'remaining':'UI and source-document/Excel intake,verified income/debt/expense evidence,coverage/overlap review,policy ownership and intended-use qualification;no credit decision or actual verification from declared references'}
row=next(r for r in doc['requirements'] if r['id']=='P1.05');entries=row.setdefault('partial_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
assert not row['full_completion_proven'] and before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
doc['as_of']='2026-10-12';path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Affordability engine/API recorded;50states unchanged')
