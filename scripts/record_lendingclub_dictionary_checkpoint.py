"""Record definition evidence without certifying prepared feature availability."""
import collections,json
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();path=root/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf8'))
before=collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
audit='artifacts/private/lendingclub-dictionary-audit-3fe039b24405/receipt.json'
browser='artifacts/private/lendingclub-source-qa-330325d8c34f/receipt.json'
tests='artifacts/private/lendingclub-dictionary-http-tests-20261012-fixed.xml'
a=json.loads((root/audit).read_text(encoding='utf8'));b=json.loads((root/browser).read_text(encoding='utf8'))
assert a['status']==b['status']=='PASS' and a['definitions_checked']==280 and a['literal_cells_checked']==560 and a['prepared_columns_checked']==90
assert b['ledger_unchanged'] and not b['browser_errors']
suite=ET.parse(root/tests).getroot().find('testsuite');assert suite.attrib['tests']=='36' and suite.attrib['failures']=='0' and suite.attrib['errors']=='0'
entry={'checkpoint':'lendingclub-issuer-dictionary-20261012','document':'docs/LENDINGCLUB_DICTIONARY_REVIEW_VI.md',
    'audit':audit,'browser':browser,'tests':tests,
    'scope':'Issuer-hosted XLSX280definitions/560cells;90prepared columns86exact/2proposedaliases/2undefined;DTI/income/amount caveats,cell-source references,privateAPI/UI/export and exclusions pending review',
    'remaining':'Contributor preprocessing/unit/time provenance,application decision dates,reject/full-booked population,event horizon/maturity,intended-use/OOT qualification'}
for identifier in ['P1.02','P1.05']:
    row=next(r for r in doc['requirements'] if r['id']==identifier);entries=row.setdefault('partial_evidence',[])
    if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(dict(entry))
    assert not row['full_completion_proven']
assert before==collections.Counter(r['checkpoint_status'] for r in doc['requirements'])
doc['as_of']='2026-10-12';path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Dictionary evidence recorded;50states unchanged')
