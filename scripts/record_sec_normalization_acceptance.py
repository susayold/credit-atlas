"""Close original P3.02 only after full source/cache/runtime evidence."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import read_json,sha256,contained

p=argparse.ArgumentParser();p.add_argument('browser_receipt');args=p.parse_args();root=Path.cwd().resolve()
audit_path=root/'artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json'
probe_path=root/'artifacts/private/sec-cache-runtime-probe-a1506d5aa260/receipt.json'
browser_path=contained(root,args.browser_receipt)
tests_path=root/'artifacts/private/sec-read-cache-tests.xml'
http_path=root/'artifacts/private/sec-cache-http-regression-tests.xml'
audit=read_json(audit_path);probe=read_json(probe_path);browser=read_json(browser_path)
assert all(r['status']=='PASS' for r in [audit,probe,browser])
assert (audit['fact_entries'],audit['unique_filings'],audit['annual_field_states_checked'])==(105441,13374,536)
assert audit['field_status_counts']=={'supported':468,'missing':48,'ambiguous':20}
assert audit['method_sha256']==sha256(root/'scripts/audit_sec_normalization_acceptance.py')
assert all(sha256(root/name)==digest for name,digest in audit['inputs_sha256'].items())
assert probe['original_full_verifier_calls']==1 and probe['concurrent_reads']==8 and probe['annual_report_parities']==67
assert probe['method_sha256']==sha256(root/'src/credit_atlas/sec_read_cache.py')
assert probe['probe_method_sha256']==sha256(root/'scripts/probe_sec_verified_cache.py')
assert browser['annual_reports_checked']==67 and browser['latest_ui_fields_checked']==32
assert browser['app_js_sha256']==sha256(root/'apps/web/app.js') and browser['server_sha256']==sha256(root/'src/credit_atlas/server.py')
assert browser['method_sha256']==sha256(root/'scripts/browser_sec_normalization_acceptance.py')
assert not browser['page_errors'] and browser['ledger_unchanged'] and probe['ledger_unchanged']
for path,count in [(tests_path,42),(http_path,31)]:
    suite=ET.parse(path).getroot().find('testsuite')
    assert int(suite.attrib['tests'])==count and suite.attrib['errors']==suite.attrib['failures']=='0'
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P3.02')
entry={'checkpoint':'p3-sec-normalization-full-current-requirement',
    'document':'docs/P3_SEC_NORMALIZATION_ACCEPTANCE_VI.md','audit':str(audit_path.relative_to(root)),
    'browser':str(browser_path.relative_to(root)),'runtime_probe':str(probe_path.relative_to(root)),
    'tests':str(tests_path.relative_to(root)),'http_regression':str(http_path.relative_to(root)),
    'scope':'Current four-issuer source-native SEC normalization;105441facts13374filings/occurrences,67annual536fields,allcandidate evidence;native units/periods/conflicts preserved;original full verification plus hash-guarded serialized cache;67actual HTTP reports32UIfields/export/reload/mobile/cutoff;no PIT,complete custom taxonomy,issuerPD or production qualification',
    'plan_sha256':sha256(root/'docs/PLAN_WORKBENCH_DETAIL.md'),
    'evidence_sha256':{str(f.relative_to(root)):sha256(f) for f in [audit_path,probe_path,browser_path,tests_path,http_path]},
    'full_completion_proven':True}
r['full_completion_proven']=True
if not any(e['checkpoint']==entry['checkpoint'] for e in r['completion_evidence']):r['completion_evidence'].append(entry)
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'accepted':sum(r['full_completion_proven'] for r in data['requirements']),'scope_unchanged':True}))
