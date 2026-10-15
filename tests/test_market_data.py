from decimal import Decimal
import json

import pyarrow.parquet as pq
import pytest

from credit_atlas import market_data
from credit_atlas.public_sources import catalog, profile
from credit_atlas.workspace import sha256, timestamp, write_new


@pytest.fixture
def market_acquisition(tmp_path, monkeypatch):
    identifiers = {'fred-' + series.lower() for series in market_data.SERIES}
    specs = [item for item in catalog() if item['source_id'] in identifiers]
    monkeypatch.setattr('credit_atlas.public_suite.catalog', lambda: specs)
    values = {'DGS2': [('2026-01-02', '2.00'), ('2026-01-05', '.'), ('2026-01-06', '2.10')],
        'DGS10': [('2026-01-02', '3.25'), ('2026-01-05', '3.50'), ('2026-01-06', '')],
        'DGS30': [('2026-01-02', '4.00'), ('2026-01-06', '4.30')],
        'BAMLC0A0CM': [('2026-01-02', '1.10'), ('2026-01-03', '1.20'), ('2026-01-05', '')],
        'MORTGAGE30US': [('2026-01-01', '6.00'), ('2026-01-08', '6.20')]}
    identifier = 'suite-cccccccccccc'
    source = tmp_path / 'data/private/public-suite' / identifier
    source.mkdir(parents=True)
    receipts = []
    for spec in specs:
        series = spec['source_id'].removeprefix('fred-').upper()
        path = source / (spec['source_id'] + '.csv')
        path.write_text('observation_date,' + series + '\n' +
                        ''.join(day + ',' + value + '\n' for day, value in values[series]))
        receipt = {**spec, 'status': 'DOWNLOADED_AND_PROFILED', 'file': path.name,
            'sha256': sha256(path), 'bytes': path.stat().st_size, 'retrieved_at': timestamp(),
            'profile': profile(path, spec), 'model_qualified': False, 'public_release_approved': False}
        receipts.append(receipt)
        write_new(source / (spec['source_id'] + '-receipt.json'), receipt)
    write_new(source / 'acquisition-complete.json', {'schema_version': 1, 'status': 'COMPLETE',
        'sources': receipts, 'failed_sources': [], 'visibility': 'private',
        'public_release_approved': False, 'model_training_performed': False})
    return tmp_path, identifier, source


def test_actual_adapter_native_alignment_and_monthly_scope(market_acquisition):
    root, identifier, _ = market_acquisition
    result = market_data.prepare_market(root, identifier)
    folder, saved = market_data.verify_market(root, result['case_id'])
    assert saved['native_records'] == 13 and saved['monthly_records'] == 5
    assert all(row['differing_rows'] == 0 for row in saved['independent_reconciliations'])
    rows = pq.read_table(folder / 'aligned-daily-context.parquet').to_pylist()
    assert len(rows) == 4 and all(row['observation_date'].isoformat() != '2026-01-08' for row in rows)
    first = rows[0]
    assert first['slope_10y_2y_bps'] == Decimal('125')
    assert first['corporate_index_oas_bps'] == Decimal('110')
    saturday = rows[1]
    assert saturday['bamlc0a0cm_native_present'] and saturday['corporate_index_oas_bps'] == 120
    assert not saturday['dgs2_native_present'] and saturday['dgs2_percent'] is None
    monday = rows[2]
    assert monday['dgs2_native_present'] and monday['dgs2_percent'] is None
    assert not monday['dgs30_native_present'] and monday['slope_10y_2y_bps'] is None
    monthly = pq.read_table(folder / 'monthly-context.parquet').to_pylist()
    dgs10 = next(row for row in monthly if row['series'] == 'DGS10')
    assert dgs10['last_known_date'].isoformat() == '2026-01-05' and dgs10['last_known_percent'] == Decimal('3.5')
    assert dgs10['known_rows'] == 2 and dgs10['missing_rows'] == 1


def test_modified_market_raw_and_output_rejected(market_acquisition):
    root, identifier, source = market_acquisition
    result = market_data.prepare_market(root, identifier)
    folder, _ = market_data.verify_market(root, result['case_id'])
    output = folder / 'aligned-daily-context.parquet'
    original = output.read_bytes()
    output.write_bytes(original + b'changed')
    with pytest.raises(ValueError, match='output bytes'):
        market_data.verify_market(root, result['case_id'])
    output.write_bytes(original)
    path = source / 'fred-dgs2.csv'
    path.write_text(path.read_text().replace('2.00', '9.00'))
    with pytest.raises(ValueError, match='source bytes'):
        market_data.verify_market(root, result['case_id'])


@pytest.mark.parametrize('body', ['2026-01-02,NaN', '2026-01-02,Infinity',
    '2026-01-02,1.1234567', '2026-01-02,1\n2026-01-02,2', '2026-01-03,1\n2026-01-02,2'])
def test_invalid_native_values_or_grain_rejected(tmp_path, body):
    path = tmp_path / 'rates.csv'
    path.write_text('observation_date,DGS2\n' + body + '\n')
    with pytest.raises(ValueError):
        market_data.native_rows(path, 'DGS2')


def test_zero_signed_values_and_missing_sentinels_stay_distinct(tmp_path):
    path = tmp_path / 'rates.csv'
    path.write_text('observation_date,DGS2\n2026-01-02,0\n2026-01-05,-0.50\n2026-01-06,.\n2026-01-07,\n')
    rows = market_data.native_rows(path, 'DGS2')
    assert [row['value_percent'] for row in rows] == [Decimal(0), Decimal('-.5'), None, None]
    assert [row['source_value'] for row in rows][-2:] == ['.', '']


def test_documented_discontinuation_conflict_preserves_raw_but_quarantines_usable_value(tmp_path):
    path = tmp_path / 'dgs30.csv'
    path.write_text('observation_date,DGS30\n2002-02-15,5.5\n2002-02-18,5.6\n2006-02-08,5.7\n2006-02-09,5.8\n')
    rows = market_data.native_rows(path, 'DGS30')
    assert [row['documented_discontinuation_conflict'] for row in rows] == [False, True, True, False]
    assert [row['value_percent'] for row in rows] == [Decimal('5.5'), None, None, Decimal('5.8')]
    assert [row['source_value_percent'] for row in rows] == [Decimal('5.5'), Decimal('5.6'), Decimal('5.7'), Decimal('5.8')]
    assert rows[1]['source_value'] == '5.6'


def test_quarantine_propagates_to_alignment_and_monthly_known_counts(market_acquisition):
    root, identifier, source = market_acquisition
    raw = source / 'fred-dgs30.csv'
    raw.write_text(raw.read_text().replace('observation_date,DGS30\n', 'observation_date,DGS30\n2003-01-02,4.2\n'))
    batch_path = source / 'acquisition-complete.json'
    batch = json.loads(batch_path.read_text())
    item = next(item for item in batch['sources'] if item['source_id'] == 'fred-dgs30')
    item.update(sha256=sha256(raw), bytes=raw.stat().st_size, profile=profile(raw, item))
    batch_path.write_text(json.dumps(batch))
    (source / 'fred-dgs30-receipt.json').write_text(json.dumps(item))
    result = market_data.prepare_market(root, identifier)
    folder, receipt = market_data.verify_market(root, result['case_id'])
    assert receipt['quarantined_records'] == 1 and receipt['historical_treasury_semantics_qualified'] is False
    daily = pq.read_table(folder / 'aligned-daily-context.parquet').to_pylist()[0]
    assert daily['dgs30_native_present'] and daily['dgs30_quarantined']
    assert daily['dgs30_source_value_percent'] == Decimal('4.2') and daily['dgs30_percent'] is None
    assert not daily['treasury_three_tenors_known']
    month = next(row for row in pq.read_table(folder / 'monthly-context.parquet').to_pylist() if row['month'].year == 2003)
    assert month['known_rows'] == 0 and month['quarantined_rows'] == 1 and month['source_missing_rows'] == 0
