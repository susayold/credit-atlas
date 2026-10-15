import json
from decimal import Decimal

import pyarrow.parquet as pq
import pytest

from credit_atlas import bank_panel as bank
from credit_atlas.workspace import sha256, timestamp


def payload(day='20260630', **changes):
    row = dict(CERT=123, REPDTE=day, NAME='Test institution', ASSET=100_000,
               DEP=75_000, EQ=10_000, ROA=1.25, CERTCONS=0)
    row.update(changes)
    return {'meta': {'total': 1}, 'data': [{'data': row}]}


def definitions():
    return '\n'.join('      ' + field + ':\n        description: ' +
        ('annualized NETINCA ASSET5' if field == 'ROA' else
         'consolidated parent' if field == 'CERTCONS' else 'Reviewed field')
        for field in bank.FIELDS) + '\n'


@pytest.fixture
def acquired(tmp_path, monkeypatch):
    def download(url, destination):
        if url == bank.DEFINITIONS:
            content = definitions()
        elif url == bank.UNITS:
            content = '50000 thousands of dollars; DEP:[50000 TO *]'
        else:
            from urllib.parse import parse_qs, urlsplit
            query = parse_qs(urlsplit(url).query)
            day = query['filters'][0].split(':')[1]
            content = json.dumps(payload(day))
        destination.write_text(content, encoding='utf-8')
        return dict(url=url, file=destination.name, sha256=sha256(destination),
                    bytes=destination.stat().st_size, retrieved_at=timestamp())
    monkeypatch.setattr(bank, '_download', download)
    return tmp_path, bank.acquire_bank_history(tmp_path)


def test_coverage_and_peer_boundaries():
    days = bank.quarter_dates()
    assert len(days) == 42 and days[0] == '20160331' and days[-1] == '20260630'
    assert bank.asset_peer(99_999) == 'under_100m'
    assert bank.asset_peer(100_000) == '100m_to_1bn'
    assert bank.asset_peer(1_000_000) == '1bn_to_10bn'
    assert bank.asset_peer(100_000_000) == '100bn_plus'
    assert bank.asset_peer(0) == bank.asset_peer(None) == 'unknown_or_nonpositive'


def test_units_ratios_and_signed_equity():
    row = bank.normalize(payload(EQ=-10_000), '20260630')[0]
    assert row['assets_usd_thousands'] == 100_000
    assert row['equity_assets_percent'] == -10
    assert row['deposits_assets_percent'] == 75
    assert row['roa_annualized_percent'] == 1.25


def test_nulls_never_become_zero_or_defined_ratios():
    row = bank.normalize(payload(ASSET=None, EQ=None, DEP=None, ROA=None, CERTCONS=None), '20260630')[0]
    assert row['consolidating_parent_cert'] is None
    assert row['equity_assets_percent'] is None and row['deposits_assets_percent'] is None
    assert row['assets_usd_thousands'] is None and row['roa_annualized_percent'] is None


def test_truncated_and_duplicate_quarters_rejected():
    p = payload()
    p['meta']['total'] = 2
    with pytest.raises(ValueError, match='Incomplete'):
        bank.normalize(p, '20260630')
    p['data'] *= 2
    with pytest.raises(ValueError, match='Duplicate'):
        bank.normalize(p, '20260630')


@pytest.mark.parametrize('changes', [{'ASSET': Decimal('10.01')}, {'CERT': True},
    {'ROA': float('inf')}, {'ROA': True}, {'CERTCONS': -1}, {'NAME': ''}])
def test_invalid_typed_values_rejected(changes):
    with pytest.raises(ValueError):
        bank.normalize(payload(**changes), '20260630')


def test_wrong_date_and_missing_consolidation_rejected():
    with pytest.raises(ValueError, match='mismatch'):
        bank.normalize(payload('20260331'), '20260630')
    p = payload()
    del p['data'][0]['data']['CERTCONS']
    with pytest.raises(ValueError, match='mismatch'):
        bank.normalize(p, '20260630')


def test_definition_drift_requires_review():
    assert set(bank.definition_blocks(definitions())) == set(bank.FIELDS)
    with pytest.raises(ValueError, match='ROA definition'):
        bank.definition_blocks(definitions().replace('ASSET5', 'ASSET'))


def test_actual_pipeline_reconciles_and_keeps_quarter_stock_grain(acquired):
    root, acquisition = acquired
    result = bank.prepare_bank_panel(root, acquisition['acquisition_id'])
    assert bank.verify_bank_panel(root, result['case_id']) == result
    assert result['records'] == 42 and result['unique_certificates'] == 1
    assert result['reconciliation_differing_rows'] == 0
    folder = root / 'artifacts/private' / result['case_id']
    peers = pq.read_table(folder / 'peer-quarter.parquet').to_pylist()
    assert len(peers) == 42
    assert sum(row['records'] for row in peers) == 42
    assert all(row['reported_assets_usd_thousands'] == 100_000 for row in peers)
    changes = pq.read_table(folder / 'matched-quarter-changes.parquet').to_pylist()
    assert len(changes) == 41 and all(row['matched_reports'] == 1 for row in changes)
    assert all(row['paired_asset_change_usd_thousands'] == 0 for row in changes)
    path = folder / 'peer-quarter.parquet'
    with path.open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(ValueError, match='output changed'):
        bank.verify_bank_panel(root, result['case_id'])


def test_changed_raw_and_receipts_rejected(acquired):
    root, receipt = acquired
    source = root / 'data/private/bank-history' / receipt['acquisition_id']
    path = source / receipt['quarters'][0]['file']
    with path.open('a') as stream:
        stream.write(' ')
    with pytest.raises(ValueError, match='bytes changed'):
        bank.verify_acquisition(root, receipt['acquisition_id'])


def test_http_host_and_existing_destination_guards(tmp_path):
    with pytest.raises(ValueError, match='Official'):
        bank._download('https://example.com/file', tmp_path / 'raw.json')
    path = tmp_path / 'raw.json'
    path.write_text('existing')
    with pytest.raises(ValueError, match='Immutable'):
        bank._download(bank.DEFINITIONS, path)
