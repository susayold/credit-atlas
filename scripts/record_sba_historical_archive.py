"""Append verified partial archive evidence without changing original scope/status."""
import json
from pathlib import Path
from credit_atlas.business_archive import AUDIT, AUDIT_SHA
from credit_atlas.workspace import sha256

root = Path.cwd().resolve()
path = root / 'docs/COMPLETION_REQUIREMENTS_50.json'
data = json.loads(path.read_text(encoding='utf-8'))
assert sha256(root / AUDIT) == AUDIT_SHA
folder = root / 'artifacts/private/sba-historical-report-f94f2ec47265'
receipt = json.loads((folder / 'receipt.json').read_text())
assert receipt['status'] == 'PASS' and sha256(folder / 'report.json') == receipt['report_sha256']
assert sha256(root / 'src/credit_atlas/business_archive.py') == receipt['method_sha256']
browser = root / 'artifacts/private/sba-archive-browser-9f81f814d663/receipt.json'
qa = json.loads(browser.read_text())
assert qa['status'] == 'PASS' and qa['ledger_unchanged'] and len(qa['checks']) == 5
assert qa['method_sha256'] == receipt['method_sha256']
assert qa['app_js_sha256'] == sha256(root / 'apps/web/app.js')
assert qa['server_sha256'] == sha256(root / 'src/credit_atlas/server.py')
entry = {'checkpoint': 'sba-march-historical-archive-api-ui-20261014',
         'document': 'docs/SBA_HISTORICAL_ARCHIVE_VI.md', 'audit': AUDIT,
         'report': str((folder / 'report.json').relative_to(root)),
         'tests': 'artifacts/private/sba-historical-archive-http-tests.xml',
         'browser': str(browser.relative_to(root)),
         'scope': 'Six March CSVs,2174502source records;independent CSV/Decimal audit;hash-verified API/UI/program-status/exact-amount report/export;21backend/HTTP tests and5actual-browser groups PASS;reload/mobile/outage-retry;frozen June case unchanged',
         'remaining': 'Current June requirement-level source/numerical/browser/export audit;historical schema/subprogram semantics,identity,transitions,publication timing and fixed-horizon PD remain unqualified',
         'full_completion_proven': False,
         'evidence_sha256': {str(f.relative_to(root)): sha256(f) for f in [root / AUDIT, folder / 'receipt.json', folder / 'report.json', browser, root / 'artifacts/private/sba-historical-archive-http-tests.xml']}}
before = [(r['id'], r['checkpoint_status'], r['full_completion_proven'], r['acceptance'], r['required_inputs'], r['required_outputs']) for r in data['requirements']]
for r in data['requirements']:
    if r['id'] in {'P3.01', 'P3.05', 'P3.09'}:
        evidence = r.setdefault('partial_evidence', [])
        if not any(e['checkpoint'] == entry['checkpoint'] for e in evidence): evidence.append(entry)
assert before == [(r['id'], r['checkpoint_status'], r['full_completion_proven'], r['acceptance'], r['required_inputs'], r['required_outputs']) for r in data['requirements']]
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Recorded partial evidence;full accepted requirements:', sum(r['full_completion_proven'] for r in data['requirements']))
