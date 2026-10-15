"""Verified country-series and same-year cross-sections; no score semantics."""
import re
import uuid
from pathlib import Path

import pyarrow.parquet as pq

from .country_observatory import END, START, verify_case
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'country-view-[0-9a-f]{12}\Z')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('country_views', 'country_observatory', 'workspace')}


def project(root, case_id, identifier):
    folder, case = verify_case(root, case_id)
    contract = read_json(folder / 'contract.json')
    observations = pq.read_table(folder / 'observations.parquet', columns=['country_code', 'is_aggregate', 'value']).to_pylist()
    codes = {row['country_code'] for row in observations}
    countries = read_json(folder / 'countries.json')
    return {'view_id': identifier, 'case_id': case_id, 'source_id': case['source_id'], 'rows': case['rows'],
        'known_rows': sum(row['value'] is not None for row in observations),
        'catalog_entries': len(countries), 'catalog_entities_not_returned': sorted(set(countries) - codes),
        'entities': [{'code': code, 'name': countries[code]['name'], 'is_aggregate': countries[code]['region']['id'] == 'NA',
                      'region_current': countries[code]['region']['value'], 'income_current': countries[code]['incomeLevel']['value']}
                     for code in sorted(codes)],
        'coverage': read_json(folder / 'coverage.json'), 'indicators': read_json(folder / 'indicators.json'),
        'contract': contract, 'visibility': 'private', 'public_release_approved': False, 'model_qualified': False}, sha256(folder / 'case-complete.json')


def build_country_view(root, case_id):
    identifier = 'country-view-' + uuid.uuid4().hex[:12]
    frozen = methods()
    snapshot, digest = project(root, case_id, identifier)
    folder = contained(root, 'artifacts/private/' + identifier)
    folder.mkdir(parents=True)
    write_new(folder / 'snapshot.json', snapshot)
    confirmed, new_digest = project(root, case_id, identifier)
    if snapshot != confirmed or digest != new_digest or frozen != methods():
        raise ValueError('Country source/methods changed while building view')
    receipt = {'view_id': identifier, 'case_id': case_id, 'case_receipt_sha256': digest,
        'status': 'VERIFIED_COUNTRY_VIEW', 'completed_at': timestamp(), 'methods': frozen,
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt


class CountryViews:
    def __init__(self, root):
        self.root = root.resolve()
        self.methods = methods()

    def view(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid country-view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_COUNTRY_VIEW'
                or receipt['methods'] != self.methods or receipt['methods'] != methods()
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
                or sha256(folder / 'snapshot.json') != receipt['snapshot_sha256']):
            raise ValueError('Country view methods/snapshot changed')
        snapshot = read_json(folder / 'snapshot.json')
        expected, digest = project(self.root, receipt['case_id'], identifier)
        if snapshot != expected or digest != receipt['case_receipt_sha256']:
            raise ValueError('Country view differs from source projection')
        return snapshot

    def catalog(self):
        result = []
        for path in (self.root / 'artifacts/private').glob('country-view-*/view-complete.json'):
            try:
                snapshot = self.view(path.parent.name)
                result.append({'view_id': snapshot['view_id'], 'status': 'verified', 'rows': snapshot['rows'],
                               'completed_at': read_json(path)['completed_at']})
            except (OSError, ValueError, KeyError):
                result.append({'view_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(result, key=lambda item: item['completed_at'], reverse=True)}

    def report(self, identifier, query):
        if set(query) - {'view_id', 'country', 'indicator', 'year', 'from', 'to', 'universe'}:
            raise ValueError('Unknown country-observatory filter')
        if 'view_id' in query and query['view_id'] != identifier:
            raise ValueError('Country view filter mismatch')
        snapshot = self.view(identifier)
        universe = query.get('universe', 'economies')
        if universe not in {'economies', 'aggregates'}:
            raise ValueError('Invalid country universe')
        country = query.get('country', 'VNM')
        selected = next((row for row in snapshot['entities'] if row['code'] == country), None)
        if selected is None or selected['is_aggregate'] != (universe == 'aggregates'):
            raise ValueError('Country must belong to selected source universe')
        indicator = query.get('indicator', 'FB.AST.NPER.ZS')
        if indicator not in snapshot['indicators']:
            raise ValueError('Unknown country indicator')
        years = {}
        for key, default in (('year', '2024'), ('from', '2010'), ('to', '2025')):
            text = query.get(key, default)
            if not isinstance(text, str) or not re.fullmatch(r'\d{4}', text) or not START <= int(text) <= END:
                raise ValueError('Country reference year outside contract')
            years[key] = int(text)
        if years['from'] > years['to']:
            raise ValueError('Inverted country timeline')
        folder = contained(self.root, 'artifacts/private/' + snapshot['case_id'])
        rows = pq.read_table(folder / 'observations.parquet').to_pylist()
        timeline = sorted([row for row in rows if row['country_code'] == country and row['indicator_id'] == indicator
                           and years['from'] <= row['year'] <= years['to']], key=lambda row: row['year'])
        peers = sorted([row for row in rows if row['indicator_id'] == indicator and row['year'] == years['year']
                        and row['is_aggregate'] == selected['is_aggregate']], key=lambda row: row['country_name'])
        selected_year = next((row for row in peers if row['country_code'] == country), None)
        latest = []
        for code, definition in snapshot['indicators'].items():
            available = [row for row in rows if row['country_code'] == country and row['indicator_id'] == code
                         and row['year'] <= years['year'] and row['value'] is not None]
            last = max(available, key=lambda row: row['year'], default=None)
            latest.append({'indicator_id': code, 'name': definition['name'],
                'latest_known_year_at_or_before_selected_year': None if last is None else last['year'],
                'latest_known_value': None if last is None else last['value'],
                'unit': snapshot['contract']['indicators'][code]['unit']})
        return {'view_id': identifier, 'case_id': snapshot['case_id'], 'source_id': snapshot['source_id'],
            'filters': {'country': country, 'indicator': indicator, 'universe': universe, **years},
            'country': selected, 'definition': snapshot['indicators'][indicator],
            'declared_unit': snapshot['contract']['indicators'][indicator]['unit'],
            'timeline': timeline, 'timeline_rows': len(timeline), 'timeline_known': sum(row['value'] is not None for row in timeline),
            'selected_year_observation': selected_year, 'same_year_peers': peers,
            'same_year_returned_entities': len(peers), 'same_year_known_entities': sum(row['value'] is not None for row in peers),
            'latest_known_profile': latest, 'no_carryforward': True,
            'contract': snapshot['contract'], 'visibility': 'private', 'public_release_approved': False, 'model_qualified': False}
