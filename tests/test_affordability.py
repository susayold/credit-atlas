import copy
from fractions import Fraction
import pytest
from credit_atlas.affordability import assess,GROUPS

def item(ref,amount,period='monthly'):
    return {'ref':ref,'amount':amount,'period':period,'evidence_ref':None,'valid_through':None}

def payload():
    return {'case_ref':'qa-case','as_of':'2026-10-12','currency':'USD','scope':'individual','scope_ref':'qa-person','members':1,
        'coverage':{g:True for g in GROUPS},'gross_income':[item('gross','60000','annual')],'net_income':[item('net','4000')],
        'recurring_expenses':[item('living','1500')],'debt_payments':[item('mortgage','1000'),item('auto','500')],
        'proposed_payments':[item('new-loan','500')],'policy':{'policy_ref':'qa-policy','max_total_dti_fraction':'0.4','min_monthly_residual':'500'}}

def test_exact_average_months_total_debt_and_policy_boundaries():
    r=assess(payload());b=r['baseline']
    assert b['gross_monthly_income']['decimal50']=='5000' and b['monthly_total_debt']['decimal50']=='2000'
    assert b['total_dti_fraction']['decimal50']=='0.4' and b['monthly_residual_after_expenses_and_debt']['decimal50']=='500'
    assert b['dti_policy_comparison']=='WITHIN_DECLARED_LIMIT' and b['residual_policy_comparison']=='MEETS_DECLARED_FLOOR'
    assert r['credit_decision'] is None and not r['income_verification_qualified'] and not r['policy_confirmed']

def test_income_sensitivity_changes_results_without_overwriting_declared_baseline():
    p=payload();p['stress']={'gross_income_reduction_fraction':'0.1','net_income_reduction_fraction':'0.25','extra_monthly_expense':'250'}
    original=copy.deepcopy(p);r=assess(p)
    assert p==original and r['baseline']['monthly_residual_after_expenses_and_debt']['decimal50']=='500'
    s=r['stress']['results'];assert s['monthly_residual_after_expenses_and_debt']['decimal50']=='-750'
    assert s['dti_policy_comparison']=='EXCEEDS_DECLARED_LIMIT' and s['residual_policy_comparison']=='BELOW_DECLARED_FLOOR'

def test_partial_income_missing_payment_and_expired_inputs_stay_unavailable():
    p=payload();p['coverage']['gross_income']=False;r=assess(p)
    assert r['groups']['gross_income']['known_monthly_sum']['decimal50']=='5000' and r['baseline']['total_dti_fraction'] is None
    assert r['baseline']['monthly_residual_after_expenses_and_debt'] is not None
    p=payload();p['proposed_payments'][0]['amount']=None;r=assess(p)
    assert r['baseline']['monthly_total_debt'] is None and r['baseline']['monthly_residual_after_expenses_and_debt'] is None
    p=payload();p['net_income'][0]['valid_through']='2026-10-11';r=assess(p)
    assert r['baseline']['monthly_residual_after_expenses_and_debt'] is None and r['baseline']['total_dti_fraction'] is not None

def test_zero_income_differs_from_missing_and_no_policy_is_invented():
    p=payload();p['gross_income'][0]['amount']='0';p['policy']={'policy_ref':None,'max_total_dti_fraction':None,'min_monthly_residual':None}
    r=assess(p);assert r['baseline']['dti_unavailable_reason']=='zero_gross_income' and r['baseline']['dti_policy_comparison']=='UNAVAILABLE'

@pytest.mark.parametrize('period,factor',[('weekly',Fraction(13,3)),('biweekly',Fraction(13,6)),('semimonthly',Fraction(2)),('quarterly',Fraction(1,3))])
def test_period_factors_are_rational_and_explicit(period,factor):
    p=payload();p['gross_income']=[item('gross','1',period)];value=assess(p)['baseline']['gross_monthly_income']
    assert Fraction(int(value['numerator']),int(value['denominator']))==factor

@pytest.mark.parametrize('value',['-1','NaN','inf','1e10','1,000',1000,True])
def test_invalid_amount_encodings_rejected(value):
    p=payload();p['gross_income'][0]['amount']=value
    with pytest.raises(ValueError):assess(p)

def test_duplicate_obligations_unknown_fields_and_invalid_household_rejected():
    p=payload();p['recurring_expenses'][0]['ref']='mortgage'
    with pytest.raises(ValueError,match='Duplicate obligation'):assess(p)
    p=payload();p['credit_limit']='100000'
    with pytest.raises(ValueError,match='Unknown'):assess(p)
    p=payload();p['members']=True
    with pytest.raises(ValueError):assess(p)
