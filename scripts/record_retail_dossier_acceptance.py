import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256

ROOT=Path.cwd();browser='artifacts/private/retail-dossier-browser-eb13e7928485/receipt.json';tests='artifacts/private/retail-dossier-tests.xml'
b=json.loads((ROOT/browser).read_text());assert b['status']=='PASS' and b['source_split_selection_metrics_parity'] and b['audit_trail_rows']==6 and b['export_parity'] and b['governance_unqualified_preserved']
assert b['forbidden_calls']==0 and b['reload'] and b['outage_retry'] and b['mobile'] and b['ledger_unchanged'] and not b['page_errors']
assert b['method_sha256']==sha256(ROOT/'src/credit_atlas/retail_dossier.py') and b['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and b['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==17 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P1.10')
assert r['required_inputs']=='Source contract, split support, saved model selection/holdout, uncertainty và limitations.'
assert r['required_outputs']=='Model dossier, audit trail và reporting package; app đọc saved artifacts.'
assert r['acceptance']=='Không refit/rescore khi mở màn; benchmark Taiwan không trở thành Vietnam PD; chưa có authenticated sign-off.'
entry={'checkpoint':'p1-model-dossier-full-current-requirement','document':'docs/P1_MODEL_DOSSIER_ACCEPTANCE_VI.md','browser':browser,'tests':tests,'scope':'Current source/target/split/selection/freeze/saved-evaluation dossier and audit-trail/reporting package;no inference/refit/rescore;owner/authenticated sign-off/monitoring/production intended-use qualification remain open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{e:sha256(ROOT/e) for e in [browser,tests]},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
r['full_completion_proven']=True
for item in data['requirements']:
    assert item['checkpoint_status']==before[item['id']][0]
    if item['id']!='P1.10':assert item['full_completion_proven']==before[item['id']][1]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P1.10','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
