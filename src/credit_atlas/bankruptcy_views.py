"""Private P3 horizon/ratio explorer backed by verified original-ARFF facts."""
from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path

import pyarrow.parquet as pq

from .bankruptcy import FEATURES, verify_bankruptcy
from .workspace import contained, read_json, sha256, timestamp, write_new


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('bankruptcy_views', 'bankruptcy', 'workspace')}


def build_bankruptcy_view(root, case_id):
    folder, case = verify_bankruptcy(root, case_id)
    identifier = 'bankruptcy-view-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    frozen_methods, digest = methods(), sha256(folder / 'bankruptcy-complete.json')
    snapshot = {'view_id': identifier, 'case_id': case_id, 'rows': case['rows'],
        'horizons': copy.deepcopy(case['horizons']), 'overlap_diagnostics': copy.deepcopy(case['overlap_diagnostics']),
        'precision_audits': copy.deepcopy(case['original_arff_audits']),
        'csv_arff_rounded_numeric_cells': case['csv_arff_rounded_numeric_cells'],
        'feature_quality': pq.read_table(folder / 'feature-quality.parquet').to_pylist(),
        'contract': read_json(folder / 'contract.json'), 'visibility': 'private',
        'public_release_approved': False, 'model_qualified': False,
        'source': {'url': 'https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data',
                   'attribution': 'Tomczak (2016), DOI 10.24432/C5F600; CC BY 4.0'}}
    write_new(output / 'snapshot.json', snapshot)
    verify_bankruptcy(root, case_id)
    if methods() != frozen_methods or sha256(folder / 'bankruptcy-complete.json') != digest:
        raise ValueError('Bankruptcy snapshot lineage changed during build')
    receipt = {'view_id': identifier, 'case_id': case_id, 'status': 'VERIFIED_BANKRUPTCY_RATIOS',
        'case_receipt_sha256': digest, 'snapshot_sha256': sha256(output / 'snapshot.json'),
        'methods': frozen_methods, 'completed_at': timestamp(), 'visibility': 'private', 'public_release_approved': False}
    write_new(output / 'view-complete.json', receipt)
    return receipt


def ratio_report(snapshot, query):
    if set(query) - {'view_id', 'horizon', 'feature'} or query.get('view_id', snapshot['view_id']) != snapshot['view_id']:
        raise ValueError('Unsupported bankruptcy ratio scope')
    horizon, feature = query.get('horizon', '1'), query.get('feature', 'A1')
    if horizon not in {'1', '2', '3', '4', '5'} or feature not in FEATURES:
        raise ValueError('Bankruptcy horizon/feature invalid')
    summary = next(row for row in snapshot['horizons'] if row['forecast_horizon_years'] == int(horizon))
    profiles = [row for row in snapshot['feature_quality'] if row['forecast_horizon_years'] == int(horizon)]
    return {'view_id': snapshot['view_id'], 'case_id': snapshot['case_id'],
        'filters': {'horizon': int(horizon), 'feature': feature}, 'horizon_summary': copy.deepcopy(summary),
        'selected_feature': copy.deepcopy(next(row for row in profiles if row['feature'] == feature)),
        'feature_definition': copy.deepcopy(next(card for card in snapshot['contract']['feature_cards'] if card['feature'] == feature)),
        'feature_quality': copy.deepcopy(profiles),
        'precision_audit': copy.deepcopy(next(row for row in snapshot['precision_audits'] if row['forecast_horizon_years'] == int(horizon))),
        'profile_scope': 'whole_selected_source_subset; feature selector changes highlighted metric, not population',
        'target_rate_scope': 'observed source class fraction, not calibrated loan PD',
        'overlap_diagnostics': copy.deepcopy(snapshot['overlap_diagnostics']),
        'contract': copy.deepcopy(snapshot['contract']), 'source': copy.deepcopy(snapshot['source']),
        'visibility': 'private', 'public_release_approved': False, 'model_qualified': False}


class BankruptcyViews:
    def __init__(self, root):
        self.root = root.resolve()
        self.methods = methods()

    def view(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-view-[0-9a-f]{12}', identifier):
            raise ValueError('Invalid bankruptcy view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_BANKRUPTCY_RATIOS'
                or receipt['methods'] != methods() or receipt['methods'] != self.methods
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False):
            raise ValueError('Bankruptcy view method/qualification changed')
        case_folder, case = verify_bankruptcy(self.root, receipt['case_id'])
        if sha256(case_folder / 'bankruptcy-complete.json') != receipt['case_receipt_sha256']:
            raise ValueError('Bankruptcy view case receipt changed')
        path = folder / 'snapshot.json'
        if sha256(path) != receipt['snapshot_sha256']:
            raise ValueError('Bankruptcy ratio snapshot changed')
        snapshot = read_json(path)
        if (snapshot['view_id'] != identifier or snapshot['case_id'] != case['case_id']
                or snapshot['rows'] != case['rows'] or snapshot['horizons'] != case['horizons']
                or snapshot['csv_arff_rounded_numeric_cells'] != case['csv_arff_rounded_numeric_cells']
                or snapshot['visibility'] != 'private' or snapshot['public_release_approved'] is not False
                or snapshot['model_qualified'] is not False):
            raise ValueError('Bankruptcy snapshot source scope changed')
        return snapshot

    def catalog(self):
        views = []
        for path in (self.root / 'artifacts/private').glob('bankruptcy-view-*/view-complete.json'):
            try:
                snapshot = self.view(path.parent.name)
                views.append({'view_id': snapshot['view_id'], 'status': 'verified', 'rows': snapshot['rows'],
                    'completed_at': read_json(path)['completed_at']})
            except (ValueError, OSError, KeyError):
                views.append({'view_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(views, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, identifier, query):
        return ratio_report(self.view(identifier), query)
