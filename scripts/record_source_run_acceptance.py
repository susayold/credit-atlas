import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained,sha256

ROOT=Path.cwd()
audit='artifacts/private/source-run-acceptance-8d10b50dbedf/receipt.json'
browser='artifacts/private/source-run-browser-acceptance-c0e7b5549a22/receipt.json'
provenance='artifacts/private/mortgage-provenance-browser-06016d651e3a/receipt.json'
tests='artifacts/private/mortgage-provenance-tests.xml'
a=json.loads((ROOT/audit).read_text());b=json.loads((ROOT/browser).read_text());p=json.loads((ROOT/provenance).read_text())
assert a['status']==b['status']==p['status']=='PASS'
assert len(a['source_inputs'])==44 and a['pipeline_stages']==8 and a['data_readiness_receipt_parity']
assert sum(x['rows'] for x in a['zip_members'])==4560559 and all(x['crc_verified_by_full_read'] for x in a['zip_members'])
for f in a['source_inputs']:assert sha256(contained(ROOT,f['path']))==f['sha256']
for f,h in a['methods'].items():assert sha256(ROOT/f)==h
assert b['run_catalog_parity'] and b['evidence_artifacts_checked']==40 and b['readiness_partition_checks']==4 and len(b['scopes'])==4
assert all(x['source_scope_and_lineage_export']=='PASS' for x in b['scopes'])
assert b['mobile'] and not b['page_errors'] and b['ledger_unchanged'] and a['ledger_unchanged']
assert p['source_receipt_sha256']==a['source_receipt_sha256']
for x in [b,p]:
    assert x['app_js_sha256']==sha256(ROOT/'apps/web/app.js')
    assert x['server_sha256']==sha256(ROOT/'src/credit_atlas/server.py')
s=ET.parse(ROOT/tests).getroot().find('testsuite');assert int(s.attrib['tests'])==25 and int(s.attrib['failures'])==int(s.attrib['errors'])==0
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'))
before={r['id']:(r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']}
r=next(x for x in data['requirements'] if x['id']=='P2.01')
assert r['required_inputs']=='Freddie annual sample2012, raw receipt và run lineage.'
assert r['required_outputs']=='Source/run context, lineage và data readiness.'
assert r['acceptance']=='Không gọi sample50k là toàn thị trường; không thay extraction time bằng publication time.'
entry={'checkpoint':'p2-source-run-full-current-requirement','document':'docs/P2_SOURCE_RUN_ACCEPTANCE_VI.md','audit':audit,'browser':browser,'provenance_browser':provenance,'tests':tests,'scope':'All current source/run explorer supplied-corpus lineage/coverage/readiness/sample/time requirements;publisher authentication and additional annual vintages remain unproven','plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{x:sha256(ROOT/x) for x in [audit,browser,provenance,tests]},'full_completion_proven':True}
entries=r.setdefault('completion_evidence',[])
if not any(x.get('checkpoint')==entry['checkpoint'] for x in entries):entries.append(entry)
r['full_completion_proven']=True
for item in data['requirements']:
    assert item['checkpoint_status']==before[item['id']][0]
    if item['id']!='P2.01':assert item['full_completion_proven']==before[item['id']][1]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted_requirement':'P2.01','full_completion_proven_count':sum(bool(x['full_completion_proven']) for x in data['requirements']),'total':50,'goal_achieved':False}))
