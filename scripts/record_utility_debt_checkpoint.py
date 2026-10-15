"""Record source/API evidence without promoting any capability state."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json'
doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit_path='artifacts/private/utility-debt-audit-381643544e02/receipt.json'
tests_path='artifacts/private/utility-debt-http-tests-20261011-warm.xml'
audit=json.loads((root/audit_path).read_text(encoding='utf8'))
assert audit['status']=='PASS' and audit['continuing_value_cells']==260 and audit['acfr_value_cells']==300
suite=ET.parse(root/tests_path).getroot().find('testsuite')
assert suite.attrib['tests']=='29' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
evidence={'checkpoint':'utility-debt-source-api-20261011','document':'docs/UTILITY_DEBT_SERVICE_VI.md',
    'audit':audit_path,'tests':tests_path,
    'scope':'EBMUD two systems,20 continuing records/260 positions,60 rounded ACFR records/300 positions,40 rational DSCR checks,source/profile integrity and private API/export',
    'remaining':'UI/browser,full indenture/amendment/applicable covenant qualification; does not replace corporate/mortgage debt-service inputs'}
ui_evidence={'checkpoint':'utility-debt-ui-20261011','document':'docs/UTILITY_DEBT_SERVICE_VI.md',
    'browser':'artifacts/private/utility-debt-qa-dfe72cbf4cef/receipt.json',
    'regression':'artifacts/private/facilities-qa-eb8a3159a041/receipt.json',
    'scope':'Dedicated EBMUD pane,edition/system/year/lien filters,source input/timeline/bridges/rounded-source mismatch,private exact export,URL reload,mobile,outage recovery and unchanged holdout ledger',
    'remaining':'Full indenture/amendment/applicable covenant qualification;actual corporate/mortgage debt-service inputs remain missing'}
for receipt in [ui_evidence['browser'],ui_evidence['regression']]:
    assert json.loads((root/receipt).read_text(encoding='utf8'))['status']=='PASS'
for identifier in ['P3.03','P3.07','P3.08']:
    row=next(r for r in doc['requirements'] if r['id']==identifier)
    entries=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==evidence['checkpoint'] for e in entries):entries.append(dict(evidence))
    if not any(e.get('checkpoint')==ui_evidence['checkpoint'] for e in entries):entries.append(dict(ui_evidence))
    assert not row['full_completion_proven']
assert collections.Counter(r['checkpoint_status'] for r in doc['requirements'])==before
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Utility source/API evidence recorded; 50 capability states unchanged')
