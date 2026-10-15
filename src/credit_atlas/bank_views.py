"""Verified P4 bank observatory snapshots and scoped private reports."""
from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

from .bank_panel import verify_bank_panel
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'bank-view-[0-9a-f]{12}\Z')
METHODS = ('bank_views', 'bank_panel', 'workspace')


def method_hashes():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in METHODS}


def json_rows(path):
    rows = pq.read_table(path).to_pylist()
    for row in rows:
        for key, value in row.items():
            if hasattr(value, 'isoformat'):
                row[key] = value.isoformat()
            elif value is not None and key.endswith('usd_thousands'):
                row[key] = str(value)  # preserve exact sums outside browser number precision
    return rows


def build_bank_view(root, panel_id):
    case = verify_bank_panel(root, panel_id)
    panel = contained(root, 'artifacts/private/' + panel_id)
    identifier = 'bank-view-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'artifacts/private/' + identifier)
    folder.mkdir(parents=True)
    contract = read_json(panel / 'field-contract.json')
    snapshot = {'view_id': identifier, 'panel_id': panel_id,
        'acquisition_id': case['acquisition_id'], 'visibility': 'private',
        'public_release_approved': False, 'model_qualified': False,
        'records': case['records'], 'unique_certificates': case['unique_certificates'],
        'quarters': copy.deepcopy(case['quarters']),
        'peers': json_rows(panel / 'peer-quarter.parquet'),
        'matched_changes': json_rows(panel / 'matched-quarter-changes.parquet'),
        'contract': contract, 'limitations': case['limitations'],
        'sources': [{'title': 'FDIC BankFind API', 'url': 'https://api.fdic.gov/banks/docs'},
            {'title': 'Financial definitions', 'url': 'https://api.fdic.gov/banks/docs/risview_properties.yaml'}]}
    if sum(row['records'] for row in snapshot['peers']) != snapshot['records']:
        raise ValueError('Peer record denominators changed')
    write_new(folder / 'snapshot.json', snapshot)
    verify_bank_panel(root, panel_id)
    receipt = {'view_id': identifier, 'status': 'VERIFIED_BANK_AGGREGATES',
        'completed_at': timestamp(), 'panel_id': panel_id,
        'panel_receipt_sha256': sha256(panel / 'panel-complete.json'),
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'methods': method_hashes(),
        'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt


def bank_report(snapshot, query):
    if set(query) - {'view_id', 'quarter', 'peer'}:
        raise ValueError('Unsupported bank aggregate filter')
    if query.get('view_id', snapshot['view_id']) != snapshot['view_id']:
        raise ValueError('Bank snapshot scope mismatch')
    quarter = query.get('quarter', snapshot['quarters'][-1]['report_date'])
    peer = query.get('peer', 'all')
    if quarter not in {row['report_date'] for row in snapshot['quarters']}:
        raise ValueError('Unknown reporting quarter')
    if peer != 'all' and peer not in {row['asset_peer'] for row in snapshot['peers']}:
        raise ValueError('Unknown asset peer')
    selected = [row for row in snapshot['peers'] if row['report_date'] == quarter
                and (peer == 'all' or row['asset_peer'] == peer)]
    return {'view_id': snapshot['view_id'], 'panel_id': snapshot['panel_id'],
        'visibility': 'private', 'public_release_approved': False, 'model_qualified': False,
        'filters': {'quarter': quarter, 'peer': peer},
        'selected_record_count': sum(row['records'] for row in selected),
        'rows': copy.deepcopy(selected),
        'quarter_quality_scope': 'whole_selected_quarter_not_filtered_by_peer',
        'quarter_quality': copy.deepcopy(next(row for row in snapshot['quarters'] if row['report_date'] == quarter)),
        'matched_change_scope': 'whole_quarter_adjacent_certificates_not_filtered_by_peer',
        'matched_change': copy.deepcopy(next((row for row in snapshot['matched_changes'] if row['report_date'] == quarter), None)),
        'contract': copy.deepcopy(snapshot['contract']),
        'limitations': copy.deepcopy(snapshot['limitations']), 'sources': copy.deepcopy(snapshot['sources'])}


class BankViews:
    def __init__(self, root):
        self.root = root.resolve()
        self.methods = method_hashes()

    def view(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid bank view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_BANK_AGGREGATES'
                or receipt['methods'] != method_hashes() or receipt['methods'] != self.methods
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False):
            raise ValueError('Bank view implementation/receipt changed')
        case = verify_bank_panel(self.root, receipt['panel_id'])
        panel = contained(self.root, 'artifacts/private/' + case['case_id'])
        if sha256(panel / 'panel-complete.json') != receipt['panel_receipt_sha256']:
            raise ValueError('Bank panel receipt changed')
        path = folder / 'snapshot.json'
        if sha256(path) != receipt['snapshot_sha256']:
            raise ValueError('Bank aggregate snapshot changed')
        snapshot = read_json(path)
        if (snapshot['view_id'] != identifier or snapshot['panel_id'] != case['case_id']
                or snapshot['records'] != case['records'] or snapshot['visibility'] != 'private'
                or snapshot['public_release_approved'] is not False or snapshot['model_qualified'] is not False):
            raise ValueError('Bank snapshot scope changed')
        return snapshot

    def catalog(self):
        results = []
        for path in sorted((self.root / 'artifacts/private').glob('bank-view-*/view-complete.json'), reverse=True):
            identifier = path.parent.name
            try:
                snapshot = self.view(identifier)
                receipt = read_json(path)
                results.append({'view_id': identifier, 'status': 'verified',
                    'completed_at': receipt['completed_at'], 'panel_id': snapshot['panel_id'],
                    'records': snapshot['records'], 'quarters': len(snapshot['quarters'])})
            except (ValueError, KeyError, OSError):
                results.append({'view_id': identifier, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(results, key=lambda row: row['completed_at'], reverse=True)}

    def timeline(self, identifier, cert):
        if not isinstance(cert, str) or not re.fullmatch(r'[1-9][0-9]{0,8}', cert):
            raise ValueError('Positive FDIC certificate required')
        snapshot = self.view(identifier)
        folder = contained(self.root, 'artifacts/private/' + snapshot['panel_id'])
        with duckdb.connect() as con:
            con.read_parquet(str(folder / 'bank-quarter.parquet')).create_view('banks')
            rows = con.execute('''SELECT cert, report_date::VARCHAR AS report_date, name,
                assets_usd_thousands::VARCHAR AS assets_usd_thousands,
                deposits_usd_thousands::VARCHAR AS deposits_usd_thousands,
                equity_usd_thousands::VARCHAR AS equity_usd_thousands,
                roa_annualized_percent, equity_assets_percent, deposits_assets_percent,
                consolidating_parent_cert, asset_peer FROM banks
                WHERE cert=? ORDER BY report_date LIMIT 42''', [int(cert)]).to_arrow_table().to_pylist()
        if not rows:
            raise KeyError('Institution not present in selected panel')
        self.view(identifier)  # verify immutable evidence after query as well
        return {'view_id': identifier, 'panel_id': snapshot['panel_id'], 'cert': int(cert),
                'rows': rows, 'visibility': 'private', 'public_release_approved': False,
                'scope': 'one_certificate_all_observed_quarters_not_filtered_by_dashboard_peer',
                'limitations': snapshot['limitations']}
