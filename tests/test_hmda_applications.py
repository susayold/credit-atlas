import json
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas import hmda_applications as app
from credit_atlas.hmda_sources import acquire_hmda_source
from credit_atlas.workspace import read_json, sha256
from tests.test_hmda_sources import fake_network
from tests import test_hmda_sources as fixtures


@pytest.fixture
def source(tmp_path, fake_network, monkeypatch):
    fields = sorted(set(fixtures.header()) | set(app.DIMENSIONS))
    actual = [name for name in fields if not name.startswith('extra_')]
    actual += ['extra_' + str(i) for i in range(99 - len(actual))]
    monkeypatch.setattr(fixtures, 'header', lambda: actual)
    receipt = acquire_hmda_source(tmp_path)
    return tmp_path, receipt


def test_full_raw_rows_exact_units_and_decision_denominator(source):
    root, src = source; case = app.build_case(root, src['source_id'])
    folder, verified = app.verify_case(root, case['case_id'])
    assert verified == case and case['records'] == 6
    assert len(pq.read_schema(folder / 'source_rows.parquet')) == 101
    typed = pq.read_table(folder / 'applications.parquet').to_pylist()
    assert typed[0]['public_loan_amount_usd_exact'] == '5000.0'
    assert typed[0]['income_thousands_usd_exact'] == '0'
    assert typed[0]['interest_rate_percent_exact'] is None and typed[0]['interest_rate_status'] == 'EXEMPT'
    assert typed[0]['dti_public_category'] == '30%-<36%'
    assert typed[0]['applicant_age_public_category'] == '8888'
    assert typed[0]['ltv_source_raw_unqualified'] == 'NA'
    report = read_json(folder / 'evidence.json')
    assert all(row['decision_denominator'] == 2 and Decimal(row['descriptive_denial_rate']) == Decimal('.5') for row in report['years'])
    assert report['quality']['application_id_available'] is False
    assert all(value is False for value in report['qualification'].values())


@pytest.mark.parametrize('raw,status,value', [('NA', 'NOT_APPLICABLE', None), ('Exempt', 'EXEMPT', None),
    ('', 'SOURCE_BLANK', None), ('0', 'VALUE', '0'), ('-5', 'VALUE', '-5'), ('1111', 'VALUE', '1111')])
def test_missing_codes_not_zero_and_numeric_income_not_exempt(raw, status, value):
    assert app.exact_optional(raw) == (value, status)


def test_purchases_preapprovals_and_withdrawals_excluded_from_decision_rate(tmp_path):
    rows = []
    base = fixtures.records(2024)[0]
    for code in ('1', '2', '3', '4', '5', '6', '7', '8'):
        rows.append({**base, **{key: 'NA' for key in app.DIMENSIONS if key not in base}, 'action_taken': code})
    name = '2024-MD-home-purchase-site-built.csv'
    fields = list(rows[0])
    fixtures.write_csv(tmp_path / name, 2024, rows=rows, fields=fields)
    report = app.evidence(tmp_path, {'profiles': [{'year': 2024}]})
    year = report['years'][0]
    assert year['records'] == 8 and year['decision_denominator'] == 3 and year['denied_numerator'] == 1
    assert Decimal(year['descriptive_denial_rate']) == Decimal(1) / 3
    assert year['actions']['6'] == 1 and year['actions']['7'] == 1


def test_zero_decision_denominator_is_unavailable_and_public_duplicates_retained(tmp_path):
    base = fixtures.records(2024)[0]
    row = {**base, **{key: 'NA' for key in app.DIMENSIONS if key not in base}, 'action_taken': '6'}
    name = '2024-MD-home-purchase-site-built.csv'
    fixtures.write_csv(tmp_path / name, 2024, rows=[row, row], fields=list(row))
    report = app.evidence(tmp_path, {'profiles': [{'year': 2024}]})
    assert report['years'][0]['descriptive_denial_rate'] is None
    assert report['quality']['exact_public_duplicate_rows_beyond_first'] == 1
    assert report['quality']['duplicates_retained'] is True


@pytest.mark.parametrize('artifact', ['source_rows.parquet', 'applications.parquet', 'evidence.json'])
def test_forged_output_with_updated_hash_is_rederived_from_source(source, artifact):
    root, src = source; case = app.build_case(root, src['source_id'])
    folder = root / 'artifacts/private' / case['case_id']; path = folder / artifact
    if artifact == 'evidence.json':
        report = read_json(path); report['years'][0]['decision_denominator'] += 1
        path.write_text(json.dumps(report), encoding='utf-8')
    else:
        table = pq.read_table(path); rows = table.to_pylist()
        if artifact == 'source_rows.parquet': rows[0]['action_taken'] = '6'
        else: rows[0]['public_loan_amount_usd_exact'] = '999999.0'
        pq.write_table(pa.Table.from_pylist(rows, schema=table.schema), path)
    case['outputs_sha256'][artifact] = sha256(path)
    (folder / 'case-complete.json').write_text(json.dumps(case), encoding='utf-8')
    with pytest.raises(ValueError, match='differ'):
        app.verify_case(root, case['case_id'])


def test_independent_csv_sql_audit(source):
    from scripts.audit_hmda_applications import run
    root, src = source; case = app.build_case(root, src['source_id'])
    audit = run(root, case['case_id'])
    assert audit['status'] == 'PASS' and audit['records'] == 6 and audit['failed_checks'] == 0
