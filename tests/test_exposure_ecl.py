import copy
import json
from fractions import Fraction

import pytest
from credit_atlas import exposure_ecl as ecl
from credit_atlas.exposure_imports import import_exposures,normalize
from credit_atlas.workspace import sha256,write_new
from tests.test_exposure_imports import metadata,rows,write_csv


def assumptions(identifier='exposure-import-000000000000',months=13):
    segment={'remaining_months':months,'monthly_effective_rate':'0','principal_due_factors':['0']*(months-1)+['1'],
        'benchmark_hazards':['0.01']*months,'assessment_hazards':['0.01']*months,'declared_dpd':0,
        'declared_credit_impaired':False,'qualitative_sicr':False,'poci':False,'revolving':False,'cure_under_review':False}
    hazards=['0']*months; hazards[0]='0.5'; hazards[-1]='0.5'
    return {'schema_version':1,'name':'Declared fixture cash-flow model','version':'v1','basis':'declared_research_cashflows_and_assessments',
        'source_import_id':identifier,'eligible_source_states':['DECLARED_PERFORMING'],
        'benchmark_comparison_basis':'same_remaining_horizon_declared_benchmark',
        'cash_convention':'default_at_start_of_month_contractual_cash_at_end',
        'staging_policy':{'relative_pd_ratio':'2','absolute_pd_increase':'0.02','sicr_dpd_gt':30,'default_dpd_gte':90,'zero_benchmark_policy':'any_positive_to_stage2'},
        'segments':{'segmentA':segment},'scenarios':[{'id':'base','label':'Declared base','weight':'1','segments':{
            'segmentA':{'conditional_default_hazards':hazards,'recovery_profile':[{'lag_months':18,'recovery_fraction':'0.4','collection_cost_fraction':'0'}]}}}],
        'visibility':'private','public_release_approved':False}


def test_stage1_default_horizon_keeps_recovery_and_cashflows_after_month12():
    plan=assumptions(); s=plan['segments']['segmentA']; assessment=ecl.stage(s,plan['staging_policy'])
    result=ecl.per_unit(s,plan['scenarios'][0]['segments']['segmentA'],assessment)
    assert ecl.rational(result['selected_ecl_per_unit'])==Fraction(3,10)
    assert ecl.rational(result['lifetime_ecl_per_unit'])==Fraction(9,20)
    assert result['default_events'][-1]['included_in_selected_horizon'] is False
    assert ecl.rational(result['default_events'][-1]['marginal_default_probability'])==Fraction(1,4)
    assert ecl.rational(result['no_default_survival'])==Fraction(1,4)
    s['monthly_effective_rate']='0.01'
    result=ecl.per_unit(s,plan['scenarios'][0]['segments']['segmentA'],assessment)
    assert ecl.rational(result['selected_ecl_per_unit'])==Fraction(1,2)*(1-Fraction(2,5)/Fraction(101,100)**18)
    assert ecl.rational(result['contract_pv_per_unit'])==1


def test_stage2_lifetime_and_stage3_default_now_net_recovery_costs():
    plan=assumptions(); s=plan['segments']['segmentA']; inputs=plan['scenarios'][0]['segments']['segmentA']
    s['qualitative_sicr']=True; result=ecl.per_unit(s,inputs,ecl.stage(s,plan['staging_policy']))
    assert ecl.rational(result['selected_ecl_per_unit'])==Fraction(9,20)
    s.update(declared_credit_impaired=True,monthly_effective_rate='0.01')
    inputs['recovery_profile']=[{'lag_months':6,'recovery_fraction':'0.4','collection_cost_fraction':'0.05'}]
    result=ecl.per_unit(s,inputs,ecl.stage(s,plan['staging_policy']))
    assert len(result['default_events'])==1 and result['default_events'][0]['default_month']==0
    assert ecl.rational(result['no_default_survival'])==0
    assert ecl.rational(result['selected_ecl_per_unit'])==1-Fraction(35,100)/Fraction(101,100)**6


@pytest.mark.parametrize('dpd,stage',[(30,1),(31,2),(89,2),(90,3)])
def test_declared_dpd_boundaries(dpd,stage):
    plan=assumptions(); s=plan['segments']['segmentA']; s['declared_dpd']=dpd
    assert ecl.stage(s,plan['staging_policy'])['stage']==stage


def test_quantitative_sicr_compares_probability_not_loss_or_scenario():
    plan=assumptions(); s=plan['segments']['segmentA']; s['assessment_hazards']=['0.1']*13
    result=ecl.stage(s,plan['staging_policy']); assert result['stage']==2
    assert 'DECLARED_RELATIVE_AND_ABSOLUTE_PD_INCREASE' in result['reasons']
    s['benchmark_hazards']=['0']*13; s['assessment_hazards']=['0.000001']*13
    result=ecl.stage(s,plan['staging_policy']); assert result['stage']==2 and result['pd_ratio'] is None
    assert result['ratio_status']=='POSITIVE_FROM_ZERO'


def test_amortization_discount_tail_matches_independent_remaining_balance_identity():
    plan=assumptions(months=3); s=plan['segments']['segmentA']
    s.update(principal_due_factors=['0.25','0.25','0.5'],monthly_effective_rate='0.01')
    inputs=plan['scenarios'][0]['segments']['segmentA']; inputs['conditional_default_hazards']=['0','0','1']
    inputs['recovery_profile']=[{'lag_months':0,'recovery_fraction':'0','collection_cost_fraction':'0'}]
    result=ecl.per_unit(s,inputs,ecl.stage(s,plan['staging_policy']))
    assert ecl.rational(result['selected_ecl_per_unit'])==Fraction(1,2)/Fraction(101,100)**2
    assert ecl.rational(result['default_events'][2]['remaining_principal_factor'])==Fraction(1,2)


@pytest.mark.parametrize('change',['weights','probability','principal_sum','poci','revolving','cure','curve_length','negative_recovery','excess_recovery','monthly_rate','unknown_basis','source_risk','dpd_bool'])
def test_bad_contracts_rejected(change,tmp_path):
    plan=assumptions(); s=plan['segments']['segmentA']; inputs=plan['scenarios'][0]['segments']['segmentA']; meta=metadata()
    path=tmp_path/'s.csv'; write_csv(path,rows()); data=normalize(path,meta)
    if change=='weights': plan['scenarios'][0]['weight']='0.9'
    elif change=='probability': inputs['conditional_default_hazards'][0]='1.2'
    elif change=='principal_sum': s['principal_due_factors'][-1]='0.9'
    elif change in ('poci','revolving'): s[change]=True
    elif change=='cure': s['cure_under_review']=True
    elif change=='curve_length': s['benchmark_hazards'].pop()
    elif change=='negative_recovery': inputs['recovery_profile'][0]['collection_cost_fraction']='0.5'
    elif change=='excess_recovery': inputs['recovery_profile']*=3
    elif change=='monthly_rate': s['monthly_effective_rate']='0.0000001'
    elif change=='unknown_basis': plan['basis']='actual_accounting_ecl'
    elif change=='source_risk': meta['risk_contract']={'scores':'existing'}
    elif change=='dpd_bool': s['declared_dpd']=True
    with pytest.raises(ValueError): ecl.project(data,meta,plan)


def test_probability_weighting_native_currencies_and_scenario_invariant_stage(tmp_path):
    plan=assumptions(); second=copy.deepcopy(plan['scenarios'][0]); second.update(id='adverse',weight='0.25')
    plan['scenarios'][0]['weight']='0.75'; second['segments']['segmentA']['recovery_profile'][0]['recovery_fraction']='0'
    plan['scenarios'].append(second); path=tmp_path/'s.csv'; records=rows(); records[0].update(amount_unit='major',reported_amount='100')
    records.append({**records[0],'position_id':'missing','source_state':'D3PLUS','reported_amount':'25'})
    write_csv(path,records); report=ecl.project(normalize(path,metadata()),metadata(),plan)
    usd=next(r for r in report['probability_weighted_aggregates'] if r['currency']=='USD' and r['dimension']=='total')
    assert ecl.rational(usd['research_ecl'])==Fraction(70,2)
    assert report['stage_assessments']['segmentA']['stage']==1 and report['global_cross_currency_total'] is None
    assert report['scope'][0]['excluded_records']==1 and not report['contract']['accounting_compliance']


def frozen(root):
    write_csv(root/'source.csv',rows()); write_new(root/'metadata.json',metadata())
    source=import_exposures(root,'source.csv','metadata.json')['import_id']; write_new(root/'ecl.json',assumptions(source))
    return ecl.build(root,'ecl.json')


def test_pinned_source_rederive_forged_report_rejected(tmp_path):
    receipt=frozen(tmp_path); folder,_,report=ecl.verify(tmp_path,receipt['ecl_id'])
    report['probability_weighted_aggregates'][0]['research_ecl']['numerator']='999'
    (folder/'report.json').write_text(json.dumps(report),encoding='utf-8')
    receipt['outputs_sha256']['report.json']=sha256(folder/'report.json')
    (folder/'ecl-complete.json').write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='rederivation'): ecl.verify(tmp_path,receipt['ecl_id'])


def test_source_change_during_calculation_rejected(tmp_path,monkeypatch):
    receipt=frozen(tmp_path); original=ecl.project
    def change(*args):
        report=original(*args); path=tmp_path/'artifacts/private'/receipt['source_import_id']/'source.csv'
        path.write_text(path.read_text(encoding='utf-8').replace('segmentA','segmentB'),encoding='utf-8'); return report
    monkeypatch.setattr(ecl,'project',change)
    with pytest.raises(ValueError,match='source changed'): ecl.verify(tmp_path,receipt['ecl_id'])
