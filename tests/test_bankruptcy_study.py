import copy
import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.bankruptcy import FEATURES, SCHEMA
from credit_atlas import bankruptcy_study as study
from credit_atlas.workspace import write_new


def example(index, label=0, role='train'):
    return {'source_row_ordinal': index + 1, 'source_subset_code': 5, 'forecast_horizon_years': 1,
        'source_bankruptcy_label': label, 'partition': role,
        **{name: None if name == 'A37' else float(index + 1) if name == 'A1' else 1.0 for name in FEATURES}}


@pytest.fixture
def case(tmp_path, monkeypatch):
    identifier = 'bankruptcy-case-aaaaaaaaaaaa'
    folder = tmp_path / 'artifacts/private' / identifier
    folder.mkdir(parents=True)
    rows = [example(i, int(i < 300)) for i in range(1000)]
    for i in range(0, 1000, 10):
        row = dict(rows[i], source_row_ordinal=len(rows) + 1)
        rows.append(row)
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), folder / 'financial-statements.parquet')
    receipt = {'case_id': identifier, 'reference': {'sha256': 'a' * 64},
        'horizons': [{'forecast_horizon_years': 1, 'rows': len(rows), 'positive': sum(row['source_bankruptcy_label'] for row in rows)}]}
    write_new(folder / 'bankruptcy-complete.json', receipt)
    # The synthetic case isolates splitting/encoding; production source verification is separately exercised.
    monkeypatch.setattr(study, 'verify_bankruptcy', lambda root, case_id: (folder, dict(receipt, case_id=case_id)))
    return tmp_path, identifier, folder


def test_group_split_order_invariant_signed_zero_and_null_identity():
    rows = [example(i, i % 2) for i in range(100)]
    rows.append(dict(rows[0], source_row_ordinal=101))
    assignments = study.assign_groups(rows, 1)
    assert assignments == study.assign_groups(list(reversed(rows)), 1)
    first = next(row for row in assignments if row['source_row_ordinal'] == 1)
    duplicate = next(row for row in assignments if row['source_row_ordinal'] == 101)
    assert first['feature_group_id'] == duplicate['feature_group_id'] and first['partition'] == duplicate['partition']
    plus, minus, missing = example(1), example(1), example(1)
    plus['A1'], minus['A1'], missing['A1'] = 0.0, -0.0, None
    assert study.fingerprint(plus) == study.fingerprint(minus)
    assert study.fingerprint(plus) != study.fingerprint(missing)


def test_conflicting_labels_stay_in_same_group_without_dropping_rows():
    rows = [example(i, i % 2) for i in range(100)]
    rows.extend([dict(rows[0], source_row_ordinal=101, source_bankruptcy_label=1)])
    result = study.assign_groups(rows, 1)
    same = [row for row in result if row['source_row_ordinal'] in (1, 101)]
    assert len({row['partition'] for row in same}) == 1 and {row['source_bankruptcy_label'] for row in same} == {0, 1}


def test_actual_freeze_reservation_development_and_serialization(case):
    root, identifier, _ = case
    frozen = study.create_study(root, identifier)
    folder, saved = study.verify_study(root, frozen['study_id'])
    assert saved['rows'] == 1100 and saved['exact_feature_groups'] == 1000
    assert study.create_study(root, identifier)['study_id'] == saved['study_id']
    assert sum(item['rows'] for item in saved['support'].values()) == 1100
    assert all(item['positive'] >= 20 for item in saved['support'].values())
    protocol = json.loads((folder / 'protocol.json').read_text())
    assert not protocol['selection']['final_test_used_for_selection']
    assert protocol['selection']['primary'].startswith('validation Brier')
    prepared = study.prepare_features(root, saved['study_id'])
    features, receipt, _, _ = study.verify_features(root, prepared['feature_id'])
    assert receipt['coverage']['dimension'] == 128
    assert receipt['coverage']['all_missing_train_features'] == ['A37']
    matrix = pq.read_table(features / 'development.parquet').to_pylist()
    assert all(row['partition'] in study.DEVELOPMENT for row in matrix)
    assert len(matrix) + saved['support']['final_test']['rows'] == 1100
    assert len({row['source_row_ordinal'] for row in matrix}) == len(matrix)


def test_new_case_cannot_reset_original_source_horizon_reservation(case):
    root, identifier, _ = case
    study.create_study(root, identifier)
    with pytest.raises(ValueError, match='already reserved'):
        study.create_study(root, 'bankruptcy-case-bbbbbbbbbbbb')


def test_final_predictor_poison_not_selected_for_development_encoding(case):
    root, identifier, folder = case
    frozen = study.create_study(root, identifier)
    first = study.prepare_features(root, frozen['study_id'])
    saved_encoder = json.loads((root / 'artifacts/private' / first['feature_id'] / 'encoder.json').read_text())
    assignments = pq.read_table(root / 'artifacts/private' / frozen['study_id'] / 'partitions.parquet').to_pylist()
    final = {row['source_row_ordinal'] for row in assignments if row['partition'] == 'final_test'}
    rows = pq.read_table(folder / 'financial-statements.parquet').to_pylist()
    for row in rows:
        if row['source_row_ordinal'] in final:
            row['A1'] = float('nan')
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), folder / 'financial-statements.parquet')
    # Verification is mocked only in this test to isolate the SQL access boundary.
    # Production rejects changed source bytes before this point.
    second = study.prepare_features(root, frozen['study_id'])
    encoder = json.loads((root / 'artifacts/private' / second['feature_id'] / 'encoder.json').read_text())
    assert encoder == saved_encoder
    assert pq.read_table(root / 'artifacts/private' / first['feature_id'] / 'development.parquet').equals(
        pq.read_table(root / 'artifacts/private' / second['feature_id'] / 'development.parquet'))


def test_encoder_train_only_nulls_signed_extremes_and_serialized_parity():
    rows = [example(i) for i in range(4)]
    rows[0]['A1'], rows[1]['A1'], rows[2]['A1'], rows[3]['A1'] = -1e308, 1e308, 1e308, None
    encoder = study.RatioEncoder().fit(rows)
    assert encoder.state['medians'][0] == 1e308 and encoder.state['medians'][36] == 0
    assert encoder.state['all_missing_train_features'] == ['A37']
    matrix = encoder.transform(rows)
    assert matrix.shape == (4, 128) and np.isfinite(matrix).all()
    assert matrix[3, 64] == 1 and matrix[0, 100] == 1
    restored = study.RatioEncoder()
    restored.state = json.loads(json.dumps(encoder.state))
    assert np.array_equal(restored.transform(rows), matrix)
    changed = [example(10000, role='validation')]
    before = copy.deepcopy(encoder.state)
    encoder.transform(changed)
    assert encoder.state == before
    with pytest.raises(ValueError, match='train rows'):
        study.RatioEncoder().fit(changed)
    with pytest.raises(ValueError):
        encoder.fit(rows)


@pytest.mark.parametrize('value', [True, float('inf'), float('nan'), '12'])
def test_invalid_encoder_values_fail(value):
    row = example(1)
    row['A1'] = value
    with pytest.raises(ValueError):
        study.RatioEncoder().fit([row])


def test_changed_protocol_and_development_evidence_rejected(case):
    root, identifier, _ = case
    frozen = study.create_study(root, identifier)
    prepared = study.prepare_features(root, frozen['study_id'])
    path = root / 'artifacts/private' / prepared['feature_id'] / 'encoder.json'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='bytes changed'):
        study.verify_features(root, prepared['feature_id'])
    path = root / 'artifacts/private' / frozen['study_id'] / 'protocol.json'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='bytes changed'):
        study.verify_study(root, frozen['study_id'])


def test_invalid_horizon_or_mixed_population_fail():
    with pytest.raises(ValueError):
        study.assign_groups([example(1)], True)
    with pytest.raises(ValueError):
        study.assign_groups([example(1)], 2)
