"""Acquire issuer-hosted annual filing; retain tables and scope caveats privately."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/c636d8a7-8025-47d2-9b13-bcf5465343b3.html'
DISCOVERY = 'https://investor.apple.com/sec-filings/'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.tables = []
        self.text = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'table':
            self.stack.append({'rows': [], 'row': None, 'cell': None})
        if self.stack:
            t = self.stack[-1]
            if tag == 'tr':
                t['row'] = []
            if tag in ('td', 'th'):
                t['cell'] = []
    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
            if self.stack and self.stack[-1]['cell'] is not None:
                self.stack[-1]['cell'].append(data)
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if self.stack:
            t = self.stack[-1]
            if tag in ('td', 'th') and t['cell'] is not None:
                if t['row'] is not None:
                    t['row'].append(' '.join(' '.join(t['cell']).split()))
                t['cell'] = None
            if tag == 'tr' and t['row'] is not None:
                t['rows'].append(t['row'])
                t['row'] = None
            if tag == 'table':
                self.tables.append(self.stack.pop()['rows'])

def main():
    out = ROOT / 'data/private/sec-documents' / ('apple-annual-debt-' + uuid4().hex[:12])
    out.mkdir(parents=True)
    partial = out / 'annual.partial'
    command = ['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
               '--user-agent', 'CreditAtlas/1.0 local financial research', '--connect-timeout', '20',
               '--max-time', '90', '--max-filesize', '20000000', '--output', str(partial),
               '--write-out', '%{http_code}', URL]
    result = subprocess.run(command, capture_output=True, timeout=100)
    receipt = {'url': URL, 'discovered_on': DISCOVERY, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
               'http_status': result.stdout.decode(), 'curl_exit': result.returncode, 'visibility': 'private'}
    if result.returncode or result.stdout != b'200':
        receipt['status'] = 'HTTP_FAILED'
        (out / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        raise RuntimeError('Annual source HTTP failed; receipt retained')
    target = out / 'apple-2025-10k.html'
    partial.rename(target)
    parser = Tables()
    parser.feed(target.read_text(encoding='utf-8'))
    text = ' '.join(' '.join(parser.text).split())
    assert all(anchor in text for anchor in ['Apple Inc.', 'September 27, 2025', 'Note 9', '91,281', '90,678'])
    matched = [rows for rows in parser.tables if any('Total term debt principal' in ' '.join(row) for row in rows)]
    assert len(matched) == 2, len(matched)
    (out / 'debt-tables.json').write_text(json.dumps({'tables': matched}, ensure_ascii=False, indent=2), encoding='utf-8')
    receipt.update(status='ACQUIRED', file=target.name, bytes=target.stat().st_size,
                   sha256=sha(target), tables_file='debt-tables.json', tables_sha256=sha(out / 'debt-tables.json'),
                   cik='0000320193', accession='0000320193-25-000079', report_end='2025-09-27',
                   filing_date='2025-10-31', series_balances_qualified=False, actual_payments_qualified=False,
                   issuer_feed_linkage_verified=False)
    (out / 'acquisition.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(out)
    print('Acquired issuer-hosted annual filing; two debt tables retained. Feed identity and numerical audit remain required.')

if __name__ == '__main__':
    main()
