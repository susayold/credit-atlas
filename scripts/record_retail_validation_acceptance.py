import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path.cwd();audit='artifacts/private/retail-validation-acceptance-1a726071255c/receipt.json';browser='artifacts/private/retail-validation-browser-acceptance-0c1160bc0618/receipt.json';tests='artifacts/private/retail-validation-acceptance-tests.xml'
a=json.loads((ROOT/audit).read_text());b=json.loads((ROOT/browser).read_text())
assert a['status']==b['status']=='PASS' and a['validation_clients']==4499 and a['events']==995 and a['saved_score_rows']==13497
assert a['point_metric_checks']==24 and a['reliability_bin_checks']==60 and a['bootstrap_replicates']==1000 and a['interval_value_checks']==132 and a['max_abs_numeric_error']<=a['tolerance']==1e-12
assert a['validation_partition_ID_label_parity'] and a['selection_rule_parity'] and a['suite_projection_parity'] and a['freeze_before_final_evaluation_receipt']
assert a['model_fit_calls']==a['scoring_calls']==a['final_test_predictor_reads']==0 and a['ledger_unchanged']
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
assert a['method_sha256']==sha256(ROOT/'scripts/audit_retail_validation_acceptance.py')
assert len(b['variants'])==6 and b['reliability_bin_rows']==60 and b['chart_point_checks']==39 and b['validation_metric_rows']==6 and b['paired_metric_rows']==20
assert all(v['status']=='PASS' for v in b['variants']) and b['export_parity'] and b['final_chart_population_label_preserved'] and b['mobile'] and b['ledger_unchanged'] and not b['page_errors']
assert b['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and b['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==19 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
regression='artifacts/private/retail-data-contract-browser-954d18e891a6/receipt.json';v=json.loads((ROOT/regression).read_text());assert v['status']=='PASS' and v['ledger_unchanged'] and not v['page_errors'] and v['app_js_sha256']==b['app_js_sha256'] and v['server_sha256']==b['server_sha256']
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P1.03')
assert r['required_inputs']=='Train/calibration/validation/final-test client splits; history features; saved constant/logistic/boosting results.'
assert r['required_outputs']=='AUC/AP/Brier/log loss, reliability bins, paired uncertainty và selected model.'
assert r['acceptance']=='Không tune trên final test; random split được ghi rõ; bin rỗng không vẽ thành zero.'
entry={'checkpoint':'p1-behavioral-validation-full-current-requirement','document':'docs/P1_BEHAVIORAL_VALIDATION_ACCEPTANCE_VI.md','audit':audit,'browser':browser,'tests':tests,'scope':'Current historical random-cohort benchmark validation,independent six-variant metrics/bins/bootstrap/selection evidence,private suite export;no actual refit/rescore/final predictor reads;temporal/deployment/production qualification remains open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit,browser,tests]},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in entries):entries.append(entry)
r['full_completion_proven']=True
for item in data['requirements']:
    if item['id']=='P1.01':
        entries=item.setdefault('runtime_regression_evidence',[])
        if not any(x.get('browser')==regression for x in entries):entries.append({'checkpoint':'retail-validation-explorer-regression','browser':regression,'browser_sha256':sha256(ROOT/regression),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'status':'PASS'})
    assert item['checkpoint_status']==before[item['id']][0]
    if item['id']!='P1.03':assert item['full_completion_proven']==before[item['id']][1]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P1.03','full_completion_proven_count':sum(bool(x['full_completion_proven']) for x in data['requirements']),'total':50,'goal_achieved':False}))
