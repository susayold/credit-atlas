import json
from datetime import date
from pathlib import Path
import pytest
from crsl.features import OriginationEncoder
from crsl.splits import split_records

CONFIG=json.loads((Path(__file__).resolve().parents[1]/'configs/split.json').read_text())

def sample(year=2012,known=date(2013,2,1),landmark=date(2012,2,1)):
    return {'loan_id':'synthetic','origination_year':year,'label_known_month':known,'landmark':landmark,'target':1}

def test_missing_vintages_never_training_ready():
    output,audit=split_records([sample()],CONFIG)
    assert output[0]['partition']=='train'
    assert not audit['training_ready']
    assert 2018 in audit['missing_years']

def test_label_on_fit_boundary_excluded():
    output,_=split_records([sample(known=date(2014,1,1))],CONFIG)
    assert output[0]['reason']=='label_not_mature_before_fit'

def test_duplicate_loan_fails():
    with pytest.raises(ValueError,match='more than once'): split_records([sample(),sample()],CONFIG)

def test_overlap_fails():
    with pytest.raises(ValueError,match='Overlapping'): split_records([],dict(CONFIG,test_years=[2012]))

def test_latest_release_cannot_claim_strict_pit():
    with pytest.raises(ValueError,match='strict'): split_records([],dict(CONFIG,claim='strict_pit'))

def test_test_is_locked_and_not_training():
    output,_=split_records([sample(2018,date(2019,2,1),date(2018,2,1))],CONFIG)
    assert output[0]['partition']=='test' and output[0]['test_locked']

def test_fit_refuses_validation_rows():
    encoder=OriginationEncoder({'numeric':['classic_fico'],'categorical':[]})
    with pytest.raises(ValueError,match='training'): encoder.fit([{'partition':'test','included':True,'classic_fico':800}])

def test_forbidden_feature_refused():
    with pytest.raises(ValueError,match='allowlist'): OriginationEncoder({'numeric':['actual_loss'],'categorical':[]})

def test_unseen_schema_and_extra_future_column_ignored():
    encoder=OriginationEncoder({'numeric':['classic_fico'],'categorical':['occupancy']})
    encoder.fit([{'partition':'train','included':True,'classic_fico':700,'occupancy':'P'},
                 {'partition':'train','included':True,'classic_fico':800,'occupancy':None}])
    before=json.dumps(encoder.state,sort_keys=True)
    row={'classic_fico':None,'occupancy':'NEW'}
    actual=encoder.transform([dict(row,actual_loss=999999)])[0]
    assert actual==encoder.transform([row])[0]
    assert len(actual)==len(encoder.state['feature_names'])
    assert actual[encoder.state['feature_names'].index('occupancy=__unseen__')]==1
    assert json.dumps(encoder.state,sort_keys=True)==before

def test_all_missing_and_literal_reserved_category():
    encoder=OriginationEncoder({'numeric':['classic_fico'],'categorical':['occupancy']})
    encoder.fit([{'partition':'train','included':True,'classic_fico':None,'occupancy':'__missing__'}])
    assert encoder.state['numeric']['classic_fico']['all_missing_train']
    assert encoder.transform([{'classic_fico':None,'occupancy':None}])!=encoder.transform([{'classic_fico':None,'occupancy':'__missing__'}])


def test_model_runner_rederives_each_split_assignment():
    from crsl.models.train import verify_split_assignments
    rows = [sample(), dict(sample(), loan_id='second')]
    assignments, audit = split_records(rows, CONFIG)
    assert verify_split_assignments(rows, list(reversed(assignments)), CONFIG, audit) == audit
    assignments[0]['partition'] = 'validation'
    with pytest.raises(ValueError, match='assignments differ'):
        verify_split_assignments(rows, assignments, CONFIG, audit)


def test_model_runner_rejects_forged_support_even_if_assignments_match():
    from crsl.models.train import verify_split_assignments
    rows = [sample()]
    assignments, audit = split_records(rows, CONFIG)
    audit['support']['train']['positive'] += 1
    with pytest.raises(ValueError, match='recomputed support'):
        verify_split_assignments(rows, assignments, CONFIG, audit)
