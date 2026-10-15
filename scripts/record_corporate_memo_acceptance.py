"""Original P3.06 output/acceptance evidence; no source-scope rewrite."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from credit_atlas.workspace import read_json, sha256, write_new

ROOT=Path(__file__).resolve().parents[1]
paths={'document':'docs/P3_CORPORATE_MEMO_ACCEPTANCE_VI.md',
       'capture':'artifacts/private/maturity-memo-capture-qa-53be504b0819/receipt.json',
       'http':'artifacts/private/corporate-memo-http-audit-19a0e10beed0/receipt.json',
       'browser':'artifacts/private/corporate-memo-qa-cf9d8c95db21/receipt.json',
       'timeline':'artifacts/private/sec-filing-timeline-audit-6c16a2df83a6/receipt.json',
       'timeline_browser':'artifacts/private/sec-events-qa-c4807e22e56d/receipt.json',
       'tests':'artifacts/private/corporate-memo-acceptance-tests.xml',
       'timeline_tests':'artifacts/private/sec-filing-timeline-acceptance-tests.xml'}
e={k:read_json(ROOT/p) for k,p in paths.items() if k in ['capture','http','browser','timeline','timeline_browser']}
assert all(r['status']=='PASS' for r in e.values())
assert len(e['capture']['cases'])==8 and e['capture']['memo_method_sha256']==sha256(ROOT/'src/credit_atlas/corporate_memos.py')
assert e['capture']['method_sha256']==sha256(ROOT/'scripts/probe_maturity_memo_capture.py')
assert e['http']['method_sha256']==sha256(ROOT/'scripts/audit_corporate_memo_http.py')
assert len(e['http']['cases'])==2 and all(c['revisions']==4 for c in e['http']['cases'])
assert all(sha256(ROOT/p)==h for p,h in e['http']['runtime_methods_sha256'].items())
assert all(sha256(ROOT/p)==h for p,h in e['http']['protected_sha256_unchanged'].items())
assert e['http']['browser_receipt_sha256']==sha256(ROOT/paths['browser'])
assert e['timeline']['row_metadata_checks']==2147 and e['timeline']['http_page_calls']==48
assert e['timeline']['method_sha256']==sha256(ROOT/'scripts/audit_sec_filing_timeline.py')
assert e['timeline']['timeline_method_sha256']==sha256(ROOT/'src/credit_atlas/sec_events.py')
assert all(sha256(ROOT/p)==h for p,h in e['timeline']['inputs_sha256'].items())
for key,count in [('tests',31),('timeline_tests',19)]:
    suite=ET.parse(ROOT/paths[key]).getroot().find('testsuite')
    assert int(suite.attrib['tests'])==count and suite.attrib['failures']==suite.attrib['errors']=='0'
for role in ['browser','timeline_browser']:
    folder=(ROOT/paths[role]).parent;pngs=list(folder.glob('*.png'));assert len(pngs)==2
    visual={'status':'PASS','scope':'Both actual desktop/mobile images directly viewed; mobile screenshot is viewport/panel scope, not entire editor fields.',
            'pngs':{p.name:sha256(p) for p in pngs},'source_receipt_sha256':sha256(folder/'receipt.json')}
    path=folder/'visual-review.json'
    if path.exists():assert read_json(path)==visual
    else:write_new(path,visual)
    paths[role+'_visual']=str(path.relative_to(ROOT))
path=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
requirement=next(r for r in data['requirements'] if r['id']=='P3.06')
entry={'checkpoint':'p3-corporate-financial-memo-full-current-requirement',**paths,
       'scope':'Verified financial memo editor/list/immutable source digest/atomic history/full private JSON; eight capture scopes and two real isolated UI/HTTP four-revision/outage/conflict/boundary cases; issuer metadata timeline2147rows48calls and browser;50tests. Self-declared owner/review; no issuerPD/approval/DSCR/covenant or full-text event qualification.',
       'plan_sha256':sha256(ROOT/'docs/PLAN_WORKBENCH_DETAIL.md'),'evidence_sha256':{p:sha256(ROOT/p) for p in paths.values()},'full_completion_proven':True}
if not any(e.get('checkpoint')==entry['checkpoint'] for e in requirement['completion_evidence']):requirement['completion_evidence'].append(entry)
requirement['full_completion_proven']=True
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Accepted:',sum(r['full_completion_proven'] for r in data['requirements']),'/50')
