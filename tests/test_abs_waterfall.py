import copy
import json
from decimal import Decimal

import pytest

from credit_atlas import abs_waterfall as waterfall


def inputs(**overrides):
    d={'input_basis':'DECLARED_SCENARIO','regime':'PRE_ACCELERATION','payment_date':'2025-02-18',
        'available_funds':'0.00','beginning_balances':{s:'100.00' if s=='A-1' else '0.00' for s in waterfall.SLOTS},
        'interest_due':{s:'0.00' for s in waterfall.SLOTS},'ending_pool':'100.00','oc_target':'0.00',
        'reserve_beginning':'0.00','reserve_required':'0.00','reviewer_fee_due':'0.00','reviewer_paid_ytd':'0.00',
        'reviewer_ytd_year':2025,'reviewer_is_sponsor_affiliate':False,'certificate_redeposit':'0.00',
        'maturity_policy':'BLOCK_IF_OUTSTANDING','terminal_release_instruction':'BLOCK_IF_TERMINAL'}
    d.update(overrides);return d


def stage(result,priority):return next(r for r in result['ledger'] if r['priority']==priority)


def check(result):
    assert Decimal(result['cash_conservation_delta'])==0 and Decimal(result['note_balance_delta'])==0
    assert all(x['pass'] for x in result['step_invariants'])
    assert all(Decimal(r['cash_after'])>=0 and Decimal(r['reserve_after'])>=0 for r in result['ledger'])


def test_due_and_paid_differ_and_later_priority_is_starved():
    d=inputs(available_funds='30.00',ending_pool='90.00')
    d['beginning_balances'].update({'B':'50.00','C':'10.00'})
    d['interest_due'].update({'A-1':'5.00','B':'5.00','C':'5.00'})
    r=waterfall.run(d);check(r)
    assert stage(r,3)['paid']=='10.00'
    assert stage(r,5)['due']=='50.00' and stage(r,5)['paid']=='10.00' and stage(r,5)['shortfall']=='40.00'
    assert stage(r,7)['due']=='50.00' and stage(r,7)['paid']=='0.00'
    assert r['interest_paid']['B']=='5.00' and r['interest_unpaid']['C']=='5.00'
    assert r['principal_paid']['A-1']=='20.00'
    assert r['qualification']['loss_allocated'] is False


def test_reserve_draw_is_exhausted_by_senior_interest():
    d=inputs(available_funds='50.00',reserve_beginning='40.00',reserve_required='40.00',ending_pool='1100.00')
    d['beginning_balances'].update({'A-1':'1000.00','B':'100.00'})
    d['interest_due'].update({'A-1':'100.00','B':'30.00'})
    r=waterfall.run(d);check(r)
    assert r['interest_paid']['A-1']=='90.00' and r['interest_unpaid']['A-1']=='10.00'
    assert r['interest_paid']['B']=='0.00' and r['interest_unpaid']['B']=='30.00'
    assert r['reserve_draw_total']=='40.00' and r['reserve_ending']=='0.00'
    assert stage(r,8)['due']=='40.00' and stage(r,8)['paid']=='0.00'


@pytest.mark.parametrize('affiliate,paid,reserve',[(True,'0.00','100.00'),(False,'10.00','90.00')])
def test_sponsor_affiliate_fee_cannot_take_reserve(affiliate,paid,reserve):
    r=waterfall.run(inputs(reviewer_fee_due='10.00',reserve_beginning='100.00',reserve_required='100.00',
        reviewer_is_sponsor_affiliate=affiliate))
    check(r);assert stage(r,1)['paid']==paid and r['reserve_ending']==reserve


def test_reviewer_cap_remainder_defers_until_after_notes_and_reserve():
    d=inputs(available_funds='100.00',reviewer_fee_due='100.00',reviewer_paid_ytd='149950.00')
    d['interest_due']['A-1']='20.00'
    r=waterfall.run(d);check(r)
    assert stage(r,1)['due']=='50.00' and stage(r,1)['paid']=='50.00'
    assert r['interest_paid']['A-1']=='20.00'
    assert stage(r,10)['paid']=='30.00' and r['reviewer_fee_unpaid']=='20.00'
    assert r['reviewer_paid_ytd_ending']=='150030.00'


def test_reserve_replenishment_precedes_oc_principal_and_certificate():
    d=inputs(available_funds='50.00',oc_target='20.00',reserve_beginning='5.00',reserve_required='15.00')
    r=waterfall.run(d);check(r)
    assert stage(r,8)['paid']=='10.00' and r['reserve_ending']=='15.00'
    assert stage(r,9)['paid']=='20.00' and r['ending_balances']['A-1']=='80.00'
    assert r['certificate_paid']=='20.00'


def test_oc_build_and_excess_reviewer_fees_cannot_draw_reserve():
    r=waterfall.run(inputs(oc_target='20.00',reserve_beginning='100.00',reserve_required='100.00',
        reviewer_paid_ytd='150000.00',reviewer_fee_due='10.00'))
    check(r);assert stage(r,9)['due']=='20.00' and stage(r,9)['paid']=='0.00'
    assert stage(r,10)['paid']=='0.00' and r['reserve_ending']=='100.00'


def test_class_a_interest_partial_payment_is_pro_rata():
    d=inputs(available_funds='20.00')
    d['interest_due'].update({'A-1':'10.00','A-2a':'30.00'})
    r=waterfall.run(d);check(r)
    assert r['interest_paid']['A-1']=='5.00' and r['interest_paid']['A-2a']=='15.00'
    assert r['interest_unpaid']['A-1']=='5.00' and r['interest_unpaid']['A-2a']=='15.00'


def test_pro_rata_cent_tie_is_stable_and_large_values_exact():
    assert waterfall.proportional('0.01',{'A':'1.00','B':'1.00'})=={'A':Decimal('.01'),'B':Decimal('0.00')}
    assert waterfall.proportional('0.01',{'A':'1000000000000000000000.00','B':'1000000000000000000000.01'})=={
        'A':Decimal('0.00'),'B':Decimal('.01')}
    with pytest.raises(ValueError):waterfall.proportional('2.00',{'A':'1.00'})


def test_sequential_a2_groups_split_at_each_principal_priority():
    d=inputs(available_funds='15.00',ending_pool='90.00',oc_target='5.00')
    d['beginning_balances'].update({'A-1':'0.00','A-2a':'75.00','A-2b':'25.00'})
    r=waterfall.run(d);check(r)
    assert stage(r,3)['paid']=='10.00' and stage(r,9)['paid']=='5.00'
    assert r['principal_paid']['A-2a']=='11.25' and r['principal_paid']['A-2b']=='3.75'
    assert r['ending_balances']['A-2a']=='63.75'


def test_declared_redelivery_is_not_counted_as_certificate_cash_paid():
    r=waterfall.run(inputs(available_funds='30.00',certificate_redeposit='12.00'))
    check(r);assert r['certificate_paid']=='18.00' and r['collection_account_redeposit']=='12.00'
    with pytest.raises(ValueError,match='exceeds residual'):
        waterfall.run(inputs(available_funds='1.00',certificate_redeposit='2.00'))


@pytest.mark.parametrize('change',[
    {'regime':'ACCELERATED'}, {'regime':'UNKNOWN'}, {'input_basis':'ACTUAL_CERTIFIED'},
    {'reviewer_ytd_year':2024}, {'reviewer_ytd_year':True}, {'reviewer_is_sponsor_affiliate':'false'},
    {'available_funds':'-1.00'}, {'reserve_beginning':'0.001'}, {'unknown_key':'ignored'},
    {'payment_date':'2026-02-17'}, {'payment_date':'2025-2-18'}])
def test_unknown_or_unsupported_branches_rejected(change):
    with pytest.raises(ValueError):waterfall.run(inputs(**change))


def test_terminal_reserve_release_does_not_use_normal_branch():
    with pytest.raises(ValueError,match='All-notes-paid'):
        waterfall.run(inputs(available_funds='100.00',ending_pool='0.00'))
    d=inputs();d['beginning_balances']['A-1']='0.00'
    with pytest.raises(ValueError,match='All-notes-paid'):waterfall.run(d)


def test_declared_maturity_floor_uses_cash_then_direct_reserve_cure():
    d=inputs(payment_date='2026-02-17',reviewer_ytd_year=2026,available_funds='30.00',ending_pool='1000.00',
        reserve_beginning='50.00',reserve_required='50.00',maturity_policy='DECLARED_SEQUENTIAL_FLOOR_THEN_RESERVE_CURE')
    d['beginning_balances']['B']='10.00'
    r=waterfall.run(d);check(r)
    assert r['principal_total_due']=='100.00' and stage(r,9)['paid']=='30.00'
    assert r['principal_paid']['A-1']=='80.00' and r['ending_balances']['A-1']=='20.00'
    assert r['reserve_ending']=='0.00' and r['maturity_cures'][0]['unpaid']=='20.00'
    assert r['ending_balances']['B']=='10.00'


def test_declared_a2_maturity_cure_does_not_pay_unmatured_a3():
    d=inputs(payment_date='2028-04-17',reviewer_ytd_year=2028,ending_pool='1000.00',reserve_beginning='40.00',
        reserve_required='40.00',maturity_policy='DECLARED_SEQUENTIAL_FLOOR_THEN_RESERVE_CURE')
    d['beginning_balances'].update({'A-1':'0.00','A-2a':'75.00','A-2b':'25.00','A-3':'100.00'})
    r=waterfall.run(d);check(r)
    assert r['principal_paid']['A-2a']=='30.00' and r['principal_paid']['A-2b']=='10.00'
    assert r['principal_paid']['A-3']=='0.00' and r['ending_balances']['A-3']=='100.00'


def test_terminal_hold_and_depositor_release_are_different():
    d=inputs(available_funds='120.00',ending_pool='0.00',reserve_beginning='10.00',reserve_required='10.00',
        terminal_release_instruction='HOLD_PENDING_FINAL_INSTRUCTION')
    r=waterfall.run(d);check(r)
    assert r['principal_paid']['A-1']=='100.00' and r['certificate_paid']=='20.00'
    assert r['reserve_ending']=='10.00' and r['reserve_release_to_depositor']=='0.00'
    assert r['terminal_state']=='PENDING_FINAL_DISTRIBUTION_INSTRUCTION'
    d['terminal_release_instruction']='DECLARED_FINAL_DISTRIBUTION_COMPLETE'
    r=waterfall.run(d);check(r)
    assert r['reserve_release_to_depositor']=='10.00' and r['reserve_ending']=='0.00'
    assert r['certificate_paid']=='20.00' and r['terminal_state']=='DECLARED_RELEASE_TO_DEPOSITOR'


def test_terminal_declaration_does_not_waive_unpaid_obligations():
    d=inputs(available_funds='100.00',ending_pool='0.00',terminal_release_instruction='DECLARED_FINAL_DISTRIBUTION_COMPLETE')
    d['interest_due']['A-1']='10.00'
    with pytest.raises(ValueError,match='settled'):waterfall.run(d)


def test_unknown_maturity_or_terminal_instruction_rejected():
    with pytest.raises(ValueError):waterfall.run(inputs(maturity_policy='DEFAULT'))
    with pytest.raises(ValueError):waterfall.run(inputs(terminal_release_instruction='TRUE'))


def test_terminal_release_cannot_leave_certificate_redeposit():
    with pytest.raises(ValueError,match='redeposit'):
        waterfall.run(inputs(available_funds='120.00',ending_pool='0.00',certificate_redeposit='10.00',
            terminal_release_instruction='DECLARED_FINAL_DISTRIBUTION_COMPLETE'))


def test_interest_obligations_are_mandatory_and_input_not_mutated():
    d=inputs();original=copy.deepcopy(d);waterfall.run(d);assert d==original
    del d['interest_due']['B']
    with pytest.raises(ValueError,match='seven'):waterfall.run(d)
    d=inputs();del d['reviewer_fee_due']
    with pytest.raises(ValueError,match='explicit'):waterfall.run(d)


def test_saved_replay_assumptions_and_payments_cannot_be_changed(tmp_path,monkeypatch):
    base={'terms_id':'term','failed_checks':0,'periods':[],
        'conditional_assumptions':['Reviewer due assumed zero'],'qualification':{'full_contractual_waterfall':False}}
    monkeypatch.setattr(waterfall,'replay_evidence',lambda root,id:copy.deepcopy(base))
    report=waterfall.build_replay(tmp_path,'term')
    folder=tmp_path/'artifacts/private'/report['waterfall_id']
    report['conditional_assumptions']=[]
    (folder/'waterfall-complete.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='differs'):waterfall.verify_replay(tmp_path,report['waterfall_id'])
