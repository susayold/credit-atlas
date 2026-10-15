"""One-time frozen P3 evaluation; subsequent verification reads saved scores only."""
from __future__ import annotations

import math
import re
import sqlite3
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .bankruptcy import FEATURES
from .bankruptcy_assessment import apply_platt, probability_metrics
from .bankruptcy_freeze import verify_freeze
from .bankruptcy_study import RatioEncoder, fingerprint, verify_features
from .retail_assessment import predict_json
from .workspace import contained, read_json, sha256, timestamp, write_new

FINAL_SETTINGS = {'version': 'uci365-one-time-frozen-random-group-final-v1',
    'replicates': 1000, 'seed': 3652, 'confidence_level': .95,
    'method': 'unstratified exact-feature-group percentile bootstrap of saved chosen-model probabilities',
    'conditioning': 'fixed trained model and observed final exact-feature groups, not retraining or firm sampling',
    'single_class_draws': 'exclude/report; require >=95percent valid draws',
    'selection_uses_final': False, 'threshold_selection_performed': False,
    'settings_set_before_final_predictor_query': True, 'production_qualified': False}
METRICS = ('roc_auc', 'average_precision', 'brier_score', 'log_loss')


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in
        ('bankruptcy_holdout', 'bankruptcy_freeze', 'bankruptcy_assessment', 'bankruptcy_study', 'retail_assessment', 'workspace')}


def ledger_path(root):
    return contained(root, 'artifacts/private/bankruptcy-holdout-access.sqlite')


def claim(ledger, lineage_key, frozen, evaluation_id, freeze_digest):
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(ledger, timeout=30) as db:
        db.execute('CREATE TABLE IF NOT EXISTS evaluations (lineage_key TEXT PRIMARY KEY, study_id TEXT NOT NULL, '
            'freeze_id TEXT NOT NULL, freeze_digest TEXT NOT NULL, evaluation_id TEXT NOT NULL, '
            'status TEXT NOT NULL, started_at TEXT NOT NULL)')
        try:
            db.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,'started',?)", (lineage_key,
                frozen['study_id'], frozen['freeze_id'], freeze_digest, evaluation_id, timestamp()))
        except sqlite3.IntegrityError as error:
            raise ValueError('Original-source/horizon final already claimed; read saved evidence, do not rescore or reset') from error


def finish(ledger, key, evaluation_id, status):
    if status not in {'completed', 'failed'}:
        raise ValueError('Unsupported final ledger transition')
    with sqlite3.connect(ledger, timeout=30) as db:
        changed = db.execute("UPDATE evaluations SET status=? WHERE lineage_key=? AND evaluation_id=? AND status='started'",
                             (status, key, evaluation_id)).rowcount
        if changed != 1:
            raise ValueError('Final access ledger no longer matches this evaluation')


def ledger_record(ledger, key):
    if not ledger.is_file():
        raise ValueError('Final consumption ledger missing')
    # Read-only connection: verifying a result cannot create or reopen the ledger.
    with sqlite3.connect(ledger.resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        result = db.execute('SELECT * FROM evaluations WHERE lineage_key=?', (key,)).fetchone()
    if result is None:
        raise ValueError('Final evaluation not registered')
    return dict(result)


def frozen_transform(state, rows):
    if not rows or any(row.get('partition') != 'final_test' for row in rows):
        raise ValueError('Frozen final transform requires final_test rows only')
    restored = RatioEncoder()
    restored.state = state
    restored.transform([])  # validates frozen state; does not fit or access predictors
    raw = np.empty((len(rows), 64), dtype=float)
    missing = np.empty((len(rows), 64), dtype=float)
    for i, row in enumerate(rows):
        for j, name in enumerate(FEATURES):
            value = row[name]
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError('Finite original ratios or NULL required')
            missing[i, j] = float(value is None)
            raw[i, j] = state['medians'][j] if value is None else value
    numeric = (np.arcsinh(raw)-state['means'])/state['scales']
    matrix = np.concatenate((numeric, missing), axis=1)
    if not np.isfinite(matrix).all():
        raise ValueError('Invalid frozen final feature matrix')
    return matrix


def check_codec(state):
    probes = [{'partition': 'final_test', **{name: None if k == 0 else state['medians'][j]+k
               for j, name in enumerate(FEATURES)}} for k in (-2, -1, 0, 1, 2)]
    original = RatioEncoder()
    original.state = state
    if not np.array_equal(frozen_transform(state, probes), original.transform(probes)):
        raise ValueError('Frozen codec differs from development transform')


def uncertainty(scores):
    y = np.asarray([row['source_bankruptcy_label'] for row in scores], dtype=np.int8)
    p = np.asarray([row['probability'] for row in scores], dtype=float)
    groups = np.asarray([row['feature_group_id'] for row in scores])
    members = [np.flatnonzero(groups == key) for key in sorted(set(groups.tolist()))]
    rng = np.random.default_rng(FINAL_SETTINGS['seed'])
    records, skipped, row_counts = [], 0, []
    for draw in range(FINAL_SETTINGS['replicates']):
        indices = np.concatenate([members[index] for index in rng.integers(0, len(members), size=len(members))])
        if len(set(y[indices].tolist())) != 2:
            skipped += 1
            continue
        metrics = probability_metrics(y[indices], p[indices])
        records.append({'draw': draw, **{name: metrics[name] for name in METRICS}})
        row_counts.append(len(indices))
    if len(records) < .95*FINAL_SETTINGS['replicates']:
        raise ValueError('Insufficient two-class final bootstrap draws')
    point = probability_metrics(y, p)
    summary = {'final_rows': len(scores), 'exact_feature_groups': len(members), 'valid_replicates': len(records),
        'skipped_single_class': skipped, 'min_draw_rows': min(row_counts), 'max_draw_rows': max(row_counts),
        'intervals': {name: {'point': point[name], 'lower': float(np.quantile([row[name] for row in records], .025)),
            'upper': float(np.quantile([row[name] for row in records], .975))} for name in METRICS}}
    return summary, records


def evaluate_holdout(root, freeze_id):
    bundle, frozen = verify_freeze(root, freeze_id)
    _, _, study_folder, study = verify_features(root, frozen['feature_id'])
    state, model = read_json(bundle / 'encoder.json'), read_json(bundle / 'model.json')
    check_codec(state)
    digest, frozen_methods = sha256(bundle / 'freeze-complete.json'), methods()
    identifier = 'bankruptcy-holdout-' + uuid.uuid4().hex[:12]
    output = contained(root, 'artifacts/private/' + identifier)
    key, ledger = study['lineage_key'], ledger_path(root)
    # Atomic source/horizon claim before final predictor query. Failed access stays consumed.
    claim(ledger, key, frozen, identifier, digest)
    provenance = {'evaluation_id': identifier, 'freeze_id': freeze_id, 'freeze_receipt_sha256': digest,
        'study_id': study['study_id'], 'lineage_key': key, 'candidate': frozen['candidate'], 'methods': frozen_methods,
        'partition': 'final_test', 'visibility': 'private', 'public_release_approved': False,
        'model_training_performed': False, 'model_selection_performed': False, 'threshold_selection_performed': False,
        'entity_disjointness_verified': False, 'temporal_out_of_time': False, 'production_qualified': False}
    try:
        output.mkdir(parents=True)
        write_new(output / 'access-start.json', {**provenance, 'started_at': timestamp(), 'codec_parity': 'PASS'})
        write_new(output / 'settings.json', FINAL_SETTINGS)
        case_folder = contained(root, 'artifacts/private/' + study['case_id'])
        with duckdb.connect() as db:
            db.read_parquet(str(case_folder / 'financial-statements.parquet')).create_view('facts')
            db.read_parquet(str(study_folder / 'partitions.parquet')).create_view('partitions')
            fields = ','.join('f."' + name + '"' for name in FEATURES)
            cursor = db.execute('SELECT p.source_row_ordinal,p.feature_group_id,p.partition,f.source_bankruptcy_label,' + fields +
                ' FROM facts f JOIN partitions p USING(source_row_ordinal) '
                "WHERE p.partition='final_test' AND f.forecast_horizon_years=? ORDER BY p.source_row_ordinal",
                [study['horizon']])
            names = [column[0] for column in cursor.description]
            rows = [dict(zip(names, batch_row, strict=True))
                    for batch in iter(lambda: cursor.fetchmany(256), []) for batch_row in batch]
        y = np.asarray([row['source_bankruptcy_label'] for row in rows], dtype=np.int8)
        expected = study['support']['final_test']
        if (len(rows) != expected['rows'] or len({row['source_row_ordinal'] for row in rows}) != len(rows)
                or int(y.sum()) != expected['positive'] or len(rows)-int(y.sum()) != expected['negative']
                or len({row['feature_group_id'] for row in rows}) != expected['exact_feature_groups']
                or any(fingerprint(row) != row['feature_group_id'] for row in rows)
                or min(int((y == value).sum()) for value in (0, 1)) < 20):
            raise ValueError('Final source identities/groups/support changed')
        probabilities = predict_json(model, frozen_transform(state, rows))
        if frozen['candidate'].endswith('_platt'):
            probabilities = apply_platt(probabilities, read_json(bundle / 'platt.json'))
        metrics = probability_metrics(y, probabilities)
        metrics['scope'] = 'reserved random source-statement final; unknown firm overlap; not OOT/production loan PD'
        scores = [{key: row[key] for key in ('source_row_ordinal', 'feature_group_id', 'source_bankruptcy_label')}
                  | {'probability': float(p)} for row, p in zip(rows, probabilities, strict=True)]
        pq.write_table(pa.Table.from_pylist(scores), output / 'private-final-scores.parquet', compression='zstd')
        saved = pq.read_table(output / 'private-final-scores.parquet').to_pylist()
        if saved != scores:
            raise ValueError('Saved final score roundtrip differs')
        write_new(output / 'final-metrics.json', metrics)
        intervals, draws = uncertainty(saved)
        write_new(output / 'uncertainty.json', intervals)
        pq.write_table(pa.Table.from_pylist(draws), output / 'bootstrap-draws.parquet', compression='zstd')
        write_new(output / 'verification.json', {'status': 'PASS', 'scored_rows': len(rows),
            'saved_score_roundtrip': True, 'model_refit': False, 'reselection': False, 'threshold_selection': False,
            'codec_parity': 'PASS', 'model_candidate': frozen['candidate']})
        verify_freeze(root, freeze_id)
        if methods() != frozen_methods or sha256(bundle / 'freeze-complete.json') != digest:
            raise ValueError('Final frozen model/method lineage changed during evaluation')
        receipt = {**provenance, 'status': 'BANKRUPTCY_ONE_TIME_FINAL_EVALUATED', 'completed_at': timestamp(),
            'final_test_scored': True, 'files': {path.name: sha256(path) for path in output.iterdir() if path.is_file()}}
        write_new(output / 'evaluation-complete.json', receipt)
        finish(ledger, key, identifier, 'completed')
        return receipt
    except Exception as error:
        finish(ledger, key, identifier, 'failed')
        output.mkdir(parents=True, exist_ok=True)
        write_new(output / 'evaluation-failed.json', {**provenance, 'status': 'FAILED', 'failed_at': timestamp(),
            'exception_type': type(error).__name__, 'final_access_consumed': True})
        raise


def verify_holdout(root, identifier):
    """Check saved outputs and frozen lineage; never query/transform/rescore final predictors."""
    if not isinstance(identifier, str) or not re.fullmatch(r'bankruptcy-holdout-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid bankruptcy final evaluation identifier')
    folder = contained(root, 'artifacts/private/' + identifier)
    receipt = read_json(folder / 'evaluation-complete.json')
    if (receipt['evaluation_id'] != identifier or receipt['status'] != 'BANKRUPTCY_ONE_TIME_FINAL_EVALUATED'
            or receipt['methods'] != methods() or receipt['visibility'] != 'private' or receipt['final_test_scored'] is not True
            or receipt['partition'] != 'final_test' or any(receipt[key] is not False for key in ('public_release_approved',
                'model_training_performed', 'model_selection_performed', 'threshold_selection_performed',
                'entity_disjointness_verified', 'temporal_out_of_time', 'production_qualified'))):
        raise ValueError('Final evaluation method/qualification changed')
    bundle, frozen = verify_freeze(root, receipt['freeze_id'])
    if (sha256(bundle / 'freeze-complete.json') != receipt['freeze_receipt_sha256']
            or frozen['study_id'] != receipt['study_id'] or frozen['lineage_key'] != receipt['lineage_key']
            or frozen['candidate'] != receipt['candidate']):
        raise ValueError('Final evaluation frozen lineage changed')
    record = ledger_record(ledger_path(root), receipt['lineage_key'])
    if (record['status'] != 'completed' or record['evaluation_id'] != identifier or record['study_id'] != receipt['study_id']
            or record['freeze_id'] != receipt['freeze_id'] or record['freeze_digest'] != receipt['freeze_receipt_sha256']):
        raise ValueError('Final consumption ledger differs from saved evaluation')
    expected_files = {'access-start.json', 'settings.json', 'private-final-scores.parquet', 'final-metrics.json',
                      'uncertainty.json', 'bootstrap-draws.parquet', 'verification.json'}
    if set(receipt['files']) != expected_files:
        raise ValueError('Final evidence population changed')
    for name, digest in receipt['files'].items():
        if sha256(contained(folder, name)) != digest:
            raise ValueError('Final evaluation evidence bytes changed')
    if read_json(folder / 'settings.json') != FINAL_SETTINGS:
        raise ValueError('Final uncertainty settings changed')
    _, _, study_folder, study = verify_features(root, frozen['feature_id'])
    targets = [(row['source_row_ordinal'], row['feature_group_id'], row['source_bankruptcy_label'])
               for row in pq.read_table(study_folder / 'partitions.parquet').to_pylist() if row['partition'] == 'final_test']
    scores = pq.read_table(folder / 'private-final-scores.parquet').to_pylist()
    if [(row['source_row_ordinal'], row['feature_group_id'], row['source_bankruptcy_label']) for row in scores] != targets:
        raise ValueError('Saved final score identities/labels/groups differ from frozen partitions')
    calculated = probability_metrics([row['source_bankruptcy_label'] for row in scores], [row['probability'] for row in scores])
    calculated['scope'] = 'reserved random source-statement final; unknown firm overlap; not OOT/production loan PD'
    metrics, summary = read_json(folder / 'final-metrics.json'), read_json(folder / 'uncertainty.json')
    if calculated != metrics or len(scores) != study['support']['final_test']['rows']:
        raise ValueError('Saved final metrics/support do not reconcile')
    draws = pq.read_table(folder / 'bootstrap-draws.parquet').to_pylist()
    if (len(draws) != summary['valid_replicates'] or len({row['draw'] for row in draws}) != len(draws)
            or any(type(row['draw']) is not int or not 0 <= row['draw'] < FINAL_SETTINGS['replicates'] for row in draws)
            or len(draws) < .95*FINAL_SETTINGS['replicates']
            or summary['valid_replicates'] + summary['skipped_single_class'] != FINAL_SETTINGS['replicates']
            or summary['final_rows'] != len(scores) or summary['exact_feature_groups'] != study['support']['final_test']['exact_feature_groups']):
        raise ValueError('Final saved bootstrap population differs')
    for name in METRICS:
        expected = {'point': metrics[name], 'lower': float(np.quantile([row[name] for row in draws], .025)),
                    'upper': float(np.quantile([row[name] for row in draws], .975))}
        if expected != summary['intervals'][name]:
            raise ValueError('Final saved uncertainty interval differs from draws')
    return folder, receipt, metrics, summary
