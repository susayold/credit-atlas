"""Exhaustive validation-cohort explanations using an unchanged finite reference."""
import hashlib
import math
import re
import uuid
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from . import retail_explanations as base
from .workspace import contained, read_json, sha256, timestamp, write_new

ID = re.compile(r'retail-cohort-explanations-[0-9a-f]{12}\Z')
TOKEN = re.compile(r'client-[0-9a-f]{24}\Z')
OUTPUTS = {'assumptions.json', 'report.json', 'private-client-explanations.parquet'}
BATCH = 32


def methods():
    return base.methods() | {'retail_cohort_explanations': sha256(Path(__file__))}


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {'schema_version', 'explanations_id', 'freeze_id', 'visibility', 'public_release_approved'} or type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise ValueError('Exact cohort-explanation plan required')
    if not isinstance(plan['explanations_id'], str) or not base.ID.fullmatch(plan['explanations_id']) or not isinstance(plan['freeze_id'], str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}', plan['freeze_id']):
        raise ValueError('Bound explanation/frozen-model IDs required')
    if plan['visibility'] != 'private' or plan['public_release_approved'] is not False:
        raise ValueError('Private cohort explanation scope required')
    return dict(plan)


def source(root, plan):
    folder, receipt, report = base.verify(root, plan['explanations_id'])
    if report['freeze_id'] != plan['freeze_id']:
        raise ValueError('Cohort explanation model mismatch')
    train, validation, scores, names, predict, pins, lineage = base.source(root, report['assumptions'])
    if pins != receipt['inputs_sha256']:
        raise ValueError('Parent explanation source changed')
    pins = pins | {str((folder / name).relative_to(root)): digest for name, digest in receipt['outputs_sha256'].items()}
    pins[str((folder / 'explanations-complete.json').relative_to(root))] = sha256(folder / 'explanations-complete.json')
    private = read_json(folder / 'private-reference-and-coalitions.json')
    by_id = {r['source_client_id']: r for r in train}
    reference = np.asarray([by_id[i]['features'] for i in private['background_source_ids']], dtype=float)
    if reference.shape != (32, len(names)):
        raise ValueError('Original finite training reference required')
    return validation, scores, reference, base.grouped_columns(names), predict, pins, report, private


def explain_batch(matrix, reference, columns, predict):
    """Batch rows independently; every row retains the same16x32 coalition game."""
    matrix = np.asarray(matrix, dtype=float)
    if not 1 <= len(matrix) <= BATCH or reference.shape[0] != 32 or matrix.shape[1:] != reference.shape[1:] or not np.isfinite(matrix).all() or not np.isfinite(reference).all():
        raise ValueError('Bounded finite explanation matrices required')
    games = np.broadcast_to(reference, (len(matrix), 16, 32, reference.shape[1])).copy()
    for player, indices in enumerate(columns.values()):
        for mask in range(16):
            if mask & (1 << player):
                # Explicit row/group assignment preserves one-hot and within-group histories.
                for i, row in enumerate(matrix):
                    games[i, mask][:, indices] = row[indices]
    p = np.asarray(predict(games.reshape(-1, reference.shape[1])), dtype=float)
    if p.shape != (len(matrix) * 512,) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Finite bounded coalition probabilities required')
    values = p.reshape(len(matrix), 16, 32).mean(axis=2)
    return [{'predicted_probability': float(v[15]), 'reference_probability': float(v[0]),
             **dict(zip(columns, base.shapley(v.tolist()), strict=True))} for v in values]


def calculate(validation, scores, reference, columns, predict, plan, parent, original):
    if len(validation) != len(scores) or not validation or len(validation) > 50000:
        raise ValueError('Complete bounded validation cohort required')
    if [(r['source_client_id'], r['target']) for r in validation] != [(r['source_client_id'], r['target']) for r in scores] or any(r['partition'] != 'validation' for r in validation):
        raise ValueError('Exact validation identities/targets required')
    identifiers = [r['source_client_id'] for r in validation]
    if any(type(i) is not int for i in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValueError('Unique validation identities required')
    matrix = np.asarray([r['features'] for r in validation], dtype=float)
    probabilities = np.asarray(predict(matrix), dtype=float)
    if probabilities.shape != (len(scores),) or not np.isfinite(probabilities).all() or not np.allclose(probabilities, [r['probability'] for r in scores], rtol=0, atol=1e-12):
        raise ValueError('Frozen whole-cohort probability parity failed')
    order = sorted(range(len(scores)), key=lambda i: (probabilities[i], identifiers[i]))
    ranks = {index: rank for rank, index in enumerate(order, 1)}
    rows = []
    for start in range(0, len(matrix), BATCH):
        local = explain_batch(matrix[start:start+BATCH], reference, columns, predict)
        for offset, explanation in enumerate(local):
            index = start + offset
            residual = explanation['reference_probability'] + math.fsum(explanation[group] for group in columns) - float(probabilities[index])
            if abs(explanation['predicted_probability'] - probabilities[index]) > 1e-12 or abs(residual) > 1e-12:
                raise ValueError('Full-cohort explanation reconstruction failed')
            token = 'client-' + hashlib.sha256(f"{plan['explanations_id']}:{identifiers[index]}".encode('ascii')).hexdigest()[:24]
            rows.append({'source_client_id': identifiers[index], 'client_token': token, 'score_rank': ranks[index],
                         **explanation, 'reconstruction_residual': residual})
    if len({r['client_token'] for r in rows}) != len(rows):
        raise ValueError('Cohort token collision')
    # Exhaustive registry must reproduce every one of the original12 examples.
    by_id = {r['source_client_id']: r for r in rows}
    for local, original_row in zip(parent['local_explanations'], original['cases'], strict=True):
        row = by_id[original_row['source_client_id']]
        if row['score_rank'] != local['selection_score_rank'] or abs(row['predicted_probability'] - local['predicted_probability']) > 1e-12 or abs(row['reference_probability'] - local['reference_probability']) > 1e-12 or any(abs(row[c['group']] - c['probability_contribution']) > 1e-12 for c in local['contributions']):
            raise ValueError('Original local explanation parity failed')
    distribution = []
    for group in columns:
        values = [r[group] for r in rows]
        distribution.append({'group': group, 'records': len(rows), 'mean_absolute_probability_contribution': math.fsum(abs(v) for v in values)/len(rows),
                             'mean_probability_contribution': math.fsum(values)/len(rows), 'minimum': min(values), 'maximum': max(values),
                             'positive_records': sum(v > 0 for v in values), 'negative_records': sum(v < 0 for v in values), 'zero_records': sum(v == 0 for v in values)})
    report = {'assumptions': plan, 'freeze_id': plan['freeze_id'], 'explanations_id': plan['explanations_id'],
              'records': len(rows), 'events': parent['events'], 'target': parent['target'], 'partition': 'validation',
              'selected_model': parent['selected_model'], 'selected_variant': parent['selected_variant'],
              'reference_records': 32, 'feature_groups': parent['feature_groups'], 'global_group_contributions': distribution,
              'maximum_absolute_reconstruction_residual': max(abs(r['reconstruction_residual']) for r in rows),
              'original_example_parity_records': len(original['cases']), 'qualification': dict(base.FLAGS),
              'definitions': parent['definitions'] | {'selection': 'Every saved validation client, no probability/label subset.',
                    'tokens': 'Study-scoped pseudonymous tokens; not anonymous identities or original client IDs.',
                    'global_local_distribution': 'Whole-cohort mean absolute grouped Shapley magnitude; differs from permutation performance reliance.'},
              'limitations': parent['limitations']}
    return report, rows


def build(root, plan):
    root = root.resolve(); plan = validate(plan)
    if root.drive.upper() != 'D:': raise ValueError('Private D: workspace required')
    validation, scores, reference, columns, predict, pins, parent, original = source(root, plan)
    method = methods(); report, rows = calculate(validation, scores, reference, columns, predict, plan, parent, original)
    folder = contained(root, 'artifacts/private/retail-cohort-explanations-' + uuid.uuid4().hex[:12]); folder.mkdir(parents=True)
    write_new(folder/'assumptions.json', plan); write_new(folder/'report.json', report)
    pq.write_table(pa.Table.from_pylist(rows), folder/'private-client-explanations.parquet', compression='zstd')
    base.guard(root, pins)
    if method != methods(): raise ValueError('Cohort explanation methods changed')
    write_new(folder/'cohort-explanations-complete.json', {'schema_version':1, 'status':'RETAIL_COMPLETE_VALIDATION_EXPLANATIONS',
              'cohort_id':folder.name, 'completed_at':timestamp(), 'methods':method, 'inputs_sha256':pins,
              'outputs_sha256':{name:sha256(folder/name) for name in OUTPUTS},
              'visibility':'private', 'public_release_approved':False, **base.FLAGS})
    return {'cohort_id':folder.name, 'records':len(rows)}


def verify(root, identifier):
    if not isinstance(identifier,str) or not ID.fullmatch(identifier): raise ValueError('Valid cohort explanation ID required')
    folder = contained(root,'artifacts/private/'+identifier); receipt = read_json(folder/'cohort-explanations-complete.json')
    if type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1 or receipt.get('status') != 'RETAIL_COMPLETE_VALIDATION_EXPLANATIONS' or receipt.get('cohort_id') != identifier or receipt.get('methods') != methods() or receipt.get('visibility') != 'private' or receipt.get('public_release_approved') is not False or any(receipt.get(k) is not v for k,v in base.FLAGS.items()):
        raise ValueError('Cohort explanation contract changed')
    if set(receipt['outputs_sha256']) != OUTPUTS: raise ValueError('Complete cohort explanation payload required')
    base.guard(root, receipt['inputs_sha256'] | {str((folder/n).relative_to(root)):h for n,h in receipt['outputs_sha256'].items()})
    plan = validate(read_json(folder/'assumptions.json'))
    validation, scores, reference, columns, predict, pins, parent, original = source(root,plan)
    if pins != receipt['inputs_sha256']: raise ValueError('Cohort explanation source changed')
    report, rows = calculate(validation,scores,reference,columns,predict,plan,parent,original)
    if report != read_json(folder/'report.json') or rows != pq.read_table(folder/'private-client-explanations.parquet').to_pylist():
        raise ValueError('Whole cohort explanations do not replay')
    return folder,receipt,report,rows
