"""Frozen-settings UCI365 development fitting; reserved final is inaccessible here."""
from __future__ import annotations

import re
import uuid
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.special import expit
from sklearn import __version__ as sklearn_version
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from threadpoolctl import threadpool_limits

# Reuse the already reviewed numerical JSON scorer without modifying P1 artifacts/methods.
from .retail_assessment import predict_json
from .bankruptcy import FEATURES
from .bankruptcy_study import DEVELOPMENT, FEATURE_COLUMNS, PROTOCOL, RatioEncoder, fingerprint, verify_features
from .workspace import contained, read_json, sha256, timestamp, write_new

CANDIDATES = tuple(PROTOCOL['selection']['candidates'])


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
            ('bankruptcy_assessment', 'bankruptcy_study', 'bankruptcy', 'retail_assessment', 'workspace')}


def probability_metrics(targets, probabilities):
    y, p = np.asarray(targets), np.asarray(probabilities, dtype=float)
    if (y.ndim != 1 or p.shape != y.shape or len(set(y.tolist())) != 2
            or set(y.tolist()) != {0, 1} or not np.isfinite(p).all() or np.any((p < 0) | (p > 1))):
        raise ValueError('Binary targets and finite probabilities with both classes required')
    bins = []
    for i in range(10):
        lower, upper = i/10, (i+1)/10
        mask = (p >= lower) & ((p < upper) if i < 9 else (p <= upper))
        count = int(mask.sum())
        bins.append({'lower': lower, 'upper': upper, 'statements': count, 'events': int(y[mask].sum()),
            'mean_probability': float(p[mask].mean()) if count else None,
            'observed_rate': float(y[mask].mean()) if count else None})
    if sum(row['statements'] for row in bins) != len(y):
        raise ValueError('Reliability bins do not reconcile')
    return {'statements': len(y), 'events': int(y.sum()), 'roc_auc': float(roc_auc_score(y, p)),
        'average_precision': float(average_precision_score(y, p)), 'brier_score': float(brier_score_loss(y, p)),
        'log_loss': float(log_loss(y, p, labels=[0, 1])), 'reliability_bins': bins,
        'scope': 'source-statement-weighted validation, not firm-independent/OOT or calibrated loan PD'}


def clipped_logit(probabilities):
    values = np.asarray(probabilities, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError('Finite probability vector required')
    epsilon = PROTOCOL['calibration']['clip_epsilon']
    values = np.clip(values, epsilon, 1-epsilon)
    return np.log(values)-np.log1p(-values)


def fit_platt(probabilities, targets):
    logits, y = clipped_logit(probabilities), np.asarray(targets)
    if len(y) != len(logits) or set(y.tolist()) != {0, 1} or min(int((y == value).sum()) for value in (0, 1)) < 20:
        raise ValueError('Insufficient separate calibration support')
    fitted = LogisticRegression(C=PROTOCOL['calibration']['C'], max_iter=3000, tol=1e-8).fit(logits.reshape(-1, 1), y)
    state = {'method': 'platt_logistic_on_clipped_raw_logit', 'C': PROTOCOL['calibration']['C'],
        'clip_epsilon': PROTOCOL['calibration']['clip_epsilon'], 'slope': float(fitted.coef_[0, 0]),
        'intercept': float(fitted.intercept_[0]), 'fit_partition': 'calibration', 'rows': len(y), 'events': int(y.sum())}
    if not np.isfinite([state['slope'], state['intercept']]).all():
        raise ValueError('Nonfinite persisted Platt state')
    return state, fitted


def apply_platt(probabilities, state):
    if (state['method'] != 'platt_logistic_on_clipped_raw_logit' or state['C'] != PROTOCOL['calibration']['C']
            or state['clip_epsilon'] != PROTOCOL['calibration']['clip_epsilon'] or state['fit_partition'] != 'calibration'
            or not np.isfinite([state['slope'], state['intercept']]).all()):
        raise ValueError('Platt calibration contract changed')
    return expit(state['slope']*clipped_logit(probabilities)+state['intercept'])


def export_boosting(fitted, dimension):
    if (sklearn_version != '1.8.0' or fitted.do_early_stopping_ or len(fitted.validation_score_)
            or fitted.n_iter_ != PROTOCOL['fixed_models']['histogram_boosting']['max_iter']):
        raise ValueError('Reviewed exporter requires sklearn1.8.0 and no internal validation')
    trees = []
    for iteration in fitted._predictors:
        if len(iteration) != 1 or any(node['is_categorical'] for node in iteration[0].nodes):
            raise ValueError('Unsupported histogram tree export')
        trees.append([{'value': float(node['value']), 'feature': int(node['feature_idx']),
            'threshold': float(node['num_threshold']), 'left': int(node['left']), 'right': int(node['right']),
            'is_leaf': bool(node['is_leaf'])} for node in iteration[0].nodes])
    return {'kind': 'histogram_boosting', 'feature_dimension': dimension,
            'initial_raw_score': float(fitted._baseline_prediction[0, 0]), 'trees': trees}


def run_assessment(root, feature_id):
    feature_folder, feature, study_folder, study = verify_features(root, feature_id)
    digest, frozen_methods = sha256(feature_folder / 'features-complete.json'), methods()
    output = contained(root, 'artifacts/private/bankruptcy-assessment-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    provenance = {'assessment_id': output.name, 'feature_id': feature_id, 'feature_receipt_sha256': digest,
        'study_id': study['study_id'], 'study_receipt_sha256': sha256(study_folder / 'study-complete.json'),
        'methods': frozen_methods, 'visibility': 'private', 'public_release_approved': False,
        'final_test_scored': False, 'champion_selected': False, 'production_qualified': False,
        'entity_disjointness_verified': False, 'temporal_out_of_time': False}
    write_new(output / 'access-start.json', {**provenance, 'started_at': timestamp(), 'allowed_predictor_roles': list(DEVELOPMENT)})
    try:
        development = pq.read_table(feature_folder / 'development.parquet').to_pylist()
        case_folder = contained(root, 'artifacts/private/' + study['case_id'])
        with duckdb.connect() as db:
            db.read_parquet(str(case_folder / 'financial-statements.parquet')).create_view('facts')
            db.read_parquet(str(study_folder / 'partitions.parquet')).create_view('partitions')
            fields = ','.join('f."' + name + '"' for name in FEATURES)
            source = db.execute('SELECT p.source_row_ordinal,p.feature_group_id,p.partition,f.source_bankruptcy_label,' + fields +
                ' FROM facts f JOIN partitions p USING(source_row_ordinal) '
                "WHERE p.partition IN ('train','calibration','validation') AND f.forecast_horizon_years=? "
                'ORDER BY p.source_row_ordinal', [study['horizon']]).to_arrow_table().to_pylist()
        keys = ('source_row_ordinal', 'feature_group_id', 'partition', 'source_bankruptcy_label')
        if ([tuple(row[key] for key in keys) for row in source] != [tuple(row[key] for key in keys) for row in development]
                or any(fingerprint(row) != row['feature_group_id'] for row in source)):
            raise ValueError('Canonical development identities/labels/groups differ')
        restored = RatioEncoder()
        restored.state = read_json(feature_folder / 'encoder.json')
        if RatioEncoder().fit([row for row in source if row['partition'] == 'train']).state != restored.state:
            raise ValueError('Encoder differs from exact training cohort')
        matrix = np.asarray([[row[column] for column in FEATURE_COLUMNS] for row in development], dtype=float)
        if not np.array_equal(matrix, restored.transform(source)):
            raise ValueError('Development features differ from canonical source/encoder')
        roles = np.asarray([row['partition'] for row in development])
        y = np.asarray([row['source_bankruptcy_label'] for row in development], dtype=np.int8)
        masks = {role: roles == role for role in DEVELOPMENT}
        for role, mask in masks.items():
            if int(mask.sum()) != study['support'][role]['rows'] or int(y[mask].sum()) != study['support'][role]['positive']:
                raise ValueError('Frozen development support mismatch')
            if min(int((y[mask] == value).sum()) for value in (0, 1)) < (50 if role == 'train' else 20):
                raise ValueError('Insufficient fixed development support')
        if sklearn_version != '1.8.0':
            raise ValueError('Reviewed model exporter requires sklearn1.8.0')
        write_new(output / 'settings.json', PROTOCOL)
        write_new(output / 'fit-start.json', {'started_at': timestamp(), 'settings_sha256': sha256(output / 'settings.json'),
            'model_training_requested': True, 'training_rows': int(masks['train'].sum()), 'sklearn_version': sklearn_version})
        train, calibration, validation = (masks[role] for role in DEVELOPMENT)
        models = {'constant': {'kind': 'constant', 'prevalence': float(y[train].mean()), 'feature_dimension': matrix.shape[1]}}
        native = {'constant': np.full(len(matrix), models['constant']['prevalence'])}
        with threadpool_limits(limits=1), warnings.catch_warnings():
            warnings.simplefilter('error', ConvergenceWarning)
            logistic = LogisticRegression(**PROTOCOL['fixed_models']['logistic']).fit(matrix[train], y[train])
            models['logistic'] = {'kind': 'logistic', 'feature_dimension': matrix.shape[1],
                'coefficients': logistic.coef_[0].tolist(), 'intercept': float(logistic.intercept_[0])}
            native['logistic'] = logistic.predict_proba(matrix)[:, 1]
            boosting = HistGradientBoostingClassifier(**PROTOCOL['fixed_models']['histogram_boosting'],
                validation_fraction=None, categorical_features=None, class_weight=None, warm_start=False).fit(matrix[train], y[train])
            models['boosting'] = export_boosting(boosting, matrix.shape[1])
            native['boosting'] = boosting.predict_proba(matrix)[:, 1]
            probabilities, parity = {}, {}
            for name, model in models.items():
                write_new(output / (name + '-model.json'), model)
                saved = predict_json(read_json(output / (name + '-model.json')), matrix)
                difference = float(np.max(np.abs(saved-native[name])))
                if difference > 1e-12:
                    raise ValueError('Native/persisted model probability parity failed')
                parity[name] = {'rows': len(matrix), 'max_absolute_difference': difference}
                probabilities[name + '_raw'] = saved
                if name != 'constant':
                    state, fitted = fit_platt(saved[calibration], y[calibration])
                    write_new(output / (name + '-platt.json'), state)
                    adjusted = apply_platt(saved, read_json(output / (name + '-platt.json')))
                    native_adjusted = fitted.predict_proba(clipped_logit(saved).reshape(-1, 1))[:, 1]
                    difference = float(np.max(np.abs(adjusted-native_adjusted)))
                    if difference > 1e-12:
                        raise ValueError('Native/persisted Platt probability parity failed')
                    parity[name + '_platt'] = {'rows': len(matrix), 'max_absolute_difference': difference,
                                             'ranking_reversed': state['slope'] < 0}
                    probabilities[name + '_platt'] = adjusted
        evaluations, score_rows = {}, []
        for candidate in CANDIDATES:
            p = probabilities[candidate][validation]
            evaluations[candidate] = probability_metrics(y[validation], p)
            for row, probability in zip([row for row in development if row['partition'] == 'validation'], p, strict=True):
                score_rows.append({'source_row_ordinal': row['source_row_ordinal'], 'feature_group_id': row['feature_group_id'],
                    'source_bankruptcy_label': row['source_bankruptcy_label'], 'candidate': candidate, 'probability': float(probability)})
        pq.write_table(pa.Table.from_pylist(score_rows), output / 'private-validation-scores.parquet', compression='zstd')
        persisted = pq.read_table(output / 'private-validation-scores.parquet').to_pylist()
        for candidate in CANDIDATES:
            selected = [row for row in persisted if row['candidate'] == candidate]
            if probability_metrics([row['source_bankruptcy_label'] for row in selected], [row['probability'] for row in selected]) != evaluations[candidate]:
                raise ValueError('Saved probability/metric reconciliation failed')
        write_new(output / 'validation-metrics.json', evaluations)
        write_new(output / 'verification.json', {'status': 'PASS', 'model_probability_parity': parity,
            'validation_rows': int(validation.sum()), 'candidates': list(CANDIDATES), 'final_test_scored': False,
            'validation_score_rows': len(score_rows), 'source_encoder_reproduced': True})
        verify_features(root, feature_id)
        if methods() != frozen_methods or sha256(feature_folder / 'features-complete.json') != digest:
            raise ValueError('Assessment input/method lineage changed during fitting')
        receipt = {**provenance, 'status': 'BANKRUPTCY_DEVELOPMENT_ASSESSMENT_VERIFIED', 'completed_at': timestamp(),
            'model_training_performed': True, 'support': study['support'], 'parity': parity,
            'files': {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
        write_new(output / 'assessment-complete.json', receipt)
        return receipt
    except Exception as error:
        write_new(output / 'assessment-failed.json', {**provenance, 'status': 'FAILED', 'failed_at': timestamp(),
                                                    'exception_type': type(error).__name__})
        raise


def verify_assessment(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-assessment-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy assessment identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'assessment-complete.json')
    if (receipt['assessment_id'] != identifier or receipt['status'] != 'BANKRUPTCY_DEVELOPMENT_ASSESSMENT_VERIFIED'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private' or receipt['model_training_performed'] is not True
            or any(receipt[key] is not False for key in ('public_release_approved', 'final_test_scored', 'champion_selected',
                                                        'production_qualified', 'entity_disjointness_verified', 'temporal_out_of_time'))):
        raise ValueError('Bankruptcy assessment method/qualification changed')
    feature_folder, feature, study_folder, study = verify_features(root, receipt['feature_id'])
    if (sha256(feature_folder / 'features-complete.json') != receipt['feature_receipt_sha256']
            or study['study_id'] != receipt['study_id'] or receipt['support'] != study['support']
            or sha256(study_folder / 'study-complete.json') != receipt['study_receipt_sha256']):
        raise ValueError('Bankruptcy assessment frozen input lineage changed')
    expected = {'access-start.json', 'fit-start.json', 'settings.json', 'constant-model.json', 'logistic-model.json',
        'boosting-model.json', 'logistic-platt.json', 'boosting-platt.json', 'private-validation-scores.parquet',
        'validation-metrics.json', 'verification.json'}
    if set(receipt['files']) != expected:
        raise ValueError('Bankruptcy assessment output population changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('Bankruptcy assessment evidence bytes changed')
    if read_json(folder / 'settings.json') != PROTOCOL:
        raise ValueError('Bankruptcy fixed assessment settings changed')
    scores = pq.read_table(folder / 'private-validation-scores.parquet').to_pylist()
    expected_keys = [(row['source_row_ordinal'], row['feature_group_id'], row['source_bankruptcy_label'])
                     for row in pq.read_table(study_folder / 'partitions.parquet').to_pylist() if row['partition'] == 'validation']
    evaluations = read_json(folder / 'validation-metrics.json')
    if set(evaluations) != set(CANDIDATES) or len(scores) != len(expected_keys)*len(CANDIDATES):
        raise ValueError('Bankruptcy candidate/validation population changed')
    for candidate in CANDIDATES:
        selected = [row for row in scores if row['candidate'] == candidate]
        if ([(row['source_row_ordinal'], row['feature_group_id'], row['source_bankruptcy_label']) for row in selected] != expected_keys
                or probability_metrics([row['source_bankruptcy_label'] for row in selected], [row['probability'] for row in selected]) != evaluations[candidate]):
            raise ValueError('Bankruptcy validation scores/metrics do not reconcile')
    verification = read_json(folder / 'verification.json')
    if (verification['status'] != 'PASS' or verification['final_test_scored'] is not False
            or verification['model_probability_parity'] != receipt['parity']
            or any(item['max_absolute_difference'] > 1e-12 for item in receipt['parity'].values())):
        raise ValueError('Bankruptcy persisted prediction parity changed')
    return folder, receipt, evaluations
