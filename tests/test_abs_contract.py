"""Prospectus-convention and allocation numerical acceptance, without private data."""
from decimal import Decimal
import json

import pytest

from credit_atlas import abs_contract as contract


def balances(**overrides):
    result={s:'0.00' for s in contract.SLOTS};result.update(overrides);return result


def test_issued_catalog_and_cover_dates():
    t=contract.terms()
    assert len(t['tranches'])==7 and sum(Decimal(r['initial_face']) for r in t['tranches'])==Decimal('1225360000.00')
    assert 'D' not in {r['slot'] for r in t['tranches']}
    assert t['first_payment_date']=='2025-02-18'
    t['evidence_pdf_pages_one_based']['issued_notes'].append(999)
    assert contract.terms()['evidence_pdf_pages_one_based']['issued_notes']==[1]


def test_interest_day_counts_use_different_initial_periods():
    assert contract.interest('A-1','241400000.00',20,16)==Decimal('591564.11')
    assert contract.interest('A-2a','309760000.00',20,16)==Decimal('618143.29')
    # Following months fixed interest uses thirty contractual days even if actual period is shorter.
    assert contract.interest('A-2a','100000.00',28,30)==Decimal('374.17')


def test_floating_spread_and_floor_without_claiming_fixing_verification():
    assert contract.coupon('A-2b','0.04')==Decimal('.0433')
    assert contract.coupon('A-2b','-0.0033')==Decimal(0)
    assert contract.coupon('A-2b','-0.02')==Decimal(0)
    assert contract.interest('A-2b','100000.00',28,30,'0.04')==Decimal('336.78')
    with pytest.raises(ValueError):contract.coupon('A-2b')
    with pytest.raises(ValueError):contract.coupon('A-3','0.04')
    with pytest.raises(ValueError):contract.coupon('D')


def test_oc_floor_and_stepdown_boundary():
    assert contract.target_oc('900.00','1000.00')==Decimal('8.10')
    assert contract.target_oc('100.00','1000.00')==Decimal('5.00')
    assert contract.target_oc('555.56','1000.00')==Decimal('5.00')
    assert contract.target_oc('556.67','1000.00')==Decimal('5.01')


def test_a2_is_pro_rata_and_remaining_principal_goes_sequentially():
    r=contract.allocate_principal('90.00',balances(**{'A-1':'10.00','A-2a':'60.00','A-2b':'20.00','A-3':'100.00'}))
    assert r['payments']=={'A-1':'10.00','A-2a':'60.00','A-2b':'20.00','A-3':'0.00','A-4':'0.00','B':'0.00','C':'0.00'}
    r=contract.allocate_principal('100.00',balances(**{'A-1':'10.00','A-2a':'60.00','A-2b':'20.00','A-3':'100.00'}))
    assert r['payments']['A-3']=='10.00'
    r=contract.allocate_principal('30.00',balances(**{'A-2a':'60.00','A-2b':'20.00','B':'50.00'}))
    assert r['payments']['A-2a']=='22.50' and r['payments']['A-2b']=='7.50' and r['payments']['B']=='0.00'


@pytest.mark.parametrize('amount',['0.00','0.01','0.02','0.03','0.04','2.00'])
def test_cent_ties_and_excess_cash_conserve_amount(amount):
    initial=balances(**{'A-2a':'0.01','A-2b':'0.01','C':'0.01'})
    r=contract.allocate_principal(amount,initial)
    assert sum(Decimal(x) for x in r['payments'].values())+Decimal(r['unallocated'])==Decimal(amount)
    for s in contract.SLOTS:
        assert Decimal(r['payments'][s])>=0 and Decimal(r['ending_balances'][s])>=0
        assert Decimal(r['payments'][s])+Decimal(r['ending_balances'][s])==Decimal(initial[s])
    if amount=='0.01':assert r['payments']['A-2a']=='0.01' and r['payments']['A-2b']=='0.00'


@pytest.mark.parametrize('amount',['-1.00','0.001','NaN','Infinity'])
def test_unfunded_invalid_cash_rejected(amount):
    with pytest.raises(ValueError):contract.allocate_principal(amount,balances())


def test_no_unknown_balances_or_float_inputs():
    b=balances();b['D']='0.00'
    with pytest.raises(ValueError):contract.allocate_principal('1.00',b)
    del b['D'];del b['A-1']
    with pytest.raises(ValueError):contract.allocate_principal('1.00',b)
    with pytest.raises(ValueError):contract.interest('A-1',1000.0,30,30)
    with pytest.raises(ValueError):contract.interest('A-1','1000.00',True,30)


def test_altered_terms_report_cannot_promote_qualification(tmp_path,monkeypatch):
    sample={'case_id':'case','failed_checks':0,'unsupported_interest_periods':0,
            'qualification':{'full_contractual_waterfall':False},'checks':[]}
    monkeypatch.setattr(contract,'evidence',lambda root,id:sample.copy())
    r=contract.build(tmp_path,'case')
    folder=tmp_path/'artifacts/private'/r['terms_id']
    r['qualification']={'full_contractual_waterfall':True}
    (folder/'terms-complete.json').write_text(json.dumps(r))
    with pytest.raises(ValueError,match='differs'):contract.verify(tmp_path,r['terms_id'])
