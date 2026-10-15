"""Bounded, sequential SEC public API acquisition; immutable source receipts."""
import re
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from .workspace import contained, read_json, sha256, timestamp, write_new

ISSUERS = {'0000320193': 'AAPL', '0000789019': 'MSFT', '0000037996': 'F', '0001467858': 'GM'}
USER_AGENT = 'CreditAtlas/1.0 local financial research'
PATTERN = re.compile(r'sec-source-[0-9a-f]{12}\Z')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('sec_sources', 'workspace')}


def download(url, destination):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'data.sec.gov' or parsed.port is not None
            or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise ValueError('Official credential-free SEC data API required')
    if not re.fullmatch(r'/(?:submissions/CIK\d{10}(?:-submissions-\d{3})?|api/xbrl/companyfacts/CIK\d{10})\.json', parsed.path):
        raise ValueError('Unsupported SEC API path')
    if destination.exists():
        raise ValueError('Immutable SEC download exists')
    time.sleep(.35)  # Sequential requests, locally below SEC's published ten requests/second.
    partial = destination.with_suffix(destination.suffix + '.partial')
    response = subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
        '--user-agent', USER_AGENT, '--connect-timeout', '20', '--max-time', '120',
        '--max-filesize', str(64 * 1024**2), '--output', str(partial), '--write-out', '%{http_code}', url],
        capture_output=True, timeout=125)
    if response.returncode or response.stdout != b'200':
        raise RuntimeError(f'SEC HTTP failed: curl={response.returncode}, HTTP={response.stdout[:3]!r}')
    if not partial.is_file() or not 0 < partial.stat().st_size <= 64 * 1024**2:
        raise ValueError('Invalid SEC response size')
    payload = read_json(partial)
    if not isinstance(payload, dict) or not payload:
        raise ValueError('Invalid SEC JSON object')
    partial.rename(destination)
    return {'url': url, 'file': destination.name, 'sha256': sha256(destination),
            'bytes': destination.stat().st_size, 'retrieved_at': timestamp()}


def filing_columns(payload):
    required = ('accessionNumber', 'filingDate', 'reportDate', 'form', 'primaryDocument')
    if any(not isinstance(payload.get(key), list) for key in required):
        raise ValueError('Missing SEC filing arrays')
    count = len(payload['accessionNumber'])
    if any(not isinstance(values, list) or len(values) != count for values in payload.values()):
        raise ValueError('SEC filing arrays do not align')
    return count


def acquire_sec_source(root):
    root = root.resolve()
    if root.drive.upper() != 'D:':
        raise ValueError('D: workspace required')
    identifier = 'sec-source-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'data/private/sec/' + identifier)
    folder.mkdir(parents=True)
    frozen = methods()
    write_new(folder / 'acquisition-start.json', {'source_id': identifier, 'started_at': timestamp(),
        'issuers': ISSUERS, 'methods': frozen, 'user_agent': USER_AGENT, 'requests': 'sequential; .35s minimum interval'})
    files, entities = [], []
    try:
        for cik, ticker in ISSUERS.items():
            name = 'CIK' + cik + '.json'
            files.append({**download('https://data.sec.gov/submissions/' + name, folder / ('submissions-' + name)),
                          'cik': cik, 'kind': 'submissions'})
            submissions = read_json(folder / ('submissions-' + name))
            if str(submissions['cik']).zfill(10) != cik or ticker not in submissions['tickers']:
                raise ValueError('SEC CIK/ticker identity mismatch')
            filing_columns(submissions['filings']['recent'])
            history = submissions['filings']['files']
            if not isinstance(history, list) or len(history) > 20:
                raise ValueError('SEC history exceeds bounded scope')
            names = set()
            for item in history:
                filename = item['name']
                if not re.fullmatch('CIK' + cik + r'-submissions-\d{3}\.json', filename) or filename in names:
                    raise ValueError('Invalid/duplicate SEC history filename')
                names.add(filename)
                files.append({**download('https://data.sec.gov/submissions/' + filename, folder / filename),
                              'cik': cik, 'kind': 'history', 'source_manifest': item})
                if filing_columns(read_json(folder / filename)) != item['filingCount']:
                    raise ValueError('SEC history manifest count differs')
            files.append({**download('https://data.sec.gov/api/xbrl/companyfacts/' + name, folder / ('companyfacts-' + name)),
                          'cik': cik, 'kind': 'companyfacts'})
            facts = read_json(folder / ('companyfacts-' + name))
            if str(facts['cik']).zfill(10) != cik or not isinstance(facts['facts'], dict) or not facts['facts']:
                raise ValueError('SEC company-facts identity/content mismatch')
            entities.append({'cik': cik, 'ticker': ticker, 'submission_name': submissions['name'],
                'facts_name': facts['entityName'], 'sic': submissions['sic'],
                'sic_description': submissions['sicDescription'], 'history_files': len(history)})
            print(ticker + ': filings/history and all company facts saved', flush=True)
        if methods() != frozen:
            raise ValueError('SEC acquisition methods changed')
        receipt = {'source_id': identifier, 'status': 'SEC_SOURCE_COMPLETE', 'completed_at': timestamp(),
            'methods': frozen, 'issuers': ISSUERS, 'entities': entities, 'files': files,
            'visibility': 'private', 'public_release_approved': False}
        write_new(folder / 'acquisition-complete.json', receipt)
        return receipt
    except Exception as error:
        write_new(folder / 'acquisition-failed.json', {'failed_at': timestamp(), 'exception_type': type(error).__name__,
                  'files_completed': files})
        raise


def verify_source(root, identifier):
    if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
        raise ValueError('Invalid SEC source identifier')
    folder = contained(root, 'data/private/sec/' + identifier)
    receipt = read_json(folder / 'acquisition-complete.json')
    if (receipt['source_id'] != identifier or receipt['status'] != 'SEC_SOURCE_COMPLETE'
            or receipt['issuers'] != ISSUERS or receipt['methods'] != methods()
            or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False):
        raise ValueError('SEC source/method contract changed')
    names = set()
    for item in receipt['files']:
        path = contained(folder, item['file'])
        if path.parent != folder or path.name in names or sha256(path) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('SEC raw source bytes changed')
        names.add(path.name)
    return folder, receipt
