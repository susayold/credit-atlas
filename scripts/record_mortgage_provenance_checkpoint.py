import json
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import contained, sha256

ROOT=Path(__file__).resolve().parents[1]
browser='artifacts/private/mortgage-provenance-browser-06016d651e3a/receipt.json'
tests='artifacts/private/mortgage-provenance-tests.xml'
b=json.loads((ROOT/browser).read_text())
assert b['status']=='PASS' and len(b['scopes'])==4 and b['ledger_unchanged'] and not b['page_errors']
assert b['mobile_no_overflow'] and b['source_receipt_parity'] and b['cross_origin_rejected']
assert sha256(ROOT/'apps/web/app.js')==b['app_js_sha256']
assert sha256(ROOT/'src/credit_atlas/server.py')==b['server_sha256']
assert sha256(ROOT/'src/credit_atlas/mortgage_provenance.py')==b['method_sha256']
s=ET.parse(ROOT/tests).getroot().find('testsuite')
assert int(s.attrib['tests'])==25 and int(s.attrib['errors'])==int(s.attrib['failures'])==0
paths={
 'P2.02':'artifacts/private/panel-quality-browser-acceptance-9b6359fcccd8/receipt.json',
 'P2.03':'artifacts/private/portfolio-browser-acceptance-3790dd4093e3/receipt.json',
 'P2.04':'artifacts/private/lifecycle-browser-acceptance-fc748c51ed1a/receipt.json',
 'P2.05':'artifacts/private/transition-browser-acceptance-13109efe0dba/receipt.json',
 'P2.06':'artifacts/private/cure-browser-acceptance-5de36f9d2a0b/receipt.json',
 'P2.07':'artifacts/private/competing-browser-acceptance-20fa0c3b1ec8/receipt.json',
}
file=ROOT/'docs/COMPLETION_REQUIREMENTS_50.json';data=json.loads(file.read_text(encoding='utf-8'))
before=[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
privacy='artifacts/private/lifecycle-acceptance-6b951d223297/receipt.json'
pv=json.loads((ROOT/privacy).read_text())
assert pv['status']=='PASS' and pv['ledger_unchanged']
for asset in pv['static_assets_checked']:assert sha256(contained(ROOT,asset['path']))==asset['sha256']
for r in data['requirements']:
    if r['id']=='P2.01':
        entry={'checkpoint':'receipt-backed-mortgage-provenance','document':'docs/P2_SOURCE_PROVENANCE_VI.md','browser':browser,'tests':tests,'scope':'Receipt declarations, publication unknown, distinct received/extraction/rebuild/case timestamps;fail-closed metadata API and scoped JSON;no source/model promotion','source_receipt_sha256':b['source_receipt_sha256'],'evidence_sha256':{p:sha256(ROOT/p) for p in [browser,tests]},'full_completion_proven':False}
        entries=r.setdefault('partial_evidence',[])
        if not any(x.get('checkpoint')==entry['checkpoint'] for x in entries):entries.append(entry)
    if r['id'] in paths:
        p=paths[r['id']];v=json.loads((ROOT/p).read_text())
        assert v['status']=='PASS' and v['ledger_unchanged'] and not v['page_errors']
        assert v['app_js_sha256']==b['app_js_sha256'] and v['server_sha256']==b['server_sha256']
        entries=r.setdefault('runtime_regression_evidence',[])
        if not any(x.get('browser')==p for x in entries):entries.append({'checkpoint':'mortgage-provenance-runtime-regression','browser':p,'browser_sha256':sha256(ROOT/p),'app_js_sha256':b['app_js_sha256'],'server_sha256':b['server_sha256'],'status':'PASS'})
        if r['id']=='P2.04':
            entry=next(x for x in entries if x.get('browser')==p)
            entry['privacy_audit']=privacy
            entry['privacy_audit_sha256']=sha256(ROOT/privacy)
assert before==[(r['id'],r['checkpoint_status'],r['full_completion_proven']) for r in data['requirements']]
file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'CHECKPOINT_RECORDED','full_completion_proven_count':sum(bool(r['full_completion_proven']) for r in data['requirements']),'total':50,'goal_achieved':False}))
