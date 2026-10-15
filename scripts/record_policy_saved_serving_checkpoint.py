import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256

ROOT=Path.cwd();probe='artifacts/private/policy-saved-no-inference-3b3a84e13d8c/receipt.json';audit='artifacts/private/retail-policy-audit-8f505ca2f0ed.json';browser='artifacts/private/retail-policy-browser-qa-8f799d39c04b/receipt.json';tests='artifacts/private/retail-policy-saved-serving-tests.xml'
p=json.loads((ROOT/probe).read_text());a=json.loads((ROOT/audit).read_text());b=json.loads((ROOT/browser).read_text())
assert p['status']==a['status']==b['status']=='PASS'
assert p['forbidden_inference_refit_verifiers_blocked'] and p['original_policy_unchanged'] and p['ledger_unchanged'] and a['checks']==184 and a['holdout_ledger_unchanged']
assert p['saved_helper_sha256']==sha256(ROOT/'src/credit_atlas/retail_policy_saved.py') and p['serving_sha256']==sha256(ROOT/'src/credit_atlas/retail_policy_views.py')
assert b['holdout_ledger_unchanged'] and not b['browser_errors'] and len(b['checks'])==9
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==20 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'));before=[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
r=next(x for x in data['requirements'] if x['id']=='P1.04');entry={'checkpoint':'policy-saved-score-serving-no-inference','document':'docs/P1_POLICY_SAVED_SERVING_CHECKPOINT_VI.md','audit':audit,'probe':probe,'browser':browser,'tests':tests,'scope':'Policy APIs verify saved freeze graph and replay Fraction costs without model inference;isolated QA persistence;source/model unchanged','remaining':'Subgroup catalog on same screen still follows legacy deep verification;full-screen no-inference probe and serving reconciliation remain required;real economic/treatment qualification unavailable','evidence_sha256':{x:sha256(ROOT/x) for x in [probe,audit,browser,tests]},'full_completion_proven':False}
items=r.setdefault('partial_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in items):items.append(entry)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'CHECKPOINT_RECORDED','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
