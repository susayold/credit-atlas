"""Private P5 market-context snapshots, bounded observations and bond scenarios."""
from __future__ import annotations

import re
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .bond_scenario import bond_scenario
from .market_data import SERIES, verify_market
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'market-view-[0-9a-f]{12}\Z')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('market_views', 'market_data', 'bond_scenario', 'workspace')}


def json_ready(rows):
    for row in rows:
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = str(value)
            elif isinstance(value, date):
                row[key] = value.isoformat()
    return rows


def build_market_view(root, case_id):
    case_folder, case = verify_market(root, case_id)
    identifier = 'market-view-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'artifacts/private/' + identifier)
    folder.mkdir(parents=True)
    rows = pq.read_table(case_folder / 'aligned-daily-context.parquet').to_pylist()
    common = [row for row in rows if row['treasury_three_tenors_known']]
    snapshot = {'view_id': identifier, 'case_id': case_id, 'visibility': 'private',
        'public_release_approved': False, 'market_calibrated': False,
        'native_records': case['native_records'], 'profiles': case['profiles'],
        'quarantined_records': case['quarantined_records'],
        'historical_treasury_semantics_qualified': case['historical_treasury_semantics_qualified'],
        'coverage': case['coverage'], 'monthly_records': case['monthly_records'],
        'latest_aligned_date': json_ready([rows[-1]])[0] if rows else None,
        'latest_three_tenor_date': json_ready([common[-1]])[0] if common else None,
        'contract': read_json(case_folder / 'contract.json'),
        'independent_reconciliations': case['independent_reconciliations']}
    write_new(folder / 'snapshot.json', snapshot)
    verify_market(root, case_id)
    receipt = {'view_id': identifier, 'status': 'VERIFIED_MARKET_CONTEXT',
        'completed_at': timestamp(), 'case_id': case_id,
        'case_receipt_sha256': sha256(case_folder / 'market-complete.json'),
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'methods': methods(),
        'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt


def selected_dates(query):
    if not all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', query.get(key, '')) for key in ('from', 'to')):
        raise ValueError('From/to dates must be YYYY-MM-DD')
    first, last = date.fromisoformat(query['from']), date.fromisoformat(query['to'])
    if first > last or (last - first).days > 3666:
        raise ValueError('Ordered date range up to ten years required')
    return first, last


class MarketViews:
    def __init__(self, root):
        self.root, self.methods = root.resolve(), methods()

    def view(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid market view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_MARKET_CONTEXT'
                or receipt['methods'] != methods() or receipt['methods'] != self.methods
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False):
            raise ValueError('Market view receipt/implementation changed')
        case_folder, case = verify_market(self.root, receipt['case_id'])
        if sha256(case_folder / 'market-complete.json') != receipt['case_receipt_sha256']:
            raise ValueError('Market case receipt changed')
        if sha256(folder / 'snapshot.json') != receipt['snapshot_sha256']:
            raise ValueError('Market snapshot changed')
        snapshot = read_json(folder / 'snapshot.json')
        if (snapshot['view_id'] != identifier or snapshot['case_id'] != case['case_id']
                or snapshot['native_records'] != case['native_records'] or snapshot['visibility'] != 'private'
                or snapshot['public_release_approved'] is not False or snapshot['market_calibrated'] is not False):
            raise ValueError('Market snapshot scope changed')
        return snapshot

    def catalog(self):
        result = []
        for path in (self.root / 'artifacts/private').glob('market-view-*/view-complete.json'):
            identifier = path.parent.name
            try:
                snapshot = self.view(identifier)
                result.append({'view_id': identifier, 'status': 'verified', 'case_id': snapshot['case_id'],
                    'completed_at': read_json(path)['completed_at'], 'native_records': snapshot['native_records']})
            except (ValueError, KeyError, OSError):
                result.append({'view_id': identifier, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(result, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, identifier, query):
        if set(query) != {'view_id', 'series', 'from', 'to'} or query['view_id'] != identifier:
            raise ValueError('Exactly snapshot, series and date range required')
        if query['series'] not in SERIES:
            raise ValueError('Unknown market series')
        first, last = selected_dates(query)
        snapshot = self.view(identifier)
        folder = contained(self.root, 'artifacts/private/' + snapshot['case_id'])
        with duckdb.connect() as con:
            con.read_parquet(str(folder / 'native-observations.parquet')).create_view('native')
            rows = con.execute('''SELECT observation_date, source_value_percent, value_percent, source_value,
                documented_discontinuation_conflict FROM native
                WHERE series=? AND observation_date BETWEEN ? AND ? ORDER BY observation_date''',
                [query['series'], first, last]).to_arrow_table().to_pylist()
        self.view(identifier)
        return {'view_id': identifier, 'case_id': snapshot['case_id'],
            'visibility': 'private', 'public_release_approved': False,
            'filters': {key: query[key] for key in ('series', 'from', 'to')},
            'native_rows': len(rows), 'known_rows': sum(row['value_percent'] is not None for row in rows),
            'source_known_rows': sum(row['source_value_percent'] is not None for row in rows),
            'quarantined_rows': sum(row['documented_discontinuation_conflict'] for row in rows),
            'rows': json_ready(rows), 'units': 'percent',
            'profile_scope': 'whole_native_series_not_filtered_by_date_range',
            'profile': next(row for row in snapshot['profiles'] if row['series'] == query['series']),
            'contract': snapshot['contract']}

    def daily(self, identifier, query):
        if set(query) != {'view_id', 'from', 'to'} or query['view_id'] != identifier:
            raise ValueError('Daily context accepts only snapshot/from/to')
        first, last = selected_dates(query)
        snapshot = self.view(identifier)
        folder = contained(self.root, 'artifacts/private/' + snapshot['case_id'])
        with duckdb.connect() as con:
            con.read_parquet(str(folder / 'aligned-daily-context.parquet')).create_view('daily')
            rows = con.execute('SELECT * FROM daily WHERE observation_date BETWEEN ? AND ? ORDER BY observation_date',
                               [first, last]).to_arrow_table().to_pylist()
        self.view(identifier)
        return {'view_id': identifier, 'filters': {'from': query['from'], 'to': query['to']},
                'rows': json_ready(rows), 'alignment': 'same_native_date_no_fill',
                'visibility': 'private', 'public_release_approved': False}

    def bond(self, identifier, query):
        if set(query) != {'view_id', 'face_usd', 'coupon_percent', 'yield_percent', 'years', 'frequency'} or query['view_id'] != identifier:
            raise ValueError('Bond scenario accepts exactly five terms and context snapshot')
        snapshot = self.view(identifier)
        result = bond_scenario({key: value for key, value in query.items() if key != 'view_id'})
        result.update(view_id=identifier, market_context_case=snapshot['case_id'],
                      visibility='private', public_release_approved=False,
                      source_market_series_used_for_pricing=False)
        return result
