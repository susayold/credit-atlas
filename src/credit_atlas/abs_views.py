"""Private source-backed ABS period views; no inferred legal-state qualification."""
import json
import re
import uuid
from pathlib import Path

from .abs_contract import SLOTS, terms
from .abs_waterfall import verify_replay
from .workspace import contained, read_json, sha256, timestamp, write_new

PATTERN = re.compile(r'abs-view-[0-9a-f]{12}\Z')
LIMITATIONS = [
    'Conditional pre-acceleration replay, not certification of legal state or complete obligations.',
    'Reviewer fee due/YTD and prior unpaid interest are disclosed assumptions; paid-zero does not prove due-zero.',
    'Priority shortfalls overlap and must not be summed as credit loss or treated as automatic payment defaults.',
    'Reserve replenishment is an internal transfer, not an additional external distribution.',
    'Reported collections and adjusted pool are inputs, not loan-level collateral or future cashflow projections.',
    'Benchmark fixing/fallback, executed agreements, amendments and event history remain unverified.',
    'No ABS valuation, collateral-loss model, credit rating or production decision qualification.',
]


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('abs_views', 'abs_waterfall', 'abs_contract', 'abs_servicer', 'workspace')}


def same(left, right):
    # JSON type-sensitive equality: qualification false cannot be replaced by 0.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def project(root, waterfall_id, identifier):
    replay = verify_replay(root, waterfall_id)
    if (replay['status'] != 'CONDITIONAL_REPORTED_REPLAY_RECONCILED'
            or type(replay['failed_checks']) is not int or replay['failed_checks'] != 0
            or any(check['pass'] is not True for check in replay['checks'])
            or replay['public_release_approved'] is not False
            or any(value is not False for value in replay['qualification'].values())):
        raise ValueError('ABS source replay is not qualified for conditional display')
    timeline = []
    for period in replay['periods']:
        inputs, result = period['inputs'], period['result']
        timeline.append({'collection_end': period['collection_end'], 'payment_date': inputs['payment_date'],
            'available_funds': inputs['available_funds'], 'ending_pool': inputs['ending_pool'],
            'oc_target': inputs['oc_target'], 'reserve_ending': result['reserve_ending'],
            'reserve_draw_total': result['reserve_draw_total'],
            'principal_paid': result['principal_paid'], 'ending_balances': result['ending_balances']})
    snapshot = {'view_id': identifier, 'waterfall_id': waterfall_id, 'case_id': replay['case_id'],
        'terms_id': replay['terms_id'], 'deal': 'World Omni Auto Receivables Trust 2025-A',
        'currency': 'USD', 'terms': terms(), 'period_options': timeline,
        'source_check_count': len(replay['checks']), 'failed_source_checks': replay['failed_checks'],
        'conditional_assumptions': replay['conditional_assumptions'], 'limitations': LIMITATIONS.copy(),
        'qualification': replay['qualification'], 'visibility': 'private', 'public_release_approved': False}
    digest = sha256(contained(root, 'artifacts/private/' + waterfall_id + '/waterfall-complete.json'))
    return snapshot, digest, replay


def build_abs_view(root, waterfall_id):
    identifier = 'abs-view-' + uuid.uuid4().hex[:12]
    frozen = methods()
    snapshot, digest, _ = project(root, waterfall_id, identifier)
    folder = contained(root, 'artifacts/private/' + identifier)
    folder.mkdir(parents=True)
    write_new(folder / 'snapshot.json', snapshot)
    confirmed, confirmed_digest, _ = project(root, waterfall_id, identifier)
    if not same(snapshot, confirmed) or digest != confirmed_digest or frozen != methods():
        raise ValueError('ABS source/methods changed while building view')
    receipt = {'view_id': identifier, 'waterfall_id': waterfall_id, 'status': 'VERIFIED_CONDITIONAL_ABS_VIEW',
        'completed_at': timestamp(), 'waterfall_receipt_sha256': digest, 'methods': frozen,
        'snapshot_sha256': sha256(folder / 'snapshot.json'), 'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'view-complete.json', receipt)
    return receipt


class AbsViews:
    def __init__(self, root):
        self.root = root.resolve()
        self.methods = methods()

    def evidence(self, identifier):
        if not isinstance(identifier, str) or not PATTERN.fullmatch(identifier):
            raise ValueError('Invalid ABS view identifier')
        folder = contained(self.root, 'artifacts/private/' + identifier)
        receipt = read_json(folder / 'view-complete.json')
        if (receipt['view_id'] != identifier or receipt['status'] != 'VERIFIED_CONDITIONAL_ABS_VIEW'
                or receipt['methods'] != self.methods or receipt['methods'] != methods()
                or receipt['visibility'] != 'private' or receipt['public_release_approved'] is not False
                or sha256(folder / 'snapshot.json') != receipt['snapshot_sha256']):
            raise ValueError('ABS view bytes/methods changed')
        snapshot = read_json(folder / 'snapshot.json')
        expected, digest, replay = project(self.root, receipt['waterfall_id'], identifier)
        if not same(snapshot, expected) or digest != receipt['waterfall_receipt_sha256']:
            raise ValueError('ABS view differs from source projection')
        return snapshot, replay

    def view(self, identifier):
        return self.evidence(identifier)[0]

    def catalog(self):
        result = []
        for path in (self.root / 'artifacts/private').glob('abs-view-*/view-complete.json'):
            try:
                snapshot = self.view(path.parent.name)
                result.append({'view_id': snapshot['view_id'], 'status': 'verified',
                    'completed_at': read_json(path)['completed_at'], 'deal': snapshot['deal'],
                    'periods': len(snapshot['period_options'])})
            except (OSError, ValueError, KeyError, TypeError):
                result.append({'view_id': path.parent.name, 'status': 'unavailable', 'completed_at': ''})
        return {'views': sorted(result, key=lambda row: row['completed_at'], reverse=True)}

    def report(self, identifier, query):
        if (not isinstance(query, dict) or set(query) - {'view_id', 'period'}
                or query.get('view_id', identifier) != identifier):
            raise ValueError('Invalid ABS report filter; only view_id and source collection period supported')
        snapshot, replay = self.evidence(identifier)
        period = query.get('period', replay['periods'][-1]['collection_end'])
        selected = next((row for row in replay['periods'] if row['collection_end'] == period), None)
        if selected is None:
            raise ValueError('ABS collection period not present in source; no extrapolation')
        inputs, result = selected['inputs'], selected['result']
        tranche_rows = [{'slot': slot, 'beginning_balance': inputs['beginning_balances'][slot],
            'interest_due': inputs['interest_due'][slot], 'interest_paid': result['interest_paid'][slot],
            'interest_unpaid': result['interest_unpaid'][slot], 'principal_paid': result['principal_paid'][slot],
            'ending_balance': result['ending_balances'][slot]} for slot in SLOTS]
        return {'view_id': identifier, 'waterfall_id': replay['waterfall_id'], 'case_id': replay['case_id'],
            'terms_id': replay['terms_id'], 'deal': snapshot['deal'], 'currency': 'USD',
            'filters': {'period': period}, 'period': selected, 'tranches': tranche_rows,
            'source_checks': [row for row in replay['checks'] if row['collection_end'] == period],
            'status': 'CONDITIONAL_REPORTED_REPLAY', 'qualification': snapshot['qualification'],
            'conditional_assumptions': snapshot['conditional_assumptions'], 'limitations': snapshot['limitations'],
            'visibility': 'private', 'public_release_approved': False}
