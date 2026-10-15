"""Frozen validation model inspection with grouped permutation and exact Shapley."""
import hashlib
import copy
import itertools
import math
import re
import uuid
from pathlib import Path
import duckdb
import numpy as np
import scipy
import sklearn
from scipy.special import expit
from sklearn.metrics import roc_auc_score
from .retail_assessment import predict_json, logit
from .retail_policy import source as policy_source
from .retail_policy_views import lineage_pins
from .workspace import contained, read_json, sha256, timestamp, write_new

ID = re.compile(r'retail-explanations-[0-9a-f]{12}\Z')
GROUPS = {
    'credit_limit': ['LIMIT_BAL'],
    'repayment_status': ['PAY_0', 'PAY_2', 'PAY_3', 'PAY_4', 'PAY_5', 'PAY_6'],
    'bill_history': ['BILL_AMT' + str(i) for i in range(1, 7)],
    'payment_history': ['PAY_AMT' + str(i) for i in range(1, 7)],
}
CONFIG = {'schema_version': 1, 'background_records': 32, 'local_cases': 12,
          'background_seed': 20261010, 'permutation_seeds': [20261010, 20261011, 20261012],
          'visibility': 'private', 'public_release_approved': False}
FLAGS = {'model_training_performed': False, 'model_selection_performed': False,
         'final_test_scored': False, 'final_test_predictors_materialized': False,
         'causal_effect_identified': False, 'adverse_action_qualified': False,
         'production_qualified': False}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
            ('retail_explanations', 'retail_assessment', 'retail_policy', 'retail_policy_views')}


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != set(CONFIG) | {'freeze_id'}:
        raise ValueError('Exact explanation schema required')
    # Exact types prevent True from passing a numeric schema/seed contract.
    if any(type(plan[k]) is not type(v) or plan[k] != v for k, v in CONFIG.items()):
        raise ValueError('Fixed reviewed explanation configuration required')
    if any(type(v) is not int for v in plan['permutation_seeds']):
        raise ValueError('Integer permutation seeds required')
    if not isinstance(plan['freeze_id'], str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}', plan['freeze_id']):
        raise ValueError('Valid frozen model required')
    return copy.deepcopy(plan)


def grouped_columns(names):
    if len(set(names)) != len(names) or {name.split('=')[0] for name in names} != set(itertools.chain.from_iterable(GROUPS.values())):
        raise ValueError('Exact allowed predictor fields required')
    columns = {group: [i for i, name in enumerate(names)
                      if name.split('=')[0] in fields] for group, fields in GROUPS.items()}
    if any(not indices for indices in columns.values()) or sorted(itertools.chain.from_iterable(columns.values())) != list(range(len(names))):
        raise ValueError('Four groups must partition all encoded predictors')
    return columns


def shapley(values):
    """Exact four-player subset formula on the explicitly saved probability game."""
    if len(values) != 16 or not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
        raise ValueError('Sixteen finite coalition probabilities required')
    result = []
    for player in range(4):
        result.append(math.fsum(math.factorial(mask.bit_count()) * math.factorial(3 - mask.bit_count()) / 24
                                * (values[mask | (1 << player)] - values[mask])
                                for mask in range(16) if not mask & (1 << player)))
    if abs(values[0] + math.fsum(result) - values[-1]) > 1e-12:
        raise ValueError('Shapley reconstruction failed')
    return result


def calculate(train, validation, scores, names, predict, plan):
    plan = validate(plan)
    columns = grouped_columns(names)
    if len(train) < 32 or len(validation) < 12 or len(validation) != len(scores):
        raise ValueError('Required training reference/validation support unavailable')
    for role, rows in (('train', train), ('validation', validation)):
        ids = [r['source_client_id'] for r in rows]
        if len(set(ids)) != len(ids) or any(type(i) is not int for i in ids) or any(r['partition'] != role for r in rows):
            raise ValueError('Unique permitted partition identities required')
    if set(r['source_client_id'] for r in train) & set(r['source_client_id'] for r in validation):
        raise ValueError('Training and validation identities overlap')
    if [(r['source_client_id'], r['target']) for r in validation] != [(r['source_client_id'], r['target']) for r in scores]:
        raise ValueError('Saved validation score identities/targets differ')
    matrix = np.asarray([r['features'] for r in validation], dtype=float)
    reference = np.asarray([r['features'] for r in train], dtype=float)
    if matrix.shape != (len(validation), len(names)) or reference.shape != (len(train), len(names)) or not np.isfinite(matrix).all() or not np.isfinite(reference).all():
        raise ValueError('Finite frozen encoded matrices required')
    targets = np.asarray([r['target'] for r in validation])
    if any(type(r['target']) is not int or r['target'] not in (0, 1) for r in validation) or len(set(targets)) != 2:
        raise ValueError('Both binary validation classes required')
    def predictions(x):
        p = np.asarray(predict(x), dtype=float)
        if p.shape != (len(x),) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
            raise ValueError('Finite bounded predictor output required')
        return p
    baseline = predictions(matrix)
    saved = np.asarray([r['probability'] for r in scores])
    if not np.isfinite(saved).all() or not np.allclose(baseline, saved, rtol=0, atol=1e-12):
        raise ValueError('Frozen prediction differs from saved validation probability')
    brier = float(np.mean((baseline - targets) ** 2))
    auc = float(roc_auc_score(targets, baseline))
    permutations = []
    for group, indices in columns.items():
        repeats = []
        for seed in plan['permutation_seeds']:
            order = np.random.Generator(np.random.PCG64(seed)).permutation(len(matrix))
            perturbed = matrix.copy()
            perturbed[:, indices] = matrix[order][:, indices]
            p = predictions(perturbed)
            loss = float(np.mean((p - targets) ** 2))
            ranking = float(roc_auc_score(targets, p))
            repeats.append({'seed': seed, 'permuted_brier': loss, 'brier_increase': loss - brier,
                            'permuted_auc': ranking, 'auc_decrease': auc - ranking})
        permutations.append({'group': group, 'source_fields': GROUPS[group], 'repeats': repeats,
                             'mean_brier_increase': math.fsum(r['brier_increase'] for r in repeats) / len(repeats),
                             'mean_auc_decrease': math.fsum(r['auc_decrease'] for r in repeats) / len(repeats)})
    background_indices = sorted(range(len(train)), key=lambda i: hashlib.sha256(
        f"{plan['background_seed']}:{train[i]['source_client_id']}".encode('ascii')).hexdigest())[:32]
    background = reference[background_indices]
    ranks = sorted(range(len(validation)), key=lambda i: (float(baseline[i]), validation[i]['source_client_id']))
    selected = [ranks[round(j * (len(ranks) - 1) / 11)] for j in range(12)]
    locals_ = []
    private_cases = []
    for ordinal, index in enumerate(selected, 1):
        batches = []
        for mask in range(16):
            hybrid = background.copy()
            for player, indices in enumerate(columns.values()):
                if mask & (1 << player):
                    hybrid[:, indices] = matrix[index, indices]
            batches.append(hybrid)
        coalition_predictions = predictions(np.concatenate(batches)).reshape(16, 32)
        values = [float(np.mean(row)) for row in coalition_predictions]
        contributions = shapley(values)
        residual = values[0] + math.fsum(contributions) - float(baseline[index])
        if abs(residual) > 1e-12:
            raise ValueError('Local explanation differs from frozen prediction')
        case = f'validation_case_{ordinal:02}'
        locals_.append({'case': case, 'selection_score_rank': ranks.index(index) + 1,
                        'predicted_probability': float(baseline[index]), 'reference_probability': values[0],
                        'contributions': [{'group': g, 'probability_contribution': v}
                                          for g, v in zip(columns, contributions, strict=True)],
                        'reconstruction_residual': residual})
        private_cases.append({'case': case, 'source_client_id': validation[index]['source_client_id'],
                              'coalition_probabilities': values})
    return ({'assumptions': plan, 'target': 'source_default_payment_next_month', 'partition': 'validation',
             'records': len(validation), 'events': int(targets.sum()), 'baseline_brier': brier, 'baseline_auc': auc,
             'feature_groups': GROUPS, 'background_records': 32, 'local_case_count': 12,
             'global_permutation': permutations, 'local_explanations': locals_, 'qualification': FLAGS,
             'definitions': {
                 'global': 'Whole-validation grouped permutation; all columns in a group use the same shuffled row. Positive Brier increase/AUC decrease indicates model reliance.',
                 'local': 'Exact four-group Shapley enumeration of all 16 coalitions; probability output, uniform finite 32-training-row reference, marginal group substitution.',
                 'reference': '32 training IDs chosen by seeded SHA-256 rank; never validation/holdout reference fitting.',
                 'selection': '12 evenly spaced saved-probability ranks; no label-based case choice.',
                 'units': 'Probability contributions; multiply by 100 for percentage points, not percent relative changes.',
                 'uncertainty': 'Three permutations measure repeat variation only, not confidence intervals.'},
             'limitations': [
                 'Validation already used for model selection; exploratory model inspection, not final evaluation.',
                 'Within-group histories/one-hot categories move together; cross-group dependence is broken and hybrid rows may be unrealistic.',
                 'Contributions depend on group definition and finite reference; not individual feature SHAP, causal effects or adverse-action reasons.',
                 'No counterfactual recommendation, production credit decision, calibration/fairness certification or temporal monitoring.']},
            {'background_source_ids': [train[i]['source_client_id'] for i in background_indices], 'cases': private_cases})


def guard(root, pins):
    if any(sha256(contained(root, path)) != digest for path, digest in pins.items()):
        raise ValueError('Explanation input evidence changed')


def source(root, plan):
    scores, lineage = policy_source(root, plan['freeze_id'])
    pins = lineage_pins(root, lineage)
    bundle = contained(root, 'artifacts/private/' + plan['freeze_id'])
    frozen = read_json(bundle / 'freeze-complete.json')
    encoder = read_json(bundle / 'encoder.json')
    model = read_json(bundle / 'model.json')
    if model['feature_dimension'] != len(encoder['feature_names']):
        raise ValueError('Frozen explanation feature dimension mismatch')
    path = contained(root, 'artifacts/private/' + frozen['feature_id'] + '/development.parquet')
    with duckdb.connect(config={'threads': 2, 'memory_limit': '256MB'}) as db:
        rows = db.execute("SELECT * FROM read_parquet(?) WHERE partition IN ('train','validation') ORDER BY partition,source_client_id", [str(path)]).to_arrow_table().to_pylist()
    train = [r for r in rows if r['partition'] == 'train']
    validation = [r for r in rows if r['partition'] == 'validation']
    scores = sorted(scores, key=lambda r: r['source_client_id'])
    calibration = read_json(bundle / 'calibration.json') if frozen['selected_variant'] == 'calibrated' else None
    def predict(matrix):
        p = predict_json(model, matrix)
        return expit(calibration['slope'] * logit(p) + calibration['intercept']) if calibration else p
    guard(root, pins)
    return train, validation, scores, encoder['feature_names'], predict, pins, lineage


def build(root, plan):
    root = root.resolve()
    plan = validate(plan)
    if root.drive.upper() != 'D:':
        raise ValueError('Private D: workspace required')
    train, validation, scores, names, predict, pins, lineage = source(root, plan)
    method = methods()
    report, private = calculate(train, validation, scores, names, predict, plan)
    report.update({key: lineage[key] for key in ('freeze_id', 'case_id', 'assessment_id', 'selected_model', 'selected_variant')})
    folder = contained(root, 'artifacts/private/retail-explanations-' + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    for name, payload in [('assumptions.json', plan), ('report.json', report), ('private-reference-and-coalitions.json', private)]:
        write_new(folder / name, payload)
    guard(root, pins)
    if method != methods():
        raise ValueError('Explanation methods changed during build')
    write_new(folder / 'explanations-complete.json', {
        'schema_version': 1, 'status': 'RETAIL_VALIDATION_EXPLANATIONS_COMPLETE', 'explanations_id': folder.name,
        'freeze_id': plan['freeze_id'], 'completed_at': timestamp(), 'methods': method, 'inputs_sha256': pins,
        'runtime': {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__},
        'outputs_sha256': {name: sha256(folder / name) for name in ('assumptions.json', 'report.json', 'private-reference-and-coalitions.json')},
        'visibility': 'private', 'public_release_approved': False, **FLAGS})
    return {'explanations_id': folder.name, 'records': report['records'], 'local_cases': 12}


def verify(root, identifier):
    if not isinstance(identifier, str) or not ID.fullmatch(identifier):
        raise ValueError('Valid explanation ID required')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'explanations-complete.json')
    if receipt.get('schema_version') != 1 or receipt.get('status') != 'RETAIL_VALIDATION_EXPLANATIONS_COMPLETE' or receipt.get('explanations_id') != identifier or receipt.get('methods') != methods() or receipt.get('visibility') != 'private' or receipt.get('public_release_approved') is not False or any(receipt.get(k) is not v for k, v in FLAGS.items()):
        raise ValueError('Explanation contract changed')
    if receipt['runtime'] != {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}:
        raise ValueError('Explanation runtime changed')
    if set(receipt['outputs_sha256']) != {'assumptions.json', 'report.json', 'private-reference-and-coalitions.json'}:
        raise ValueError('Complete explanation payload required')
    guard(root, {**receipt['inputs_sha256'], **{str((folder / name).relative_to(root)): digest for name, digest in receipt['outputs_sha256'].items()}})
    plan = validate(read_json(folder / 'assumptions.json'))
    if plan['freeze_id'] != receipt['freeze_id']:
        raise ValueError('Explanation frozen model binding changed')
    train, validation, scores, names, predict, pins, lineage = source(root, plan)
    if pins != receipt['inputs_sha256']:
        raise ValueError('Explanation lineage changed')
    report, private = calculate(train, validation, scores, names, predict, plan)
    report.update({key: lineage[key] for key in ('freeze_id', 'case_id', 'assessment_id', 'selected_model', 'selected_variant')})
    if report != read_json(folder / 'report.json') or private != read_json(folder / 'private-reference-and-coalitions.json'):
        raise ValueError('Explanations do not replay from frozen development evidence')
    return folder, receipt, report
