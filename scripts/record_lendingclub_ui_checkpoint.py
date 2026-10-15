"""Record source-explorer delivery independently of underwriting qualification."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
browser='artifacts/private/lendingclub-source-qa-c7baf1748a66/receipt.json'
tests='artifacts/private/lendingclub-http-tests-20261012.xml'
b=json.loads((root/browser).read_text(encoding='utf8'));assert b['status']=='PASS' and b['ledger_unchanged'] and not b['browser_errors']
suite=ET.parse(root/tests).getroot().find('testsuite');assert suite.attrib['tests']=='30' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
entry={'checkpoint':'lendingclub-source-explorer-20261012','document':'docs/LENDINGCLUB_SOURCE_PROFILE_VI.md','browser':browser,'tests':tests,
    'scope':'Publisher-hash checked privateAPI/UI/export,booking-month/status/field filters,source-cohort chart,whole-source90column missingness/numeric profiles,label encoding,URL reload,mobile,outage/guard',
    'remaining':'Original fidelity/dictionary/preprocessing,application decision chronology,reject/full-booked population,event horizon/maturity and intended-use/OOT qualification'}
for identifier in ['P1.02','P1.05']:
    row=next(r for r in doc['requirements'] if r['id']==identifier);evidence=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in evidence):evidence.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print('LendingClub explorer evidence recorded;50states unchanged')
