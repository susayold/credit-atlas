"""Preserve full scope while recording dated legal-description evidence."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json'
doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit='artifacts/private/utility-contract-audit-4e07ea00a93c/receipt.json'
browser='artifacts/private/utility-debt-qa-0708e7218772/receipt.json'
tests='artifacts/private/utility-contract-http-tests-20261011.xml'
for receipt in [audit,browser]:assert json.loads((root/receipt).read_text(encoding='utf8'))['status']=='PASS'
suite=ET.parse(root/tests).getroot().find('testsuite')
assert suite.attrib['tests']=='36' and suite.attrib['errors']=='0' and suite.attrib['failures']=='0'
entry={'checkpoint':'utility-covenant-description-20261011','document':'docs/UTILITY_COVENANT_EVIDENCE_VI.md',
    'audit':audit,'browser':browser,'tests':tests,
    'scope':'Two dated official statements590pages,22selected evidence pages,reported1.1x covenant vs1.6xpolicy,definition continuations,proposed amendment/certificate/default caveats,privateAPI/UI/export',
    'remaining':'Executed full indenture chain,trustee certificate/effective date,historical applicability and test reconciliation;legal threshold/headroom/compliance remain null'}
for identifier in ['P3.03','P3.07','P3.08']:
    row=next(r for r in doc['requirements'] if r['id']==identifier)
    evidence=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in evidence):evidence.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Utility covenant-description evidence recorded; all capability states unchanged')
