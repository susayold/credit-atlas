import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path(__file__).resolve().parents[1]
audit_path='artifacts/private/competing-acceptance-64e6477ee6ba/receipt.json'
browser_path='artifacts/private/competing-browser-acceptance-b90cdc483f69/receipt.json'
tests_path='artifacts/private/competing-acceptance-tests-20261012.xml'
a=json.loads((ROOT/audit_path).read_text());b=json.loads((ROOT/browser_path).read_text())
assert a['status']=='PASS' and a['source_loans']==50000 and a['eligible_loans']==a['ledger_rows_checked']==48066
assert a['curve_rows_checked']==72 and a['probability_checks']==216 and a['bootstrap_bound_checks']==18 and a['export_scopes']==12
assert not a['bootstrap_coverage_claimed'] and a['ledger_unchanged']
assert b['status']=='PASS' and len(b['scopes'])==12 and all(s['status']=='PASS' for s in b['scopes'])
assert b['mobile'] and b['unavailable_reload'] and not b['page_errors'] and b['ledger_unchanged']
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for p,h in a['methods'].items():assert sha256(ROOT/p)==h
assert sha256(ROOT/'apps/web/app.js')==b['app_js_sha256']
assert sha256(ROOT/'src/credit_atlas/server.py')==b['server_sha256']
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/case-complete.json')==a['case_receipt_sha256']
s=ET.parse(ROOT/tests_path).getroot().find('testsuite')
assert int(s.attrib['tests'])==49 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(r for r in data['requirements'] if r['id']=='P2.07')
assert r['required_inputs']=='Early-entry eligible loans, horizon6/12/24m, endpoint observations và censoring.'
assert r['required_outputs']=='Cohort support, incidence/exits charts và target exclusions.'
assert r['acceptance']=='Không gọi horizon connector là monthly prediction; censored/unknown không thành negative.'
entry={'checkpoint':'p2-competing-full-current-requirement-20261012','as_of':'2026-10-12','document':'docs/P2_COMPETING_ACCEPTANCE_VI.md','audit':audit_path,'browser':browser_path,'tests':tests_path,
       'scope':'All current P2.07 cohort/incidence/exits/exclusion and unavailable semantics on official2012 panel;next-stage temporal survival/model work remains open',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit_path,browser_path,tests_path]},
       'test_method_sha256':{p:sha256(ROOT/p) for p in ['vendor/credit_risk_strategy_lab/tests/test_vintage.py','vendor/credit_risk_strategy_lab/tests/test_labels.py','tests/test_frozen_service.py']},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
r['full_completion_proven']=True
for other in data['requirements']:
    assert before[other['id']][0]==other['checkpoint_status']
    if other['id']!='P2.07':assert before[other['id']][1]==other['full_completion_proven']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.07','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
