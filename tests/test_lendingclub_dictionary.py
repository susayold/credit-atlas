from pathlib import Path
import pytest
from credit_atlas import lendingclub_dictionary as d
ROOT=Path(__file__).resolve().parents[1]

def test_definitions_do_not_certify_prepared_scales_or_application_timing():
    r=d.report(ROOT,'dti')
    assert r['coverage']=={'prepared_columns':90,'exact_names':86,'proposed_aliases':2,'undefined':2}
    assert 'excluding mortgage and the requested LC loan' in r['selected_field']['issuer_definition']['source_description']
    assert 'income' in r['selected_field']['issuer_definition']['source_description']
    assert not r['selected_field']['application_time_qualified'] and not r['contributor_preprocessing_verified']

def test_modified_amount_alias_and_duplicate_outcome_are_distinct():
    amount=d.report(ROOT,'loan_amnt')['selected_field']
    assert 'reduces the loan amount' in amount['issuer_definition']['source_description']
    alias=d.report(ROOT,'SubGrade')['selected_field']
    assert alias['definition_mapping']=='proposed_alias_requires_contributor_provenance'
    assert alias['issuer_definition']['source_field']=='sub_grade'
    encoded=d.report(ROOT,'LoanStatus')['selected_field']
    assert encoded['issuer_definition'] is None and encoded['proposed_role']=='outcome_exclude'
    r=d.report(ROOT,'EmploymentLength')
    assert {'LoanStatus','loan_amnt','term','EmploymentLength','verification_status_joint'}<=set(r['candidate_exclusions_pending_review'])
    known=d.report(ROOT,'open_act_il')['selected_field']
    assert known['definition_mapping']=='exact_name' and not known['application_time_qualified']

@pytest.mark.parametrize('name',['acquisition-complete.json','LCDataDictionary.xlsx','profile.json'])
def test_dictionary_integrity_guards(monkeypatch,name):
    original=d.sha256
    monkeypatch.setattr(d,'sha256',lambda p:'changed' if p.name==name else original(p))
    with pytest.raises(ValueError,match='changed'):d.report(ROOT,'dti')

def test_unknown_field_rejected():
    with pytest.raises(ValueError):d.report(ROOT,'DefaultPD')
