import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path(__file__).resolve().parents[1]
audit_path='artifacts/private/cure-acceptance-ac5b999767fe/receipt.json'
browser_path='artifacts/private/cure-browser-acceptance-f3834b743ccf/receipt.json'
tests_path='artifacts/private/cure-acceptance-tests-20261012.xml'
a=json.loads((ROOT/audit_path).read_text());b=json.loads((ROOT/browser_path).read_text())
assert a['status']=='PASS' and a['event_count']==4902 and a['event_differences']==0
assert a['followup_cells']==82 and a['followup_event_horizon_checks']==9804 and a['export_scopes_checked']==8
types={'FIRST_OBSERVED_D3','ONE_MONTH_CURE','SUSTAINED_CURE_CONFIRMED','REDEFAULT_AFTER_SUSTAINED_CURE'}
assert {r['event_type'] for r in a['timeline_checks']}==types
assert b['status']=='PASS' and len(b['followup_scopes'])==8 and all(s['status']=='PASS' for s in b['followup_scopes'])
assert set(b['timeline_event_types'])==types and b['export_segment_scopes']==4 and b['mobile'] and not b['page_errors']
assert a['ledger_unchanged'] and b['ledger_unchanged']
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for p,digest in a['methods'].items():assert sha256(ROOT/p)==digest
assert sha256(ROOT/'apps/web/app.js')==b['app_js_sha256']
assert sha256(ROOT/'src/credit_atlas/server.py')==b['server_sha256']
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/case-complete.json')==a['case_receipt_sha256']
s=ET.parse(ROOT/tests_path).getroot().find('testsuite')
assert int(s.attrib['tests'])==26 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(r for r in data['requirements'] if r['id']=='P2.06')
assert r['required_inputs']=='D3 episodes, CURRENT nonterminal consecutive months, gaps và follow-up windows.'
assert r['required_outputs']=='Episode events, follow-up support và loan timeline.'
assert r['acceptance']=='Gap/unknown phá linkage; terminal CURRENT không thành cure; follow-up thiếu không thành no-event.'
entry={'checkpoint':'p2-cure-full-current-requirement-20261012','as_of':'2026-10-12','document':'docs/P2_CURE_ACCEPTANCE_VI.md','audit':audit_path,'browser':browser_path,'tests':tests_path,
       'scope':'All current P2.06 episode/follow-up/timeline requirements on official2012 panel;multi-cohort time-to-event/censoring extension remains open',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit_path,browser_path,tests_path]},
       'test_method_sha256':{p:sha256(ROOT/p) for p in ['vendor/credit_risk_strategy_lab/tests/test_portfolio.py','tests/test_episode_followup.py','tests/test_frozen_service.py']},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
r['full_completion_proven']=True
for other in data['requirements']:
    assert before[other['id']][0]==other['checkpoint_status']
    if other['id']!='P2.06':assert before[other['id']][1]==other['full_completion_proven']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.06','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
