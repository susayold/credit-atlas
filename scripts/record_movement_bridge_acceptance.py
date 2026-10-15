"""Close original observation movement requirement, preserving all qualifications."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from credit_atlas.workspace import read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
paths={'document':'docs/P4_MOVEMENT_BRIDGE_ACCEPTANCE_VI.md',
       'source':'artifacts/private/exposure-movement-audit-0228d51fcb29/audit-complete.json',
       'boundaries':'artifacts/private/movement-boundary-audit-012d14f1a641/receipt.json',
       'browser':'artifacts/private/movement-scope-browser-557afb22290b/receipt.json',
       'tests':'artifacts/private/p4-movement-current-tests.xml',
       'movement':'artifacts/private/exposure-movement-dbd1ecad612e/movement-complete.json'}
source=read_json(ROOT/paths['source']);boundary=read_json(ROOT/paths['boundaries']);browser=read_json(ROOT/paths['browser']);movement=read_json(ROOT/paths['movement'])
assert source['status']==boundary['status']==browser['status']=='PASS'
assert len(source['checks'])==500 and all(c['passed'] for c in source['checks'])
assert source['script_sha256']==sha256(ROOT/'scripts/audit_exposure_movement.py')
assert source['movement_receipt_sha256']==sha256(ROOT/paths['movement'])
assert len(boundary['cases'])==100 and boundary['exact_checks']==26668 and boundary['synthetic_only']
assert boundary['method_sha256']==sha256(ROOT/'scripts/audit_movement_boundaries.py')
assert boundary['movement_method_sha256']==sha256(ROOT/'src/credit_atlas/exposure_movements.py')
assert all(sha256(ROOT/p)==h for p,h in movement['inputs_sha256'].items())
assert all(sha256(ROOT/'src/credit_atlas'/(n+'.py'))==h for n,h in movement['methods'].items())
assert browser['movement_receipt_sha256']==sha256(ROOT/paths['movement'])
report_path=ROOT/'artifacts/private/exposure-movement-dbd1ecad612e/report.json'
assert browser['source_report_sha256']==movement['report_sha256']==sha256(report_path)
report=read_json(report_path);assert all(not v for v in report['contract'].values() if isinstance(v,bool))
assert report['global_cross_currency_total'] is None
assert len(browser['scopes'])==8 and browser['outage_recovery'] and browser['reload_mobile'] and not browser['page_errors']
assert browser['method_sha256']==sha256(ROOT/'scripts/browser_movement_scope_qa.py')
assert browser['app_js_sha256']==sha256(ROOT/'apps/web/app.js')
assert browser['view_method_sha256']==sha256(ROOT/'src/credit_atlas/exposure_movement_views.py')
assert all(sha256(ROOT/p)==h for p,h in browser['protected_sha256_unchanged'].items())
folder=(ROOT/paths['browser']).parent
assert all(sha256(folder/c['export'])==c['sha256'] for c in browser['scopes'])
suite=ET.parse(ROOT/paths['tests']).getroot().find('testsuite');assert suite.attrib['tests']=='15' and suite.attrib['errors']==suite.attrib['failures']=='0'
visual={'status':'PASS','scope':'Actual final desktop/mobile movement panel images viewed directly; mobile tables scroll inside panel',
        'pngs':{p.name:sha256(p) for p in folder.glob('*.png')},'source_receipt_sha256':sha256(folder/'receipt.json')};assert len(visual['pngs'])==2
v=folder/'visual-review.json'
if v.exists():assert read_json(v)==visual
else:write_new(v,visual)
paths['visual']=str(v.relative_to(ROOT));paths['source_report']=str(report_path.relative_to(ROOT))
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P4.06')
entry={'checkpoint':'p4-observation-movement-bridge-full-current-requirement',**paths,
       'scope':'Actual same-source February/March bridge,500independent checks;100synthetic boundary pairs26668rational checks;15tests;all8current API/UI/private export scopes,source guards/outage/recovery and immutable ledgers. No actual payoff/default/cashflow attribution, borrower linkage, FX P&L or EL movement inference.',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in paths.values()},'full_completion_proven':True}
if not any(x.get('checkpoint')==entry['checkpoint'] for x in r['completion_evidence']):r['completion_evidence'].append(entry)
r['full_completion_proven']=True
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Accepted',sum(r['full_completion_proven'] for r in data['requirements']),'/50')
