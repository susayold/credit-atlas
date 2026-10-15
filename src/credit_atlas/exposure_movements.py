"""Ordered native-currency observation bridge; no inferred exits/defaults/cash flows."""
import json
import re
import uuid
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

from .exposure_imports import methods as import_methods, normalize, verify_import
from .workspace import contained, read_json, sha256, timestamp, write_new

DIMENSIONS = ('region', 'segment', 'source_state', 'representation')
VALUES = ('opening_amount', 'removed_amount', 'continuing_amount_change', 'transfer_in',
          'transfer_out', 'added_amount', 'closing_amount', 'residual')


def methods():
    return {**import_methods(), 'exposure_movements': sha256(Path(__file__))}


def bridge(opening, closing, before, after):
    for key in ('source_namespace', 'dataset_kind', 'amount_kind', 'date_grain'):
        if before[key] != after[key]: raise ValueError('Incompatible snapshot scope: ' + key)
    if before['as_of'] >= after['as_of']: raise ValueError('Opening snapshot must precede closing snapshot')
    old = {row['position_id']: row for row in opening}; new = {row['position_id']: row for row in closing}
    if len(old) != len(opening) or len(new) != len(closing): raise ValueError('Duplicate snapshot position')
    shared = set(old) & set(new)
    for key in shared:
        if any(old[key][field] != new[key][field] for field in ('pool_key', 'representation')):
            raise ValueError('Matched position pool/representation changed; explicit identity adapter required')
    same_currency = {key for key in shared if old[key]['currency'] == new[key]['currency']}
    migration = shared - same_currency
    removed = set(old) - same_currency; added = set(new) - same_currency
    with localcontext() as context:
        context.prec = 120
        totals = defaultdict(lambda: {field: Decimal(0) for field in VALUES})
        groups = defaultdict(lambda: {field: Decimal(0) for field in VALUES})
        def amount(row): return Decimal(row['reported_amount_major_exact'])
        for rows, field in ((opening, 'opening_amount'), (closing, 'closing_amount')):
            for row in rows:
                totals[row['currency']][field] += amount(row)
                for dim in DIMENSIONS: groups[(row['currency'], dim, row[dim])][field] += amount(row)
        for mapping, keys, field in ((old, removed, 'removed_amount'), (new, added, 'added_amount')):
            for key in sorted(keys):
                row = mapping[key]; totals[row['currency']][field] += amount(row)
                for dim in DIMENSIONS: groups[(row['currency'], dim, row[dim])][field] += amount(row)
        changes = []
        for key in sorted(same_currency):
            a, b = old[key], new[key]; delta = amount(b) - amount(a); currency = a['currency']
            totals[currency]['continuing_amount_change'] += delta
            for dim in DIMENSIONS:
                # First change amount in the old bucket, then transfer the closing amount.
                groups[(currency, dim, a[dim])]['continuing_amount_change'] += delta
                if a[dim] != b[dim]:
                    groups[(currency, dim, a[dim])]['transfer_out'] += amount(b)
                    groups[(currency, dim, b[dim])]['transfer_in'] += amount(b)
                    changes.append((currency, dim, a[dim], b[dim], amount(b)))
        def serialize(values):
            expected = (values['opening_amount'] - values['removed_amount'] + values['continuing_amount_change']
                        + values['transfer_in'] - values['transfer_out'] + values['added_amount'])
            values['residual'] = values['closing_amount'] - expected
            return {field: str(value) for field, value in values.items()}
        transitions = defaultdict(lambda: [0, Decimal(0)])
        for currency, dim, a, b, value in changes:
            transitions[(currency, dim, a, b)][0] += 1; transitions[(currency, dim, a, b)][1] += value
        currencies = []
        for currency, values in sorted(totals.items()):
            row = {'currency': currency, **serialize(values)}
            row.update(opening_records=sum(r['currency'] == currency for r in opening),
                closing_records=sum(r['currency'] == currency for r in closing),
                removed_records=sum(old[k]['currency'] == currency for k in removed),
                added_records=sum(new[k]['currency'] == currency for k in added),
                continuing_records=sum(old[k]['currency'] == currency for k in same_currency),
                currency_migration_out_records=sum(old[k]['currency'] == currency for k in migration),
                currency_migration_in_records=sum(new[k]['currency'] == currency for k in migration))
            currencies.append(row)
        return {'opening_as_of': before['as_of'], 'closing_as_of': after['as_of'], 'date_grain': before['date_grain'],
            'source_namespace': before['source_namespace'], 'amount_kind': before['amount_kind'],
            'dataset_kind': before['dataset_kind'], 'opening_records': len(old), 'closing_records': len(new),
            'identity_counts': {'opening_only': len(set(old)-shared), 'closing_only': len(set(new)-shared),
                'matched_same_currency': len(same_currency), 'matched_currency_migration': len(migration)},
            'currencies': currencies,
            'groups': [{'currency': c, 'dimension': d, 'bucket': b, **serialize(v)} for (c,d,b),v in sorted(groups.items())],
            'transitions': [{'currency': c, 'dimension': d, 'from_bucket': a, 'to_bucket': b, 'records': n,
                'closing_amount_transferred': str(v)} for (c,d,a,b),(n,v) in sorted(transitions.items())],
            'order': ['remove_missing_and_currency_migration_out', 'change_same_currency_amount_in_opening_bucket',
                      'transfer_closing_amount_between_buckets', 'add_new_and_currency_migration_in', 'retain_residual'],
            'contract': {'exit_reason_inferred': False, 'cash_flow_attribution': False, 'fx_conversion': False,
                'borrower_identity_certified': False, 'el_movement': False,
                'identity_basis': 'Exact position IDs within declared source namespace; not borrower linkage',
                'currency_migration': 'Paired removal/addition in native currencies; not an FX gain/loss',
                'continuing_change': 'Observed amount change; no principal/interest/charge-off decomposition'},
            'global_cross_currency_total': None, 'visibility': 'private', 'public_release_approved': False}


def inputs(root, opening_id, closing_id):
    snapshots = []; pins = {}
    for identifier in (opening_id, closing_id):
        folder, receipt, _ = verify_import(root, identifier)
        metadata = read_json(folder / 'metadata.json')
        snapshots.append((normalize(folder / 'source.csv', metadata), metadata))
        pins[str((folder / 'import-complete.json').relative_to(root))] = sha256(folder / 'import-complete.json')
        for name, digest in receipt['outputs_sha256'].items(): pins[str((folder / name).relative_to(root))] = digest
        for row in metadata['source_lineage']: pins[row['path']] = row['sha256']
    return snapshots, pins


def guard(root, pins):
    if any(sha256(contained(root, path)) != digest for path,digest in pins.items()):
        raise ValueError('Movement source changed')


def build(root, opening_id, closing_id):
    frozen_methods = methods(); snapshots, pins = inputs(root, opening_id, closing_id)
    report = bridge(snapshots[0][0], snapshots[1][0], snapshots[0][1], snapshots[1][1])
    identifier = 'exposure-movement-' + uuid.uuid4().hex[:12]
    folder = contained(root, 'artifacts/private/' + identifier)
    write_new(folder / 'report.json', report)
    guard(root, pins)
    if methods() != frozen_methods: raise ValueError('Movement method changed during build')
    receipt = {'movement_id': identifier, 'opening_import_id': opening_id, 'closing_import_id': closing_id,
        'methods': frozen_methods, 'inputs_sha256': pins, 'report_sha256': sha256(folder / 'report.json'),
        'status': 'SOURCE_BOUND_OBSERVATION_BRIDGE', 'completed_at': timestamp(),
        'visibility': 'private', 'public_release_approved': False}
    write_new(folder / 'movement-complete.json', receipt)
    return receipt


def verify(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch('exposure-movement-[0-9a-f]{12}', identifier): raise ValueError('Invalid movement ID')
    folder = contained(root, 'artifacts/private/' + identifier); receipt = read_json(folder / 'movement-complete.json')
    if (receipt['movement_id'] != identifier or receipt['methods'] != methods()
            or receipt['status'] != 'SOURCE_BOUND_OBSERVATION_BRIDGE' or receipt['visibility'] != 'private'
            or receipt['public_release_approved'] is not False or sha256(folder / 'report.json') != receipt['report_sha256']):
        raise ValueError('Movement receipt/payload/method changed')
    snapshots, pins = inputs(root, receipt['opening_import_id'], receipt['closing_import_id'])
    if pins != receipt['inputs_sha256']: raise ValueError('Movement source pins differ')
    expected = bridge(snapshots[0][0], snapshots[1][0], snapshots[0][1], snapshots[1][1])
    report = read_json(folder / 'report.json'); guard(root, pins)
    if json.dumps(report, sort_keys=True) != json.dumps(expected, sort_keys=True): raise ValueError('Movement source rederivation differs')
    return folder, receipt, report
