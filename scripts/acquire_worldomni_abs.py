"""Download one public issuer deal package, without authentication or browser automation."""
import hashlib
import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = 'https://www.worldomni.com/asset_securities.html'
FILES = ['WOART_2025-A_Final_Prospectus.pdf', 'WOART_2025-A_2025.xls', 'WOART_2025-A_2026.xls']


def now():
    return datetime.now(timezone.utc).isoformat()


def acquire():
    if ROOT.drive.upper() != 'D:':
        raise ValueError('D: workspace required')
    folder = ROOT / 'data/private/structured' / ('abs-source-' + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    records = []
    scope = {'deal': 'World Omni Auto Receivables Trust 2025-A', 'issuer_cik': '0002046523',
             'asset_class': 'auto retail installment receivables', 'source_index': INDEX,
             'visibility': 'private', 'public_release_approved': False}
    (folder / 'acquisition-start.json').write_text(json.dumps({**scope, 'started_at': now()}, indent=2))
    try:
        for name, url in [('issuer-index.html', INDEX)] + [(name, 'https://www.worldomni.com/abs/' + name) for name in FILES]:
            if name in FILES and url not in (folder / 'issuer-index.html').read_text():
                raise ValueError('File URL absent from official issuer index')
            destination = folder / name
            partial = folder / (name + '.partial')
            time.sleep(.5)
            result = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
                '--user-agent', 'CreditAtlas/1.0 local financial research', '--connect-timeout', '20',
                '--max-time', '90', '--max-filesize', '16777216', '--output', str(partial),
                '--write-out', '%{http_code}', url], capture_output=True, timeout=95)
            if result.returncode or result.stdout != b'200':
                raise RuntimeError(f'Official HTTP failed: curl={result.returncode}, HTTP={result.stdout[:3]!r}')
            payload = partial.read_bytes()
            if not 0 < len(payload) <= 16777216:
                raise ValueError('Invalid file size')
            if name.endswith('.pdf') and not payload.startswith(b'%PDF-'):
                raise ValueError('Expected PDF signature')
            if name.endswith('.xls') and not payload.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):
                raise ValueError('Expected legacy Excel compound-file signature')
            partial.rename(destination)
            records.append({'file': name, 'url': url, 'http_status': 200, 'bytes': len(payload),
                            'sha256': hashlib.sha256(payload).hexdigest(), 'retrieved_at': now()})
            print(f'{name}: {len(payload):,} bytes', flush=True)
        receipt = {**scope, 'source_id': folder.name, 'status': 'ABS_ISSUER_SOURCE_COMPLETE',
                   'completed_at': now(), 'files': records,
                   'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   'limitations': ['Published deal-level reports, not loan-level ABS-EE XML',
                                   'Spreadsheet formula caches are publisher values, not independently recalculated',
                                   'Current web retrieval is not historical availability certification',
                                   'Deal waterfall and collateral semantics require separate adaptation and audit']}
        (folder / 'acquisition-complete.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print(json.dumps({'source_id': folder.name, 'files': len(records), 'bytes': sum(r['bytes'] for r in records)}))
        return receipt
    except Exception as error:
        (folder / 'acquisition-failed.json').write_text(json.dumps({'failed_at': now(),
            'error_type': type(error).__name__, 'files_completed': records}, indent=2))
        raise


if __name__ == '__main__':
    acquire()
