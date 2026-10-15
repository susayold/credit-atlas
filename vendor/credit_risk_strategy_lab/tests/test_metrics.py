import pytest
from crsl.metrics import ratio,validate_monthly

def row():
    return dict(period='fixture-month',reported_loans=10,active_loans=8,terminal_loans=2,
      state_usable_active_loans=7,unknown_active_loans=1,d3_active_loans=2,reo_active_loans=1,
      missing_active_balance_loans=0,d3_active_upb=100,state_usable_active_upb=1000,
      d3_count_share=2/7,d3_balance_share=.1)

def test_count_and_balance_are_different_denominators():
    assert validate_monthly([row()])['months_checked']==1
    with pytest.raises(ValueError,match='Rate'): validate_monthly([{**row(),'d3_balance_share':2/7}])

def test_undefined_not_zero():
    data={**row(),'d3_active_upb':None,'state_usable_active_upb':0,'d3_balance_share':0}
    with pytest.raises(ValueError,match='Undefined'): validate_monthly([data])
    data['d3_balance_share']=None
    assert validate_monthly([data])['status']=='PASS'

@pytest.mark.parametrize('n,d',[(2,1),(-1,2),(1,-2),(float('nan'),1),(1,float('inf'))])
def test_invalid_ratio(n,d):
    with pytest.raises(ValueError): ratio(n,d)

def test_empty_output_not_zero():
    with pytest.raises(ValueError,match='Empty'): validate_monthly([])

def test_reconciliation():
    with pytest.raises(ValueError,match='reconciliation'): validate_monthly([{**row(),'active_loans':9}])

def test_duplicates():
    with pytest.raises(ValueError,match='Duplicate'): validate_monthly([row(),row()])
