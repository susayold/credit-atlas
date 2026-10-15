import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256,contained

ROOT=Path.cwd();audit='artifacts/private/retail-data-contract-audit-b3bb54ab0deb/receipt.json';browser='artifacts/private/retail-data-contract-browser-da8a969e3028/receipt.json';tests='artifacts/private/retail-data-contract-tests.xml'
a=json.loads((ROOT/audit).read_text());b=json.loads((ROOT/browser).read_text())
assert a['status']==b['status']=='PASS' and a['clients']==30000 and a['history_rows']==180000 and a['fresh_predictor_row_reads']==0
assert a['fresh_footer_checks']==2 and a['feature_mapping_checks']==23 and a['category_cells']==133 and a['ledger_unchanged']
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
assert a['method_sha256']==sha256(ROOT/'scripts/audit_retail_data_contract.py')
assert b['history_rows_checked']==6 and b['split_rows_checked']==4 and b['feature_fields_checked']==23 and b['category_rows_checked']==133
assert b['json_export_parity'] and b['reload_and_tab_navigation'] and b['outage_retry'] and b['mobile'] and b['ledger_unchanged'] and not b['page_errors']
assert b['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and b['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py') and b['method_sha256']==sha256(ROOT/'src/credit_atlas/retail_data_contract.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==22 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
reference=ROOT/'data/private/retail-reference/uci350-reference-6d33854afcef';rr=json.loads((reference/'receipt.json').read_text(encoding='utf-8-sig'))
assert rr['status']=='ACQUIRED' and rr['added_temporal_cohorts']==rr['client_rows_downloaded']==0 and len(rr['files'])==2
for f in rr['files']:assert sha256(reference/f['file'])==f['sha256']
assert json.loads((reference/'metadata.json').read_text())['data']==json.loads((ROOT/'data/private/public-suite/suite-619b1ee9aa8c/uci-retail-metadata.json').read_text())['data']
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P1.01')
assert r['required_inputs']=='UCI350: khách hàng thẻ Taiwan; bill/payment/status sáu tháng; target tháng kế tiếp.'
assert r['required_outputs']=='Source profile, target card, split support và giới hạn population.'
assert r['acceptance']=='Client/history counts reconcile; source ID không là predictor; tháng và missing sentinels có nghĩa rõ.'
entry={'checkpoint':'p1-data-target-full-current-requirement','document':'docs/P1_DATA_TARGET_ACCEPTANCE_VI.md','audit':audit,'browser':browser,'tests':tests,'scope':'Current source/target/month/missing-category/split/population contract;hash-verified pre-freeze full-row parity,current footers and aggregate consistency;no new final predictor read or model change;temporal/Vietnam/intended-use qualification remains open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'reference_receipt':str((reference/'receipt.json').relative_to(ROOT)),'reference_receipt_sha256':sha256(reference/'receipt.json'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit,browser,tests]},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in entries):entries.append(entry)
r['full_completion_proven']=True
quality='artifacts/private/retail-source-quality-qa-228bfa9a3dc9/receipt.json';q=json.loads((ROOT/quality).read_text());assert q['status']=='PASS' and q['ledger_unchanged'] and len(q['checks'])==6
entries=r.setdefault('runtime_regression_evidence',[])
if not any(x.get('browser')==quality for x in entries):entries.append({'checkpoint':'retail-source-quality-monitor-json-excel-regression','browser':quality,'browser_sha256':sha256(ROOT/quality),'scope':'Existing source-quality API/UI/monitor/JSON/Excel,690000 denominator,outage-null/reload/mobile;no native Excel qualification inferred','status':'PASS'})
regression='artifacts/private/source-run-browser-acceptance-3883e6d66a75/receipt.json';v=json.loads((ROOT/regression).read_text());assert v['status']=='PASS' and v['ledger_unchanged'] and not v['page_errors'] and v['app_js_sha256']==b['app_js_sha256'] and v['server_sha256']==b['server_sha256']
for item in data['requirements']:
    if item['id']=='P2.01':
        entries=item.setdefault('runtime_regression_evidence',[])
        if not any(x.get('browser')==regression for x in entries):entries.append({'checkpoint':'retail-data-contract-non-retail-regression','browser':regression,'browser_sha256':sha256(ROOT/regression),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'status':'PASS'})
    assert item['checkpoint_status']==before[item['id']][0]
    if item['id']!='P1.01':assert item['full_completion_proven']==before[item['id']][1]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P1.01','full_completion_proven_count':sum(bool(x['full_completion_proven']) for x in data['requirements']),'total':50,'goal_achieved':False}))
