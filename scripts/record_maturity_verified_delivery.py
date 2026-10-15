"""Record verified maturity delivery without claiming actual debt-service qualification."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

paths = {
    'source': 'artifacts/private/sec-maturity-acceptance-audit-36b22846d6dc/receipt.json',
    'browser': 'artifacts/private/sec-debt-qa-5648923643e0/receipt.json',
    'exports': 'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json',
    'metadata': 'artifacts/private/maturity-excel-metadata-3245a487a50e/receipt.json',
    'native': 'artifacts/private/native-excel-qa-sec-817f40ce0d7a/receipt.json',
    'perturbations': 'artifacts/private/native-excel-qa-maturity-cases-81cc3e93cc8b/perturbation-receipt.json',
    'workbook_browser': 'artifacts/private/sec-debt-xlsx-qa-798b967d62b7/receipt.json',
    'memo': 'artifacts/private/maturity-memo-capture-qa-53be504b0819/receipt.json',
}
evidence = {key: read(ROOT / path) for key, path in paths.items()}
assert all(item['status'] == 'PASS' for item in evidence.values())
assert len(evidence['source']['scopes']) == 134
assert evidence['source']['bucket_cells_checked'] == 804
assert evidence['source']['debt_method_sha256'] == digest(ROOT / 'src/credit_atlas/sec_debt.py')
assert len(evidence['exports']['scopes']) == len(evidence['metadata']['books']) == len(evidence['native']['books']) == 8
assert evidence['metadata']['method_sha256'] == digest(ROOT / 'scripts/audit_maturity_excel_metadata.py')
assert evidence['metadata']['source_receipt_sha256'] == digest(ROOT / paths['exports'])
assert evidence['exports']['builder_sha256'] == digest(ROOT / 'scripts/build_sec_debt_workbook.mjs')
for scope in evidence['exports']['scopes']:
    assert digest(ROOT / scope['workbook']) == scope['sha256']
    assert digest(ROOT / scope['capture']) == scope['capture_sha256']
assert evidence['native']['failed_checks'] == evidence['perturbations']['failed_checks'] == 0
assert evidence['native']['copies_not_saved'] and evidence['perturbations']['copies_not_saved']
assert len(evidence['perturbations']['cases']) == 48
assert sum(len(case['reads']) for case in evidence['perturbations']['cases']) == 336
assert len(evidence['memo']['cases']) == 8 and evidence['memo']['ledger_unchanged']
assert evidence['memo']['manifest_sha256'] == digest(ROOT / paths['exports'])
assert evidence['memo']['method_sha256'] == digest(ROOT / 'scripts/probe_maturity_memo_capture.py')
assert evidence['memo']['memo_method_sha256'] == digest(ROOT / 'src/credit_atlas/corporate_memos.py')

render_dir = ROOT / 'artifacts/private/maturity-native-render-20261015'
render = read(render_dir / 'receipt.json')
assert render['sources_unchanged'] and len(render['books']) == 8
for book in render['books']:
    assert digest(Path(book['source'])).upper() == book['source_sha256'].upper()
pngs = sorted(render_dir.glob('*.png'))
assert len(pngs) == 16
visual = {
    'status': 'PASS',
    'scope': 'All 16 native Excel images directly viewed in four batches: four issuers, two explicit families, summary and Facts A2:H11 ranges.',
    'reviewed_pngs': {p.name: digest(p) for p in pngs},
    'source_receipt_sha256': digest(render_dir / 'receipt.json'),
    'checks': ['leading-zero CIK', 'accession and dates', 'family', 'numeric and exact text', 'supported zero versus missing', 'subtotal and shares', 'readable headers and no clipping'],
    'limitation': 'Facts I onward and Metadata sheet are covered by XML metadata audit, not these rendered ranges.'
}
visual_path = render_dir / 'visual-review.json'
if visual_path.exists():
    assert read(visual_path) == visual
else:
    visual_path.write_text(json.dumps(visual, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
paths['visual'] = str(visual_path.relative_to(ROOT))
tests_path = ROOT / 'artifacts/private/maturity-memo-acceptance-tests.xml'
suite = ET.parse(tests_path).getroot().find('testsuite')
assert suite is not None and suite.attrib['tests'] == '33'
assert suite.attrib['errors'] == suite.attrib['failures'] == '0'
paths['tests'] = str(tests_path.relative_to(ROOT))

ledger_path = ROOT / 'docs/COMPLETION_REQUIREMENTS_50.json'
ledger = read(ledger_path)
original_requirements = [(r['id'], r['checkpoint_status'], r['required_inputs'], r['required_outputs'], r['acceptance'], r['next']) for r in ledger['requirements']]
requirement = next(r for r in ledger['requirements'] if r['id'] == 'P3.08')
entry = {
    'checkpoint': 'p3-maturity-metadata-native-visual-memo-20261015',
    'document': 'docs/P3_MATURITY_SOURCE_AUDIT_VI.md',
    **paths,
    'scope': 'Complete delivered SEC bucket workflow evidence: 134 API scopes, 8 Excel scopes, metadata, 48 native input cases/336 checks, 16 native images, 8 isolated synthetic memo histories, 33 tests. Actual facility payment/coupon/calendar/outstanding and full debt service remain unqualified.',
    'remaining': 'Instrument terms/effective amendments, actual balances and dated principal/interest payments, calendar qualification; memo full UI/review-package acceptance is separately open under P3.06/P3.10.',
    'full_completion_proven': False,
    'evidence_sha256': {p: digest(ROOT / p) for p in paths.values()},
}
if not any(x.get('checkpoint') == entry['checkpoint'] for x in requirement.setdefault('partial_evidence', [])):
    requirement['partial_evidence'].append(entry)
assert original_requirements == [(r['id'], r['checkpoint_status'], r['required_inputs'], r['required_outputs'], r['acceptance'], r['next']) for r in ledger['requirements']]
ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Verified maturity delivery recorded; full acceptance remains:', sum(bool(r['full_completion_proven']) for r in ledger['requirements']), '/50')
