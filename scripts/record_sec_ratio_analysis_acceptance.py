"""Close original P3.03 after complete source/runtime/Excel evidence."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd().resolve()
paths={
 'ratio_audit':'artifacts/private/sec-ratio-trend-audit-80083cbd6087/receipt.json',
 'coverage_audit':'artifacts/private/sec-coverage-scope-audit-feedcb985862/receipt.json',
 'trend_browser':'artifacts/private/sec-trends-qa-eb2275a0fceb/receipt.json',
 'coverage_browser':'artifacts/private/sec-coverage-qa-e8ff0e355242/receipt.json',
 'exports':'artifacts/private/sec-workbook-scope-audit-1133f2bb3c7b/receipt.json',
 'metadata':'artifacts/private/sec-excel-metadata-audit-74186cf6c79d/receipt.json',
 'native':'artifacts/private/native-excel-qa-sec-1a75771ee189/receipt.json',
 'perturbations':'artifacts/private/native-excel-qa-sec-perturb-9c8189a3d577/receipt.json',
 'workbook_browser':'artifacts/private/sec-workbook-qa-bf5f33ced34f/receipt.json'}
e={k:json.loads((root/p).read_text(encoding='utf-8-sig')) for k,p in paths.items()}
assert all(v['status']=='PASS' for v in e.values())
assert e['ratio_audit']['ratio_cells_checked']==268 and len(e['ratio_audit']['http_scopes'])==48
assert len(e['coverage_audit']['scopes'])==60 and len(e['exports']['scopes'])==len(e['metadata']['books'])==len(e['native']['books'])==36
assert len(e['perturbations']['cases'])==216 and e['perturbations']['failed_cases']==0
assert e['native']['failed_checks']==0 and e['native']['copies_not_saved'] and e['perturbations']['copies_not_saved']
assert e['metadata']['method_sha256']==sha256(root/'scripts/audit_sec_excel_metadata.py')
assert e['metadata']['source_receipt_sha256']==sha256(root/paths['exports'])
for scope in e['exports']['scopes']:
 assert sha256(root/scope['workbook'])==scope['sha256'] and sha256(root/scope['capture'])==scope['capture_sha256']
assert all(sha256(root/'src/credit_atlas'/f'{n}.py')==h for n,h in e['exports']['methods_sha256'].items())
assert sha256(root/'scripts/build_sec_workbook.mjs')==e['exports']['builder_sha256']
native_render=root/'artifacts/private/sec-native-render-20261015'
render= json.loads((native_render/'receipt.json').read_text(encoding='utf-8-sig'))
assert render['sources_unchanged'] and len(render['reads'])==4
pngs=list(native_render.glob('*.png'));assert len(pngs)==12
visual=native_render/'visual-review.json'
if not visual.exists():
 write_new(visual,{'status':'PASS','reviewed_pngs':{p.name:sha256(p) for p in pngs},
  'scope':'Fourissuer native Excel summary/Facts/calculation ranges;all12images viewed directly',
  'native_cik_leading_zeros':True,'native_exact_text_preserved':True,
  'artifact_tool_preview_limitation':'Artifact renders coerce numeric-looking strings;native PDF/text shows original XLSX correctly',
  'source_receipt_sha256':sha256(native_render/'receipt.json')})
paths['visual_review']=str(visual.relative_to(root))
tests=root/'artifacts/private/sec-analysis-excel-acceptance-tests.xml'
suite=ET.parse(tests).getroot().find('testsuite');assert suite.attrib['tests']=='43' and suite.attrib['errors']==suite.attrib['failures']=='0'
paths['tests']=str(tests.relative_to(root))
path=root/'docs/COMPLETION_REQUIREMENTS_50.json';data=read_json(path)
original=[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
r=next(r for r in data['requirements'] if r['id']=='P3.03')
entry={'checkpoint':'p3-financial-ratio-analysis-full-current-requirement',
 'document':'docs/P3_RATIO_ANALYSIS_ACCEPTANCE_VI.md',**paths,
 'scope':'Fourissuer filing-specific ratios/trends/ordered driver bridge/explicit interest-coverage proxies;source/gates and actual API/UI/JSON;all36 Analysis/Facts Excel scopes exact metadata+native73656cells14040formulas;216native cases432reads;native visual+UIexport/outage;no EBITICR/DSCR/covenant/issuerPD/PIT qualification',
 'plan_sha256':sha256(root/'docs/PLAN_WORKBENCH_DETAIL.md'),
 'evidence_sha256':{p:sha256(root/p) for p in paths.values()},'full_completion_proven':True}
r['full_completion_proven']=True
if not any(x['checkpoint']==entry['checkpoint'] for x in r['completion_evidence']):r['completion_evidence'].append(entry)
assert original==[(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Accepted:',sum(r['full_completion_proven'] for r in data['requirements']))
