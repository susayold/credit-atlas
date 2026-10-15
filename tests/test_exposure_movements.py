import copy
import json
from decimal import Decimal

import pytest

from credit_atlas import exposure_movements as movements
from credit_atlas.exposure_imports import import_exposures
from credit_atlas.workspace import read_json, sha256, write_new
from tests.test_exposure_imports import metadata, rows, write_csv


def sample():
    a = rows()[0]; a.update(amount_unit='major', reported_amount='100', reported_amount_major_exact='100')
    b = {**a, 'position_id': 'B', 'reported_amount_major_exact': '30'}
    c = {**a, 'position_id': 'C', 'currency': 'VND', 'reported_amount_major_exact': '1000'}
    before = metadata(); after = {**before, 'as_of': '2026-10-10'}
    new = [{**a, 'reported_amount_major_exact': '80', 'region': 'JP', 'source_state': 'D1'},
           {**c, 'currency': 'USD', 'reported_amount_major_exact': '40'},
           {**a, 'position_id': 'D', 'reported_amount_major_exact': '20'}]
    return [a,b,c], new, before, after


def test_ordered_bridge_partial_amount_change_reclassification_and_currency_migration():
    report = movements.bridge(*sample()); currency = {r['currency']:r for r in report['currencies']}
    assert report['identity_counts'] == {'opening_only':1,'closing_only':1,'matched_same_currency':1,'matched_currency_migration':1}
    usd = currency['USD']
    assert {k:Decimal(usd[k]) for k in ('opening_amount','removed_amount','continuing_amount_change','added_amount','closing_amount','residual')} == {
        'opening_amount':130,'removed_amount':30,'continuing_amount_change':-20,'added_amount':60,'closing_amount':140,'residual':0}
    assert Decimal(currency['VND']['removed_amount']) == 1000 and Decimal(currency['VND']['closing_amount']) == 0
    assert usd['currency_migration_in_records'] == 1 and currency['VND']['currency_migration_out_records'] == 1
    groups = {(r['currency'],r['dimension'],r['bucket']):r for r in report['groups']}
    old = groups[('USD','region','VN')]; new = groups[('USD','region','JP')]
    assert Decimal(old['continuing_amount_change']) == -20 and Decimal(old['transfer_out']) == 80
    assert Decimal(old['closing_amount']) == 60 and Decimal(new['transfer_in']) == 80
    assert all(Decimal(r['residual']) == 0 for r in report['groups'])
    assert report['global_cross_currency_total'] is None and report['contract']['exit_reason_inferred'] is False


def test_zero_balance_and_exact_unit_precision_not_cashflow():
    old,new,before,after = sample(); old=old[:1]; new=[{**old[0], 'reported_amount_major_exact':'0'}]
    old[0]['reported_amount_major_exact']='0.123456789012345678'
    report = movements.bridge(old,new,before,after)
    assert report['identity_counts']['matched_same_currency'] == 1
    assert report['currencies'][0]['continuing_amount_change'] == '-0.123456789012345678'
    assert report['currencies'][0]['removed_records'] == 0
    assert not report['contract']['cash_flow_attribution']


@pytest.mark.parametrize('field,value', [('source_namespace','other'),('amount_kind','other'),('dataset_kind','other'),('date_grain','month'),('as_of','2026-10-09')])
def test_incompatible_scope_or_reversed_time_rejected(field,value):
    old,new,before,after = sample(); after[field]=value
    with pytest.raises(ValueError): movements.bridge(old,new,before,after)


@pytest.mark.parametrize('field,value', [('pool_key','other'),('representation','SECURITY_POSITION')])
def test_changed_identity_representation_needs_adapter(field,value):
    old,new,before,after = sample(); new[0][field]=value
    with pytest.raises(ValueError,match='identity adapter'): movements.bridge(old,new,before,after)


def imported_pair(root):
    identifiers=[]
    for period in ('2026-10-09','2026-10-10'):
        meta=metadata(); meta['as_of']=period; records=rows()
        for row in records: row['as_of']=period
        if period.endswith('10'): records[0]['reported_amount']='1'; records[0]['region']='JP'
        path=root / (period+'.csv'); write_csv(path,records); write_new(root/(period+'.json'),meta)
        identifiers.append(import_exposures(root,path.name,period+'.json')['import_id'])
    return identifiers


def test_source_bound_receipt_rederive_rejects_forged_aggregate(tmp_path):
    opening,closing=imported_pair(tmp_path); receipt=movements.build(tmp_path,opening,closing)
    folder,_,report=movements.verify(tmp_path,receipt['movement_id'])
    assert all(Decimal(row['residual']) == 0 for row in report['groups'])
    report['currencies'][0]['closing_amount']='999'
    (folder/'report.json').write_text(json.dumps(report),encoding='utf-8')
    receipt['report_sha256']=sha256(folder/'report.json')
    (folder/'movement-complete.json').write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='rederivation'): movements.verify(tmp_path,receipt['movement_id'])


def test_source_corruption_with_updated_payload_hashes_rejected(tmp_path):
    opening,closing=imported_pair(tmp_path); receipt=movements.build(tmp_path,opening,closing)
    path=tmp_path/'artifacts/private'/opening/'source.csv'
    path.write_text(path.read_text(encoding='utf-8').replace('1.234567890123456789','8.234567890123456789'),encoding='utf-8')
    with pytest.raises(ValueError): movements.verify(tmp_path,receipt['movement_id'])
