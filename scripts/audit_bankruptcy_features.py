"""Independent DuckDB train-statistics and every-cell development-feature audit."""
import argparse
import json
import math
import uuid
from pathlib import Path

import duckdb

from credit_atlas.bankruptcy import FEATURES
from credit_atlas.bankruptcy_study import FEATURE_COLUMNS, verify_features
from credit_atlas.workspace import app_root, read_json, sha256, timestamp, write_new


def run(root, feature_id):
    folder, features, study_folder, study = verify_features(root, feature_id)
    digest = sha256(folder / 'features-complete.json')
    encoder = read_json(folder / 'encoder.json')
    source = root / 'artifacts/private' / study['case_id'] / 'financial-statements.parquet'
    with duckdb.connect() as db:
        db.read_parquet(str(source)).create_view('facts')
        db.read_parquet(str(study_folder / 'partitions.parquet')).create_view('partitions')
        db.read_parquet(str(folder / 'development.parquet')).create_view('development')
        train = " FROM facts f JOIN partitions p USING(source_row_ordinal) WHERE p.partition='train'"
        native_medians = db.execute('SELECT ' + ','.join('median(f."' + name + '")' for name in FEATURES) + train).fetchone()
        medians = [0.0 if value is None else value for value in native_medians]
        db.execute('CREATE TEMP TABLE transformed_train AS SELECT ' +
            ','.join('asinh(coalesce(f."' + name + '",?)) AS "' + name + '"' for name in FEATURES) + train, medians)
        statistics = db.execute('SELECT ' + ','.join('avg("' + name + '"),stddev_pop("' + name + '")'
                               for name in FEATURES) + ' FROM transformed_train').fetchone()
        means = [statistics[i*2] for i in range(64)]
        scales = [statistics[i*2+1] or 1.0 for i in range(64)]
        stat_error = max(abs(expected-saved) / max(1, abs(expected))
                        for values, key in ((medians, 'medians'), (means, 'means'), (scales, 'scales'))
                        for expected, saved in zip(values, encoder[key], strict=True))
        if not math.isfinite(stat_error) or stat_error > 1e-10:
            raise ValueError('Independent train median/asinh/scale audit failed')
        expressions, parameters = [], []
        for i, name in enumerate(FEATURES):
            expressions.append('(asinh(coalesce(f."' + name + '",?)) - ?)/? AS ' + FEATURE_COLUMNS[i])
            parameters.extend([medians[i], means[i], scales[i]])
        expressions.extend('CASE WHEN f."' + name + '" IS NULL THEN 1.0 ELSE 0.0 END AS ' + FEATURE_COLUMNS[i+64]
                           for i, name in enumerate(FEATURES))
        db.execute('CREATE TEMP TABLE reference AS SELECT p.source_row_ordinal,' + ','.join(expressions) +
            ' FROM facts f JOIN partitions p USING(source_row_ordinal) '
            "WHERE p.partition IN ('train','calibration','validation')", parameters)
        errors = db.execute('SELECT ' + ','.join('max(abs(r.' + name + '-d.' + name + '))' for name in FEATURE_COLUMNS) +
            ' FROM reference r JOIN development d USING(source_row_ordinal)').fetchone()
        max_error = max(errors)
        if not math.isfinite(max_error) or max_error > 1e-10:
            raise ValueError('Independent every-cell development transform differs')
        population = db.execute('SELECT count(*) FROM reference').fetchone()[0]
        if population != features['coverage']['development_rows']:
            raise ValueError('Independent development population differs')
        crossing = db.execute('SELECT count(*) FROM (SELECT feature_group_id FROM partitions '
                              'GROUP BY feature_group_id HAVING count(DISTINCT partition)>1)').fetchone()[0]
        final_encoded = db.execute("SELECT count(*) FROM development d JOIN partitions p USING(source_row_ordinal) "
                                   "WHERE p.partition='final_test'").fetchone()[0]
        missing_keys = db.execute('SELECT count(*) FROM ((SELECT source_row_ordinal FROM reference EXCEPT ALL '
            'SELECT source_row_ordinal FROM development) UNION ALL (SELECT source_row_ordinal FROM development '
            'EXCEPT ALL SELECT source_row_ordinal FROM reference))').fetchone()[0]
        if crossing or final_encoded or missing_keys:
            raise ValueError('Independent partition/holdout/population audit failed')
    verify_features(root, feature_id)
    if sha256(folder / 'features-complete.json') != digest:
        raise ValueError('Feature receipt changed during audit')
    output = root / 'artifacts/private' / ('bankruptcy-feature-audit-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    receipt = {'status': 'PASS', 'feature_id': feature_id, 'feature_receipt_sha256': digest,
        'completed_at': timestamp(), 'method_sha256': sha256(Path(__file__)),
        'development_rows': population, 'dimension': 128, 'numeric_cells_audited': population*128,
        'train_stat_max_scaled_difference': stat_error, 'encoded_max_absolute_difference': max_error,
        'tolerance': 1e-10, 'groups_crossing_partitions': crossing, 'final_test_encoded_rows': final_encoded,
        'development_key_differences': missing_keys, 'visibility': 'private', 'public_release_approved': False}
    write_new(output / 'receipt.json', receipt)
    return {'directory': str(output), **receipt}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--features', required=True)
    args = parser.parse_args()
    print(json.dumps(run(app_root(), args.features), indent=2))
