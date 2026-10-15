import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path(__file__).resolve().parents[1]
audit_path='artifacts/private/lifecycle-acceptance-54135e394300/receipt.json'
browser_path='artifacts/private/lifecycle-browser-acceptance-b48e0b41cd89/receipt.json'
tests_path='artifacts/private/lifecycle-acceptance-tests-20261012.xml'
a=json.loads((ROOT/audit_path).read_text());b=json.loads((ROOT/browser_path).read_text())
assert a['status']=='PASS' and a['index_rows']==a['unique_keys']==50000 and a['index_source_differences']==0 and a['list_scopes']==16
assert len(a['timeline_checks'])==10 and len(a['static_assets_checked'])==15 and a['ledger_unchanged']
assert b['status']=='PASS' and len(b['timeline_checks'])==10 and all(c['status']=='PASS' for c in b['timeline_checks'])
assert all(b[k] for k in ['empty_search_clears','pending_context_clears','late_list_response_discarded','timeline_outage_clears','invalid_search_clears','mobile','ledger_unchanged']) and not b['page_errors']
for f in a['source_inputs']+a['static_assets_checked']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for p,h in a['methods'].items():assert sha256(ROOT/p)==h
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/loan-index.parquet')==a['index_sha256']
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/case-complete.json')==a['case_receipt_sha256']
assert sha256(ROOT/'apps/web/app.js')==b['app_js_sha256'] and sha256(ROOT/'src/credit_atlas/server.py')==b['server_sha256']
s=ET.parse(ROOT/tests_path).getroot().find('testsuite');assert int(s.attrib['tests'])==19 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(r for r in data['requirements'] if r['id']=='P2.04')
assert r['required_inputs']=='Run-scoped pseudonymous loan key, observed states/UPB và confirmed events.'
assert r['required_outputs']=='Timeline, observed UPB chart và source-backed event detail.'
assert r['acceptance']=='Không lộ raw loan ID; không coi observed timeline là forecast; không backdate confirmation.'
entry={'checkpoint':'p2-lifecycle-full-current-requirement-20261012','as_of':'2026-10-12','document':'docs/P2_LIFECYCLE_ACCEPTANCE_VI.md','audit':audit_path,'browser':browser_path,'tests':tests_path,
       'scope':'All current P2.04 source-backed/private/observed timeline requirements;stale context defect fixed;extended paging/loan-review remains next-stage work',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit_path,browser_path,tests_path]},'full_completion_proven':True}
items=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in items):items.append(entry)
r['full_completion_proven']=True
regressions={'P2.05':'artifacts/private/transition-browser-acceptance-269c134a5dc0/receipt.json',
             'P2.06':'artifacts/private/cure-browser-acceptance-fb399d21b288/receipt.json',
             'P2.07':'artifacts/private/competing-browser-acceptance-84a581a3cd33/receipt.json'}
for requirement in data['requirements']:
    if requirement['id'] in regressions:
        p=regressions[requirement['id']];receipt=json.loads((ROOT/p).read_text())
        assert receipt['status']=='PASS' and receipt['ledger_unchanged'] and not receipt['page_errors']
        assert receipt['app_js_sha256']==b['app_js_sha256'] and receipt['server_sha256']==b['server_sha256']
        if requirement['id']=='P2.05':assert len(receipt['scopes'])==6
        elif requirement['id']=='P2.06':assert len(receipt['followup_scopes'])==8 and len(receipt['timeline_event_types'])==4
        else:assert len(receipt['scopes'])==12
        entries=requirement.setdefault('runtime_regression_evidence',[])
        if not any(e.get('browser')==p for e in entries):entries.append({'checkpoint':'lifecycle-context-clear-regression-20261012','browser':p,'browser_sha256':sha256(ROOT/p),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'status':'PASS'})
    assert before[requirement['id']][0]==requirement['checkpoint_status']
    if requirement['id']!='P2.04':assert before[requirement['id']][1]==requirement['full_completion_proven']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.04','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
