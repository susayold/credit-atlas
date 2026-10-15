import argparse,json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256

ROOT=Path.cwd();parser=argparse.ArgumentParser();parser.add_argument('persistence_receipt');args=parser.parse_args()
policy='artifacts/private/retail-policy-browser-qa-f6c67fc270d9/receipt.json'
policy_audit='artifacts/private/retail-policy-audit-8f505ca2f0ed.json'
groups='artifacts/private/retail-subgroups-browser-qa-0b36e96a972d/receipt.json'
group_audit='artifacts/private/retail-subgroups-audit-5aa17c776d15.json'
tests='artifacts/private/policy-subgroup-saved-tests.xml';persist=args.persistence_receipt
p=json.loads((ROOT/policy).read_text());g=json.loads((ROOT/groups).read_text());a=json.loads((ROOT/policy_audit).read_text());ga=json.loads((ROOT/group_audit).read_text());s=json.loads((ROOT/persist).read_text())
assert all(x['status']=='PASS' for x in [p,g,a,ga,s])
assert p['entire_policy_subgroup_inference_tripwires'] and p['forbidden_calls']==0 and p['real_subgroup_dimensions_checked']==4 and len(p['checks'])==9
assert p['holdout_ledger_unchanged'] and not p['browser_errors'] and a['checks']==184 and a['holdout_ledger_unchanged']
assert ga['checks']==314 and ga['holdout_ledger_unchanged'] and len(g['checks'])==5 and g['holdout_ledger_unchanged'] and not g['browser_errors']
assert s['save_reopen_catalog_dimensions']==4 and s['full_report_equal'] and s['forbidden_calls']==0 and s['ledger_unchanged'] and s['source_study_unchanged'] and s['qa_storage_only']
for key,file in [('saved_subgroups_helper_sha256','src/credit_atlas/retail_subgroups_saved.py'),('saved_policy_helper_sha256','src/credit_atlas/retail_policy_saved.py'),('subgroup_serving_sha256','src/credit_atlas/retail_subgroup_views.py'),('policy_serving_sha256','src/credit_atlas/retail_policy_views.py')]:assert p[key]==sha256(ROOT/file)
assert s['saved_helper_sha256']==p['saved_subgroups_helper_sha256'] and s['serving_sha256']==p['subgroup_serving_sha256']
suite=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(suite.attrib['tests'])==35 and int(suite.attrib['errors'])==int(suite.attrib['failures'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
for r in data['requirements']:
    if r['id'] in {'P1.04','P1.09'}:
        if r['id']=='P1.04':
            assert r['required_outputs']=='Action counts, expected declared cost, retrospective proxy, capacity overflow; preview/version/export.'
            assert r['acceptance']=='Không tự reassignment khi vượt capacity; cost units không tự gọi là cash loss; validation comparisons là exploratory.'
        else:
            assert r['required_outputs']=='Coverage, calibration/AUC/policy capture theo nhóm và exact export.'
            assert r['acceptance']=='Bỏ demographic predictors không chứng minh fairness; small groups không được gán ranking metrics; chưa có temporal drift.'
        evidence=[policy,policy_audit,groups,group_audit,tests,persist]
        entry={'checkpoint':r['id'].lower().replace('.','-')+'-saved-policy-subgroup-full-current-requirement','document':'docs/P1_POLICY_SUBGROUP_ACCEPTANCE_VI.md','policy_browser':policy,'policy_audit':policy_audit,'subgroup_browser':groups,'subgroup_audit':group_audit,'persistence':persist,'tests':tests,'scope':'Current historical validation policy/subgroup workflow,source/numerical reconciliation,immutable QA persistence and scoped export;all serving paths avoid inference;actual economics,temporal monitoring,fairness/production qualification remain open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{e:sha256(ROOT/e) for e in evidence},'full_completion_proven':True}
        entries=r.setdefault('completion_evidence',[])
        if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
        r['full_completion_proven']=True
    assert r['checkpoint_status']==before[r['id']][0]
    if r['id'] not in {'P1.04','P1.09'}:assert r['full_completion_proven']==before[r['id']][1]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirements':['P1.04','P1.09'],'full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
