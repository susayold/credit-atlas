import copy
import csv
import json

import pytest

from credit_atlas import exposure_imports as exposures
from credit_atlas.workspace import read_json, sha256, write_new


def metadata(risk=False):
    return {'schema_version': 1, 'dataset_kind': 'declared_portfolio', 'amount_kind': 'declared_position_amount',
        'as_of': '2026-10-09', 'date_grain': 'day', 'source_namespace': 'fixture', 'source_description': 'Declared test portfolio',
        'risk_contract': {'pd_semantics': 'cumulative_default_probability', 'lgd_semantics': 'conditional_fraction_of_ead_on_default',
            'ead_semantics': 'declared_exposure_at_default_major_currency', 'basis': 'declared_research_assumption',
            'default_definition': 'Declared fixture default event', 'horizon_months': 12} if risk else None,
        'source_lineage': [], 'visibility': 'private', 'public_release_approved': False}


def rows(risk=False):
    first = dict(zip(exposures.FIELDS, ['P1', 'poolA', 'DIRECT_ASSET', '2026-10-09', 'USD', 'thousand',
        '1.234567890123456789', 'segmentA', 'VN', 'DECLARED_PERFORMING', '0.03' if risk else '', '0.4' if risk else '', '1250' if risk else '']))
    return [first, {**first, 'position_id': 'P2', 'currency': 'VND', 'amount_unit': 'million', 'reported_amount': '2'},
            {**first, 'position_id': 'P3', 'amount_unit': 'major', 'reported_amount': '0'}]


def write_csv(path, records):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=exposures.FIELDS); writer.writeheader(); writer.writerows(records)


def test_exact_units_mixed_currency_no_fx_or_cross_currency_sum(tmp_path):
    path = tmp_path / 'source.csv'; write_csv(path, rows())
    normalized = exposures.normalize(path, metadata()); report = exposures.aggregate(normalized, metadata())
    assert normalized[0]['reported_amount_major_exact'] == '1234.567890123456789000'
    assert report['global_cross_currency_total'] is None and report['currencies'][1]['reported_amount_major_exact'] == '2000000'
    assert report['currencies'][0]['research_el_major_exact'] is None
    assert report['currencies'][0]['zero_amount_records'] == 1


def test_declared_factorized_el_requires_explicit_risk_semantics_and_ead(tmp_path):
    path = tmp_path / 'source.csv'; write_csv(path, rows(True))
    normalized = exposures.normalize(path, metadata(True)); report = exposures.aggregate(normalized, metadata(True))
    assert normalized[0]['research_el_major_exact'] == '15.000'
    assert report['currencies'][0]['research_el_major_exact'] == '30.000'
    assert report['contract']['amount_is_ead'] is False and report['contract']['accounting_ecl'] is False


@pytest.mark.parametrize('field,value', [('reported_amount', '-1'), ('reported_amount', 'NaN'), ('reported_amount', '1e6'),
    ('reported_amount', '0.1234567890123456789'), ('currency', 'XYZ'), ('amount_unit', 'cents'),
    ('as_of', '2026-10-10'), ('position_id', ' P1'), ('pool_key', '')])
def test_bad_amounts_units_dates_and_identity_rejected(tmp_path, field, value):
    records = rows(); records[0][field] = value; path = tmp_path / 'x.csv'; write_csv(path, records)
    with pytest.raises(ValueError): exposures.normalize(path, metadata())


def test_duplicate_position_and_overlapping_representation_rejected(tmp_path):
    path = tmp_path / 'x.csv'; records = rows(); records[1]['position_id'] = 'P1'; write_csv(path, records)
    with pytest.raises(ValueError): exposures.normalize(path, metadata())
    records = rows(); records[1]['representation'] = 'SECURITY_POSITION'; write_csv(path, records)
    with pytest.raises(ValueError, match='Overlapping'): exposures.normalize(path, metadata())
    records[1]['pool_key'] = 'distinctPool'; write_csv(path, records)
    assert len(exposures.normalize(path, metadata())) == 3


@pytest.mark.parametrize('change', ['unknown_pd', 'conditional_pd', 'basis', 'horizon', 'percentage', 'nonperforming', 'untyped_scores'])
def test_unknown_or_mixed_score_semantics_and_units_rejected(tmp_path, change):
    meta = metadata(True); records = rows(True)
    if change == 'unknown_pd': meta['risk_contract']['pd_semantics'] = 'hmda_denial_rate'
    elif change == 'conditional_pd': meta['risk_contract']['pd_semantics'] = 'monthly_conditional_hazard'
    elif change == 'basis': meta['risk_contract']['basis'] = 'validated_model_estimate'
    elif change == 'horizon': meta['risk_contract']['horizon_months'] = True
    elif change == 'percentage': records[0]['pd'] = '3'
    elif change == 'nonperforming': records[0]['source_state'] = 'DEFAULTED'
    else: meta['risk_contract'] = None
    path = tmp_path / 'source.csv'; write_csv(path, records)
    with pytest.raises(ValueError): exposures.normalize(path, meta)


@pytest.mark.parametrize('change', ['report', 'positions', 'qualification'])
def test_reverification_rederives_even_updated_receipt_hashes(tmp_path, change):
    path = tmp_path / 'input.csv'; write_csv(path, rows()); write_new(tmp_path / 'meta.json', metadata())
    receipt = exposures.import_exposures(tmp_path, 'input.csv', 'meta.json'); folder = tmp_path / 'artifacts/private' / receipt['import_id']
    exposures.verify_import(tmp_path, receipt['import_id'])
    if change == 'positions':
        import pyarrow as pa
        import pyarrow.parquet as pq
        table = pq.read_table(folder / 'positions.parquet'); positions = table.to_pylist(); positions[0]['reported_amount_major_exact'] = '9999'
        pq.write_table(pa.Table.from_pylist(positions, schema=table.schema), folder / 'positions.parquet'); name = 'positions.parquet'
    else:
        report = read_json(folder / 'report.json')
        if change == 'report': report['records'] = 999
        else: report['contract']['accounting_ecl'] = 0
        (folder / 'report.json').write_text(json.dumps(report), encoding='utf-8'); name = 'report.json'
    receipt['outputs_sha256'][name] = sha256(folder / name)
    (folder / 'import-complete.json').write_text(json.dumps(receipt), encoding='utf-8')
    with pytest.raises(ValueError): exposures.verify_import(tmp_path, receipt['import_id'])
