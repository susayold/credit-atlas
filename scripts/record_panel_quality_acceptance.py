import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path(__file__).resolve().parents[1]
audit_path='artifacts/private/panel-quality-acceptance-6f1ed5abead2/receipt.json'
browser_path='artifacts/private/panel-quality-browser-acceptance-861f7799b297/receipt.json'
tests_path='artifacts/private/panel-quality-acceptance-tests.xml'
a=json.loads((ROOT/audit_path).read_text());b=json.loads((ROOT/browser_path).read_text())
assert a['status']=='PASS' and a['technical_checks']==18 and a['raw_blank_field_checks']==64 and a['sentinel_fields']==6
assert a['monthly_mapping_rows']==4510559 and a['mapping_differences']==0 and a['ledger_unchanged']
assert b['status']=='PASS' and len(b['scopes'])==4 and all(r['status']=='PASS' for r in b['scopes']) and b['mobile'] and b['ledger_unchanged'] and not b['page_errors']
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for p,h in a['methods'].items():assert sha256(ROOT/p)==h
assert sha256(ROOT/'apps/web/app.js')==b['app_js_sha256'] and sha256(ROOT/'src/credit_atlas/server.py')==b['server_sha256']
assert sha256(ROOT/'artifacts/private/d01-a24484b21a21/case-complete.json')==a['case_receipt_sha256']
s=ET.parse(ROOT/tests_path).getroot().find('testsuite');assert int(s.attrib['tests'])==49 and int(s.attrib['errors'])==0 and int(s.attrib['failures'])==0
receipt_path=ROOT/'vendor/credit_risk_strategy_lab/data/private/raw/35c41582157804e3f632d68140246fcc6eb0973590ba0cf9a0f03600bf8499f9.receipt.json'
receipt=json.loads(receipt_path.read_text());assert receipt['release_confirmation']=='user_supplied; not authenticated by file hash registry'
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(path.read_text(encoding='utf-8'));before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(r for r in data['requirements'] if r['id']=='P2.02')
assert r['required_inputs']=='Origination/performance panel, keys/months, sentinels và quality findings.'
assert r['required_outputs']=='Quality issues, affected counts, source investigation evidence.'
assert r['acceptance']=='Unknown/gap không trở thành current; không nối qua khoảng thiếu dữ liệu.'
entry={'checkpoint':'p2-panel-quality-full-current-requirement','document':'docs/P2_PANEL_QUALITY_ACCEPTANCE_VI.md','audit':audit_path,'browser':browser_path,'tests':tests_path,
       'scope':'All current P2.02 supplied-corpus quality/readout/unknown/gap requirements;publisher release/PIT authentication not claimed',
       'source_release_confirmation':receipt['release_confirmation'],'source_receipt_sha256':sha256(receipt_path),
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in [audit_path,browser_path,tests_path]},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(e.get('checkpoint')==entry['checkpoint'] for e in entries):entries.append(entry)
r['full_completion_proven']=True
finding={'checkpoint':'raw-receipt-release-provenance-finding','document':'docs/P2_PANEL_QUALITY_ACCEPTANCE_VI.md','source_receipt_sha256':sha256(receipt_path),'scope':'Supplied release47 declaration is not authenticated by publisher hash registry;byte consistency is not publication time or publisher release identity','full_completion_proven':False}
p1=next(r for r in data['requirements'] if r['id']=='P2.01');findings=p1.setdefault('partial_evidence',[])
if not any(e.get('checkpoint')==finding['checkpoint'] for e in findings):findings.append(finding)
for other in data['requirements']:
    assert before[other['id']][0]==other['checkpoint_status']
    if other['id']!='P2.02':assert before[other['id']][1]==other['full_completion_proven']
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.02','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
