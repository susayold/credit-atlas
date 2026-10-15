"""Paired exact-feature-group validation uncertainty; no final-test access."""
from __future__ import annotations

import itertools
import re
import uuid
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

from .bankruptcy_assessment import CANDIDATES, apply_platt, probability_metrics, verify_assessment
from .bankruptcy_study import FEATURE_COLUMNS, PROTOCOL, verify_features
from .retail_assessment import predict_json
from .workspace import contained, read_json, sha256, timestamp, write_new

METRICS = ('roc_auc', 'average_precision', 'brier_score', 'log_loss')
BOOTSTRAP = {'replicates': 1000, 'seed': 3651, 'confidence_level': .95,
    'method': 'unstratified_paired_exact_feature_group_percentile; retain source-record weights',
    'conditioning': 'fixed fitted models and observed validation groups, not retraining or firm sampling',
    'single_class_draws': 'exclude and report; require >=95percent valid draws',
    'intervals': 'exploratory, unadjusted for multiple comparisons',
    'replicate_count_and_seed_chosen_after_point_metric_inspection': True,
    'champion_selected': False, 'final_test_scored': False}


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
            ('bankruptcy_comparison', 'bankruptcy_assessment', 'bankruptcy_study', 'retail_assessment', 'workspace')}


def verified_validation(root, assessment_id):
    folder, receipt, metrics = verify_assessment(root, assessment_id)
    feature_folder, _, _, _ = verify_features(root, receipt['feature_id'])
    rows = [row for row in pq.read_table(feature_folder / 'development.parquet').to_pylist() if row['partition'] == 'validation']
    matrix = np.asarray([[row[name] for name in FEATURE_COLUMNS] for row in rows], dtype=float)
    y = np.asarray([row['source_bankruptcy_label'] for row in rows], dtype=np.int8)
    groups = np.asarray([row['feature_group_id'] for row in rows])
    scores = pq.read_table(folder / 'private-validation-scores.parquet').to_pylist()
    probabilities = {}
    for candidate in CANDIDATES:
        name, variant = candidate.split('_')
        expected = predict_json(read_json(folder / (name + '-model.json')), matrix)
        if variant == 'platt':
            expected = apply_platt(expected, read_json(folder / (name + '-platt.json')))
        selected = [row for row in scores if row['candidate'] == candidate]
        p = np.asarray([row['probability'] for row in selected])
        if (len(p) != len(y) or not np.allclose(p, expected, rtol=0, atol=1e-12)
                or probability_metrics(y, p) != metrics[candidate]):
            raise ValueError('Validation scores differ from frozen persisted model/calibration')
        probabilities[candidate] = p
    return folder, receipt, y, groups, probabilities


def _metrics(y, p):
    return [roc_auc_score(y, p), average_precision_score(y, p), brier_score_loss(y, p), log_loss(y, p, labels=[0, 1])]


def paired_group_bootstrap(y, groups, probabilities, replicates=1000, seed=3651):
    y, groups = np.asarray(y), np.asarray(groups)
    if (y.ndim != 1 or groups.shape != y.shape or set(y.tolist()) != {0, 1}
            or len(set(groups.tolist())) < 4 or type(replicates) is not int or not 100 <= replicates <= 5000
            or type(seed) is not int or set(probabilities) != set(CANDIDATES)):
        raise ValueError('Valid paired group-bootstrap inputs required')
    arrays = {name: np.asarray(probabilities[name], dtype=float) for name in CANDIDATES}
    if any(p.shape != y.shape or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)) for p in arrays.values()):
        raise ValueError('Identical ordered finite candidate vectors required')
    members = [np.flatnonzero(groups == key) for key in sorted(set(groups.tolist()))]
    rng = np.random.default_rng(seed)
    samples, draw_groups = [], []
    skipped, min_rows, max_rows = 0, None, None
    for replicate in range(replicates):
        # Each draw repeats *all* rows of each selected group, preserving duplicate weights.
        drawn = rng.integers(0, len(members), size=len(members))
        indices = np.concatenate([members[index] for index in drawn])
        if len(set(y[indices].tolist())) != 2:
            skipped += 1
            continue
        samples.append([_metrics(y[indices], arrays[name][indices]) for name in CANDIDATES])
        draw_groups.append(replicate)
        min_rows = len(indices) if min_rows is None else min(min_rows, len(indices))
        max_rows = len(indices) if max_rows is None else max(max_rows, len(indices))
    if len(samples) < replicates*.95:
        raise ValueError('Too many single-class group-bootstrap draws for supported intervals')
    values = np.asarray(samples, dtype=float)
    point = np.asarray([_metrics(y, arrays[name]) for name in CANDIDATES])
    intervals = {}
    for i, name in enumerate(CANDIDATES):
        intervals[name] = {metric: {'point': float(point[i, j]),
            'lower': float(np.quantile(values[:, i, j], .025)), 'upper': float(np.quantile(values[:, i, j], .975))}
            for j, metric in enumerate(METRICS)}
    paired = {}
    for i, j in itertools.combinations(range(len(CANDIDATES)), 2):
        delta = values[:, j]-values[:, i]
        paired[CANDIDATES[j] + '_minus_' + CANDIDATES[i]] = {metric: {
            'point': float(point[j, k]-point[i, k]), 'lower': float(np.quantile(delta[:, k], .025)),
            'upper': float(np.quantile(delta[:, k], .975))} for k, metric in enumerate(METRICS)}
    return {'valid_replicates': len(samples), 'skipped_single_class': skipped, 'validation_rows': len(y),
        'validation_groups': len(members), 'min_replicate_rows': min_rows, 'max_replicate_rows': max_rows,
        'metric_order': list(METRICS), 'candidate_order': list(CANDIDATES), 'intervals': intervals,
        'paired_deltas': paired}, values, draw_groups


def run_comparison(root, assessment_id):
    folder, assessment, y, groups, probabilities = verified_validation(root, assessment_id)
    digest, frozen_methods = sha256(folder / 'assessment-complete.json'), methods()
    output = contained(root, 'artifacts/private/bankruptcy-comparison-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output / 'access-start.json', {'assessment_id': assessment_id, 'assessment_receipt_sha256': digest,
        'methods': frozen_methods, 'started_at': timestamp(), 'predictor_roles': ['validation'], 'final_test_scored': False})
    write_new(output / 'bootstrap-settings.json', BOOTSTRAP)
    summary, values, draws = paired_group_bootstrap(y, groups, probabilities,
        replicates=BOOTSTRAP['replicates'], seed=BOOTSTRAP['seed'])
    records = [{'draw': draw, 'candidate': name, **dict(zip(METRICS, values[i, j].tolist(), strict=True))}
               for i, draw in enumerate(draws) for j, name in enumerate(CANDIDATES)]
    pq.write_table(pa.Table.from_pylist(records), output / 'paired-replicates.parquet', compression='zstd')
    write_new(output / 'uncertainty.json', summary)
    verified_validation(root, assessment_id)
    if methods() != frozen_methods or sha256(folder / 'assessment-complete.json') != digest:
        raise ValueError('Validation comparison input/method changed')
    receipt = {'comparison_id': output.name, 'assessment_id': assessment_id, 'assessment_receipt_sha256': digest,
        'status': 'BANKRUPTCY_PAIRED_GROUP_UNCERTAINTY_VERIFIED', 'methods': frozen_methods,
        'completed_at': timestamp(), 'visibility': 'private', 'public_release_approved': False,
        'champion_selected': False, 'final_test_scored': False,
        'files': {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    write_new(output / 'comparison-complete.json', receipt)
    return receipt


def verify_comparison(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-comparison-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy comparison identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'comparison-complete.json')
    if (receipt['comparison_id'] != identifier or receipt['status'] != 'BANKRUPTCY_PAIRED_GROUP_UNCERTAINTY_VERIFIED'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or any(receipt[key] is not False for key in ('public_release_approved', 'champion_selected', 'final_test_scored'))):
        raise ValueError('Bankruptcy comparison method/qualification changed')
    assessment_folder, _, y, groups, probabilities = verified_validation(root, receipt['assessment_id'])
    if sha256(assessment_folder / 'assessment-complete.json') != receipt['assessment_receipt_sha256']:
        raise ValueError('Bankruptcy comparison assessment lineage changed')
    if set(receipt['files']) != {'access-start.json', 'bootstrap-settings.json', 'paired-replicates.parquet', 'uncertainty.json'}:
        raise ValueError('Bankruptcy comparison output population changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('Bankruptcy comparison evidence bytes changed')
    if read_json(folder / 'bootstrap-settings.json') != BOOTSTRAP:
        raise ValueError('Bankruptcy comparison bootstrap settings changed')
    summary = read_json(folder / 'uncertainty.json')
    rows = pq.read_table(folder / 'paired-replicates.parquet').to_pylist()
    if (len(rows) != summary['valid_replicates']*len(CANDIDATES)
            or summary['validation_rows'] != len(y) or summary['validation_groups'] != len(set(groups.tolist()))
            or summary['valid_replicates'] + summary['skipped_single_class'] != BOOTSTRAP['replicates']):
        raise ValueError('Bankruptcy group-bootstrap population changed')
    keys = {(row['draw'], row['candidate']) for row in rows}
    draw_ids = {row['draw'] for row in rows}
    if (len(keys) != len(rows) or {row['candidate'] for row in rows} != set(CANDIDATES)
            or len(draw_ids) != summary['valid_replicates'] or summary['valid_replicates'] < .95*BOOTSTRAP['replicates']
            or any(type(draw) is not int or not 0 <= draw < BOOTSTRAP['replicates'] for draw in draw_ids)
            or any((draw, name) not in keys for draw in draw_ids for name in CANDIDATES)):
        raise ValueError('Paired bootstrap draws/candidate identities changed')
    for name in CANDIDATES:
        selected = [row for row in rows if row['candidate'] == name]
        if len(selected) != summary['valid_replicates']:
            raise ValueError('Bootstrap candidates do not share draw counts')
        point = _metrics(y, probabilities[name])
        for i, metric in enumerate(METRICS):
            values = np.asarray([row[metric] for row in selected])
            expected = {'point': float(point[i]), 'lower': float(np.quantile(values, .025)), 'upper': float(np.quantile(values, .975))}
            if expected != summary['intervals'][name][metric]:
                raise ValueError('Bootstrap interval does not reconcile with persisted draws')
    # Paired differences must use matching draw IDs, not marginal endpoint subtraction.
    mapped = {(row['draw'], row['candidate']): row for row in rows}
    draw_ids = sorted({row['draw'] for row in rows})
    for left, right in itertools.combinations(CANDIDATES, 2):
        left_point, right_point = _metrics(y, probabilities[left]), _metrics(y, probabilities[right])
        for i, metric in enumerate(METRICS):
            delta = [mapped[(draw, right)][metric]-mapped[(draw, left)][metric] for draw in draw_ids]
            expected = {'point': float(right_point[i]-left_point[i]), 'lower': float(np.quantile(delta, .025)),
                        'upper': float(np.quantile(delta, .975))}
            if expected != summary['paired_deltas'][right + '_minus_' + left][metric]:
                raise ValueError('Paired bootstrap differences do not reconcile')
    return folder, receipt, summary
