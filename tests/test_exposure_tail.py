import copy
import json
from fractions import Fraction

import numpy as np
import pytest
from credit_atlas import exposure_tail as tail
from credit_atlas.exposure_scenarios import build as scenario_build
from credit_atlas.exposure_imports import import_exposures
from credit_atlas.workspace import sha256,write_new
from tests.test_exposure_imports import metadata,rows,write_csv
from tests.test_exposure_scenarios import assumptions as scenario_assumptions


def plan(scenario_id='exposure-scenario-000000000000'):
    return {'schema_version':1,'name':'Declared tail fixture','version':'v1','basis':'declared_research_dependence_and_recovery',
        'scenario_set_id':scenario_id,'scenario_case_id':'adverse','seed':42,'draws':256,'alphas':['0.95','0.99'],
        'cases':[{'id':'independent','label':'Independent fixture','asset_correlation':'0','lgd_systemic_spread':'0'},
                 {'id':'coupled','label':'Coupled fixture','asset_correlation':'0.3','lgd_systemic_spread':'0.1'}],
        'visibility':'private','public_release_approved':False}


def positions():
    return [{'currency':'USD','segment':'A','region':'US','pd':.1,'lgd':.4,'ead':100.0,'ead_exact':Fraction(100)},
            {'currency':'USD','segment':'B','region':'US','pd':.2,'lgd':.5,'ead':200.0,'ead_exact':Fraction(200)}]


def test_fractional_es_probability_mass_and_tie_averaged_contributions():
    losses=np.array([0.,10.,20.,20.]); groups={'A':np.array([0.,0.,20.,0.]),'B':np.array([0.,10.,0.,20.])}
    result=tail.tail_summary(losses,groups,'0.625')
    assert result['var']==20 and result['es']==20 and result['tail_mass_draws']==1.5
    assert result['es_segment_contributions']=={'A':10.,'B':10.}
    assert result['boundary_tied_draws']==2 and result['boundary_tie_weight']==.75
    result=tail.tail_summary(np.array([0.,10.,20.,30.]),{'A':np.array([0.,10.,20.,30.])},'0.625')
    assert result['es']==pytest.approx(80/3)


def test_extreme_quantile_rank_interval_does_not_claim_sample_max_as_upper_bound():
    result=tail.tail_summary(np.arange(128,dtype=float),{'A':np.arange(128,dtype=float)},'0.999')
    assert result['var_order_stat_95_interval'][1] is None and result['var_interval_order_ranks'][1]==129


def test_seed_reproducibility_and_common_random_numbers_case_order_invariant():
    report,a,b=tail.simulate(plan(),positions()); repeated,c,d=tail.simulate(plan(),positions())
    assert report==repeated and a==c and b==d
    reversed_plan=plan(); reversed_plan['cases'].reverse(); _,e,_=tail.simulate(reversed_plan,positions())
    assert sorted(a,key=lambda r:(r['case_id'],r['draw_index']))==sorted(e,key=lambda r:(r['case_id'],r['draw_index']))
    assert all(r['total_loss']>=0 for r in a)


def test_native_currency_separate_and_pd_zero_one_boundaries():
    records=positions(); records[0]['pd']=0; records[1]['pd']=1; records[1]['currency']='VND'
    p=plan(); p['cases']=p['cases'][:1]; report,total,segments=tail.simulate(p,records)
    result={r['currency']:r for r in report['results']}
    assert result['USD']['mean_loss']==0 and result['VND']['mean_loss']==100
    assert result['VND']['analytic_expected_loss']==100 and report['global_cross_currency_total'] is None
    assert all(sum(r['es_segment_contributions'].values())==pytest.approx(r['es']) for v in result.values() for r in v['tails'])


def test_systemic_lgd_coupling_changes_expectation_and_disclosed_clipping():
    independent=tail.expected_loss(.1,.4,100,0,.1); coupled=tail.expected_loss(.1,.4,100,.3,.1)
    assert independent==pytest.approx(4,rel=1e-9) and coupled>independent
    records=positions(); records[0]['lgd']=records[1]['lgd']=.99
    p=plan(); report,_,_=tail.simulate(p,records)
    assert report['results'][1]['lgd_clipped_segment_draws']>0


@pytest.mark.parametrize('field,value',[('draws',True),('draws',127),('seed',-1),('alphas',['1']),('basis','validated_model')])
def test_invalid_simulation_contract(field,value):
    p=plan(); p[field]=value
    with pytest.raises(ValueError): tail.parameters(p,[],{})


def frozen(root):
    write_csv(root/'source.csv',rows()); write_new(root/'metadata.json',metadata())
    source_id=import_exposures(root,'source.csv','metadata.json')['import_id']
    write_new(root/'risk.json',scenario_assumptions(source_id)); scenario_id=scenario_build(root,'risk.json')['scenario_id']
    write_new(root/'tail.json',plan(scenario_id)); return tail.build(root,'tail.json')


def test_receipt_replay_rejects_forged_summary_with_updated_hash(tmp_path):
    receipt=frozen(tmp_path); folder,_,report=tail.verify(tmp_path,receipt['tail_id'])
    report['results'][0]['mean_loss']=999
    (folder/'report.json').write_text(json.dumps(report),encoding='utf-8'); receipt['outputs_sha256']['report.json']=sha256(folder/'report.json')
    (folder/'tail-complete.json').write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='replay'): tail.verify(tmp_path,receipt['tail_id'])


def test_source_changes_during_replay_rejected(tmp_path,monkeypatch):
    receipt=frozen(tmp_path); original=tail.simulate
    def changed(*args):
        result=original(*args); source_path=next((tmp_path/'artifacts/private').glob('exposure-import-*/source.csv'))
        source_path.write_text(source_path.read_text(encoding='utf-8').replace('segmentA','segmentB'),encoding='utf-8'); return result
    monkeypatch.setattr(tail,'simulate',changed)
    with pytest.raises(ValueError,match='source changed'): tail.verify(tmp_path,receipt['tail_id'])
