"""Close only original descriptive SBA requirements after all scoped evidence."""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from credit_atlas.workspace import contained, read_json, sha256

parser = argparse.ArgumentParser();parser.add_argument('support_receipt');args = parser.parse_args()
root = Path.cwd().resolve()
audit_path = root/'artifacts/private/sba-june-acceptance-audit-68fc1c9fc7f3/receipt.json'
dictionary_path = root/'artifacts/private/sba-dictionary-cells-audit-3a7a239b2dcc/receipt.json'
browser_path = root/'artifacts/private/sba-june-browser-acceptance-2aa48e282571/receipt.json'
support_path = contained(root,args.support_receipt)
tests_path = root/'artifacts/private/sba-june-acceptance-tests.xml'
audit = read_json(audit_path);dictionary = read_json(dictionary_path);browser = read_json(browser_path);support = read_json(support_path)
assert all(x['status'] == 'PASS' for x in [audit,dictionary,browser,support])
assert audit['source_records'] == 2190504 and audit['canonical_cells_compared'] == 54762600
assert audit['aggregate_cells_checked'] == 1197 and len(audit['segments']) == 6
assert set(audit['aggregate_dimensions_checked']) == {'program_status','approval_fiscal_year','project_state','naics_two_digit'}
assert sha256(root/'scripts/audit_sba_june_acceptance.py') == audit['audit_method_sha256']
assert sha256(root/'scripts/audit_sba_dictionary_cells.py') == dictionary['method_sha256']
assert dictionary['total_fields'] == 81 and dictionary['total_cells'] == 162
assert browser['program_dimension_combinations'] == 12 and browser['dictionary_fields_checked'] == 81
assert support['snapshot_share_cells_checked'] == 1197 and support['selected_status_drilldown']
for qa,method in [(browser,'browser_sba_june_acceptance.py'),(support,'browser_sba_status_support.py')]:
    assert qa['ledger_unchanged'] and not qa['page_errors']
    assert qa['app_js_sha256'] == sha256(root/'apps/web/app.js')
    assert qa['server_sha256'] == sha256(root/'src/credit_atlas/server.py')
    assert qa['method_sha256'] == sha256(root/'scripts'/method)
for evidence in [audit,dictionary]:
    assert all(sha256(root/p) == digest for p,digest in evidence['inputs_sha256'].items())
suite = ET.parse(tests_path).getroot().find('testsuite')
assert int(suite.attrib['tests']) == 23 and int(suite.attrib['failures']) == int(suite.attrib['errors']) == 0
path = root/'docs/COMPLETION_REQUIREMENTS_50.json';data = read_json(path)
original = [(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
entry = {'checkpoint':'p3-sba-descriptive-full-current-requirements',
    'document':'docs/P3_SBA_DESCRIPTIVE_ACCEPTANCE_VI.md','audit':str(audit_path.relative_to(root)),
    'dictionary_audit':str(dictionary_path.relative_to(root)),'browser':str(browser_path.relative_to(root)),
    'support_browser':str(support_path.relative_to(root)),'tests':str(tests_path.relative_to(root)),
    'scope':'Current June six-source dictionary/quality/status/FY/sector/geography descriptive workflow;whole raw-to-canonical and all1197marts cells parity;81fields162dictionarycells,12scope downloads and1197share denominators;not unique borrowers,EAD,fixed-horizon PD or whole SME market',
    'plan_sha256':sha256(root/'docs/PLAN_WORKBENCH_DETAIL.md'),
    'evidence_sha256':{str(f.relative_to(root)):sha256(f) for f in [audit_path,dictionary_path,browser_path,support_path,tests_path]},
    'full_completion_proven':True}
for r in data['requirements']:
    if r['id'] in {'P3.01','P3.05','P3.09'}:
        r['full_completion_proven'] = True
        if not any(e['checkpoint'] == entry['checkpoint'] for e in r['completion_evidence']):r['completion_evidence'].append(entry)
assert original == [(r['id'],r['checkpoint_status'],r['required_inputs'],r['required_outputs'],r['acceptance'],r['next']) for r in data['requirements']]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'full_completion_proven':sum(r['full_completion_proven'] for r in data['requirements']),'scope_unchanged':True}))
