import copy
import json
from fractions import Fraction

import pytest
from credit_atlas import exposure_scenarios as scenarios
from credit_atlas.exposure_imports import import_exposures,normalize
from credit_atlas.workspace import sha256,write_new
from tests.test_exposure_imports import metadata,rows,write_csv


def assumptions(identifier='exposure-import-000000000000'):
    return {'schema_version':1,'name':'Illustrative fixture','version':'v1','basis':'declared_research_assumptions',
        'source_import_id':identifier,'horizon_months':12,'default_definition':'Declared test default event',
        'eligible_source_states':['DECLARED_PERFORMING'],'ead_basis':'reported_amount_times_declared_factor',
        'lgd_boundary_policy':'clip_and_report','segment_assumptions':{'segmentA':{'pd':'0.1','lgd':'0.4','ead_factor':'1.5'}},
        'scenarios':[{'id':'adverse','label':'Declared adverse fixture','pd_odds_multiplier':'2','lgd_addition':'0.7','ead_multiplier':'2'}],
        'visibility':'private','public_release_approved':False}


def ratio(value): return Fraction(int(value['numerator']),int(value['denominator']))


def test_exact_odds_el_attribution_and_native_currency_boundaries(tmp_path):
    path=tmp_path/'s.csv'; records=rows(); records[0]['amount_unit']='major'; records[0]['reported_amount']='100'
    records.append({**records[0],'position_id':'excluded','source_state':'D3PLUS','reported_amount':'50'})
    write_csv(path,records); report=scenarios.project(normalize(path,metadata()),metadata(),assumptions())
    baseline=next(r for r in report['scenarios'][0]['aggregates'] if r['dimension']=='total' and r['currency']=='USD')
    adverse=next(r for r in report['scenarios'][1]['aggregates'] if r['dimension']=='total' and r['currency']=='USD')
    assert ratio(baseline['research_el'])==6
    assert ratio(adverse['research_el'])==Fraction(600,11)/1
    assert ratio(adverse['pd_effect'])==Fraction(54,11)/1
    assert ratio(adverse['lgd_effect'])==Fraction(180,11)/1
    assert ratio(adverse['ead_effect'])==Fraction(300,11)/1
    assert ratio(adverse['attribution_residual'])==0 and adverse['lgd_clipped_records']==2
    usd=next(r for r in report['scope'] if r['currency']=='USD')
    assert usd['source_records']==3 and usd['eligible_records']==2 and usd['excluded_records']==1
    assert ratio(usd['source_amount'])==150 and ratio(usd['excluded_amount'])==50
    assert report['global_cross_currency_total'] is None and not report['contract']['accounting_ecl']


@pytest.mark.parametrize('pd',['0','1'])
def test_pd_boundaries_and_zero_ead(pd,tmp_path):
    plan=assumptions(); plan['segment_assumptions']['segmentA'].update(pd=pd,ead_factor='0')
    path=tmp_path/'s.csv'; write_csv(path,rows()); report=scenarios.project(normalize(path,metadata()),metadata(),plan)
    assert all(ratio(r['research_el'])==0 for s in report['scenarios'] for r in s['aggregates'])


@pytest.mark.parametrize('pd,expected',[('0',0),('1',300)])
def test_pd_boundary_nonzero_ead(pd,expected,tmp_path):
    plan=assumptions(); plan['segment_assumptions']['segmentA']['pd']=pd
    records=rows()[:1]; records[0].update(reported_amount='100',amount_unit='major')
    path=tmp_path/'s.csv'; write_csv(path,records); report=scenarios.project(normalize(path,metadata()),metadata(),plan)
    total=next(r for r in report['scenarios'][1]['aggregates'] if r['dimension']=='total')
    assert ratio(total['research_el'])==expected and ratio(total['pd_effect'])==0


def test_negative_lgd_addition_disclosed_lower_boundary(tmp_path):
    plan=assumptions(); plan['scenarios'][0]['lgd_addition']='-0.7'
    path=tmp_path/'s.csv'; write_csv(path,rows()); report=scenarios.project(normalize(path,metadata()),metadata(),plan)
    assert all(ratio(r['research_el'])==0 and r['lgd_clipped_records']==r['records'] for r in report['scenarios'][1]['aggregates'])


@pytest.mark.parametrize('change',['unknown_basis','percentage','zero_odds','duplicate_id','missing_segment','defaulted','unclear_ead','silent_clip','bad_horizon','source_risk','negative_ead','too_many'])
def test_unsupported_semantics_and_bounds_rejected(change,tmp_path):
    plan=assumptions(); meta=metadata(); path=tmp_path/'s.csv'; write_csv(path,rows()); records=normalize(path,meta)
    if change=='unknown_basis': plan['basis']='calibrated_model'
    elif change=='percentage': plan['segment_assumptions']['segmentA']['pd']='3'
    elif change=='zero_odds': plan['scenarios'][0]['pd_odds_multiplier']='0'
    elif change=='duplicate_id': plan['scenarios'].append(copy.deepcopy(plan['scenarios'][0]))
    elif change=='missing_segment': plan['segment_assumptions']={}
    elif change=='defaulted': plan['eligible_source_states']=['D3PLUS']
    elif change=='unclear_ead': plan['ead_basis']='observed_ead'
    elif change=='silent_clip': plan['lgd_boundary_policy']='clip'
    elif change=='bad_horizon': plan['horizon_months']=True
    elif change=='source_risk': meta['risk_contract']={'existing':'scores'}
    elif change=='negative_ead': plan['scenarios'][0]['ead_multiplier']='-1'
    elif change=='too_many': plan['scenarios']*=13
    with pytest.raises(ValueError): scenarios.project(records,meta,plan)


def test_assumption_file_duplicate_key_and_size_rejected(tmp_path):
    path=tmp_path/'bad.json'; path.write_text('{"pd":1,"pd":2}',encoding='utf-8')
    with pytest.raises(ValueError,match='Duplicate'): scenarios.read_plan(path)
    path.write_text(' '*100001,encoding='utf-8')
    with pytest.raises(ValueError,match='bound'): scenarios.read_plan(path)


def frozen(tmp_path):
    write_csv(tmp_path/'input.csv',rows()); write_new(tmp_path/'metadata.json',metadata())
    source=import_exposures(tmp_path,'input.csv','metadata.json')['import_id']
    write_new(tmp_path/'assumptions.json',assumptions(source))
    return scenarios.build(tmp_path,'assumptions.json')


def test_frozen_copy_and_source_rederive_reject_forged_report(tmp_path):
    receipt=frozen(tmp_path); folder,_,report=scenarios.verify(tmp_path,receipt['scenario_id'])
    (tmp_path/'assumptions.json').write_text('{}',encoding='utf-8')
    scenarios.verify(tmp_path,receipt['scenario_id']) # Copied version stays authoritative.
    report['scenarios'][1]['aggregates'][0]['research_el']['numerator']='999'
    (folder/'report.json').write_text(json.dumps(report),encoding='utf-8')
    receipt['outputs_sha256']['report.json']=sha256(folder/'report.json')
    (folder/'scenario-complete.json').write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='rederivation'): scenarios.verify(tmp_path,receipt['scenario_id'])


def test_source_mutation_during_projection_rejected(tmp_path,monkeypatch):
    receipt=frozen(tmp_path); original=scenarios.project
    def change_after_projection(*args):
        report=original(*args)
        path=tmp_path/'artifacts/private'/receipt['source_import_id']/'source.csv'
        path.write_text(path.read_text(encoding='utf-8').replace('segmentA','segmentB'),encoding='utf-8')
        return report
    monkeypatch.setattr(scenarios,'project',change_after_projection)
    with pytest.raises(ValueError,match='source changed'): scenarios.verify(tmp_path,receipt['scenario_id'])
