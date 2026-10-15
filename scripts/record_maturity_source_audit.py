import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import read_json,sha256

root=Path.cwd();paths={
 'audit':'artifacts/private/sec-maturity-acceptance-audit-36b22846d6dc/receipt.json',
 'browser':'artifacts/private/sec-debt-qa-5648923643e0/receipt.json',
 'excel':'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json',
 'native':'artifacts/private/native-excel-qa-sec-817f40ce0d7a/receipt.json',
 'excel_browser':'artifacts/private/sec-debt-xlsx-qa-798b967d62b7/receipt.json',
 'tests':'artifacts/private/sec-maturity-acceptance-tests.xml'}
receipts={k:json.loads((root/p).read_text(encoding='utf-8-sig')) for k,p in paths.items() if k!='tests'}
assert all(r['status']=='PASS' for r in receipts.values())
assert receipts['audit']['bucket_cells_checked']==804 and len(receipts['audit']['scopes'])==134
assert receipts['audit']['method_sha256']==sha256(root/'scripts/audit_sec_maturity_acceptance.py')
assert receipts['audit']['debt_method_sha256']==sha256(root/'src/credit_atlas/sec_debt.py')
assert len(receipts['excel']['scopes'])==len(receipts['native']['books'])==8
assert receipts['native']['failed_checks']==0 and receipts['native']['copies_not_saved']
for s in receipts['excel']['scopes']:
 assert sha256(root/s['workbook'])==s['sha256'] and sha256(root/s['capture'])==s['capture_sha256']
suite=ET.parse(root/paths['tests']).getroot().find('testsuite');assert suite.attrib['tests']=='23' and suite.attrib['errors']==suite.attrib['failures']=='0'
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
before=[(r['id'],r['checkpoint_status'],r['full_completion_proven'],r['required_inputs'],r['required_outputs'],r['acceptance']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P3.08')
entry={'checkpoint':'p3-maturity-whole-source-api-excel-native-baseline-20261015',
 'document':'docs/P3_MATURITY_SOURCE_AUDIT_VI.md',**paths,
 'scope':'67filings2families134APIscopes804buckets exact raw candidates/definitions/summary;8latestExcel captures;native1408cells184formulas;current JSON/Excel browser,exports/reload/mobile/outage and23testsPASS;source/production calculations unchanged',
 'remaining':'Full maturity Facts metadata/summary,date/native perturbation+visual and new memo capture/source freshness/history/export;actual facility/coupon/cashflow qualification remains missing',
 'full_completion_proven':False,'evidence_sha256':{p:sha256(root/p) for p in paths.values()}}
entries=r.setdefault('partial_evidence',[])
if not any(e['checkpoint']==entry['checkpoint'] for e in entries):entries.append(entry)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven'],r['required_inputs'],r['required_outputs'],r['acceptance']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Recorded maturity evidence;accepted:',sum(r['full_completion_proven'] for r in data['requirements']))
