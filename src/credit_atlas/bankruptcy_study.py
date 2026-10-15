"""Frozen horizon-specific duplicate-group protocol and train-only transforms."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import uuid
from collections import defaultdict
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .bankruptcy import FEATURES, HORIZONS, verify_bankruptcy
from .workspace import contained, read_json, sha256, timestamp, write_new

ROLES = ('train', 'calibration', 'validation', 'final_test')
DEVELOPMENT = ROLES[:3]
PROTOCOL = {'version': 'uci365-original-arff-group-benchmark-v1',
    'intended_use': 'Historical financial-statement bankruptcy classification at one source-specific horizon',
    'prior_source_quality_inspection': True, 'protocol_before_model_fitting_and_validation_metrics': True,
    'random_group_split': True, 'entity_disjointness_verified': False, 'temporal_out_of_time': False,
    'pool_horizons': False, 'seed': 'CreditAtlas-UCI365-group-v1',
    'stratification': 'exact-feature-group source labels: 0, 1, or mixed; weighted group midpoint',
    'fractions': dict(zip(ROLES, (.60, .15, .15, .10), strict=True)),
    'duplicates': 'retain every source row; exact numeric-feature groups remain in one partition; not firm IDs',
    'features': list(FEATURES), 'missing_indicators': list(FEATURES),
    'transform': 'train median -> signed asinh -> train mean/population std; 64 fixed missing indicators',
    'all_missing_train_feature': 'median zero, scale one; explicit recorded fallback',
    'feature_exclusions': ['source_row_ordinal', 'source_subset_code', 'forecast_horizon_years',
                           'source_bankruptcy_label', 'feature_group_id'],
    'fixed_models': {'constant': 'train source-label prevalence',
        'logistic': {'C': 1.0, 'max_iter': 3000, 'tol': 1e-8, 'class_weight': None},
        'histogram_boosting': {'learning_rate': .05, 'max_iter': 120, 'max_leaf_nodes': 15,
            'min_samples_leaf': 30, 'l2_regularization': 1.0, 'random_state': 365, 'early_stopping': False}},
    'calibration': {'method': 'Platt logistic on clipped raw logit, separate calibration split',
                    'C': 1.0, 'clip_epsilon': 1e-12, 'compare_raw_and_calibrated': True},
    'selection': {'candidates': ['constant_raw', 'logistic_raw', 'logistic_platt', 'boosting_raw', 'boosting_platt'],
        'primary': 'validation Brier score, lower is better', 'secondary': 'validation log loss',
        'metric_tie_tolerance': 1e-6,
        'tie_preference': ['constant_raw', 'logistic_raw', 'logistic_platt', 'boosting_raw', 'boosting_platt'],
        'ranking_metrics_reported_not_selection': ['ROC AUC', 'average precision'],
        'final_test_used_for_selection': False, 'hyperparameter_search': False},
    'uncertainty': 'paired resampling of exact-feature groups with source-record weights; groups are not identified firms',
    'reserved_final': 'one evaluation after model/transform freeze; lineage registry shared across recreated canonical cases',
    'production_qualified': False, 'public_release_approved': False}
PARTITION_SCHEMA = pa.schema([('source_row_ordinal', pa.int32()), ('feature_group_id', pa.string()),
                             ('partition', pa.string()), ('source_bankruptcy_label', pa.int8())])
FEATURE_COLUMNS = tuple('x' + str(i).zfill(3) for i in range(1, 129))


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py'))
            for name in ('bankruptcy_study', 'bankruptcy', 'workspace')}


def fingerprint(row):
    values = []
    for name in FEATURES:
        value = row[name]
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError('Finite numeric features or NULL required for groups')
        # Signed zero has the same numeric meaning; explicit NULL remains distinct.
        values.append(None if value is None else float(0 if value == 0 else value).hex())
    return hashlib.sha256(json.dumps(values, separators=(',', ':')).encode('ascii')).hexdigest()


def assign_groups(rows, horizon):
    if type(horizon) is not int or horizon not in HORIZONS:
        raise ValueError('Forecast horizon must be integer1..5')
    if not rows or any(type(row['source_row_ordinal']) is not int or row['source_row_ordinal'] <= 0
            or type(row['source_bankruptcy_label']) is not int or row['source_bankruptcy_label'] not in (0, 1)
            or row['forecast_horizon_years'] != horizon for row in rows):
        raise ValueError('One valid horizon with binary source labels required')
    if len({row['source_row_ordinal'] for row in rows}) != len(rows):
        raise ValueError('Duplicate source ordinals')
    groups = defaultdict(list)
    for row in rows:
        groups[fingerprint(row)].append(row)
    strata = defaultdict(list)
    for key, members in groups.items():
        labels = {row['source_bankruptcy_label'] for row in members}
        strata['mixed' if len(labels) == 2 else str(next(iter(labels)))].append((key, members))
    assignments = []
    for stratum, items in sorted(strata.items()):
        ranked = sorted(items, key=lambda item: hashlib.sha256((PROTOCOL['seed'] + ':' + str(horizon)
                        + ':' + stratum + ':' + item[0]).encode('ascii')).hexdigest())
        total, cumulative = sum(len(members) for _, members in ranked), 0
        for key, members in ranked:
            midpoint = (cumulative + len(members)/2) / total
            role = ROLES[0] if midpoint < .60 else ROLES[1] if midpoint < .75 else ROLES[2] if midpoint < .90 else ROLES[3]
            assignments.extend({'source_row_ordinal': row['source_row_ordinal'], 'feature_group_id': key,
                'partition': role, 'source_bankruptcy_label': row['source_bankruptcy_label']} for row in members)
            cumulative += len(members)
    return sorted(assignments, key=lambda row: row['source_row_ordinal'])


def partition_support(assignments):
    result = {}
    for role in ROLES:
        members = [row for row in assignments if row['partition'] == role]
        positive = sum(row['source_bankruptcy_label'] for row in members)
        result[role] = {'rows': len(members), 'positive': positive, 'negative': len(members)-positive,
                        'exact_feature_groups': len({row['feature_group_id'] for row in members})}
    return result


def create_study(root, case_id, horizon=1):
    if type(horizon) is not int or horizon not in HORIZONS:
        raise ValueError('Forecast horizon must be integer1..5')
    case_folder, case = verify_bankruptcy(root, case_id)
    # Dataset identity uses original ZIP, so rebuilding CSV/case/method cannot reset the reservation.
    lineage_key = hashlib.sha256(('UCI365:original-arff:' + case['reference']['sha256'] + ':horizon:' + str(horizon)).encode()).hexdigest()
    registry = contained(root, 'artifacts/private/bankruptcy-study-registry/' + lineage_key)
    if registry.exists():
        reservation = read_json(registry / 'reservation.json')
        folder, saved = verify_study(root, reservation['study_id'])
        if saved['case_id'] != case_id:
            raise ValueError('Original source/horizon already reserved; reuse the existing study instead of resetting a holdout')
        return saved
    with duckdb.connect() as db:
        db.read_parquet(str(case_folder / 'financial-statements.parquet')).create_view('facts')
        rows = db.execute('SELECT * FROM facts WHERE forecast_horizon_years=? ORDER BY source_row_ordinal',
                          [horizon]).to_arrow_table().to_pylist()
    assignments = assign_groups(rows, horizon)
    support = partition_support(assignments)
    if any(item['positive'] < (50 if role == 'train' else 20) or item['negative'] < 20
           for role, item in support.items()):
        raise ValueError('Insufficient source-label support for the frozen four-part benchmark')
    identifier = 'bankruptcy-study-' + uuid.uuid4().hex[:12]
    frozen_methods, digest = methods(), sha256(case_folder / 'bankruptcy-complete.json')
    registry.mkdir(parents=True)  # atomic: one reservation per original source/horizon
    write_new(registry / 'reservation.json', {'study_id': identifier, 'lineage_key': lineage_key,
        'original_zip_sha256': case['reference']['sha256'], 'horizon': horizon, 'reserved_at': timestamp()})
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    write_new(output / 'run-start.json', {'study_id': identifier, 'case_id': case_id, 'horizon': horizon,
        'case_receipt_sha256': digest, 'lineage_key': lineage_key, 'methods': frozen_methods, 'started_at': timestamp()})
    write_new(output / 'protocol.json', copy.deepcopy(PROTOCOL))
    pq.write_table(pa.Table.from_pylist(assignments, schema=PARTITION_SCHEMA), output / 'partitions.parquet', compression='zstd')
    groups = defaultdict(set)
    for row in assignments:
        groups[row['feature_group_id']].add(row['partition'])
    if any(len(roles) != 1 for roles in groups.values()):
        raise ValueError('Exact feature group crosses partitions')
    write_new(output / 'support.json', {'support': support, 'rows': len(rows), 'exact_feature_groups': len(groups),
        'duplicate_excess': len(rows)-len(groups), 'groups_crossing_partitions': 0,
        'entity_disjointness_verified': False, 'temporal_out_of_time': False})
    verify_bankruptcy(root, case_id)
    if methods() != frozen_methods or sha256(case_folder / 'bankruptcy-complete.json') != digest:
        raise ValueError('Bankruptcy study lineage changed during freeze')
    receipt = {'study_id': identifier, 'case_id': case_id, 'horizon': horizon, 'lineage_key': lineage_key,
        'status': 'BANKRUPTCY_PROTOCOL_FROZEN', 'completed_at': timestamp(), 'case_receipt_sha256': digest,
        'methods': frozen_methods, 'support': support, 'rows': len(rows), 'exact_feature_groups': len(groups),
        'visibility': 'private', 'public_release_approved': False, 'model_training_performed': False,
        'final_test_scored': False, 'final_test_predictors_materialized_in_development': False,
        'entity_disjointness_verified': False, 'temporal_out_of_time': False,
        'files': {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    write_new(output / 'study-complete.json', receipt)
    return receipt


def verify_study(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-study-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy study identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'study-complete.json')
    if (receipt['study_id'] != identifier or receipt['status'] != 'BANKRUPTCY_PROTOCOL_FROZEN'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or any(receipt[key] is not False for key in ('public_release_approved', 'model_training_performed',
                'final_test_scored', 'final_test_predictors_materialized_in_development', 'entity_disjointness_verified', 'temporal_out_of_time'))
            or type(receipt['horizon']) is not int or receipt['horizon'] not in HORIZONS):
        raise ValueError('Bankruptcy study method/qualification changed')
    case_folder, case = verify_bankruptcy(root, receipt['case_id'])
    if sha256(case_folder / 'bankruptcy-complete.json') != receipt['case_receipt_sha256']:
        raise ValueError('Bankruptcy study source case changed')
    key = hashlib.sha256(('UCI365:original-arff:' + case['reference']['sha256'] + ':horizon:' + str(receipt['horizon'])).encode()).hexdigest()
    if receipt['lineage_key'] != key:
        raise ValueError('Bankruptcy source/horizon lineage changed')
    reservation = read_json(contained(root, 'artifacts/private/bankruptcy-study-registry/' + key + '/reservation.json'))
    if (reservation['study_id'] != identifier or reservation['lineage_key'] != key
            or reservation['horizon'] != receipt['horizon'] or reservation['original_zip_sha256'] != case['reference']['sha256']):
        raise ValueError('Bankruptcy holdout reservation changed')
    expected = {'run-start.json', 'protocol.json', 'support.json', 'partitions.parquet'}
    if set(receipt['files']) != expected:
        raise ValueError('Bankruptcy study evidence population changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('Bankruptcy study evidence bytes changed')
    if read_json(folder / 'protocol.json') != PROTOCOL:
        raise ValueError('Bankruptcy frozen protocol changed')
    start = read_json(folder / 'run-start.json')
    if any(start[key] != receipt[key] for key in ('study_id', 'case_id', 'horizon', 'case_receipt_sha256', 'lineage_key', 'methods')):
        raise ValueError('Bankruptcy study start/completion differs')
    table = pq.read_table(folder / 'partitions.parquet')
    assignments = table.to_pylist()
    if (table.schema != PARTITION_SCHEMA or len(assignments) != receipt['rows']
            or len({row['source_row_ordinal'] for row in assignments}) != len(assignments)
            or any(row['partition'] not in ROLES or row['source_bankruptcy_label'] not in (0, 1)
                   or not re.fullmatch(r'[0-9a-f]{64}', row['feature_group_id']) for row in assignments)
            or partition_support(assignments) != receipt['support']):
        raise ValueError('Bankruptcy partition support changed')
    groups = defaultdict(set)
    for row in assignments:
        groups[row['feature_group_id']].add(row['partition'])
    if len(groups) != receipt['exact_feature_groups'] or any(len(roles) != 1 for roles in groups.values()):
        raise ValueError('Bankruptcy groups overlap partitions')
    summary = next(item for item in case['horizons'] if item['forecast_horizon_years'] == receipt['horizon'])
    if (summary['rows'] != receipt['rows'] or summary['positive'] != sum(row['source_bankruptcy_label'] for row in assignments)
            or read_json(folder / 'support.json')['support'] != receipt['support']):
        raise ValueError('Bankruptcy source target/support mismatch')
    return folder, receipt


class RatioEncoder:
    def __init__(self):
        self.state = None

    @staticmethod
    def matrix(rows):
        if any(type(row[name]) not in (int, float, type(None)) or
               row[name] is not None and not math.isfinite(row[name]) for row in rows for name in FEATURES):
            raise ValueError('Finite numeric values or NULL required; booleans are rejected')
        matrix = np.asarray([[np.nan if row[name] is None else row[name] for name in FEATURES] for row in rows], dtype=float)
        return matrix.reshape((len(rows), 64))

    def fit(self, rows):
        if self.state is not None or not rows or any(row.get('partition') != 'train' for row in rows):
            raise ValueError('Fit one new ratio encoder on train rows only')
        raw = self.matrix(rows)
        medians, empty = [], []
        for i, name in enumerate(FEATURES):
            values = sorted(raw[~np.isnan(raw[:, i]), i])
            medians.append(float(values[(len(values)-1)//2]/2 + values[len(values)//2]/2) if values else 0.0)
            if not values:
                empty.append(name)
        transformed = np.arcsinh(np.where(np.isnan(raw), medians, raw))
        means, scales = transformed.mean(axis=0), transformed.std(axis=0)
        scales[scales == 0] = 1
        self.state = {'version': PROTOCOL['version'], 'features': list(FEATURES),
            'feature_names': [name + '_train_scaled_asinh' for name in FEATURES] + [name + '_missing' for name in FEATURES],
            'medians': medians, 'means': means.tolist(), 'scales': scales.tolist(),
            'all_missing_train_features': empty, 'fit_partition': 'train', 'train_rows': len(rows)}
        return self

    def transform(self, rows):
        if self.state is None:
            raise ValueError('Fit or restore a reviewed ratio encoder first')
        state = self.state
        if (state['version'] != PROTOCOL['version'] or state['features'] != list(FEATURES)
                or any(len(state[key]) != 64 or any(type(value) not in (int, float) or not math.isfinite(value)
                    for value in state[key]) for key in ('medians', 'means', 'scales'))
                or any(value <= 0 for value in state['scales']) or state['fit_partition'] != 'train'):
            raise ValueError('Invalid serialized train-only ratio encoder')
        raw = self.matrix(rows)
        missing = np.isnan(raw)
        matrix = np.concatenate(((np.arcsinh(np.where(missing, state['medians'], raw))-state['means']) / state['scales'],
                                 missing.astype(float)), axis=1)
        if not np.isfinite(matrix).all():
            raise ValueError('Nonfinite encoded bankruptcy features')
        return matrix


def prepare_features(root, study_id):
    study_folder, study = verify_study(root, study_id)
    digest, frozen_methods = sha256(study_folder / 'study-complete.json'), methods()
    case_folder = contained(root, 'artifacts/private/' + study['case_id'])
    identifier = 'bankruptcy-features-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    output.mkdir(parents=True)
    write_new(output / 'access-start.json', {'study_id': study_id, 'study_receipt_sha256': digest,
        'methods': frozen_methods, 'allowed_roles': list(DEVELOPMENT), 'started_at': timestamp(),
        'final_test_predictors_selected_for_encoding': False})
    with duckdb.connect() as db:
        db.read_parquet(str(case_folder / 'financial-statements.parquet')).create_view('facts')
        db.read_parquet(str(study_folder / 'partitions.parquet')).create_view('partitions')
        fields = ','.join('f."' + name + '"' for name in FEATURES)
        rows = db.execute('SELECT p.source_row_ordinal, p.feature_group_id, p.partition, p.source_bankruptcy_label, ' + fields +
            ' FROM partitions p JOIN facts f ON f.source_row_ordinal=p.source_row_ordinal '
            "WHERE p.partition IN ('train','calibration','validation') AND f.forecast_horizon_years=? "
            'ORDER BY p.source_row_ordinal', [study['horizon']]).to_arrow_table().to_pylist()
    if any(row['partition'] not in DEVELOPMENT for row in rows) or len(rows) != sum(study['support'][role]['rows'] for role in DEVELOPMENT):
        raise ValueError('Development query returned incorrect population')
    encoder = RatioEncoder().fit([row for row in rows if row['partition'] == 'train'])
    matrix = encoder.transform(rows)
    write_new(output / 'encoder.json', encoder.state)
    restored = RatioEncoder()
    restored.state = read_json(output / 'encoder.json')
    if not np.array_equal(matrix, restored.transform(rows)):
        raise ValueError('Serialized ratio encoder predictions differ')
    records = [{**{name: row[name] for name in PARTITION_SCHEMA.names},
                **dict(zip(FEATURE_COLUMNS, values.tolist(), strict=True))} for row, values in zip(rows, matrix, strict=True)]
    schema = pa.schema([*PARTITION_SCHEMA, *[pa.field(name, pa.float64()) for name in FEATURE_COLUMNS]])
    table = pa.Table.from_pylist(records, schema=schema)
    pq.write_table(table, output / 'development.parquet', compression='zstd')
    if not pq.read_table(output / 'development.parquet').equals(table):
        raise ValueError('Development features roundtrip differs')
    coverage = {'development_rows': len(rows), 'dimension': 128, 'support': {role: study['support'][role] for role in DEVELOPMENT},
        'all_missing_train_features': encoder.state['all_missing_train_features'], 'scaling_fit_role': 'train',
        'reserved_final_rows': study['support']['final_test']['rows'], 'reserved_final_encoded_rows': 0,
        'transform_serialization_max_absolute_difference': 0.0, 'model_training_performed': False}
    write_new(output / 'coverage.json', coverage)
    verify_study(root, study_id)
    if methods() != frozen_methods or sha256(study_folder / 'study-complete.json') != digest:
        raise ValueError('Bankruptcy features lineage changed during preparation')
    receipt = {'feature_id': identifier, 'status': 'BANKRUPTCY_DEVELOPMENT_FEATURES_PREPARED',
        'study_id': study_id, 'study_receipt_sha256': digest, 'methods': frozen_methods,
        'completed_at': timestamp(), 'coverage': coverage, 'visibility': 'private', 'public_release_approved': False,
        'final_test_scored': False, 'final_test_predictors_materialized_in_development': False, 'model_training_performed': False,
        'files': {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
    write_new(output / 'features-complete.json', receipt)
    return receipt


def verify_features(root, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-features-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy feature identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'features-complete.json')
    if (receipt['feature_id'] != identifier or receipt['status'] != 'BANKRUPTCY_DEVELOPMENT_FEATURES_PREPARED'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private'
            or any(receipt[key] is not False for key in ('public_release_approved', 'final_test_scored',
                                                       'final_test_predictors_materialized_in_development', 'model_training_performed'))):
        raise ValueError('Bankruptcy feature method/qualification changed')
    study_folder, study = verify_study(root, receipt['study_id'])
    if sha256(study_folder / 'study-complete.json') != receipt['study_receipt_sha256']:
        raise ValueError('Bankruptcy features frozen study changed')
    expected = {'access-start.json', 'encoder.json', 'coverage.json', 'development.parquet'}
    if set(receipt['files']) != expected:
        raise ValueError('Bankruptcy feature evidence population changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('Bankruptcy feature evidence bytes changed')
    coverage = read_json(folder / 'coverage.json')
    if coverage != receipt['coverage'] or coverage['reserved_final_encoded_rows'] != 0:
        raise ValueError('Bankruptcy development coverage changed')
    table = pq.read_table(folder / 'development.parquet')
    rows = table.to_pylist()
    if (table.num_rows != coverage['development_rows'] or table.column_names != [*PARTITION_SCHEMA.names, *FEATURE_COLUMNS]
            or any(row['partition'] not in DEVELOPMENT for row in rows)
            or partition_support(rows) != {**coverage['support'], 'final_test': {'rows': 0, 'positive': 0, 'negative': 0, 'exact_feature_groups': 0}}):
        raise ValueError('Bankruptcy development roles/support changed')
    return folder, receipt, study_folder, study
