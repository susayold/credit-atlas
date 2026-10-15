"""Independent SQL checks before defining any bankruptcy validation partitions."""
import argparse
import json
import uuid
from pathlib import Path

import duckdb

from credit_atlas.bankruptcy import FEATURES, verify_bankruptcy
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def run(root, case_id):
    folder, case = verify_bankruptcy(root, case_id)
    digest = sha256(folder / 'bankruptcy-complete.json')
    with duckdb.connect() as db:
        db.read_parquet(str(folder / 'financial-statements.parquet')).create_view('facts')
        feature_columns = ','.join('"' + name + '"' for name in FEATURES)
        db.execute('CREATE TEMP TABLE groups AS SELECT source_subset_code, ' + feature_columns +
            ',count(*) AS records,min(source_bankruptcy_label) AS min_label,max(source_bankruptcy_label) AS max_label '
            'FROM facts GROUP BY source_subset_code,' + feature_columns)
        summaries = db.execute('''SELECT source_subset_code,
            sum(records)::BIGINT AS records, count(*) AS distinct_feature_vectors,
            sum(records-1)::BIGINT AS duplicate_excess,
            count(*) FILTER (WHERE records>1) AS duplicate_groups,
            count(*) FILTER (WHERE min_label<>max_label) AS conflicting_label_groups,
            coalesce(sum(records) FILTER (WHERE min_label<>max_label),0)::BIGINT AS records_in_conflicting_label_groups
            FROM groups GROUP BY source_subset_code ORDER BY source_subset_code''').to_arrow_table().to_pylist()
        for row, horizon in zip(summaries, case['horizons'], strict=True):
            if (row['source_subset_code'] != horizon['source_subset_code'] or row['records'] != horizon['rows']
                    or row['duplicate_excess'] != horizon['exact_feature_duplicate_excess']):
                raise ValueError('Independent SQL duplicate reconciliation failed')
        cross = db.execute('SELECT count(*) FROM (SELECT ' + feature_columns +
            ' FROM groups GROUP BY ' + feature_columns + ' HAVING count(DISTINCT source_subset_code)>1)').fetchone()[0]
        if cross != case['overlap_diagnostics']['exact_feature_vectors_present_in_multiple_subsets']:
            raise ValueError('Independent cross-subset diagnostic differs')
    verify_bankruptcy(root, case_id)
    if sha256(folder / 'bankruptcy-complete.json') != digest:
        raise ValueError('Case changed during duplicate audit')
    output = root / 'artifacts/private' / ('bankruptcy-duplicates-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    receipt = {'status': 'PASS', 'case_id': case_id, 'case_receipt_sha256': digest,
        'completed_at': timestamp(), 'method_sha256': sha256(Path(__file__)), 'horizons': summaries,
        'exact_vectors_in_multiple_subsets': cross,
        'scope': 'exact numeric vectors, NULLs grouped; does not establish firm identity or near-duplicate independence',
        'visibility': 'private', 'public_release_approved': False}
    write_new(output / 'receipt.json', receipt)
    return {'directory': str(output), **receipt}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', required=True)
    args = parser.parse_args()
    print(json.dumps(run(app_root(), args.case), indent=2))
