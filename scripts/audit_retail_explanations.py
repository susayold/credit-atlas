"""Independent tree traversal, permutation metrics and all-order Shapley audit."""
import argparse
import hashlib
import itertools
import json
import math
import uuid
from pathlib import Path
import duckdb
import numpy as np
from scipy.special import expit
from sklearn.metrics import brier_score_loss
from credit_atlas.retail_explanations import verify, guard
from credit_atlas.workspace import app_root, contained, read_json, sha256, timestamp, write_new


def independent_predict(model, matrix, calibration=None):
    if model['kind'] == 'constant':
        probabilities = np.full(len(matrix), model['prevalence'])
    else:
        if model['kind'] == 'logistic':
            raw = np.sum(matrix * np.asarray(model['coefficients']), axis=1) + model['intercept']
        elif model['kind'] == 'histogram_boosting':
            raw = np.full(len(matrix), model['initial_raw_score'])
            for tree in model['trees']:
                values = np.empty(len(matrix))
                stack = [(0, np.arange(len(matrix)))]
                while stack:
                    index, rows = stack.pop()
                    node = tree[index]
                    if node['is_leaf']:
                        values[rows] = node['value']
                    elif len(rows):
                        left = matrix[rows, node['feature']] <= node['threshold']
                        stack.extend([(node['left'], rows[left]), (node['right'], rows[~left])])
                raw += values
        else:
            raise ValueError('Unsupported persisted model')
        probabilities = expit(raw)
    if calibration:
        p = np.clip(probabilities, calibration['logit_clip'], 1 - calibration['logit_clip'])
        probabilities = expit(calibration['slope'] * (np.log(p) - np.log1p(-p)) + calibration['intercept'])
    return probabilities


def independent_auc(y, p):
    groups = {}
    for target, probability in zip(y, p, strict=True):
        counts = groups.setdefault(float(probability), [0, 0]); counts[int(target)] += 1
    below = 0; twice_concordance = 0
    for _, (non_events, events) in sorted(groups.items()):
        twice_concordance += events * (2 * below + non_events)
        below += non_events
    return twice_concordance / (2 * int(sum(y)) * (len(y) - int(sum(y))))


def run(root, identifier):
    audit_method = sha256(Path(__file__))
    ledger = root / 'artifacts/private/retail-holdout-access.sqlite'
    before = sha256(ledger)
    assert before == read_json(root / 'artifacts/private/retail-explanations-holdout-guard-before-20261010.json')['sha256']
    folder, receipt, report = verify(root, identifier)
    private = read_json(folder / 'private-reference-and-coalitions.json')
    bundle = root / 'artifacts/private' / report['freeze_id']
    freeze = read_json(bundle / 'freeze-complete.json'); encoder = read_json(bundle / 'encoder.json'); model = read_json(bundle / 'model.json')
    path = root / 'artifacts/private' / freeze['feature_id'] / 'development.parquet'
    with duckdb.connect(config={'threads': 2, 'memory_limit': '256MB'}) as db:
        rows = db.execute("SELECT * FROM read_parquet(?) WHERE partition IN ('train','validation') ORDER BY partition,source_client_id", [str(path)]).to_arrow_table().to_pylist()
    train = [r for r in rows if r['partition'] == 'train']; validation = [r for r in rows if r['partition'] == 'validation']
    matrix = np.asarray([r['features'] for r in validation]); y = np.asarray([r['target'] for r in validation])
    calibration = read_json(bundle / 'calibration.json') if report['selected_variant'] == 'calibrated' else None
    predict = lambda x: independent_predict(model, x, calibration)
    baseline = predict(matrix); baseline_brier = brier_score_loss(y, baseline); baseline_auc = independent_auc(y, baseline)
    checks = 0
    def equal(actual, expected):
        nonlocal checks
        assert math.isfinite(float(actual)) and math.isclose(float(actual), float(expected), abs_tol=1e-12, rel_tol=0), (actual, expected)
        checks += 1
    equal(report['records'], len(y)); equal(report['events'], y.sum())
    equal(report['baseline_brier'], baseline_brier); equal(report['baseline_auc'], baseline_auc)
    groups = report['feature_groups']
    # Independent contiguous encoder layout, not the engine's group-column parser.
    columns = {'credit_limit': [0], 'bill_history': list(range(1, 7)), 'payment_history': list(range(7, 13)),
               'repayment_status': list(range(13, len(encoder['feature_names'])))}
    assert set(groups) == set(columns)
    for row in report['global_permutation']:
        results = []
        for repeat in row['repeats']:
            indices = np.random.Generator(np.random.PCG64(repeat['seed'])).permutation(len(y))
            x = matrix.copy(); fields = columns[row['group']]; x[:, fields] = matrix[indices][:, fields]
            p = predict(x); brier = brier_score_loss(y, p); auc = independent_auc(y, p)
            equal(repeat['permuted_brier'], brier); equal(repeat['brier_increase'], brier - baseline_brier)
            equal(repeat['permuted_auc'], auc); equal(repeat['auc_decrease'], baseline_auc - auc)
            results.append((brier - baseline_brier, baseline_auc - auc))
        equal(row['mean_brier_increase'], np.mean([r[0] for r in results])); equal(row['mean_auc_decrease'], np.mean([r[1] for r in results]))
    expected_ids = [r['source_client_id'] for r in sorted(train, key=lambda r: hashlib.sha256(
        f"{report['assumptions']['background_seed']}:{r['source_client_id']}".encode('ascii')).hexdigest())[:32]]
    assert expected_ids == private['background_source_ids']; checks += 1
    by_id = {r['source_client_id']: r for r in train}; background = np.asarray([by_id[i]['features'] for i in expected_ids])
    ranks = sorted(range(len(y)), key=lambda i: (baseline[i], validation[i]['source_client_id']))
    expected_cases = [validation[ranks[round(j * (len(y) - 1) / 11)]]['source_client_id'] for j in range(12)]
    assert expected_cases == [r['source_client_id'] for r in private['cases']]; checks += 1
    by_id = {r['source_client_id']: (i, r) for i, r in enumerate(validation)}
    ordered_groups = [r['group'] for r in report['local_explanations'][0]['contributions']]
    for local, original in zip(report['local_explanations'], private['cases'], strict=True):
        index, r = by_id[original['source_client_id']]
        assert local['case'] == original['case']; checks += 1
        values = []
        for mask in range(16):
            x = background.copy()
            for player, group in enumerate(ordered_groups):
                if mask & (1 << player): x[:, columns[group]] = np.asarray(r['features'])[columns[group]]
            value = float(np.mean(predict(x))); values.append(value)
            equal(original['coalition_probabilities'][mask], value)
        # Average marginal increment over every ordering, independent of subset weights.
        increments = [[] for _ in range(4)]
        for order in itertools.permutations(range(4)):
            mask = 0
            for player in order:
                next_mask = mask | (1 << player)
                increments[player].append(values[next_mask] - values[mask]); mask = next_mask
        contributions = [math.fsum(v) / 24 for v in increments]
        for saved, value in zip(local['contributions'], contributions, strict=True): equal(saved['probability_contribution'], value)
        equal(local['predicted_probability'], baseline[index]); equal(local['reference_probability'], values[0])
        equal(local['selection_score_rank'], ranks.index(index) + 1)
        equal(values[0] + math.fsum(contributions), baseline[index]); equal(local['reconstruction_residual'], 0)
    assert not any(report['qualification'].values()) and 'source_client_id' not in json.dumps(report); checks += 1
    guard(root, receipt['inputs_sha256']); assert sha256(ledger) == before and sha256(Path(__file__)) == audit_method
    output = root / 'artifacts/private' / ('retail-explanations-audit-' + uuid.uuid4().hex[:12] + '.json')
    write_new(output, {'status': 'PASS', 'checks': checks, 'explanations_id': identifier, 'completed_at': timestamp(),
                      'method_sha256': audit_method, 'study_receipt_sha256': sha256(folder / 'explanations-complete.json'),
                      'holdout_ledger_unchanged': True, 'visibility': 'private', 'public_release_approved': False})
    return {'status': 'PASS', 'checks': checks, 'receipt': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--explanations-id', required=True); args = parser.parse_args()
    print(json.dumps(run(app_root(), args.explanations_id), indent=2))
