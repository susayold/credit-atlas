"""Independent DOM instance audit plus original annual table reconciliation."""
from pathlib import Path
from decimal import Decimal, InvalidOperation
from collections import Counter
from uuid import uuid4
import hashlib
import json
import zipfile
from xml.dom import minidom
from acquire_apple_annual_debt_evidence import Tables

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/private/sec-documents/apple-annual-xbrl-a596bfb03297'
ANNUAL = ROOT / 'data/private/sec-documents/apple-annual-debt-d2fac541f9a3'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

acquisition = read(SOURCE / 'acquisition.json')
assert acquisition['status'] == 'ACQUIRED_AND_PROFILED'
assert sha(SOURCE / acquisition['file']) == acquisition['sha256']
assert sha(SOURCE / acquisition['profile']) == acquisition['profile_sha256']
assert sha(ROOT / acquisition['feed_path']) == acquisition['feed_sha256']
assert sha(ROOT / 'scripts/acquire_apple_annual_xbrl_debt.py') == acquisition['method_sha256']
annual = read(ANNUAL / 'acquisition.json')
assert sha(ANNUAL / annual['file']) == annual['sha256']
inline_receipt = read(SOURCE / 'inline-acquisition.json')
assert inline_receipt['status'] == 'ACQUIRED' and inline_receipt['issuer_filing_id'] == acquisition['issuer_filing_id']
assert sha(SOURCE / inline_receipt['file']) == inline_receipt['sha256']
assert inline_receipt['feed_sha256'] == acquisition['feed_sha256']
filing = next(f for f in read(ROOT / acquisition['feed_path'])['GetEdgarFilingListResult'] if f['FilingId'] == acquisition['issuer_filing_id'])
assert any(d['DocumentType'] == 'XBRL_HTML' and d['Url'] == inline_receipt['url'] for d in filing['DocumentList'])
raw_numeric = Counter()
with zipfile.ZipFile(SOURCE / acquisition['file']) as archive:
    instance = next(i for i in archive.namelist() if i.endswith('_htm.xml'))
    raw = archive.read(instance)
    assert b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper()
    dom = minidom.parseString(raw)
    for node in dom.documentElement.childNodes:
        if node.nodeType != node.ELEMENT_NODE or not node.hasAttribute('contextRef'): continue
        name = node.localName
        if 'debt' not in name.lower() and 'interest' not in name.lower(): continue
        text = ''.join(c.data for c in node.childNodes if c.nodeType in [c.TEXT_NODE, c.CDATA_SECTION_NODE]).strip()
        try: value = Decimal(text)
        except InvalidOperation: continue
        raw_numeric[(name, node.getAttribute('contextRef'), value)] += 1
profile = read(SOURCE / acquisition['profile'])
numeric, nonnumeric = [], []
for fact in profile['debt_and_interest_facts']:
    assert fact['context']['entity_identifiers'] == ['0000320193']
    try: value = Decimal(fact['value_exact'])
    except InvalidOperation:
        nonnumeric.append(fact); continue
    key = (fact['concept'].rsplit('}', 1)[-1], fact['context_id'], value)
    assert raw_numeric[key] > 0, key
    numeric.append(fact)
assert len(numeric) == 150 and len(nonnumeric) == 5
assert Counter((f['concept'].rsplit('}', 1)[-1], f['context_id'], Decimal(f['value_exact'])) for f in numeric) == raw_numeric
groups = {}
for fact in numeric:
    name = fact['concept'].rsplit('}', 1)[-1]
    if name != 'DebtInstrumentCarryingAmount' or fact['context']['period'] != {'instant': '2025-09-27'}: continue
    members = {d['axis']: d['member'] for d in fact['context']['dimensions']}
    if members.get('us-gaap:DebtInstrumentAxis'):
        assert fact['unit_measures'] == ['iso4217:USD']
        group = members['us-gaap:DebtInstrumentAxis']
        assert group not in groups
        groups[group] = {'value_usd_exact': fact['value_exact'], 'context_id': fact['context_id'], 'dimensions': fact['context']['dimensions']}
assert set(groups) == {'aapl:A20132023DebtIssuancesMember', 'aapl:A2025DebtIssuanceMember'}
assert int(groups['aapl:A20132023DebtIssuancesMember']['value_usd_exact']) + int(groups['aapl:A2025DebtIssuanceMember']['value_usd_exact']) == 91281000000
assert groups['aapl:A2025DebtIssuanceMember']['value_usd_exact'] == '4500000000'
annual_parser = Tables()
annual_parser.feed((ANNUAL / annual['file']).read_text(encoding='utf-8'))
table = next(rows for rows in annual_parser.tables if any(row and row[0] == 'Fixed-rate 4.000% – 4.750% notes' for row in rows))
prior = next(row for row in table if row and row[0] == 'Fixed-rate 0.000% – 4.850% notes')
current = next(row for row in table if row and row[0] == 'Fixed-rate 4.000% – 4.750% notes')
assert '86,781' in prior and '97,341' in prior and '4,500' in current
assert int(groups['aapl:A20132023DebtIssuancesMember']['value_usd_exact']) == int(prior[4].replace(',', '')) * 1000000
assert int(groups['aapl:A2025DebtIssuanceMember']['value_usd_exact']) == int(current[3].replace(',', '')) * 1000000
out = ROOT / 'artifacts/private' / ('apple-xbrl-debt-audit-' + uuid4().hex[:12])
out.mkdir()
paths = [SOURCE / 'acquisition.json', SOURCE / acquisition['file'], SOURCE / acquisition['profile'],
         SOURCE / 'inline-acquisition.json', SOURCE / inline_receipt['file'],
         ROOT / acquisition['feed_path'], ANNUAL / 'acquisition.json', ANNUAL / annual['file']]
receipt = {'status': 'PASS', 'numeric_raw_dom_parity': len(numeric), 'nonnumeric_facts_retained_not_numeric_tested': len(nonnumeric),
           'annual_html_table_group_amount_checks': 2,
           'format_note': 'Issuer XBRL_HTML is a rendered XBRL report, not original inline XBRL. DOM parity uses the raw XML instance; original annual HTML supplies two group amount checks, not all 150 facts.',
           'instant_2025_debt_instrument_groups': groups,
           'interpretation': 'DebtInstrumentCarryingAmount is displayed in the issuer table on principal basis: group total 91.281bn, versus carrying after costs/hedges 90.678bn. Concept name alone does not determine analytical basis.',
           'missing_evidence': ['Individual series amounts within each issuance group', 'Dated paid/unpaid coupon events', 'Verified payment-place calendar and amendments'],
           'qualification': {'per_series_outstanding': False, 'actual_payments': False, 'debt_service': False},
           'source_population_note': '155 broad debt/interest name matches include debt-security investments, noncontrolling-interest income facts and narrative blocks; this is not 155 borrower liabilities.',
           'inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in paths}, 'method_sha256': sha(Path(__file__))}
(out / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(out)
print('PASS: 150 numeric facts matched independent DOM raw instance; two annual HTML group checks, per-series qualification remains false')
