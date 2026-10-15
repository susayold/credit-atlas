import copy
from fractions import Fraction
import pytest
from credit_atlas import retail_policy as policy
from credit_atlas.retail_policy_views import RetailPolicyViews
from credit_atlas.workspace import read_json,sha256,write_new

FREEZE='retail-freeze-aaaaaaaaaaaa'

def plan():
    return {'schema_version':1,'freeze_id':FREEZE,'cost_unit':'declared_cost_units',
        'cost_matrix':{'accept':{'non_event':'0','event':'10'},'review':{'non_event':'1','event':'3'},'decline':{'non_event':'2','event':'0'}},
        'review_capacity':0,'cases':[{'id':'declared','lower_threshold':'0.2','upper_threshold':'0.5'}],
        'visibility':'private','public_release_approved':False}

def scores():
    return [{'source_client_id':i+1,'target':y,'probability':p} for i,(y,p) in enumerate([(0,0.),(1,.2),(0,.5),(1,1.)])]

def rational(value): return Fraction(int(value['numerator']),int(value['denominator']))

def test_boundary_ties_exact_cost_matrix_capacity_and_no_policy_qualification():
    report=policy.calculate(scores(),plan()); case=report['cases'][-1]
    assert [r['records'] for r in case['actions']]==[1,1,2]
    assert [r['events'] for r in case['actions']]==[0,1,1]
    assert rational(case['expected_declared_cost'])==Fraction(12,5)
    assert rational(case['retrospective_cost_proxy'])==5
    assert case['review_capacity_exceeded'] is True and case['review_overflow_records']==1
    assert not any(report['qualification'].values())
    assert 'source_client_id' not in str(report)
    assert sum(r['records'] for r in case['actions'])==report['records']

def test_empty_review_bucket_missing_rates_and_same_score_ties_remain_together():
    recipe=plan(); recipe['cases'][0]['upper_threshold']='0.2'; recipe['review_capacity']=None
    report=policy.calculate(scores()+[{'source_client_id':5,'target':0,'probability':.2}],recipe)
    case=report['cases'][-1]; review=case['actions'][1]
    assert review['records']==0 and review['event_rate'] is None and review['mean_probability'] is None
    assert case['review_capacity_exceeded'] is None and case['review_overflow_records'] is None
    assert case['actions'][2]['records']==4

@pytest.mark.parametrize('field,value',[('review_capacity',True),('review_capacity',-1),('schema_version',True),('public_release_approved',True),('cost_unit','TWD')])
def test_strict_recipe_contract(field,value):
    recipe=plan(); recipe[field]=value
    with pytest.raises(ValueError): policy.validate(recipe)

@pytest.mark.parametrize('value',['NaN','Infinity','-1','1e100000000',True,0.2])
def test_explicit_decimal_text_bounds(value):
    recipe=plan(); recipe['cost_matrix']['review']['event']=value
    with pytest.raises(ValueError): policy.calculate(scores(),recipe)

def test_reversed_thresholds_duplicate_ids_bad_scores_and_zero_costs():
    recipe=plan(); recipe['cases'][0]['lower_threshold']='0.8'
    with pytest.raises(ValueError,match='reversed'): policy.validate(recipe)
    recipe=plan(); recipe['cases']*=2
    with pytest.raises(ValueError,match='Unique'): policy.validate(recipe)
    with pytest.raises(ValueError,match='identities'): policy.calculate(scores()+[scores()[0]],plan())
    for probability in (float('nan'),1.1,True):
        rows=scores(); rows[0]['probability']=probability
        with pytest.raises(ValueError,match='finite'): policy.calculate(rows,plan())
    recipe=plan(); recipe['cost_matrix']={a:{'event':'0','non_event':'0'} for a in policy.ACTIONS}
    assert all(rational(r['expected_declared_cost'])==0 for r in policy.calculate(scores(),recipe)['cases'])

@pytest.fixture
def evidence(tmp_path,monkeypatch):
    source_file=tmp_path/'scores.txt'; source_file.write_text('fixed validation scores',encoding='utf-8')
    def source(root,freeze):
        assert root==tmp_path and freeze==FREEZE
        return scores(),{'freeze_id':FREEZE,'case_id':'case','assessment_id':'assessment','selected_model':'boosting',
            'selected_variant':'raw','inputs_sha256':{'scores.txt':sha256(source_file)}}
    monkeypatch.setattr(policy,'source',source)
    import credit_atlas.retail_policy_saved as saved_policy
    monkeypatch.setattr(saved_policy,'saved_source',source)
    import credit_atlas.retail_policy_views as views
    monkeypatch.setattr(views,'lineage_pins',lambda root,report:dict(report['inputs_sha256']))
    monkeypatch.setattr(views,'pinned_scores',lambda root,report:scores())
    identifier=policy.build(tmp_path,plan())['policy_id']
    return tmp_path,identifier,source_file

def test_complete_replay_source_binding_and_changed_source_rejected(evidence):
    root,identifier,source_file=evidence
    folder,receipt,report=policy.verify(root,identifier)
    assert report['records']==4 and not receipt['final_test_scored']
    view=RetailPolicyViews(root); query={'policy_id':identifier,'freeze_id':FREEZE}
    assert view.report(query)['records']==4
    with pytest.raises(ValueError,match='mismatch'): view.report({**query,'freeze_id':'retail-freeze-bbbbbbbbbbbb'})
    source_file.write_text('changed',encoding='utf-8')
    with pytest.raises(ValueError,match='lineage'): policy.verify(root,identifier)
    assert view.catalog(FREEZE)['policies']==[]

def test_semantic_cost_corruption_detected_even_with_updated_output_digest(evidence):
    root,identifier,_=evidence; folder=root/'artifacts/private'/identifier
    report=read_json(folder/'report.json'); report['cases'][-1]['expected_declared_cost']['numerator']='999'
    import json
    (folder/'report.json').write_text(json.dumps(report),encoding='utf-8')
    receipt=read_json(folder/'policy-complete.json'); receipt['outputs_sha256']['report.json']=sha256(folder/'report.json')
    (folder/'policy-complete.json').write_text(json.dumps(receipt),encoding='utf-8')
    with pytest.raises(ValueError,match='replay'): policy.verify(root,identifier)

def test_preview_requires_all_cost_inputs_preserves_source_and_saves_new_version(evidence):
    root,identifier,_=evidence; view=RetailPolicyViews(root)
    query={'policy_id':identifier,'freeze_id':FREEZE,'lower_threshold':'0.2','upper_threshold':'0.5','review_capacity':'2',
        **{a+'_'+y:value for a,row in plan()['cost_matrix'].items() for y,value in row.items()}}
    result=view.preview(query)
    assert result['status']=='UNSAVED_POLICY_PREVIEW' and not result['cases'][-1]['review_capacity_exceeded']
    fresh=view.save(result['assumptions'])['policy_id']; assert fresh!=identifier
    assert view.report({'policy_id':fresh,'freeze_id':FREEZE})['assumptions']==result['assumptions']
    with pytest.raises(ValueError,match='Exact'): view.preview({**query,'final_test':'true'})
    with pytest.raises(ValueError,match='Integer'): view.preview({**query,'review_capacity':'2.5'})

def test_cached_reports_skip_replay_but_hash_check_even_restored_file_metadata(evidence,monkeypatch):
    import os
    import credit_atlas.retail_policy_views as views
    root,identifier,source_file=evidence; original=views.verify; calls=[]
    def checked(*args):
        calls.append(args); return original(*args)
    monkeypatch.setattr(views,'verify',checked)
    view=RetailPolicyViews(root); query={'policy_id':identifier,'freeze_id':FREEZE}
    first=view.report(query); first['cases'].clear()
    assert len(view.report(query)['cases'])==4 and len(calls)==1
    stat=source_file.stat(); content=source_file.read_bytes()
    source_file.write_bytes(b'X'+content[1:]); os.utime(source_file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match='cached evidence'): view.report(query)
    assert len(calls)==1
