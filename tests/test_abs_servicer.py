"""Contract tests without relying on private real issuer files."""
import copy
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas import abs_servicer as abs
from credit_atlas.workspace import sha256


@pytest.mark.parametrize('ctype,raw',[(0,''),(6,''),(1,'')])
def test_blank_never_becomes_zero(ctype,raw):
    assert abs.scalar(raw,ctype,'USD')==(None,'SOURCE_BLANK')
    assert abs.scalar('0.0',2,'USD')==('0.00','VALUE')


def test_money_normalization_retains_material_subcent_exception():
    assert abs.scalar('1225361707.1499999',2,'USD')==('1225361707.15','VALUE')
    assert abs.scalar('-680277.51',2,'USD')==('-680277.51','VALUE')
    with pytest.raises(ValueError,match='sub-cent'):
        abs.scalar('12.345',2,'USD')


@pytest.mark.parametrize('raw,ctype,unit',[('1.2',2,'accounts'),('-1',2,'days'),('NaN',2,'USD'),
    ('0.1',1,'ratio'),('0',4,'USD'),('1',2,'EUR'),('1',2,'percent')])
def test_untyped_or_unsupported_values_rejected(raw,ctype,unit):
    with pytest.raises(ValueError):abs.scalar(raw,ctype,unit)


def test_ratio_is_source_fraction_without_money_rounding():
    assert abs.scalar('0.01728485586772178',2,'ratio')==('0.01728485586772178','VALUE')
    assert abs.scalar('50.82334034730373',2,'months')==('50.82334034730373','VALUE')


def test_short_initial_collection_period_is_preserved():
    a,b=abs.date_interval('01/03/25 - 01/31/25')
    assert a.isoformat()=='2025-01-03' and b.isoformat()=='2025-01-31'
    with pytest.raises(ValueError):abs.date_interval('02/28/25 - 02/01/25')
    with pytest.raises(ValueError):abs.date_interval('2025-01-01 - 2025-01-31')


@pytest.fixture
def balances():
    p={'collection_start':'2025-01-03','collection_end':'2025-01-31'}
    metrics=[]
    def add(section,key,value='0',slot=''):
        metrics.append({'collection_end':p['collection_end'],'section':section,'slot':slot,
                        'metric':key,'value':value,'status':'VALUE'})
    for key in ('beginning_receivables','beginning_pool','beginning_ysoa','principal_payments','defaulted_receivables',
        'repurchased_receivables','ending_ysoa','ending_pool','beginning_receivables_accounts',
        'principal_payments_accounts','defaulted_receivables_accounts','repurchased_receivables_accounts',
        'ending_pool_accounts','recoveries','net_losses','delinquent_31_60','delinquent_61_90','delinquent_91_120',
        'delinquent_121_plus','delinquent_total','delinquent_31_60_accounts','delinquent_61_90_accounts',
        'delinquent_91_120_accounts','delinquent_121_plus_accounts','delinquent_total_accounts'):
        add('pool',key, '1000' if key in ('beginning_receivables','beginning_pool','ending_pool') else '0')
    for key in ('collections','investment_earnings','servicing_fee_signed','collection_account_transfer',
        'available_funds','reported_total_distributions'):add('flow',key)
    for row in range(65,81):add('distribution','line_'+str(row))
    for key in ('beginning_balance','principal_paid','ending_balance','interest_paid','total_principal_paid','total_paid'):
        add('notes_total',key)
    for slot in abs.CLASSES:
        for key in ('beginning_balance','principal_paid','ending_balance','payment_principal','interest_paid','total_paid'):
            add('note_slot',key,slot=slot)
    for key in ('beginning_balance','investment_earnings','earnings_paid_signed','deposit_withdrawal','ending_balance','change'):
        add('reserve',key)
    return metrics,[p]


def test_accounting_does_not_double_count_subtotals(balances):
    metrics,periods=balances
    def put(section,key,value,slot=''):
        next(m for m in metrics if (m['section'],m['metric'],m['slot'])==(section,key,slot))['value']=value
    put('flow','collections','300');put('flow','available_funds','300');put('flow','reported_total_distributions','300')
    put('distribution','line_66','10');put('distribution','line_77','250');put('distribution','line_79','40')
    for key,value in [('beginning_balance','1000'),('ending_balance','750'),('principal_paid','250'),
        ('interest_paid','10'),('total_principal_paid','250'),('total_paid','260')]:put('notes_total',key,value)
    for key,value in [('beginning_balance','1000'),('ending_balance','750'),('principal_paid','250'),
        ('payment_principal','250'),('interest_paid','10'),('total_paid','260')]:put('note_slot',key,value,'A-1')
    assert all(c['pass'] for c in abs.reconcile(metrics,periods))
    put('note_slot','total_paid','261','A-1')
    failed={c['check'] for c in abs.reconcile(metrics,periods) if not c['pass']}
    assert {'note_payment_A-1','note_slots_sum_total_paid'}<=failed


@pytest.mark.parametrize('section,key,value,expected',[('pool','ending_pool','999.98','pool_money_rollforward'),
    ('pool','ending_pool_accounts','1','pool_accounts_rollforward'),('flow','available_funds','1','cash_conservation'),
    ('reserve','ending_balance','1','reserve_rollforward')])
def test_real_arithmetic_errors_remain_visible(balances,section,key,value,expected):
    metrics,periods=balances
    next(m for m in metrics if m['section']==section and m['metric']==key)['value']=value
    assert expected in {c['check'] for c in abs.reconcile(metrics,periods) if not c['pass']}


def test_missing_or_duplicate_required_metric_is_rejected(balances):
    metrics,periods=balances
    metrics[0]['value']=None;metrics[0]['status']='SOURCE_BLANK'
    with pytest.raises(ValueError,match='unavailable'):abs.reconcile(metrics,periods)
    metrics[0]['value']='0';metrics[0]['status']='VALUE'
    metrics.append(copy.deepcopy(metrics[0]))
    with pytest.raises(ValueError,match='Duplicate'):abs.reconcile(metrics,periods)


def test_period_gap_never_infers_missing_month(balances):
    metrics,periods=balances
    second=copy.deepcopy(metrics)
    for m in second:m['collection_end']='2025-03-31'
    with pytest.raises(ValueError,match='nonadjacent'):
        abs.reconcile(metrics+second,periods+[{'collection_start':'2025-03-01','collection_end':'2025-03-31'}])


@pytest.fixture
def canonical(tmp_path,monkeypatch):
    raw=[{'file':'example.xls','sheet':'Jan','row':1,'column':1,'cell_type':1,'raw_value':'example','number_format':'General'}]
    metric=[{'file':'example.xls','sheet':'Jan','collection_end':'2025-01-31','section':'pool','slot':'',
        'metric':'ending_pool','unit':'USD','value':'1.00','status':'VALUE','row':2,'column':2,
        'label':'Pool Balance','raw_value':'1.0','cell_type':2}]
    source=tmp_path/'data/private/structured/abs-source-000000000000';source.mkdir(parents=True)
    (source/'acquisition-complete.json').write_text('{}')
    monkeypatch.setattr(abs,'derive',lambda root,id:(raw,metric,[],[]))
    receipt=abs.prepare(tmp_path,'abs-source-000000000000')
    return tmp_path,receipt


def test_altered_canonical_values_rejected_even_with_updated_digest(canonical):
    root,receipt=canonical
    folder=root/'artifacts/private'/receipt['case_id']
    path=folder/'reported_metrics.parquet'
    rows=pq.read_table(path).to_pylist();rows[0]['value']='2.00'
    pq.write_table(pa.Table.from_pylist(rows,schema=abs.METRIC_SCHEMA),path)
    receipt['files'][1]['sha256']=sha256(path)
    (folder/'case-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='bytes/schema/values'):abs.verify_case(root,receipt['case_id'])


def test_equivalent_values_wrong_schema_rejected(canonical):
    root,receipt=canonical;folder=root/'artifacts/private'/receipt['case_id'];path=folder/'reported_metrics.parquet'
    table=pq.read_table(path);idx=table.schema.get_field_index('row')
    table=table.set_column(idx,pa.field('row',pa.int64()),table.column(idx).cast(pa.int64()))
    pq.write_table(table,path);receipt['files'][1]['sha256']=sha256(path)
    (folder/'case-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='bytes/schema/values'):abs.verify_case(root,receipt['case_id'])


def test_receipt_cannot_claim_projection_or_publication(canonical):
    root,receipt=canonical;folder=root/'artifacts/private'/receipt['case_id']
    receipt['qualification']['projected_waterfall']=True
    (folder/'case-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='qualification'):abs.verify_case(root,receipt['case_id'])
