"""P3.10 requirement closure from whole export coverage and native equivalence."""
from pathlib import Path
import json
from credit_atlas.workspace import read_json,sha256

ROOT=Path(__file__).resolve().parents[1]
paths={
 'document':'docs/P3_BUSINESS_REVIEW_EXPORT_ACCEPTANCE_VI.md',
 'exports':'artifacts/private/business-review-export-audit-1d5eda8fb468/receipt.json',
 'quality':'artifacts/private/business-export-quality-audit-630368d18d8e/receipt.json',
 'sba_browser':'artifacts/private/sba-june-browser-acceptance-75fe6d2cd40f/receipt.json',
 'excel_browser':'artifacts/private/sec-workbook-qa-77226775fb35/receipt.json',
 'excel_scopes':'artifacts/private/sec-workbook-scope-audit-09ac934bdc4e/receipt.json',
 'excel_equivalence':'artifacts/private/sec-excel-equivalence-17a3f1d744a8/receipt.json',
 'native':'artifacts/private/native-excel-qa-sec-1a75771ee189/receipt.json',
 'native_input_cases':'artifacts/private/native-excel-qa-sec-perturb-9c8189a3d577/receipt.json',
 'excel_metadata':'artifacts/private/sec-excel-metadata-audit-74186cf6c79d/receipt.json',
 'memo':'docs/P3_CORPORATE_MEMO_ACCEPTANCE_VI.md'}
e={k:read_json(ROOT/p) for k,p in paths.items() if p.endswith('.json')};assert all(v['status']=='PASS' for v in e.values())
for key,script in [('exports','audit_business_review_exports.py'),('quality','audit_business_export_quality.py'),('excel_equivalence','audit_current_sec_excel_equivalence.py')]:
    assert e[key]['method_sha256']==sha256(ROOT/'scripts'/script)
for key in ['exports','quality']:
    assert all(sha256(ROOT/p)==h for p,h in e[key]['inputs_sha256'].items())
assert len(e['exports']['sec_scopes'])==67 and e['exports']['sec_statement_fields_checked']==536 and e['exports']['sec_ratios_checked']==268
assert e['quality']['total_sba_program_dimension_bucket_scopes']==378 and len(e['quality']['supported_empty_intersections'])==7
folder=(ROOT/paths['exports']).parent
assert all(sha256(folder/p)==h for p,h in e['exports']['private_exports_sha256'].items())
assert all(sha256(ROOT/p)==h for p,h in e['exports']['runtime_methods_sha256'].items())
folder=(ROOT/paths['quality']).parent
assert all(sha256(folder/c['export'])==c['sha256'] for c in e['quality']['supported_empty_intersections'])
assert e['sba_browser']['program_dimension_combinations']==12 and e['sba_browser']['ledger_unchanged'] and not e['sba_browser']['page_errors']
assert e['sba_browser']['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and e['sba_browser']['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
assert not e['excel_browser']['errors']
assert len(e['excel_scopes']['scopes'])==len(e['excel_equivalence']['books'])==len(e['native']['books'])==36
assert e['excel_equivalence']['populated_cells_identical']==73656 and e['excel_equivalence']['formula_cells_identical']==14040
assert e['excel_equivalence']['current_manifest_sha256']==sha256(ROOT/paths['excel_scopes'])
assert e['excel_equivalence']['native_receipt_sha256']==sha256(ROOT/paths['native'])
assert e['native']['failed_checks']==0 and e['native']['copies_not_saved']
assert e['excel_scopes']['builder_sha256']==sha256(ROOT/'scripts/build_sec_workbook.mjs')
for scope in e['excel_scopes']['scopes']:
    assert sha256(ROOT/scope['workbook'])==scope['sha256'] and sha256(ROOT/scope['capture'])==scope['capture_sha256']
assert all(sha256(ROOT/'src/credit_atlas'/(n+'.py'))==h for n,h in e['excel_scopes']['methods_sha256'].items())
assert e['exports']['ledger_sha256_unchanged']==sha256(ROOT/'artifacts/private/retail-holdout-access.sqlite')
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
for identifier in ['P3.01','P3.03','P3.05','P3.06','P3.09']:
    dependency=next(r for r in data['requirements'] if r['id']==identifier);assert dependency['full_completion_proven']
    for proof in dependency['completion_evidence']:
        assert all(sha256(ROOT/p)==h for p,h in proof['evidence_sha256'].items())
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P3.10')
entry={'checkpoint':'p3-business-review-export-full-current-requirement',**paths,
       'scope':'67 full private SEC projections and all378 SBA report scopes with quality/grain separation; current UI/private downloads and36 Excel scopes;73656cells14040formulas identical to native-verified baseline; accepted financial memo/history. No fuzzy issuer join, authenticated reviewer, currentEAD, fixed-horizon PD or actual debt/covenant qualification.',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in paths.values()},'full_completion_proven':True}
if not any(x.get('checkpoint')==entry['checkpoint'] for x in r['completion_evidence']):r['completion_evidence'].append(entry)
r['full_completion_proven']=True
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Accepted',sum(r['full_completion_proven'] for r in data['requirements']),'/50')
