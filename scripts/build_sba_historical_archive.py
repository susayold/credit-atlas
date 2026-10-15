"""Build a private, hash-verified report of the March SBA historical archive."""
from pathlib import Path
from uuid import uuid4
from credit_atlas.business_archive import report
from credit_atlas.workspace import write_new, sha256, timestamp

root = Path.cwd().resolve()
result = report(root)
out = root / 'artifacts/private' / ('sba-historical-report-' + uuid4().hex[:12])
write_new(out / 'report.json', result)
write_new(out / 'receipt.json', {'status': 'PASS', 'created_at': timestamp(),
    'report_sha256': sha256(out / 'report.json'), 'inputs_sha256': result['evidence_hashes'],
    'method_sha256': sha256(root / 'src/credit_atlas/business_archive.py'),
    'source_records': result['records'], 'added_to_frozen_case': False,
    'full_completion_proven': False})
print(out)
