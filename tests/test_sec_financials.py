import copy
import json
from decimal import Decimal

import pyarrow.parquet as pq
import pytest

from credit_atlas import sec_sources as sources
from credit_atlas import sec_financials as financials
from credit_atlas.workspace import sha256, timestamp, read_json

ACC = '0001193125-26-000001'  # Agent prefix need not match issuer CIK.


def filing(cik='0000320193'):
    return {'cik': cik, 'accession': ACC, 'filing_date': '2026-02-01', 'report_date': '2025-12-31',
            'acceptance_datetime': None, 'form': '10-K', 'primary_document': 'annual.htm', 'is_xbrl': True, 'occurrences': 1}


def payload(cik):
    concepts = {}
    for field, (kind, tags) in financials.FIELDS.items():
        row = {'end': '2025-12-31', 'val': 1000 if field in ('assets', 'revenue') else 500,
               'accn': ACC, 'fy': 2025, 'fp': 'FY', 'form': '10-K', 'filed': '2026-02-01'}
        if kind == 'annual_duration': row['start'] = '2025-01-01'
        concepts[tags[0]] = {'label': tags[0], 'description': 'Definition', 'units': {'USD': [row]}}
    return {'cik': int(cik), 'entityName': 'Source issuer', 'facts': {'us-gaap': concepts}}


@pytest.fixture
def acquired(tmp_path, monkeypatch):
    def download(url, destination):
        cik = destination.name.split('CIK')[1][:10]
        if 'companyfacts' in destination.name:
            content = payload(cik)
        else:
            content = {'cik': cik, 'name': 'Source issuer', 'tickers': [sources.ISSUERS[cik]], 'sic': '3711',
                'sicDescription': 'Industry', 'filings': {'files': [], 'recent': {
                    'accessionNumber': [ACC], 'filingDate': ['2026-02-01'], 'reportDate': ['2025-12-31'],
                    'form': ['10-K'], 'primaryDocument': ['annual.htm'], 'isXBRL': [1]}}}
        destination.write_text(json.dumps(content), encoding='utf-8')
        return {'url': url, 'file': destination.name, 'bytes': destination.stat().st_size,
                'sha256': sha256(destination), 'retrieved_at': timestamp()}
    monkeypatch.setattr(sources, 'download', download)
    return tmp_path, sources.acquire_sec_source(tmp_path)


def test_exact_decimal_units_periods_and_native_duplicates():
    content = payload('0000320193')
    instant = content['facts']['us-gaap']['Assets']['units']['USD'][0]
    instant['val'] = Decimal('1000.00000000000000000001')
    content['facts']['us-gaap']['Assets']['units']['USD'].append(copy.deepcopy(instant))
    rows, _ = financials.fact_rows(content, '0000320193')
    assert rows[0]['value_exact'] == '1000.00000000000000000001'
    assert rows[0]['source_ordinal'] == 0 and rows[1]['source_ordinal'] == 1
    snapshot = financials.statement(filing(), rows)
    assert snapshot['fields']['assets']['status'] == 'supported'
    assert len(snapshot['fields']['assets']['evidence']) == 2
    assert snapshot['ratios']['current_ratio']['value_exact'] == '1'
    assert snapshot['ratios']['net_income_margin']['value_exact'] == '0.5'


def test_conflicting_concepts_and_periods_fail_closed():
    content = payload('0000320193')
    alt = copy.deepcopy(content['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax'])
    alt['units']['USD'][0]['val'] = 999
    content['facts']['us-gaap']['Revenues'] = alt
    rows, _ = financials.fact_rows(content, '0000320193')
    snapshot = financials.statement(filing(), rows)
    assert snapshot['fields']['revenue']['status'] == 'ambiguous'
    assert snapshot['ratios']['net_income_margin']['value_exact'] is None
    rows = [row for row in rows if row['concept'] != 'Revenues']
    income = next(row for row in rows if row['concept'] == 'NetIncomeLoss')
    income['start_date'] = '2025-01-02'
    assert financials.statement(filing(), rows)['ratios']['net_income_margin']['status'] == 'period_mismatch'


@pytest.mark.parametrize('mutation,status', [('zero', 'nonpositive_denominator'), ('negative', 'nonpositive_denominator'),
    ('unit', 'missing_or_ambiguous_input'), ('quarter', 'missing_or_ambiguous_input'), ('late', 'missing_or_ambiguous_input')])
def test_noncomparable_or_undefined_inputs_do_not_create_ratio(mutation, status):
    rows, _ = financials.fact_rows(payload('0000320193'), '0000320193')
    target = next(row for row in rows if row['concept'] == 'RevenueFromContractWithCustomerExcludingAssessedTax')
    if mutation == 'zero': target['value_exact'] = '0'
    if mutation == 'negative': target['value_exact'] = '-1'
    if mutation == 'unit': target['unit'] = 'EUR'
    if mutation == 'quarter': target['start_date'] = '2025-10-01'
    if mutation == 'late': target['filed_date'] = '2026-02-02'
    result = financials.statement(filing(), rows)['ratios']['net_income_margin']
    assert result['status'] == status and result['value_exact'] is None


def test_canonical_verification_rejects_forged_ratio_and_raw(acquired):
    root, source = acquired
    case = financials.prepare_sec_case(root, source['source_id'])
    folder, receipt = financials.verify_case(root, case['case_id'])
    assert receipt['fact_entries'] == 32 and receipt['annual_statements'] == 4
    snapshots = read_json(folder / 'annual-statements.json')
    snapshots[0]['ratios']['current_ratio']['value_exact'] = '99'
    (folder / 'annual-statements.json').write_text(json.dumps(snapshots), encoding='utf-8')
    case['files']['annual-statements.json'] = sha256(folder / 'annual-statements.json')
    (folder / 'case-complete.json').write_text(json.dumps(case), encoding='utf-8')
    with pytest.raises(ValueError, match='calculations differ'):
        financials.verify_case(root, case['case_id'])
    path = root / 'data/private/sec' / source['source_id'] / source['files'][0]['file']
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError, match='bytes changed'):
        sources.verify_source(root, source['source_id'])


@pytest.mark.parametrize('value', [True, Decimal('NaN'), Decimal('Infinity'), '10'])
def test_invalid_numeric_values_rejected(value):
    content = payload('0000320193'); content['facts']['us-gaap']['Assets']['units']['USD'][0]['val'] = value
    with pytest.raises(ValueError, match='numeric'):
        financials.fact_rows(content, '0000320193')


def test_filing_arrays_unaligned_rejected():
    columns = {'accessionNumber': [ACC], 'filingDate': [], 'reportDate': ['2025-12-31'],
               'form': ['10-K'], 'primaryDocument': ['annual.htm']}
    with pytest.raises(ValueError, match='align'):
        sources.filing_columns(columns)


def test_equivalent_values_in_changed_parquet_types_rejected(acquired):
    import pyarrow as pa
    root, source = acquired
    case = financials.prepare_sec_case(root, source['source_id'])
    folder = root / 'artifacts/private' / case['case_id']
    table = pq.read_table(folder / 'facts.parquet')
    index = table.schema.get_field_index('source_ordinal')
    altered = table.set_column(index, 'source_ordinal', table.column(index).cast(pa.float64()))
    pq.write_table(altered, folder / 'facts.parquet')
    case['files']['facts.parquet'] = sha256(folder / 'facts.parquet')
    (folder / 'case-complete.json').write_text(json.dumps(case), encoding='utf-8')
    with pytest.raises(ValueError, match='schema changed'):
        financials.verify_case(root, case['case_id'])


@pytest.mark.parametrize('url', ['https://data.sec.gov/submissions/../../secret.json',
    'https://data.sec.gov/submissions/CIK0000320193.json?token=x', 'https://other.example/data',
    'http://data.sec.gov/submissions/CIK0000320193.json'])
def test_non_source_downloads_rejected(tmp_path, url):
    with pytest.raises(ValueError):
        sources.download(url, tmp_path / 'raw.json')
