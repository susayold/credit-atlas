from decimal import Decimal
import pyarrow as pa
import pyarrow.parquet as pq
from credit_atlas.absee_profile import profile_file,MONEY
import pytest
from pathlib import Path
from credit_atlas import absee_profile as a

def write(tmp_path,rows):
    f=tmp_path/'sample.parquet';pq.write_table(pa.Table.from_pylist(rows),f);return f

def row(asset='private-key'):
    return {**{k:'10.00' for k in MONEY},'assetNumber':asset,'assetTypeNumber':'SPONSOR',
            'reportingPeriodBeginningDate':'01-01-2025','reportingPeriodEndingDate':'01-31-2025','currentDelinquencyStatus':'0'}

def test_exact_totals_dates_private_keys_and_zero(tmp_path):
    a=row();b=row('other');b['recoveredAmount']='0.00'
    report,keys=profile_file(write(tmp_path,[a,b]),'2025-01-31')
    assert report['rows']==2 and report['duplicate_key_rows']==0 and not report['invalid_by_field']
    assert Decimal(report['money_sums_exact']['recoveredAmount'])==10
    assert 'private-key' not in str(report)
    assert len(keys)==2 and report['raw_status_counts']=={'0':2}

def test_duplicates_bad_dates_nonfinite_and_missing_exposed(tmp_path):
    a=row();b=row();b['recoveredAmount']=None;b['originalLoanAmount']='NaN';b['reportingPeriodEndingDate']='02-28-2025'
    report,_=profile_file(write(tmp_path,[a,b]),'2025-01-31')
    assert report['duplicate_key_rows']==1
    assert report['invalid_by_field']=={'reporting_dates':1,'originalLoanAmount':1}
    assert report['missing_by_field']['recoveredAmount']==1
    assert report['money_sums_exact']['originalLoanAmount']=='10.00'

def test_negative_preserved_not_unconditionally_rejected(tmp_path):
    a=row();a['recoveredAmount']='-1.25'
    report,_=profile_file(write(tmp_path,[a]),'2025-01-31')
    assert report['negative_money_counts']=={'recoveredAmount':1}
    assert report['money_sums_exact']['recoveredAmount']=='-1.25'

def test_saved_scope_and_mutation_rejected(monkeypatch):
    root=Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError):a.saved_report(root,{'period':'2025-01-31'})
    monkeypatch.setattr(a,'source',lambda root:None)
    monkeypatch.setattr(a,'sha256',lambda path:'changed')
    with pytest.raises(ValueError):a.saved_report(root,{})

def test_saved_profile_qualification_and_gaps():
    r=a.saved_report(Path(__file__).resolve().parents[1],{})
    assert r['total_rows']==488219 and not r['model_ready'] and not r['source_value_fidelity_verified']
    assert len([x for x in r['linkage'] if x['adjacent_month']])==7
    assert len([x for x in r['linkage'] if not x['adjacent_month']])==3
    n=r['official_nissan_2024b_external_validation']
    assert n['audit']['row_month_observations']==1154259
    assert n['certificate_tieout']['check_counts']['pool_balance_exact']==23
    assert n['certificate_tieout']['check_counts']['chargeoff_event_count_matches']==20
    assert n['certificate_tieout']['check_counts']['first_code4_event_count_matches_certificate']==21
    assert n['certificate_tieout']['check_counts']['monthly_net_loss_equals_defaulted_principal_less_recoveries']==23
    assert n['certificate_tieout']['check_counts']['cumulative_net_loss_equals_sum_of_monthly_net_loss']==23
    july=next(p for p in n['certificate_tieout']['periods'] if p['report_date']=='2025-07-31')
    assert july['certificate_performance_kpis']['current_net_loss_ratio_pct']=='-0.39'
    assert july['certificate_performance_kpis']['monthly_net_losses']=='-316637.01'
    assert n['certificate_tieout']['check_counts']['recovered_amount_matches_current_total_recoveries']==17
    assert n['submission_history']['live_matches_acquisition_snapshot'] is True
    assert n['submission_history']['snapshot_latest_filing_date']=='2026-09-25'
    assert n['submission_history']['july_report_date_amendments']==[]
    assert n['recovery_dpd_exception_audit']['june_2025_delinquency']['exact_day_60_count_and_balance']=={'count':2,'balance':'50837.98000000'}
    assert n['dpd_boundary_diagnostic']['aggregate_exact_checks']=={'literal':178,'shifted':86}
    assert n['model_external_validation_completed'] is False
