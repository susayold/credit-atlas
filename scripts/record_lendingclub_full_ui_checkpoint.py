"""Record complete-source explorer separately from application/OOT readiness."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
browser='artifacts/private/lendingclub-full-source-qa-58d41056f7e3/receipt.json';tests='artifacts/private/lendingclub-full-http-tests-20261012.xml'
b=json.loads((root/browser).read_text(encoding='utf8'));assert b['status']=='PASS' and b['ledger_unchanged'] and not b['browser_errors']
suite=ET.parse(root/tests).getroot().find('testsuite');assert suite.attrib['tests']=='30' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
entry={'checkpoint':'lendingclub-full-source-explorer-20261012','document':'docs/LENDINGCLUB_FULL_SOURCE_VI.md','browser':browser,'tests':tests,
    'scope':'Separate accepted funded-month/rejected application-day privateAPI/UI/export;category windows,151/9whole-source quality tables,active/missing statuses,URL/reset/mobile/outage and raw/dated/missing denominators',
    'remaining':'Snapshot/feature availability,original issuer fidelity/rights,application decision dates,comparable eligible populations,event horizon/maturity,borrower grouping and intended-use/OOT qualification'}
for identifier in ['P1.02','P1.05']:
    row=next(r for r in doc['requirements'] if r['id']==identifier);evidence=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in evidence):evidence.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
doc['as_of']='2026-10-12';path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('Full-source explorer recorded;50states unchanged')
