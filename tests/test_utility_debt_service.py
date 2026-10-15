from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import pytest
from credit_atlas import utility_debt_service as d

ROOT=Path(__file__).resolve().parents[1]

def test_distinct_lien_scopes_and_no_invented_compliance():
    total=d.report(ROOT,{})
    parity=d.report(ROOT,{'basis':'parity'})
    assert total['reported_dscr']=='2.51' and parity['reported_dscr']=='2.63'
    assert total['selected']['values']['net_revenues']=='526596219'
    assert total['selected']['values']['total_debt_service']=='209515790'
    assert Decimal(parity['actual_dscr_decimal50'])>Decimal(total['actual_dscr_decimal50'])
    assert all(total[k] is None for k in ['threshold','headroom','compliance'])
    assert total['contractual_compliance_qualified'] is False

def test_source_residuals_are_not_overwritten_and_zero_debt_is_retained():
    water=d.report(ROOT,{})['selected']
    waste=d.report(ROOT,{'system':'wastewater'})['selected']
    assert water['checks']['net_revenue_bridge_residual_usd']=='1'
    assert waste['checks']['maintenance_bridge_residual_usd']=='1'
    assert waste['values']['subordinate_debt_service']=='0'
    assert waste['checks']['recomputed_parity_dscr_decimal50']==waste['checks']['recomputed_total_dscr_decimal50']

def test_calendar_baseline_and_edition_revision_stay_separate():
    first=d.report(ROOT,{'year':'2021'})
    assert first['prior_year_dscr_decimal50'] is None and first['year_change_decimal50'] is None
    assert first['previous_edition_same_year']['edition']==2024
    assert first['selected']['values']['stabilization_deposits']=='-55000000'

def test_cross_source_rounding_discrepancy_is_visible():
    r=d.report(ROOT,{'system':'wastewater','year':'2024'})
    checks=[c for c in r['acfr_precision_comparisons'] if c['field']=='operation_maintenance']
    assert any(c['acfr_source_value']=='82.1' and c['continuing_value_at_acfr_precision']=='82.2' and not c['matches'] for c in checks)

@pytest.mark.parametrize('q',[{'year':'2026'},{'year':'2019'},{'edition':'2023'},{'system':'corporate'},{'basis':'interest'},{'year':2024},{'scope':'all'}])
def test_invalid_scope_fails_closed(q):
    with pytest.raises(ValueError):d.report(ROOT,q)

def test_source_tampering_fails_closed(monkeypatch):
    monkeypatch.setattr(d,'sha256',lambda p:'changed')
    with pytest.raises(ValueError,match='receipt changed'):d.report(ROOT,{})

def test_profile_tampering_fails_closed(monkeypatch):
    original=d.sha256
    monkeypatch.setattr(d,'sha256',lambda p:'changed' if p.name=='profile.json' else original(p))
    with pytest.raises(ValueError,match='profile changed'):d.report(ROOT,{})

def test_parser_rejects_ambiguous_or_incomplete_rows():
    with pytest.raises(ValueError,match='Ambiguous'):d.values('A 1 2 3 4 5 B A 1 2 3 4 5 B','A','B')
    with pytest.raises(ValueError,match='five annual'):d.values('A 1 2 3 B','A','B')
    assert d.values('A (55,000,000) 0 0 0 0 B','A','B')==['-55000000','0','0','0','0']

@pytest.mark.parametrize('edition',[2024,2025])
@pytest.mark.parametrize('system',['water','wastewater'])
@pytest.mark.parametrize('basis',['parity','total'])
def test_exact_driver_all_supported_calendar_pairs(edition,system,basis):
    for year in range(edition-3,edition+1):
        r=d.report(ROOT,{'edition':str(edition),'system':system,'basis':basis,'year':str(year)})
        driver=r['dscr_driver'];a=driver['current']['values'];b=driver['baseline']['values']
        assert r['year_change_decimal50']==driver['ratio_change']['decimal50']
        expected=Fraction(a['net_revenues'])/Fraction(a[basis+'_debt_service'])-Fraction(b['net_revenues'])/Fraction(b[basis+'_debt_service'])
        actual=sum((Fraction(int(x['effect_times']['numerator']),int(x['effect_times']['denominator'])) for x in driver['effects']),Fraction(0))
        assert actual==expected and driver['exact_residual']['numerator']=='0'
        assert driver['reconciles_exactly'] and not driver['causal_attribution_qualified']

def test_driver_missing_baseline_and_source_one_dollar_effect():
    first=d.report(ROOT,{'year':'2021'})['dscr_driver']
    assert first['baseline'] is None and first['effects']==[]
    driver=d.report(ROOT,{})['dscr_driver']
    residual=next(e for e in driver['effects'] if e['key']=='source_residual')
    assert residual['source_change_usd']=='1'
    assert Fraction(int(residual['effect_times']['numerator']),int(residual['effect_times']['denominator']))==Fraction(1,204802678)

def test_driver_rejects_zero_denominator_and_cross_edition_baseline():
    import copy
    r=d.report(ROOT,{})['dscr_driver'];current=copy.deepcopy(r['current']);prior=copy.deepcopy(r['baseline'])
    for row in [current,prior]:row.update(system='water',edition=2025)
    current['values']['total_debt_service']='0'
    with pytest.raises(ValueError,match='positive'):d.dscr_driver(current,prior,'total')
    prior['edition']=2024
    with pytest.raises(ValueError,match='same source'):d.dscr_driver(current,prior,'total')
