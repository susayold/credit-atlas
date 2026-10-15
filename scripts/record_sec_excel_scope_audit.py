"""Record scoped workbook/native evidence without claiming full P3.03 acceptance."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import read_json,sha256

root=Path.cwd();exports=root/'artifacts/private/sec-workbook-scope-audit-1133f2bb3c7b/receipt.json'
native=root/'artifacts/private/native-excel-qa-sec-1a75771ee189/receipt.json'
tests=root/'artifacts/private/sec-analysis-excel-acceptance-tests.xml'
e=read_json(exports);n=json.loads(native.read_text(encoding='utf-8-sig'))
assert e['status']==n['status']=='PASS' and len(e['scopes'])==len(n['books'])==36
assert n['failed_checks']==0 and n['copies_not_saved'] and e['ledger_unchanged']
assert sum(b['cells_checked'] for b in n['books'])==73656 and sum(b['formulas_checked'] for b in n['books'])==14040
assert all(sha256(root/s['workbook'])==s['sha256'] and sha256(root/s['capture'])==s['capture_sha256'] for s in e['scopes'])
assert all(sha256(root/'src/credit_atlas'/f'{name}.py')==digest for name,digest in e['methods_sha256'].items())
assert e['builder_sha256']==sha256(root/'scripts/build_sec_workbook.mjs')
suite=ET.parse(tests).getroot().find('testsuite');assert suite.attrib['tests']=='43' and suite.attrib['errors']==suite.attrib['failures']=='0'
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
before=[(r['id'],r['checkpoint_status'],r['full_completion_proven'],r['required_inputs'],r['required_outputs'],r['acceptance']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P3.03')
entry={'checkpoint':'p3-sec-excel-36-scope-native-baseline-20261015',
    'document':'docs/P3_SEC_EXCEL_SCOPE_AUDIT_VI.md','exports':str(exports.relative_to(root)),
    'native_excel':str(native.relative_to(root)),'tests':str(tests.relative_to(root)),
    'scope':'36issuer/window/expense API captures,XLSX/JSON scope+SHA parity,independent XML/Fraction arithmetic/missing guards;native Excel16 fullrebuild73656cells14040formulas on36unsaved copies;43testsPASS;source/builder unchanged',
    'remaining':'Full Facts metadata/date/summary audit,current-copy native input perturbations,current render and browser download/outage scope acceptance',
    'full_completion_proven':False,
    'evidence_sha256':{str(f.relative_to(root)):sha256(f) for f in [exports,native,tests]},
    'native_audit_method_observed_sha256':sha256(root/'scripts/audit_sec_scope_native.ps1')}
entries=r.setdefault('partial_evidence',[])
if not any(x['checkpoint']==entry['checkpoint'] for x in entries):entries.append(entry)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven'],r['required_inputs'],r['required_outputs'],r['acceptance']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Recorded workbook/native baseline;accepted:',sum(r['full_completion_proven'] for r in data['requirements']))
