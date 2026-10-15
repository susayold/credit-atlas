"""Verified HMDA aggregate filters and exports, with frozen-source cache guards."""
import copy
import json
import re
import threading
import uuid
from decimal import Decimal
from pathlib import Path

import duckdb

from .hmda_applications import ACTIONS, methods as case_methods, verify_case
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'hmda-view-[0-9a-f]{12}\Z')
FILTERS = {'lei': 'lei', 'county': 'county_code', 'loan_type': 'loan_type', 'dti': 'dti_public_category'}
DIMENSIONS = {'county': 'county_code', 'lender': 'lei', 'loan_type': 'loan_type', 'dti': 'dti_public_category',
              'dwelling': 'derived_dwelling_category', 'race': 'derived_race',
              'ethnicity': 'derived_ethnicity', 'sex': 'derived_sex'}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('hmda_views', 'hmda_applications', 'hmda_sources', 'workspace')}


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def summarize(rows):
    counts = {code: 0 for code in ACTIONS}; amounts = {code: Decimal(0) for code in ACTIONS}
    for code, count, amount in rows:
        if code not in counts: raise ValueError('Unknown HMDA action in verified aggregate')
        counts[code] += count; amounts[code] += amount
    denominator = sum(counts[code] for code in ('1', '2', '3'))
    return {'records': sum(counts.values()), 'decision_denominator': denominator,
        'denied_numerator': counts['3'], 'descriptive_denial_rate': str(Decimal(counts['3']) / denominator) if denominator else None,
        'public_amount_sum_usd': str(sum(amounts.values())),
        'actions': [{'code': code, 'name': ACTIONS[code], 'records': counts[code], 'public_amount_sum_usd': str(amounts[code])}
                    for code in ACTIONS]}


class HmdaViews:
    def __init__(self, root):
        self.root = root.resolve(); self.methods = methods(); self.cache = {}; self.lock = threading.RLock()

    def case(self, case_id):
        if not isinstance(case_id, str) or not re.fullmatch(r'hmda-case-[0-9a-f]{12}', case_id):
            raise ValueError('Invalid HMDA case identity')
        if methods() != self.methods: raise ValueError('HMDA serving methods changed; restart required')
        with self.lock:
            if case_id not in self.cache:
                folder, case = verify_case(self.root, case_id)
                source = contained(self.root, 'data/private/hmda/' + case['source_id'])
                src = read_json(source / 'source-complete.json')
                files = {folder / 'case-complete.json': sha256(folder / 'case-complete.json'),
                    source / 'source-complete.json': case['source_receipt_sha256']}
                files.update({folder / name: digest for name, digest in case['outputs_sha256'].items()})
                files.update({contained(source, row['file']): row['sha256'] for row in src['files']})
                self.cache[case_id] = {'folder': folder, 'case': copy.deepcopy(case), 'source': copy.deepcopy(src), 'files': files}
            cached = self.cache[case_id]
            if cached['case']['methods'] != case_methods() or any(sha256(path) != digest for path, digest in cached['files'].items()):
                raise ValueError('Frozen HMDA source/canonical evidence changed')
            return cached

    def project(self, case_id, identifier):
        cached = self.case(case_id); case = cached['case']; evidence = read_json(cached['folder'] / 'evidence.json')
        connection = duckdb.connect()
        try:
            connection.from_parquet(str(cached['folder'] / 'applications.parquet')).create_view('applications')
            options = {key: [row[0] for row in connection.execute('SELECT DISTINCT ' + field + ' FROM applications ORDER BY 1').fetchall()]
                       for key, field in FILTERS.items()}
        finally: connection.close()
        if any(value is not False for value in evidence['qualification'].values()):
            raise ValueError('Unexpected HMDA qualification')
        snapshot = {'view_id': identifier, 'case_id': case_id, 'source_id': case['source_id'],
            'records': case['records'], 'source_fields': 99, 'years': evidence['years'], 'options': options,
            'dimensions': DIMENSIONS, 'quality': evidence['quality'], 'field_contract': evidence['field_contract'],
            'denominator_contract': evidence['denominator_contract'], 'qualification': evidence['qualification'],
            'scope': cached['source']['filters'], 'limitations': cached['source']['limitations'],
            'source_url': 'https://ffiec.cfpb.gov/documentation/api/data-browser/',
            'visibility': 'private', 'public_release_approved': False}
        self.case(case_id)
        return snapshot, sha256(cached['folder'] / 'case-complete.json')

    def view(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier): raise ValueError('Invalid HMDA view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier); receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_HMDA_AGGREGATE_VIEW'
                or receipt['methods'] != self.methods or receipt['methods'] != methods()
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
                or sha256(folder / 'snapshot.json') != receipt['snapshot_sha256']):
            raise ValueError('HMDA view bytes/methods changed')
        snapshot = read_json(folder / 'snapshot.json'); expected, digest = self.project(receipt['case_id'], identifier)
        if not same(snapshot, expected) or digest != receipt['case_receipt_sha256']:
            raise ValueError('HMDA view differs from original source projection')
        return snapshot

    def catalog(self):
        rows = []
        for path in (self.root / 'artifacts/private').glob('hmda-view-*/view-complete.json'):
            try:
                snapshot = self.view(path.parent.name)
                rows.append({'view_id': snapshot['view_id'], 'status': 'verified', 'records': snapshot['records'],
                             'completed_at': read_json(path)['completed_at']})
            except (OSError, ValueError, KeyError, TypeError):
                rows.append({'view_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(rows, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, identifier, query):
        if (not isinstance(query, dict) or set(query) - {'view_id', 'year', 'dimension', *FILTERS}
                or query.get('view_id', identifier) != identifier): raise ValueError('Invalid HMDA aggregate filter')
        snapshot = self.view(identifier)
        filters = {key: query.get(key, 'all') for key in FILTERS}
        year = query.get('year', str(max(row['year'] for row in snapshot['years'])))
        dimension = query.get('dimension', 'county')
        if not isinstance(year, str) or year not in [str(row['year']) for row in snapshot['years']] or dimension not in DIMENSIONS:
            raise ValueError('HMDA year/dimension absent from verified source')
        for key, value in filters.items():
            if not isinstance(value, str) or value != 'all' and value not in snapshot['options'][key]:
                raise ValueError('HMDA filter value absent from verified source')
        clauses = [field + '=?' for key, field in FILTERS.items() if filters[key] != 'all']
        parameters = [filters[key] for key in FILTERS if filters[key] != 'all']
        where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
        cached = self.case(snapshot['case_id']); connection = duckdb.connect()
        try:
            connection.from_parquet(str(cached['folder'] / 'applications.parquet')).create_view('applications')
            selected = ' FROM applications WHERE activity_year=?' + ((' AND ' + ' AND '.join(clauses)) if clauses else '')
            rows = connection.execute('SELECT action_code,count(*),sum(CAST(public_loan_amount_usd_exact AS DECIMAL(38,2)))' + selected + ' GROUP BY 1', [int(year), *parameters]).fetchall()
            summary = summarize(rows)
            buckets = connection.execute('SELECT ' + DIMENSIONS[dimension] + ',action_code,count(*),sum(CAST(public_loan_amount_usd_exact AS DECIMAL(38,2)))' + selected + ' GROUP BY 1,2 ORDER BY 1,2', [int(year), *parameters]).fetchall()
            grouped = {}
            for bucket, code, count, amount in buckets: grouped.setdefault(bucket, []).append((code, count, amount))
            breakdown = [{'bucket': bucket, **summarize(values)} for bucket, values in grouped.items()]
            series = connection.execute('SELECT activity_year,action_code,count(*),sum(CAST(public_loan_amount_usd_exact AS DECIMAL(38,2))) FROM applications' + where + ' GROUP BY 1,2 ORDER BY 1,2', parameters).fetchall()
            timeline = [{'year': row['year'], **summarize([(code, count, amount) for y, code, count, amount in series if y == row['year']])}
                        for row in snapshot['years']]
            quality = []
            for field in ('income_status', 'property_value_status', 'interest_rate_status'):
                statuses = connection.execute('SELECT ' + field + ',count(*)' + selected + ' GROUP BY 1 ORDER BY 1', [int(year), *parameters]).fetchall()
                quality.extend({'field': field, 'status': status, 'records': count} for status, count in statuses)
        finally: connection.close()
        self.case(snapshot['case_id'])
        return {'view_id': identifier, 'case_id': snapshot['case_id'], 'source_id': snapshot['source_id'],
            'filters': {'year': year, **filters, 'dimension': dimension},
            'status': 'PUBLIC_APPLICATION_OUTCOME_AGGREGATES' if summary['records'] else 'NO_SOURCE_RECORDS_FOR_FILTERS',
            'summary': summary, 'breakdown': breakdown, 'timeline': timeline, 'filtered_quality': quality,
            'source_quality_whole_case': snapshot['quality'], 'scope': snapshot['scope'],
            'denominator_contract': snapshot['denominator_contract'], 'field_contract': snapshot['field_contract'],
            'limitations': snapshot['limitations'], 'qualification': snapshot['qualification'],
            'visibility': 'private', 'public_release_approved': False}


def build_hmda_view(root, case_id):
    identifier = 'hmda-view-' + uuid.uuid4().hex[:12]; service = HmdaViews(root); frozen = methods()
    snapshot, digest = service.project(case_id, identifier)
    folder = contained(root, 'artifacts/private/' + identifier); folder.mkdir(parents=True)
    write_new(folder / 'snapshot.json', snapshot)
    expected, confirmed = service.project(case_id, identifier)
    if not same(snapshot, expected) or digest != confirmed or methods() != frozen:
        raise ValueError('HMDA source/methods changed during view build')
    receipt = {'view_id': identifier, 'case_id': case_id, 'status': 'VERIFIED_HMDA_AGGREGATE_VIEW',
        'completed_at': timestamp(), 'case_receipt_sha256': digest, 'methods': frozen,
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt
