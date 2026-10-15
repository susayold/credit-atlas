"""Ratio movement attribution checked with independent rational arithmetic."""
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import pytest
from credit_atlas.sec_trends import driver_bridge, derive_trend
from tests.test_sec_trends import annual


def pair(n0,d0,n1,d1):
    prior,current=annual(2024),annual(2025)
    for s,n,d in [(prior,n0,d0),(current,n1,d1)]:
        r=s['ratios']['net_income_margin']
        s['fields'][r['numerator']]['value_exact']=str(n)
        s['fields'][r['denominator']]['value_exact']=str(d)
        r['value_exact']=str(Decimal(n)/Decimal(d)) if d else None
    return current,prior


@pytest.mark.parametrize('inputs',[(10,100,20,200),(-10,100,5,125),(0,100,-5,80),(7,3,11,9)])
def test_bridge_rational_identity_and_rounding(inputs):
    n0,d0,n1,d1=inputs;c,p=pair(*inputs);b=driver_bridge(c,p,'net_income_margin')
    assert b['status']=='SUPPORTED'
    for key,expected in [('numerator_effect_exact',Fraction(n1,d0)-Fraction(n0,d0)),('denominator_effect_exact',Fraction(n1,d1)-Fraction(n1,d0)),('total_change_exact',Fraction(n1,d1)-Fraction(n0,d0))]:
        assert abs(Fraction(Decimal(b[key]))-expected)<Fraction(1,10**58)
    assert abs(Decimal(b['rounding_residual_exact']))<=Decimal('1e-58')
    if inputs==(10,100,20,200):
        assert Decimal(b['total_change_exact'])==0 and Decimal(b['numerator_effect_exact'])==Decimal('.1') and Decimal(b['denominator_effect_exact'])==Decimal('-.1')


@pytest.mark.parametrize('kind,status',[('gap','NOT_ADJACENT_ANNUAL_PERIOD'),('concept','CONCEPT_MAPPING_CHANGED'),('missing','UNSUPPORTED_RATIO_INPUT'),('duration','ANNUAL_DURATION_CHANGED'),('zero','NONPOSITIVE_DENOMINATOR')])
def test_bridge_gate_no_older_fallback(kind,status):
    c,p=pair(10,100,20,200)
    if kind=='gap':p['report_date']='2022-12-31'
    if kind=='concept':p['fields']['revenue']['evidence'][0]['concept']='DifferentRevenue'
    if kind=='missing':p['ratios']['net_income_margin']['status']='missing_or_ambiguous_input'
    if kind=='duration':p['fields']['revenue']['start_date']='2024-02-01'
    if kind=='zero':p['fields']['revenue']['value_exact']='0'
    b=driver_bridge(c,p,'net_income_margin')
    assert b['status']==status and b['numerator_effect_exact'] is None


def test_ambiguous_period_breaks_bridge_linkage():
    a,b=pair(10,100,20,200);duplicate=deepcopy(b);duplicate['accession']='0001193125-25-000002'
    periods=derive_trend([a,b,duplicate],3)
    assert periods[-1]['comparisons']['net_income_margin']['driver_bridge']['status']=='NO_PRIOR_PERIOD'
