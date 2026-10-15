"""Verified SEC filing-specific financial evidence and bounded private reports."""
import re
import uuid
from datetime import date
from pathlib import Path

from .sec_financials import ACCESSION, FIELDS, verify_case
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'sec-view-[0-9a-f]{12}\Z')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('sec_views', 'sec_financials', 'sec_sources', 'workspace')}


def project(root, case_id, identifier):
    folder, case = verify_case(root, case_id)
    snapshots = read_json(folder / 'annual-statements.json')
    return {'view_id': identifier, 'case_id': case_id, 'source_id': case['source_id'],
        'entities': case['entities'], 'fact_entries': case['fact_entries'], 'unique_filings': case['unique_filings'],
        'annual_statements': case['annual_statements'], 'quality': read_json(folder / 'quality.json'),
        'field_contract': {name: {'kind': kind, 'candidate_concepts': list(concepts), 'taxonomy': 'us-gaap', 'unit': 'USD'}
                           for name, (kind, concepts) in FIELDS.items()},
        'annual_options': [{key: row[key] for key in ('cik', 'accession', 'filing_date', 'report_date', 'form')}
                           for row in sorted(snapshots, key=lambda row: (row['filing_date'], row['accession']), reverse=True)],
        'source_url': 'https://www.sec.gov/search-filings/edgar-application-programming-interfaces',
        'limitations': ['Current SEC API snapshot; filed-date filter alone is not historical availability qualification.',
            'Only four selected issuers; not a representative default-labelled corporate population.',
            'Whole-entity non-custom API facts; custom/dimensional/segment and debt terms require raw filing work.',
            'Issuer names from companyfacts/submissions may differ; identity is explicit CIK, not fuzzy name join.',
            'USD-only statement calculations; native units remain separate in canonical storage.',
            'Captive finance subsidiaries and consolidated issuer scope affect comparisons across sectors.'],
        'visibility': 'private', 'public_release_approved': False, 'model_qualified': False}, sha256(folder / 'case-complete.json')


def build_sec_view(root, case_id):
    identifier = 'sec-view-' + uuid.uuid4().hex[:12]
    frozen = methods()
    snapshot, digest = project(root, case_id, identifier)
    folder = contained(root, 'artifacts/private/' + identifier); folder.mkdir(parents=True)
    write_new(folder / 'snapshot.json', snapshot)
    confirmed, confirmed_digest = project(root, case_id, identifier)
    if snapshot != confirmed or digest != confirmed_digest or methods() != frozen:
        raise ValueError('SEC source/methods changed while building view')
    receipt = {'view_id': identifier, 'case_id': case_id, 'status': 'VERIFIED_SEC_FINANCIALS_VIEW',
        'completed_at': timestamp(), 'case_receipt_sha256': digest, 'methods': frozen,
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt


class SecViews:
    def __init__(self, root):
        self.root = root.resolve()
        self.methods = methods()

    def view(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid SEC view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_SEC_FINANCIALS_VIEW'
                or receipt['methods'] != self.methods or receipt['methods'] != methods()
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
                or sha256(folder / 'snapshot.json') != receipt['snapshot_sha256']):
            raise ValueError('SEC view bytes/methods changed')
        snapshot = read_json(folder / 'snapshot.json')
        expected, digest = project(self.root, receipt['case_id'], identifier)
        if snapshot != expected or digest != receipt['case_receipt_sha256']:
            raise ValueError('SEC view differs from source projection')
        return snapshot

    def catalog(self):
        result = []
        for path in (self.root / 'artifacts/private').glob('sec-view-*/view-complete.json'):
            try:
                snapshot = self.view(path.parent.name)
                result.append({'view_id': snapshot['view_id'], 'status': 'verified',
                               'completed_at': read_json(path)['completed_at'], 'entities': len(snapshot['entities'])})
            except (OSError, ValueError, KeyError):
                result.append({'view_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(result, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, identifier, query):
        if set(query) - {'view_id', 'cik', 'accession', 'asof'} or query.get('view_id', identifier) != identifier:
            raise ValueError('Invalid SEC report filter')
        snapshot = self.view(identifier)
        cik = query.get('cik', '0000320193')
        entity = next((row for row in snapshot['entities'] if row['cik'] == cik), None)
        if entity is None:
            raise ValueError('Unknown SEC issuer CIK')
        asof = query.get('asof', timestamp()[:10])
        if not isinstance(asof, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', asof):
            raise ValueError('SEC filing-date cutoff must be ISO date')
        date.fromisoformat(asof)
        accession = query.get('accession', '')
        if not isinstance(accession, str) or accession and not ACCESSION.fullmatch(accession):
            raise ValueError('Invalid SEC accession filter')
        options = [row for row in snapshot['annual_options'] if row['cik'] == cik and row['filing_date'] <= asof]
        if accession and not any(row['accession'] == accession for row in options):
            raise ValueError('SEC accession is not available for issuer/cutoff')
        chosen = accession or (options[0]['accession'] if options else '')
        folder = contained(self.root, 'artifacts/private/' + snapshot['case_id'])
        statement = next((row for row in read_json(folder / 'annual-statements.json')
                          if row['cik'] == cik and row['accession'] == chosen), None)
        return {'view_id': identifier, 'case_id': snapshot['case_id'], 'source_id': snapshot['source_id'],
            'filters': {'cik': cik, 'accession': chosen, 'asof': asof}, 'entity': entity, 'annual_options': options,
            'statement': statement, 'status': 'FILING_SPECIFIC_RESEARCH_STATEMENT' if statement else 'NO_SOURCE_STATEMENT_AS_OF',
            'quality': next(row for row in snapshot['quality'] if row['cik'] == cik),
            'limitations': snapshot['limitations'], 'historical_availability_qualified': False,
            'visibility': 'private', 'public_release_approved': False, 'model_qualified': False}
