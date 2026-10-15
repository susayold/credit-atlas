"""Append numerical/runtime evidence;P3.03 Excel acceptance remains open."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import read_json,sha256,contained

p=argparse.ArgumentParser();p.add_argument('coverage_receipt');a=p.parse_args();root=Path.cwd().resolve()
ratio=root/'artifacts/private/sec-ratio-trend-audit-80083cbd6087/receipt.json'
coverage=contained(root,a.coverage_receipt)
trend_browser=root/'artifacts/private/sec-trends-qa-eb2275a0fceb/receipt.json'
coverage_browser=root/'artifacts/private/sec-coverage-qa-e8ff0e355242/receipt.json'
tests=root/'artifacts/private/sec-ratio-trend-acceptance-tests.xml'
r=read_json(ratio);c=read_json(coverage);tb=read_json(trend_browser);cb=read_json(coverage_browser)
assert all(x['status']=='PASS' for x in [r,c,tb,cb])
assert r['ratio_cells_checked']==268 and len(r['http_scopes'])==48 and r['supported_bridges_checked']==360
assert len(c['scopes'])==60 and not tb['errors'] and not cb['errors']
assert r['method_sha256']==sha256(root/'scripts/audit_sec_ratio_trend_acceptance.py')
assert c['method_sha256']==sha256(root/'scripts/audit_sec_coverage_scopes.py')
assert r['source_method_sha256']==sha256(root/'src/credit_atlas/sec_trends.py')
assert c['coverage_method_sha256']==sha256(root/'src/credit_atlas/sec_coverage.py')
assert r['source_statement_sha256']==sha256(root/'artifacts/private/sec-case-33077fe45722/annual-statements.json')
for name,digest in c['helper_sha256'].items():assert sha256(root/'scripts'/f'{name}.py')==digest
suite=ET.parse(tests).getroot().find('testsuite');assert suite.attrib['tests']=='36' and suite.attrib['errors']==suite.attrib['failures']=='0'
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
before=[(x['id'],x['checkpoint_status'],x['full_completion_proven'],x['required_inputs'],x['required_outputs'],x['acceptance']) for x in data['requirements']]
item=next(x for x in data['requirements'] if x['id']=='P3.03')
entry={'checkpoint':'p3-ratio-trend-coverage-source-runtime-audit-20261015',
    'document':'docs/P3_RATIO_TREND_AUDIT_VI.md','ratio_audit':str(ratio.relative_to(root)),
    'coverage_audit':str(coverage.relative_to(root)),'browser':str(trend_browser.relative_to(root)),
    'coverage_browser':str(coverage_browser.relative_to(root)),'tests':str(tests.relative_to(root)),
    'scope':'All268saved ratios201supported67unavailable;48trendHTTPscopes552comparisons360exact/rationalbridges;60explicit-expensecoverageHTTPscopes/rawcandidates;4issuer trend/coverage browser,exports/mobile/outage/reload and36testsPASS;no source/model change',
    'remaining':'Current complete Analysis/Facts Excel source/formula/filter/precision/missing qualification and final original requirement audit;ICR/DSCR/covenant/issuerPD/PIT qualifications remain unavailable',
    'full_completion_proven':False,
    'evidence_sha256':{str(f.relative_to(root)):sha256(f) for f in [ratio,coverage,trend_browser,coverage_browser,tests]}}
evidence=item.setdefault('partial_evidence',[])
if not any(x['checkpoint']==entry['checkpoint'] for x in evidence):evidence.append(entry)
assert before==[(x['id'],x['checkpoint_status'],x['full_completion_proven'],x['required_inputs'],x['required_outputs'],x['acceptance']) for x in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Added ratio/trend/coverage evidence;accepted:',sum(x['full_completion_proven'] for x in data['requirements']))
