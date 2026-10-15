"""Acquire issuer-feed XBRL package and inspect debt dimensions without inferring balances."""
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import hashlib
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'data/private/sec-documents/apple-annual-debt-d2fac541f9a3/issuer-feed.json'
feed = json.loads(FEED.read_text())['GetEdgarFilingListResult']
filing = next(f for f in feed if f['StockSymbol'] == '0000320193' and f['FilingTypeMnemonic'] == '10-K' and f['FilingDate'] == '10/31/2025 00:00:00')
url = next(d['Url'] for d in filing['DocumentList'] if d['DocumentType'] == 'XBRL')
out = ROOT / 'data/private/sec-documents' / ('apple-annual-xbrl-' + uuid4().hex[:12])
out.mkdir(parents=True)
partial = out / 'annual.partial'
result = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
    '--connect-timeout', '20', '--max-time', '90', '--max-filesize', '32000000',
    '--output', str(partial), '--write-out', '%{http_code}', url], capture_output=True, timeout=100)
receipt = {'status': 'HTTP_FAILED', 'url': url, 'issuer_filing_id': filing['FilingId'], 'cik': filing['StockSymbol'],
           'filing_date': '2025-10-31', 'http_status': result.stdout.decode(), 'curl_exit': result.returncode,
           'feed_path': str(FEED.relative_to(ROOT)), 'feed_sha256': hashlib.sha256(FEED.read_bytes()).hexdigest(),
           'retrieved_at': datetime.now(timezone.utc).isoformat(), 'visibility': 'private'}
if result.returncode or result.stdout != b'200':
    (out / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    raise RuntimeError('XBRL HTTP failed; receipt retained')
archive = out / 'apple-2025-xbrl.zip'
partial.rename(archive)
local = lambda tag: tag.rsplit('}', 1)[-1]
contexts, facts, units, instances = {}, [], {}, []
with zipfile.ZipFile(archive) as z:
    members = z.infolist()
    assert len(members) <= 200 and sum(i.file_size for i in members) <= 100000000
    assert z.testzip() is None
    for member in members:
        if not member.filename.endswith('.xml'):
            continue
        assert member.file_size <= 32000000
        raw = z.read(member)
        assert b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper()
        tree = ET.fromstring(raw)
        if local(tree.tag) != 'xbrl':
            continue
        instances.append({'member': member.filename, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
        for node in tree:
            name = local(node.tag)
            if name == 'context':
                dimensions = [{'axis': v.attrib.get('dimension'), 'member': (v.text or '').strip()}
                              for v in node.iter() if local(v.tag) == 'explicitMember']
                period = {local(v.tag): (v.text or '').strip() for v in node.iter() if local(v.tag) in ['instant', 'startDate', 'endDate']}
                contexts[node.attrib['id']] = {'period': period, 'dimensions': dimensions,
                    'entity_identifiers': [(v.text or '').strip() for v in node.iter() if local(v.tag) == 'identifier']}
            elif name == 'unit':
                units[node.attrib['id']] = [(v.text or '').strip() for v in node.iter() if local(v.tag) == 'measure']
        for node in tree:
            name = local(node.tag)
            if node.attrib.get('contextRef') and ('debt' in name.lower() or 'interest' in name.lower()):
                facts.append({'concept': node.tag, 'context_id': node.attrib['contextRef'], 'unit_id': node.attrib.get('unitRef'),
                              'decimals': node.attrib.get('decimals'), 'value_exact': (node.text or '').strip(),
                              'nil': node.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}nil')})
assert len(instances) == 1 and contexts and facts
for fact in facts:
    assert fact['context_id'] in contexts
    fact['context'] = contexts[fact['context_id']]
    fact['unit_measures'] = units.get(fact['unit_id'], [])
profile = {'instances': instances, 'debt_and_interest_facts': facts, 'fact_count': len(facts),
           'debt_dimension_members': sorted({d['member'] for f in facts for d in f['context']['dimensions']}),
           'qualification': {'per_series_outstanding': False, 'actual_payments': False, 'debt_service': False},
           'limitations': ['Tagged values retain period, dimension and units; dimension labels alone do not establish instrument identity or outstanding balance.']}
profile_path = out / 'debt-dimensions.json'
profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
receipt.update(status='ACQUIRED_AND_PROFILED', file=archive.name, bytes=archive.stat().st_size,
               sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), profile=profile_path.name,
               profile_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest(),
               method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), instance_count=len(instances), fact_count=len(facts))
(out / 'acquisition.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(out)
print(json.dumps({'debt_interest_facts': len(facts), 'dimension_members': profile['debt_dimension_members']}))
