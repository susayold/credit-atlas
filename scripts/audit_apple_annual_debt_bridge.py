"""Independent integer reconciliation of acquired issuer annual debt tables."""
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/private/sec-documents/apple-annual-debt-d2fac541f9a3'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def numbers(row):
    values = []
    for cell in row[1:]:
        if re.fullmatch(r'\(?[0-9]+(?:,[0-9]{3})*\)?', cell):
            values.append(int(cell.strip('()').replace(',', '')) * (-1 if cell.startswith('(') else 1))
    return values

receipt = read(SOURCE / 'acquisition.json')
assert receipt['status'] == 'ACQUIRED'
assert sha(SOURCE / receipt['file']) == receipt['sha256']
assert sha(SOURCE / receipt['tables_file']) == receipt['tables_sha256']
feed = read(SOURCE / 'issuer-feed.json')['GetEdgarFilingListResult']
matches = [x for x in feed if x['StockSymbol'] == receipt['cik'] and x['FilingTypeMnemonic'] == '10-K'
           and x['FilingDate'].startswith('10/31/2025')
           and any(d['DocumentType'] == 'HTML' and d['Url'] == receipt['url'] for d in x['DocumentList'])]
assert len(matches) == 1
tables = read(SOURCE / 'debt-tables.json')['tables']
summary, maturity = tables
labels = ['Total term debt principal', 'Unamortized premium/(discount) and issuance costs, net',
          'Hedge accounting fair value adjustments', 'Total term debt',
          'Less: Current portion of term debt', 'Total non-current portion of term debt']
rows = {row[0]: numbers(row) for row in summary if row and row[0] in labels}
assert all(len(rows[label]) == 2 for label in labels)
bridges = []
for index, year in enumerate([2025, 2024]):
    principal, discount, hedge, carrying, current, noncurrent = [rows[k][index] for k in labels]
    assert principal + discount + hedge == carrying
    assert carrying + current == noncurrent
    bridges.append({'year': year, 'unit': 'USD millions', 'principal': principal,
                    'discount_and_costs': discount, 'hedge_fair_value_adjustment': hedge,
                    'carrying': carrying, 'current_carrying': -current, 'noncurrent_carrying': noncurrent})
profile = {row[0]: numbers(row)[0] for row in maturity if row and row[0]}
keys = ['2026', '2027', '2028', '2029', '2030', 'Thereafter']
assert sum(profile[k] for k in keys) == profile['Total term debt principal'] == bridges[0]['principal']
exports = ROOT / 'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json'
scope = next(s for s in read(exports)['scopes'] if s['query']['cik'] == receipt['cik'] and s['query']['debt_scope'] == 'debt_only')
capture_path = ROOT / scope['capture']
assert sha(capture_path) == scope['capture_sha256']
capture = read(capture_path)
assert capture['statement']['accession'] == receipt['accession']
assert capture['statement']['report_date'] == receipt['report_end']
assert capture['statement']['filing_date'] == receipt['filing_date']
for label, bucket in zip(keys, capture['buckets']):
    assert profile[label] * 1000000 == int(bucket['field']['value_exact'])
catalog_path = ROOT / 'artifacts/private/apple-notes-be3d7047f347/catalog.json'
catalog = read(catalog_path)
aggregate_2025 = next(numbers(row)[0] for row in summary if row and row[0] == 'Fixed-rate 4.000% – 4.750% notes')
assert aggregate_2025 * 1000000 == sum(int(note['original_issue_principal_usd_exact']) for note in catalog['notes'])
out = ROOT / 'artifacts/private' / ('apple-annual-debt-bridge-' + uuid4().hex[:12])
out.mkdir()
result = {'status': 'PASS', 'source': str(SOURCE.relative_to(ROOT)), 'filing_id': matches[0]['FilingId'],
          'cik': receipt['cik'], 'accession': receipt['accession'], 'report_end': receipt['report_end'],
          'bridges': bridges, 'maturity_usd_millions': profile,
          'first_year_principal_minus_current_carrying_usd_millions': profile['2026'] - bridges[0]['current_carrying'],
          'four_series_original_principal_matches_2025_aggregate': True,
          'qualification': {'per_series_outstanding': False, 'actual_payments': False, 'payment_calendar': False, 'full_debt_service': False},
          'interpretation': 'Aggregate 2025 issue principal matches four original note sizes; this does not prove each series remained outstanding or actual coupon payments. Fiscal buckets are not calendar payment dates. Current carrying debt differs from first-year principal.',
          'inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in [SOURCE / 'acquisition.json', SOURCE / receipt['file'], SOURCE / 'debt-tables.json', SOURCE / 'issuer-feed.json', exports, capture_path, catalog_path]},
          'method_sha256': sha(Path(__file__))}
(out / 'receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(out)
print('PASS: two annual carrying bridges, six fiscal maturity buckets, aggregate original issuance; actual series payments remain unqualified')
