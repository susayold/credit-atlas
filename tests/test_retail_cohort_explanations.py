import math
import numpy as np
import pytest
from credit_atlas import retail_cohort_explanations as cohort
from credit_atlas import retail_explanations as base
from credit_atlas.workspace import sha256
from tests.test_retail_explanations import fixture, plan as base_plan


def plan():
    return {'schema_version':1,'freeze_id':base_plan()['freeze_id'],'explanations_id':'retail-explanations-aaaaaaaaaaaa',
            'visibility':'private','public_release_approved':False}


def inputs():
    train,validation,scores,names,predict=fixture()
    parent,private=base.calculate(train,validation,scores,names,predict,base_plan())
    parent.update(selected_model='logistic',selected_variant='raw')
    reference=np.asarray([next(r['features'] for r in train if r['source_client_id']==i) for i in private['background_source_ids']])
    return validation,scores,reference,base.grouped_columns(names),predict,parent,private


def test_full_coverage_batch_boundary_reconstruction_distribution_and_original_parity():
    validation,scores,ref,columns,predict,parent,private=inputs()
    report,rows=cohort.calculate(validation,scores,ref,columns,predict,plan(),parent,private)
    assert report['records']==40 and len(rows)==40 and report['original_example_parity_records']==12
    assert {r['score_rank'] for r in rows}==set(range(1,41)) and len({r['client_token'] for r in rows})==40
    assert all(cohort.TOKEN.fullmatch(r['client_token']) for r in rows)
    assert report['maximum_absolute_reconstruction_residual']<1e-12
    for row in rows:
        assert row['reference_probability']+sum(row[g] for g in columns)==pytest.approx(row['predicted_probability'],abs=1e-12)
    for row in report['global_group_contributions']:
        assert row['positive_records']+row['negative_records']+row['zero_records']==40
        expected=np.mean([abs(r[row['group']]) for r in rows])
        assert row['mean_absolute_probability_contribution']==pytest.approx(expected,abs=1e-14)
    # Scalar and batched computations agree at the last, partial batch.
    single=cohort.explain_batch(np.asarray([validation[-1]['features']]),ref,columns,predict)[0]
    assert all(single[k]==pytest.approx(rows[-1][k],abs=1e-14) for k in single)


def test_probability_partition_duplicate_and_invalid_tensor_guards():
    validation,scores,ref,columns,predict,parent,private=inputs()
    wrong=[dict(r) for r in scores]; wrong[0]['probability']+=.01
    with pytest.raises(ValueError,match='probability parity'):cohort.calculate(validation,wrong,ref,columns,predict,plan(),parent,private)
    invalid=[dict(r) for r in validation]; invalid[0]['partition']='final_test'
    with pytest.raises(ValueError,match='validation identities'):cohort.calculate(invalid,scores,ref,columns,predict,plan(),parent,private)
    duplicate=[dict(r) for r in validation]; duplicate[1]['source_client_id']=duplicate[0]['source_client_id']
    duplicate_scores=[dict(r) for r in scores]; duplicate_scores[1]['source_client_id']=duplicate_scores[0]['source_client_id']
    with pytest.raises(ValueError,match='Unique validation'):cohort.calculate(duplicate,duplicate_scores,ref,columns,predict,plan(),parent,private)
    import copy
    corrupted=copy.deepcopy(parent);corrupted['local_explanations'][0]['contributions'][0]['probability_contribution']+=.1
    with pytest.raises(ValueError,match='Original local explanation parity'):cohort.calculate(validation,scores,ref,columns,predict,plan(),corrupted,private)
    with pytest.raises(ValueError,match='Bounded finite'):cohort.explain_batch(np.zeros((33,ref.shape[1])),ref,columns,predict)
    with pytest.raises(ValueError,match='coalition probabilities'):cohort.explain_batch(np.zeros((1,ref.shape[1])),ref,columns,lambda x:np.full(len(x),math.nan))


@pytest.mark.parametrize('change',[{'schema_version':True},{'public_release_approved':True},{'freeze_id':'../escape'},{'explanations_id':'wrong'}])
def test_exact_plan(change):
    with pytest.raises(ValueError):cohort.validate(plan()|change)


def test_immutable_whole_cohort_replay_and_corruption(tmp_path,monkeypatch):
    file=tmp_path/'source.txt'; file.write_text('fixed evidence')
    validation,scores,ref,columns,predict,parent,private=inputs()
    monkeypatch.setattr(cohort,'source',lambda root,p:(validation,scores,ref,columns,predict,{'source.txt':sha256(file)},parent,private))
    identifier=cohort.build(tmp_path,plan())['cohort_id']
    _,_,report,rows=cohort.verify(tmp_path,identifier)
    assert report['records']==len(rows)==40
    file.write_text('corrupt evidence')
    with pytest.raises(ValueError,match='input evidence'):cohort.verify(tmp_path,identifier)
