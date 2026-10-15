import json
import pytest
from credit_atlas import exposure_convergence as c
from credit_atlas.exposure_tail import verify as tail_verify
from credit_atlas.workspace import sha256,write_new
from tests.test_exposure_tail import frozen


def plan(identifier):
    return {'schema_version':1,'tail_id':identifier,'seeds':[42,43],'draw_counts':[128,256],
        'visibility':'private','public_release_approved':False}


@pytest.mark.parametrize('field,value',[('seeds',[42,42]),('seeds',[True,43]),('draw_counts',[256,128]),('draw_counts',[127,256]),('public_release_approved',True)])
def test_invalid_contract(field,value):
    p=plan('exposure-tail-000000000000'); p[field]=value
    with pytest.raises(ValueError): c.validate(p)


def test_replay_diagnostics_and_no_certification(tmp_path):
    base=frozen(tmp_path); write_new(tmp_path/'convergence.json',plan(base['tail_id']))
    receipt=c.build(tmp_path,'convergence.json'); folder,_,report=c.verify(tmp_path,receipt['convergence_id'])
    assert len(report['runs'])==4 and not report['contract']['statistical_convergence_certified']
    for d in report['diagnostics']:
        assert [v['draws'] for v in d['levels']]==[128,256]
        assert len(d['last_two_level_changes'])==4
        for v in d['levels']:
            assert v['mean_loss']['seed_min']<=v['mean_loss']['seed_mean']<=v['mean_loss']['seed_max']
    report['diagnostics'][0]['levels'][0]['mean_loss']['seed_mean']+=1
    (folder/'report.json').write_text(json.dumps(report),encoding='utf-8')
    receipt['outputs_sha256']['report.json']=sha256(folder/'report.json')
    (folder/'convergence-complete.json').write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='replay'): c.verify(tmp_path,receipt['convergence_id'])


def test_last_level_seed_support_derived_from_actual_runs():
    from tests.test_exposure_tail import positions,plan as tail_plan
    p=plan('exposure-tail-000000000000'); base={'source_import_id':'fixture','assumptions':tail_plan()}
    report=c.calculate(p,base,positions()); d=report['diagnostics'][0]
    values=[r['mean_loss'] for run in report['runs'] if run['draws']==256 for r in run['results'] if r['id']==d['case_id']]
    assert d['levels'][-1]['mean_loss']['seed_mean']==sum(values)/2
