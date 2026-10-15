"""Promote only P2.05 after inspecting evidence for every explicit requirement."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256

ROOT=Path(__file__).resolve().parents[1]
audit_path='artifacts/private/transition-acceptance-be68432843fc/receipt.json'
browser_path='artifacts/private/transition-browser-acceptance-a2c7e68b7d22/receipt.json'
tests_path='artifacts/private/transition-acceptance-tests-20261012.xml'
audit=json.loads((ROOT/audit_path).read_text());browser=json.loads((ROOT/browser_path).read_text())
assert audit['status']=='PASS' and audit['requirement']=='P2.05' and audit['adjacent_pairs']==4460559
assert audit['year_cells']==1091 and audit['lifetime_cells']==94 and audit['export_scopes_checked']==68
assert audit['origin_and_cell_amount_checks']==2370 and audit['max_probability_error']<=audit['probability_tolerance']
assert audit['ledger_unchanged'] and browser['ledger_unchanged'] and browser['status']=='PASS' and not browser['page_errors']
assert len(browser['scopes'])==6 and all(s['status']=='PASS' for s in browser['scopes'])
for file in audit['source_inputs_verified']:assert sha256(ROOT/file['path'])==file['sha256']
for file,digest in audit['methods'].items():assert sha256(ROOT/file)==digest
assert sha256(ROOT/'apps/web/app.js')==browser['app_js_sha256']
assert sha256(ROOT/'src/credit_atlas/server.py')==browser['server_sha256']
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/case-complete.json')==audit['raw_case_receipt_sha256']
suite=ET.parse(ROOT/tests_path).getroot().find('testsuite')
assert int(suite.attrib['tests'])==22 and int(suite.attrib['failures'])==0 and int(suite.attrib['errors'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';doc=json.loads(path.read_text(encoding='utf-8'))
before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in doc['requirements']}
r=next(r for r in doc['requirements'] if r['id']=='P2.05')
assert r['required_inputs']=='Adjacent loan-month pairs; opening UPB; selected reporting year/segment.'
assert r['required_outputs']=='Matrix, selected-cell detail và year-scoped export.'
assert r['acceptance']=='Không nối gaps/terminal pairs sai; năm không có pairs giữ unavailable; lifetime comparator ghi rõ scope.'
entry={'checkpoint':'p2-transition-full-current-requirement-20261012','document':'docs/P2_TRANSITION_ACCEPTANCE_VI.md','audit':audit_path,'browser':browser_path,'tests':tests_path,
       'as_of':'2026-10-12','scope':'All explicit current P2.05 inputs/outputs/acceptance on official2012 descriptive case;next-stage CI/multi-vintage/OOT requirements remain open',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit_path,browser_path,tests_path]},
       'test_method_sha256':{p:sha256(ROOT/p) for p in ['tests/test_period_transitions.py','tests/test_frozen_service.py']},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
r['full_completion_proven']=True
for item in doc['requirements']:
    if item['id']!='P2.05':assert before[item['id']]==(item['checkpoint_status'],item['full_completion_proven'])
assert all(before[item['id']][0]==item['checkpoint_status'] for item in doc['requirements'])
path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.05','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in doc['requirements']),'total':50,'goal_achieved':False}))
