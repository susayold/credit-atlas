import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path.cwd()
audit='artifacts/private/observed-loss-source-audit-627ae17a9d01/receipt.json'
browser='artifacts/private/observed-loss-details-browser-84fdd0059671/receipt.json'
tests='artifacts/private/observed-loss-details-tests.xml'
a=json.loads((ROOT/audit).read_text());b=json.loads((ROOT/browser).read_text())
assert a['status']=='SOURCE_AUDIT_PASS_WITH_PRESENTATION_GAPS' and a['source_terminal_rows']==381 and a['canonical_decimal_parity_checks']==4191 and a['saved_row_field_checks']==3810
assert a['reported_loss_loans']==374 and a['unresolved']==7 and a['expense_formula_checked_rows']==a['loss_formula_checked_rows']==374
assert a['max_abs_expense_residual_exact']==a['max_abs_loss_residual_exact']=='0.000000'
assert a['method_sha256']==sha256(ROOT/'scripts/audit_observed_loss_source.py')
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
assert b['status']=='PASS' and len(b['scopes'])==4 and b['field_quality_checks']==220 and b['source_decimal_parity'] and b['mobile'] and b['ledger_unchanged'] and not b['page_errors']
assert b['method_sha256']==sha256(ROOT/'src/credit_atlas/observed_loss_details.py')
assert b['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and b['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==26 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
regressions={
 'P2.01':'artifacts/private/source-run-browser-acceptance-da37474bfe05/receipt.json',
 'P2.02':'artifacts/private/panel-quality-browser-acceptance-6e3631025258/receipt.json',
 'P2.03':'artifacts/private/portfolio-browser-acceptance-e0b3239eb2e4/receipt.json',
 'P2.04':'artifacts/private/lifecycle-browser-acceptance-a06a777c0b44/receipt.json',
 'P2.05':'artifacts/private/transition-browser-acceptance-7327858464ff/receipt.json',
 'P2.06':'artifacts/private/cure-browser-acceptance-1fb9e3e65dd7/receipt.json',
 'P2.07':'artifacts/private/competing-browser-acceptance-4b51905da157/receipt.json'}
privacy='artifacts/private/lifecycle-acceptance-33b471978f24/receipt.json';p=json.loads((ROOT/privacy).read_text());assert p['status']=='PASS' and p['ledger_unchanged']
for f in p['static_assets_checked']:assert sha256(contained(ROOT,f['path']))==f['sha256']
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'))
before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P2.09')
assert r['required_inputs']=='Source loss/recovery/cost fields, observation periods và terminal information.'
assert r['required_outputs']=='Loss components/coverage, reconciliation và selected-scope export.'
assert r['acceptance']=='Không fill missing bằng zero; sample không representative LGD calibration; UPB không tự là economic loss.'
entry={'checkpoint':'p2-observed-loss-full-current-requirement','document':'docs/P2_OBSERVED_LOSS_ACCEPTANCE_VI.md','audit':audit,'browser':browser,'tests':tests,'scope':'Current supplied-corpus observed loss bridge,exact component/expense reconciliation,coverage,signs and scoped exports;legacy magnitude clarified,signed diagnostic added;qualified LGD/ECL and recovery timing remain open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{x:sha256(ROOT/x) for x in [audit,browser,tests]},'full_completion_proven':True}
items=r.setdefault('completion_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in items):items.append(entry)
r['full_completion_proven']=True
for requirement in data['requirements']:
    if requirement['id'] in regressions:
        path=regressions[requirement['id']];v=json.loads((ROOT/path).read_text())
        assert v['status']=='PASS' and v['ledger_unchanged'] and not v['page_errors']
        assert v['app_js_sha256']==b['app_js_sha256'] and v['server_sha256']==b['server_sha256']
        entries=requirement.setdefault('runtime_regression_evidence',[])
        if not any(x.get('browser')==path for x in entries):entries.append({'checkpoint':'observed-loss-details-regression','browser':path,'browser_sha256':sha256(ROOT/path),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'privacy_audit':privacy if requirement['id']=='P2.04' else None,'status':'PASS'})
    assert requirement['checkpoint_status']==before[requirement['id']][0]
    if requirement['id']!='P2.09':assert requirement['full_completion_proven']==before[requirement['id']][1]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.09','full_completion_proven_count':sum(bool(x['full_completion_proven']) for x in data['requirements']),'total':50,'goal_achieved':False}))
