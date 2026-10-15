"""Original typed intake/concentration requirements; preserve next-step scope."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from credit_atlas.workspace import read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
paths={'document':'docs/P4_INTAKE_CONCENTRATION_ACCEPTANCE_VI.md',
 'tests':'artifacts/private/p4-intake-current-tests.xml',
 'source_audit':'artifacts/private/exposure-audit-7c271e6aa162/audit-complete.json',
 'browser':'artifacts/private/p4-acceptance-qa-b6a5a8af88d0/receipt.json',
 'native':'artifacts/private/native-excel-qa-input-6f3311baa851/receipt.json',
 'inventory':'artifacts/private/p4-inventory-scope-audit-9ee97f218c01/receipt.json',
 'concentration':'artifacts/private/p4-concentration-browser-bc8433735b24/receipt.json'}
e={k:read_json(ROOT/p) for k,p in paths.items() if p.endswith('.json')};assert all(r['status']=='PASS' for r in e.values())
assert len(e['source_audit']['checks'])==66 and all(c['passed'] for c in e['source_audit']['checks'])
assert e['source_audit']['script_sha256']==sha256(ROOT/'scripts/audit_exposure_import.py')
assert e['source_audit']['import_receipt_sha256']==sha256(ROOT/'artifacts/private/exposure-import-57b88e00bedb/import-complete.json')
assert len(e['inventory']['scopes'])==20 and e['inventory']['cell_checks']==664
assert e['inventory']['method_sha256']==sha256(ROOT/'scripts/audit_p4_inventory_scopes.py')
assert e['inventory']['view_method_sha256']==sha256(ROOT/'src/credit_atlas/exposure_views.py')
assert all(sha256(ROOT/p)==h for p,h in e['inventory']['inputs_sha256'].items())
assert e['browser']['ledger_unchanged'] and len(e['browser']['checks'])==5
assert len(e['concentration']['scopes'])==12 and e['concentration']['zero_denominator_ui_fixture'] and not e['concentration']['page_errors']
assert e['concentration']['app_js_sha256']==sha256(ROOT/'apps/web/app.js')
assert e['concentration']['method_sha256']==sha256(ROOT/'scripts/browser_p4_concentration_qa.py')
assert all(sha256(ROOT/p)==h for p,h in e['concentration']['protected_sha256_unchanged'].items())
native_folder=(ROOT/paths['native']).parent
assert e['native']['cells_compared']==78 and e['native']['originals_unchanged'] and not e['native']['differences'] and not e['native']['formula_errors']
assert e['native']['plan_sha256']==sha256(native_folder/'plan.json') and e['native']['readback_sha256']==sha256(native_folder/'native-results.json')
plan=read_json(native_folder/'plan.json');assert len(plan['books'])==1
for book in plan['books']:assert sha256(Path(book['source']))==sha256(Path(book['copy']))==book['source_sha256']
paths['native_plan']=str((native_folder/'plan.json').relative_to(ROOT));paths['native_readback']=str((native_folder/'native-results.json').relative_to(ROOT))
suite=ET.parse(ROOT/paths['tests']).getroot().find('testsuite');assert suite.attrib['tests']=='47' and suite.attrib['errors']==suite.attrib['failures']=='0'
folder=(ROOT/paths['concentration']).parent
visual={'status':'PASS','scope':'Final synthetic zero widget and actual mobile concentration images directly viewed; no native workbook visual review claimed',
        'pngs':{p.name:sha256(p) for p in folder.glob('*.png')},'source_receipt_sha256':sha256(folder/'receipt.json')};assert len(visual['pngs'])==2
v=folder/'visual-review.json'
if v.exists():assert read_json(v)==visual
else:write_new(v,visual)
paths['visual']=str(v.relative_to(ROOT))
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
entry={'checkpoint':'p4-typed-intake-concentration-full-current-requirements',**paths,
       'scope':'Current typed XLSX bounds/formula/precision/identity/risk contract, actual9698 source observations and3EXAMPLE positions,47tests,66source math checks,20scopes664inventory checks,78native template cells,12UI scopes plus zero-share meter fix. No institution ownership, obligor concentration, FX totals, EAD inference, calibrated PD/ECL or authenticated governance claim.',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in paths.values()},'full_completion_proven':True}
for r in data['requirements']:
    if r['id'] in ['P4.01','P4.02']:
        if not any(x.get('checkpoint')==entry['checkpoint'] for x in r['completion_evidence']):r['completion_evidence'].append(entry)
        r['full_completion_proven']=True
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Accepted',sum(r['full_completion_proven'] for r in data['requirements']),'/50')
