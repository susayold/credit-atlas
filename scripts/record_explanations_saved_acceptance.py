import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256
from credit_atlas.retail_explanations_saved import CERTIFICATES,certificate

ROOT=Path.cwd();probe='artifacts/private/explanations-saved-probe-59f8ebc3bf4b/receipt.json';browser='artifacts/private/retail-cohort-browser-qa-fea76087b373/receipt.json';tests='artifacts/private/explanations-saved-view-tests.xml'
p=json.loads((ROOT/probe).read_text());b=json.loads((ROOT/browser).read_text())
assert p['status']==b['status']=='PASS' and p['clients']==4499 and p['pages']==90 and p['local_cases']==12 and p['forbidden_calls']==0 and p['exact_token_search'] and p['ledger_unchanged']
for key,file in [('saved_verifier_sha256','src/credit_atlas/retail_explanations_saved.py'),('base_serving_sha256','src/credit_atlas/retail_explanation_views.py'),('cohort_serving_sha256','src/credit_atlas/retail_cohort_explanation_views.py')]:assert p[key]==sha256(ROOT/file)
assert len(b['checks'])==8 and not b['browser_errors'] and b['holdout_ledger_unchanged'] and b['saved_audited_consistency_before_navigation'] and b['model_inference_rerun'] is False
assert b['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and b['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==4 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
for identifier in CERTIFICATES:
    name='cohort-explanations-complete.json' if identifier.startswith('retail-cohort-') else 'explanations-complete.json'
    certificate(ROOT,identifier,ROOT/'artifacts/private'/identifier/name)
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P1.07')
assert r['required_inputs']=='Frozen model, training reference, bốn feature groups và toàn bộ4499 validation clients.'
assert r['required_outputs']=='Global contribution distributions, token search/paging, signed local contributions và private export.'
assert r['acceptance']=='Contributions cộng về prediction đúng tolerance; references/source pinned; không gọi là nguyên nhân hoặc adverse-action reason.'
entry={'checkpoint':'p1-complete-cohort-audited-saved-explanations','document':'docs/P1_EXPLANATIONS_SAVED_ACCEPTANCE_VI.md','probe':probe,'browser':browser,'tests':tests,'historical_exhaustive_audits':{identifier:{'path':'artifacts/private/'+name,'sha256':digest} for identifier,(name,digest) in CERTIFICATES.items()},'scope':'Current4499-client historical benchmark explanation workflow;exact audit receipt/source bindings and fresh saved arithmetic/rank/token/distribution checks;no fresh model/coalition inference;reference sensitivity/intended-use/adverse-action/production qualification remain open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{e:sha256(ROOT/e) for e in [probe,browser,tests]},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
r['full_completion_proven']=True
for item in data['requirements']:
    assert item['checkpoint_status']==before[item['id']][0]
    if item['id']!='P1.07':assert item['full_completion_proven']==before[item['id']][1]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P1.07','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
