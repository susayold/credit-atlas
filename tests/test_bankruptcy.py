import csv
import json
import zipfile

import pyarrow.parquet as pq
import pytest

from credit_atlas import bankruptcy
from credit_atlas.public_sources import catalog, profile
from credit_atlas.workspace import sha256, timestamp, write_new


def metadata():
    return {'status': 200, 'data': {'uci_id': 365, 'name': 'Polish Companies Bankruptcy',
        'num_instances': 10503, 'num_features': 65, 'target_col': ['class'],
        'data_url': 'https://archive.ics.uci.edu/static/public/365/data.csv',
        'variables': [{'name': name} for name in bankruptcy.HEADER],
        'additional_info': {'variable_info': '\n'.join('X' + str(i) + '\tdefinition ' + str(i) for i in range(1, 65))}}}


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(bankruptcy.HEADER)
        writer.writerows(rows)


def fixture_rows():
    return [[str(code), *(['-1200000', '0', 'NaN'] + ['1.25'] * 61), str(label)]
            for code in range(1, 6) for label in (0, 1)]


def write_reference(path, rows):
    with zipfile.ZipFile(path, 'w') as archive:
        for code in range(1, 6):
            text = '@relation reference\n' + ''.join('@attribute Attr' + str(i) + ' numeric\n' for i in range(1, 65))
            text += '@attribute class {0,1}\n@data\n'
            text += ''.join(','.join('?' if token == 'NaN' else token for token in row[1:]) + '\n'
                            for row in rows if row[0] == str(code))
            archive.writestr(str(code) + 'year.arff', text)


@pytest.fixture
def acquisition(tmp_path, monkeypatch):
    specs = [item for item in catalog() if item['source_id'] in {'uci-bankruptcy', 'uci-bankruptcy-metadata'}]
    monkeypatch.setattr('credit_atlas.public_suite.catalog', lambda: specs)
    monkeypatch.setattr(bankruptcy, 'SOURCE_COUNTS', {code: (2, 1) for code in range(1, 6)})
    suite = 'suite-dddddddddddd'
    source = tmp_path / 'data/private/public-suite' / suite
    source.mkdir(parents=True)
    rows = fixture_rows()
    write_csv(source / 'uci-bankruptcy.csv', rows)
    write_new(source / 'uci-bankruptcy-metadata.json', metadata())
    receipts = []
    for spec in specs:
        path = source / (spec['source_id'] + '.' + spec['kind'])
        item = {**spec, 'status': 'DOWNLOADED_AND_PROFILED', 'file': path.name,
            'sha256': sha256(path), 'bytes': path.stat().st_size, 'retrieved_at': timestamp(),
            'profile': profile(path, spec), 'model_qualified': False, 'public_release_approved': False}
        receipts.append(item)
        write_new(source / (spec['source_id'] + '-receipt.json'), item)
    write_new(source / 'acquisition-complete.json', {'schema_version': 1, 'status': 'COMPLETE',
        'sources': receipts, 'failed_sources': [], 'visibility': 'private',
        'public_release_approved': False, 'model_training_performed': False})
    reference = 'polish-reference-dddddddddddd'
    folder = tmp_path / 'data/private' / reference
    folder.mkdir()
    path = folder / 'original-arff.zip'
    write_reference(path, rows)
    write_new(folder / 'receipt.json', {'reference_id': reference, 'url': bankruptcy.REFERENCE_URL,
        'http_status': 200, 'file': path.name, 'sha256': sha256(path), 'bytes': path.stat().st_size,
        'members': sorted(bankruptcy.REFERENCE_FILES), 'visibility': 'private', 'public_release_approved': False})
    return tmp_path, suite, reference, source


def test_horizons_raw_missing_extremes_and_independent_reference(acquisition):
    root, suite, reference, _ = acquisition
    result = bankruptcy.prepare_bankruptcy(root, suite, reference)
    folder, saved = bankruptcy.verify_bankruptcy(root, result['case_id'])
    assert saved['rows'] == 10 and saved['independent_csv_differing_rows'] == 0
    assert all(item['unexplained_numeric_differences'] == 0 for item in saved['original_arff_audits'])
    assert saved['csv_arff_rounded_numeric_cells'] == 0
    facts = pq.read_table(folder / 'financial-statements.parquet').to_pylist()
    assert [row['forecast_horizon_years'] for row in facts] == [5, 5, 4, 4, 3, 3, 2, 2, 1, 1]
    assert facts[0]['A1'] == -1200000 and facts[0]['A2'] == 0 and facts[0]['A3'] is None
    assert [row['source_row_ordinal'] for row in facts] == list(range(1, 11))
    quality = pq.read_table(folder / 'feature-quality.parquet').to_pylist()
    assert len(quality) == 320
    assert quality[0]['abs_over_1e6'] == 2 and quality[0]['negative'] == 2
    assert quality[2]['known'] == 0 and quality[2]['median'] is None
    assert saved['overlap_diagnostics']['exact_feature_vectors_present_in_multiple_subsets'] == 1
    assert saved['overlap_diagnostics']['rows_in_cross_subset_exact_vectors'] == 10
    assert saved['horizons'][0]['exact_feature_duplicate_excess'] == 1
    contract = json.loads((folder / 'contract.json').read_text())
    assert not contract['source_year_is_calendar_year'] and not contract['pool_horizons_allowed']
    assert not contract['entity_overlap_verified'] and not contract['imputation_performed']
    assert contract['feature_cards'][0]['original_attribute'] == 'Attr1'


@pytest.mark.parametrize('field,value', [('year', '2005'), ('year', '0'), ('class', '2'),
    ('A1', ''), ('A1', 'inf'), ('A1', '1e999'), ('A1', '?'), ('A1', 'nan')])
def test_invalid_source_codes_or_values_fail(tmp_path, field, value):
    row = fixture_rows()[0]
    row[bankruptcy.HEADER.index(field)] = value
    path = tmp_path / 'raw.csv'
    write_csv(path, [row])
    with pytest.raises(ValueError):
        bankruptcy.canonical_rows(path, metadata())


def test_original_reference_value_mismatch_fails(tmp_path):
    rows = fixture_rows()
    path = tmp_path / 'data.csv'
    write_csv(path, rows)
    canonical = bankruptcy.canonical_rows(path, metadata())
    rows[0][1] = '11.5'
    archive = tmp_path / 'original.zip'
    write_reference(archive, rows)
    with pytest.raises(ValueError, match='values differ'):
        bankruptcy.audit_reference(canonical, archive)


def test_scientific_rounding_preserves_original_and_csv_versions(tmp_path):
    rows = fixture_rows()
    rows[0][1] = '243000'
    rows[1][1] = '-0.0000753'
    path = tmp_path / 'raw.csv'
    write_csv(path, rows)
    canonical = bankruptcy.canonical_rows(path, metadata())
    rows[0][1] = '2.425e+005'
    rows[1][1] = '-7.525e-005'
    archive = tmp_path / 'original.zip'
    write_reference(archive, rows)
    original, audits, differences = bankruptcy.audit_reference(canonical, archive)
    assert original[0]['A1'] == 242500 and canonical[0]['A1'] == 243000
    assert original[1]['A1'] == -.00007525 and canonical[1]['A1'] == -.0000753
    assert audits[0]['rounded_numeric_cells'] == 2
    assert differences[0]['original_arff_token'] == '2.425e+005'
    assert differences[0]['csv_value'] == 243000


def test_reference_archive_scope_rejects_extra_or_traversal_member(tmp_path):
    path = tmp_path / 'original.zip'
    write_reference(path, fixture_rows())
    with zipfile.ZipFile(path, 'a') as archive:
        archive.writestr('../other.arff', 'data')
    with pytest.raises(ValueError, match='members'):
        bankruptcy._members(path)


@pytest.mark.parametrize('altered', ['source', 'output', 'reference', 'qualification'])
def test_changed_case_evidence_rejected(acquisition, altered):
    root, suite, reference, source = acquisition
    result = bankruptcy.prepare_bankruptcy(root, suite, reference)
    folder = root / 'artifacts/private' / result['case_id']
    if altered == 'source':
        with (source / 'uci-bankruptcy.csv').open('a') as stream:
            stream.write('\n')
    elif altered == 'output':
        with (folder / 'financial-statements.parquet').open('ab') as stream:
            stream.write(b'changed')
    elif altered == 'reference':
        with (root / 'data/private' / reference / 'original-arff.zip').open('ab') as stream:
            stream.write(b'changed')
    else:
        path = folder / 'bankruptcy-complete.json'
        receipt = json.loads(path.read_text())
        receipt['production_qualified'] = True
        path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        bankruptcy.verify_bankruptcy(root, result['case_id'])


def test_metadata_schema_and_definition_order_rejected(tmp_path):
    path = tmp_path / 'raw.csv'
    write_csv(path, fixture_rows())
    changed = metadata()
    changed['data']['variables'][1]['name'] = 'X1'
    with pytest.raises(ValueError, match='metadata'):
        bankruptcy.canonical_rows(path, changed)
    changed = metadata()
    changed['data']['additional_info']['variable_info'] = 'X2\tdefinition\n'
    with pytest.raises(ValueError, match='order'):
        bankruptcy.definitions(changed)
