import argparse,json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path.cwd();parser=argparse.ArgumentParser();parser.add_argument('browser');args=parser.parse_args()
browser=args.browser;tests='artifacts/private/finding-review-tests.xml'
b=json.loads(contained(ROOT,browser).read_text())
assert b['status']=='PASS' and len(b['view_scopes'])==9 and b['historical_exports']==4 and b['loan_timeline_export_parity']
assert b['conflict_rejected'] and b['modal_context_preserved'] and b['text_injection_not_executed'] and b['source_file_entries_unchanged']==44
assert b['user_reviews_unchanged'] and b['ledger_unchanged'] and b['mobile'] and not b['page_errors']
assert b['app_js_sha256']==sha256(ROOT/'apps/web/app.js') and b['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
assert b['method_sha256']==sha256(ROOT/'src/credit_atlas/finding_reports.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==41 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
regressions={
 'P2.01':'artifacts/private/source-run-browser-acceptance-1a612bed47a0/receipt.json',
 'P2.02':'artifacts/private/panel-quality-browser-acceptance-30e849b7f003/receipt.json',
 'P2.03':'artifacts/private/portfolio-browser-acceptance-45e115c3a11d/receipt.json',
 'P2.04':'artifacts/private/lifecycle-browser-acceptance-38c014dc0f34/receipt.json',
 'P2.05':'artifacts/private/transition-browser-acceptance-fa7846ab36a8/receipt.json',
 'P2.06':'artifacts/private/cure-browser-acceptance-c7e9d2f7a541/receipt.json',
 'P2.07':'artifacts/private/competing-browser-acceptance-d6afa092ce4d/receipt.json',
 'P2.09':'artifacts/private/observed-loss-details-browser-58cc5fc3e62d/receipt.json'}
privacy='artifacts/private/lifecycle-acceptance-e854aabc27b7/receipt.json';pv=json.loads((ROOT/privacy).read_text());assert pv['status']=='PASS' and pv['ledger_unchanged']
for f in pv['static_assets_checked']:assert sha256(contained(ROOT,f['path']))==f['sha256']
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'))
before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P2.10')
assert r['required_inputs']=='Current run/view/filters, quality/target/numerical evidence và reviewer text.'
assert r['required_outputs']=='Private findings, review history và evidence reports.'
assert r['acceptance']=='Không sửa source bằng memo; reviewed không là authenticated bank approval.'
entry={'checkpoint':'p2-private-finding-review-full-current-requirement','document':'docs/P2_FINDING_REVIEW_ACCEPTANCE_VI.md','browser':browser,'tests':tests,'scope':'All current local draft/revision/reopen/history/evidence-report requirements;modal context preserved;no source mutation or authenticated bank approval;identity/roles/team policy remain open','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{x:sha256(contained(ROOT,x)) for x in [browser,tests]},'full_completion_proven':True}
items=r.setdefault('completion_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in items):items.append(entry)
r['full_completion_proven']=True
for item in data['requirements']:
    if item['id'] in regressions:
        p=regressions[item['id']];v=json.loads((ROOT/p).read_text())
        assert v['status']=='PASS' and v['ledger_unchanged'] and not v['page_errors']
        assert v['app_js_sha256']==b['app_js_sha256'] and v['server_sha256']==b['server_sha256']
        entries=item.setdefault('runtime_regression_evidence',[])
        if not any(x.get('browser')==p for x in entries):entries.append({'checkpoint':'finding-review-regression','browser':p,'browser_sha256':sha256(ROOT/p),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'privacy_audit':privacy if item['id']=='P2.04' else None,'status':'PASS'})
    assert item['checkpoint_status']==before[item['id']][0]
    if item['id']!='P2.10':assert item['full_completion_proven']==before[item['id']][1]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.10','full_completion_proven_count':sum(bool(x['full_completion_proven']) for x in data['requirements']),'total':50,'goal_achieved':False}))
