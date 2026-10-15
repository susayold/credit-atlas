import copy
import json
from urllib.parse import parse_qs, urlsplit

import pyarrow.parquet as pq
import pytest

from credit_atlas import country_observatory as module
from credit_atlas.workspace import sha256, timestamp


def page(rows, **changes):
    metadata = {'page': 1, 'pages': 1, 'total': len(rows), 'per_page': 20000}
    metadata.update(changes)
    return [metadata, rows]


def country(code='VNM', iso2='VN', name='Viet Nam', aggregate=False):
    return {'id': code, 'iso2Code': iso2, 'name': name,
            'region': {'id': 'NA' if aggregate else 'EAS', 'value': 'Aggregates' if aggregate else 'East Asia & Pacific'},
            'incomeLevel': {'value': 'Not classified' if aggregate else 'Lower middle income'}}


def observation(indicator, code='VNM', iso2='VN', name='Viet Nam', year='2025', value=1.5):
    return {'indicator': {'id': indicator, 'value': 'Source label'},
            'country': {'id': iso2, 'value': name}, 'countryiso3code': code, 'date': year, 'value': value,
            'unit': '', 'obs_status': '', 'decimal': 1, 'footnote': 'Source footnote'}


@pytest.fixture
def acquired(tmp_path, monkeypatch):
    def download(url, destination):
        path = urlsplit(url).path
        if path.endswith('/country'):
            payload = page([country(), country('WLD', '1W', 'World', True)])
        elif '/country/all/indicator/' in path:
            indicator = path.rsplit('/', 1)[1]
            payload = page([observation(indicator), observation(indicator, year='2024', value=None),
                            observation(indicator, 'WLD', '1W', 'World', value=-2.5)], sourceid='2', lastupdated='2026-10-08')
        elif '/v2/indicator/' in path:
            indicator = path.rsplit('/', 1)[1]
            payload = page([{'id': indicator, 'name': 'Source label', 'source': {'id': '2'}, 'sourceNote': 'Definition'}])
        else:
            payload = None
        content = json.dumps(payload) if payload is not None else 'Official glossary CC BY-4.0'
        destination.write_text(content, encoding='utf-8')
        return {'url': url, 'file': destination.name, 'bytes': destination.stat().st_size,
                'sha256': sha256(destination), 'retrieved_at': timestamp()}
    monkeypatch.setattr(module, '_download', download)
    receipt = module.acquire_country_source(tmp_path)
    return tmp_path, receipt


def test_partial_and_wrong_page_versions_rejected():
    with pytest.raises(ValueError, match='Incomplete'):
        module.page_payload(page([{}], total=2))
    with pytest.raises(ValueError, match='Missing'):
        module.collect_pages([page([{}], total=2, per_page=1, pages=2)])
    first = page([{}], total=2, per_page=1, pages=2, lastupdated='2026-10-08')
    second = page([{}], total=2, per_page=1, pages=2, page=2, lastupdated='2026-10-09')
    with pytest.raises(ValueError, match='version changed'):
        module.collect_pages([first, second])
    second[0]['lastupdated'] = '2026-10-08'
    assert len(module.collect_pages([first, second])[1]) == 2


def test_country_aggregate_null_and_native_annotation_contract(acquired):
    root, receipt = acquired
    completed = module.prepare_country_case(root, receipt['source_id'])
    folder, verified = module.verify_case(root, completed['case_id'])
    assert verified['rows'] == 21 and verified['source_country_catalog_entries'] == 2
    rows = pq.read_table(folder / 'observations.parquet').to_pylist()
    assert sum(row['is_aggregate'] for row in rows) == 7
    assert sum(row['value'] is None for row in rows) == 7
    assert rows[0]['source_unit'] == '' and rows[0]['footnote'] == 'Source footnote'
    assert rows[0]['income_group_current'] == 'Lower middle income'
    assert any(row['value'] == -2.5 for row in rows)
    assert not verified['model_qualified'] and not verified['public_release_approved']


@pytest.mark.parametrize('mutation,match', [
    ('duplicate', 'Duplicate'), ('orphan', 'join mismatch'), ('bool', 'numeric'),
    ('infinity', 'numeric'), ('nonannual', 'Annual'), ('label', 'join mismatch'),
    ('date', 'out-of-range'), ('annotation', 'annotations')])
def test_invalid_source_observations_rejected(acquired, mutation, match):
    root, receipt = acquired
    folder, _ = module.verify_source(root, receipt['source_id'])
    indicator = next(iter(module.INDICATORS))
    path = folder / (indicator + '-data-page-1.json')
    payload = json.loads(path.read_text())
    row = payload[1][0]
    if mutation == 'duplicate':
        payload[1].append(copy.deepcopy(row)); payload[0]['total'] += 1
    elif mutation == 'orphan': row['countryiso3code'] = 'ZZZ'
    elif mutation == 'bool': row['value'] = True
    elif mutation == 'infinity': row['value'] = float('inf')
    elif mutation == 'nonannual': row['date'] = '2025Q1'
    elif mutation == 'label': row['country']['value'] = 'Other economy'
    elif mutation == 'date': row['date'] = '2026'
    elif mutation == 'annotation': row.pop('footnote')
    path.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError, match=match):
        module.derive_source(folder, receipt)


def test_changed_raw_and_forged_canonical_rejected(acquired):
    root, receipt = acquired
    case = module.prepare_country_case(root, receipt['source_id'])
    folder = root / 'artifacts/private' / case['case_id']
    table = pq.read_table(folder / 'observations.parquet')
    rows = table.to_pylist(); rows[0]['value'] = 99
    import pyarrow as pa
    pq.write_table(pa.Table.from_pylist(rows, schema=module.SCHEMA), folder / 'observations.parquet')
    case['files']['observations.parquet'] = sha256(folder / 'observations.parquet')
    (folder / 'case-complete.json').write_text(json.dumps(case), encoding='utf-8')
    with pytest.raises(ValueError, match='differs from raw'):
        module.verify_case(root, case['case_id'])
    source = root / 'data/private/country-observatory' / receipt['source_id'] / 'countries-page-1.json'
    source.write_text(source.read_text() + '\n')
    with pytest.raises(ValueError, match='bytes changed'):
        module.verify_source(root, receipt['source_id'])


def test_missing_iso3_exact_iso2_join_preserves_native_fields(acquired):
    root, receipt = acquired
    folder, _ = module.verify_source(root, receipt['source_id'])
    indicator = next(iter(module.INDICATORS))
    path = folder / (indicator + '-data-page-1.json')
    payload = json.loads(path.read_text())
    payload[1][2]['countryiso3code'] = ''
    payload[1][2]['country']['value'] = 'World '
    path.write_text(json.dumps(payload), encoding='utf-8')
    facts, _, _, _ = module.derive_source(folder, receipt)
    row = facts[2]
    assert row['country_code'] == 'WLD' and row['source_country_iso3'] == ''
    assert row['source_country_name'] == 'World ' and row['is_aggregate'] is True
    assert row['country_join_basis'] == 'exact_catalog_iso2_missing_source_iso3'
    payload[1][2]['country']['id'] = 'ZZ'
    path.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError, match='join mismatch'):
        module.derive_source(folder, receipt)


@pytest.mark.parametrize('url', ['http://api.worldbank.org/v2/country', 'https://other.example/data',
                                'https://api.worldbank.org:443/data', 'https://user@api.worldbank.org/data'])
def test_unapproved_http_hosts_rejected(tmp_path, url):
    with pytest.raises(ValueError, match='HTTPS required'):
        module._download(url, tmp_path / 'data.json')
