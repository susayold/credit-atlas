from pathlib import Path
import pytest
from credit_atlas import lendingclub_temporal as d
ROOT=Path(__file__).resolve().parents[1]

def test_activity_and_schedule_dates_do_not_become_cutoff_or_mature_labels():
    r=d.report(ROOT,'accepted','2007-06','2018-12','all')
    assert {x['field']:x['max_observed_month'] for x in r['date_profiles']}=={'issue_d':'2018-12','last_pymnt_d':'2019-03','last_credit_pull_d':'2019-04','next_pymnt_d':'2019-05'}
    assert r['summary']['last_payment_span_at_least_12m']==1519965
    assert r['summary']['last_credit_pull_before_booking']==2255
    assert r['certified_observation_cutoff'] is None and r['fixed_horizon_pd12_labels'] is None
    assert not r['maturity_qualified'] and not r['model_training_performed']
    assert r['whole_source_missing_member_id']==2260701

def test_current_status_filter_and_global_date_profile_are_separate():
    r=d.report(ROOT,'accepted','2018-01','2018-12','Current')
    assert r['summary']['records']<878317
    assert all(x['source_loan_status']=='Current' and x['issue_month'].startswith('2018') for x in r['cohorts'])
    assert r['date_profile_scope']=='whole_accepted_source_not_window_filtered'
    missing=d.report(ROOT,'accepted','2007-06','2018-12','__missing__')
    assert missing['cohorts']==[] and missing['whole_source_unavailable_booking_month']==33

def test_rejected_does_not_get_accepted_loan_followup():
    r=d.report(ROOT,'rejected','2007-05','2018-12','all')
    assert not r['applicable'] and 'cohorts' not in r and r['fixed_horizon_pd12_labels'] is None

def test_temporal_profile_tampering_is_rejected(monkeypatch):
    monkeypatch.setattr(d,'sha256',lambda p:'changed')
    with pytest.raises(ValueError,match='profile changed'):d.report(ROOT,'accepted','2007-06','2018-12','all')
