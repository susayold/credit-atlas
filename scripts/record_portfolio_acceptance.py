import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path(__file__).resolve().parents[1]
audit_path='artifacts/private/portfolio-acceptance-d7a11b41726a/receipt.json'
browser_path='artifacts/private/portfolio-browser-acceptance-28552f897b7b/receipt.json'
tests_path='artifacts/private/portfolio-acceptance-tests.xml'
a=json.loads((ROOT/audit_path).read_text());b=json.loads((ROOT/browser_path).read_text())
assert a['status']=='PASS' and a['loan_months']==4510559 and a['monthly_checks']==7182
assert a['monthly_scope_rows']==513 and a['profile_dimensions']==13 and a['profile_groups']==102 and a['source_loans']==50000 and a['export_scopes']==16
assert b['status']=='PASS' and len(b['scopes'])==6 and b['profile_bucket_checks']==408 and b['chart_point_checks']==360
assert all(c['status']=='PASS' for c in b['scopes']) and b['mobile'] and b['empty_range_reload'] and not b['page_errors'] and b['ledger_unchanged'] and a['ledger_unchanged']
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for p,h in a['methods'].items():assert sha256(ROOT/p)==h
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/case-complete.json')==a['case_receipt_sha256']
assert sha256(ROOT/'apps/web/app.js')==b['app_js_sha256'] and sha256(ROOT/'src/credit_atlas/server.py')==b['server_sha256']
s=ET.parse(ROOT/tests_path).getroot().find('testsuite');assert int(s.attrib['tests'])==27 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(r for r in data['requirements'] if r['id']=='P2.03')
assert r['required_inputs']=='Observed loan-month states/UPB; segment, reporting-month filters và vintage labels.'
assert r['required_outputs']=='Monthly charts, profile, selected-scope aggregate export.'
assert r['acceptance']=='Zero UPB giữ riêng; count và balance có denominator khác; không cộng duplicate loan-months thành unique loans.'
entry={'checkpoint':'p2-portfolio-full-current-requirement','document':'docs/P2_PORTFOLIO_ACCEPTANCE_VI.md','audit':audit_path,'browser':browser_path,'tests':tests_path,
       'scope':'All current P2.03 monthly/profile/filter/zero/denominator requirements;ledger basis display corrected;multi-vintage composition remains next-stage work',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit_path,browser_path,tests_path]},'full_completion_proven':True}
items=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in items):items.append(entry)
r['full_completion_proven']=True
regressions={'P2.04':'artifacts/private/lifecycle-browser-acceptance-d26ebafc7b2b/receipt.json','P2.05':'artifacts/private/transition-browser-acceptance-e67e015a9055/receipt.json','P2.06':'artifacts/private/cure-browser-acceptance-d2f94359d516/receipt.json','P2.07':'artifacts/private/competing-browser-acceptance-3117cc8058a2/receipt.json'}
privacy='artifacts/private/lifecycle-acceptance-326d86ee5e4e/receipt.json';priv=json.loads((ROOT/privacy).read_text());assert priv['status']=='PASS' and priv['ledger_unchanged']
for f in priv['static_assets_checked']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for requirement in data['requirements']:
    if requirement['id'] in regressions:
        p=regressions[requirement['id']];receipt=json.loads((ROOT/p).read_text())
        assert receipt['status']=='PASS' and receipt['ledger_unchanged'] and not receipt['page_errors']
        assert receipt['app_js_sha256']==b['app_js_sha256'] and receipt['server_sha256']==b['server_sha256']
        entries=requirement.setdefault('runtime_regression_evidence',[])
        if not any(e.get('browser')==p for e in entries):entries.append({'checkpoint':'portfolio-basis-regression','browser':p,'browser_sha256':sha256(ROOT/p),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'status':'PASS','privacy_audit':privacy if requirement['id']=='P2.04' else None})
    assert before[requirement['id']][0]==requirement['checkpoint_status']
    if requirement['id']!='P2.03':assert before[requirement['id']][1]==requirement['full_completion_proven']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.03','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
