import copy
from fractions import Fraction
import pytest
from credit_atlas import retail_subgroups as groups
from credit_atlas.workspace import sha256

def plan():
    return {'schema_version':1,'policy_id':'retail-policy-aaaaaaaaaaaa','freeze_id':'retail-freeze-bbbbbbbbbbbb','case_id':'declared',
        'dimensions':['sex','education','marriage','age_band'],'minimum_records':30,'minimum_class_records':10,'visibility':'private','public_release_approved':False}

def rows():
    return [{'source_client_id':i,'target':i%2,'probability':float(i%2),'SEX':1 if i<40 else 2,
        'EDUCATION':3,'MARRIAGE':1,'AGE':29 if i<40 else 50} for i in range(80)]

RULE={'id':'declared','lower_threshold':'0.2','upper_threshold':'0.5'}
def frac(v): return Fraction(int(v['numerator']),int(v['denominator']))

def test_perfect_scores_support_calibration_capture_and_full_dimension_reconciliation():
    result=groups.calculate(rows(),plan(),RULE); overall=result['overall']
    assert overall['records']==80 and overall['events']==40
    assert frac(overall['brier_score'])==0 and frac(overall['roc_auc'])==1
    assert frac(overall['high_risk_event_capture'])==1 and frac(overall['high_risk_non_event_flag_rate'])==0
    assert not any(result['qualification'].values()) and 'source_client_id' not in str(result)
    for dimension in plan()['dimensions']:
        selected=[r for r in result['groups'] if r['dimension']==dimension]
        assert sum(r['records'] for r in selected)==80 and sum(r['events'] for r in selected)==40

def test_tied_auc_and_single_class_support_are_not_fabricated():
    data=rows()
    for row in data: row['probability']=.5
    result=groups.calculate(data,plan(),RULE)
    assert frac(result['overall']['roc_auc'])==Fraction(1,2) and frac(result['overall']['brier_score'])==Fraction(1,4)
    for row in data: row['target']=0
    result=groups.calculate(data,plan(),RULE)
    assert result['overall']['roc_auc'] is None and result['overall']['high_risk_event_capture'] is None
    assert frac(result['overall']['event_rate'])==0

def test_small_unknown_groups_retained_with_unavailable_metrics_and_age_boundaries():
    data=rows();data[0]['AGE']=None;data[0]['SEX']=None;data[1]['EDUCATION']=0
    result=groups.calculate(data,plan(),RULE)
    tiny=next(r for r in result['groups'] if r['dimension']=='education' and r['bucket']=='source_code_0')
    assert tiny['records']==1 and tiny['mean_probability'] is None and tiny['event_rate'] is None
    assert next(r for r in result['coverage'] if r['dimension']=='age_band')['unavailable_or_invalid_records']==1
    assert [groups.bucket('age_band',v) for v in [18,29,30,39,40,49,50,120,121,True]]==['under_30','under_30','30_39','30_39','40_49','40_49','50_plus','50_plus','UNAVAILABLE_OR_INVALID','UNAVAILABLE_OR_INVALID']

@pytest.mark.parametrize('change',[{'dimensions':['sex','sex']},{'minimum_records':True},{'minimum_class_records':0},{'public_release_approved':True},{'dimensions':['income']}])
def test_strict_research_plan(change):
    with pytest.raises(ValueError): groups.calculate(rows(),plan()|change,RULE)

def test_duplicate_join_and_nonfinite_score_rejected():
    with pytest.raises(ValueError,match='identities'): groups.calculate(rows()+[rows()[0]],plan(),RULE)
    data=rows();data[0]['probability']=float('nan')
    with pytest.raises(ValueError,match='Finite'): groups.calculate(data,plan(),RULE)

def test_build_verify_replay_and_changed_join_source_rejected(tmp_path,monkeypatch):
    file=tmp_path/'source.txt';file.write_text('immutable')
    def source(root,recipe):return rows(),RULE,{'source.txt':sha256(file)}
    monkeypatch.setattr(groups,'source',source)
    result=groups.build(tmp_path,plan());_,receipt,report=groups.verify(tmp_path,result['subgroups_id'])
    assert report['overall']['records']==80 and receipt['final_test_scored'] is False
    file.write_text('changed')
    with pytest.raises(ValueError,match='input evidence'): groups.verify(tmp_path,result['subgroups_id'])
