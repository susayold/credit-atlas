"""Declared pre-acceleration WOART waterfall; cash/dues/source assumptions explicit."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import re
import uuid

import pyarrow.parquet as pq

from .abs_contract import SLOTS, FINALS, allocate_principal, cents, interest, money, target_oc, verify as verify_terms
from .abs_servicer import verify_case
from .workspace import contained, read_json, sha256, timestamp, write_new


def proportional(amount, obligations):
    """Integer-cent largest remainder, stable input order resolves exact ties."""
    values={s:money(v) for s,v in obligations.items()}
    total=sum(values.values());amount=money(amount)
    if amount>total:raise ValueError('Interest payment exceeds due amount')
    paid={s:Decimal('0.00') for s in values}
    if total:
        amount_cents=int(amount*100);total_cents=int(total*100)
        remainders={}
        for s,v in values.items():
            floor,remainder=divmod(amount_cents*int(v*100),total_cents)
            paid[s]=Decimal(floor)/Decimal(100);remainders[s]=remainder
        residual=int((amount-sum(paid.values()))*100)
        order=sorted(values,key=lambda s:remainders[s],reverse=True)
        for s in order[:residual]:paid[s]+=Decimal('.01')
    if sum(paid.values())!=amount or any(paid[s]>values[s] for s in values):
        raise ValueError('Interest pro-rata conservation failure')
    return paid


def run(inputs):
    required={'input_basis','regime','payment_date','available_funds','beginning_balances','interest_due',
        'ending_pool','oc_target','reserve_beginning','reserve_required','reviewer_fee_due',
        'reviewer_paid_ytd','reviewer_ytd_year','reviewer_is_sponsor_affiliate','certificate_redeposit'}
    required.update({'maturity_policy','terminal_release_instruction'})
    if not isinstance(inputs,dict) or set(inputs)!=required:
        raise ValueError('Complete explicit waterfall inputs required; unknown fields rejected')
    if inputs['input_basis'] not in ('DECLARED_SCENARIO','CONDITIONAL_REPORTED_REPLAY'):
        raise ValueError('Declared scenario or conditional source replay required')
    if inputs['regime']!='PRE_ACCELERATION':raise ValueError('Acceleration regime requires a different waterfall')
    if inputs['maturity_policy'] not in ('BLOCK_IF_OUTSTANDING','DECLARED_SEQUENTIAL_FLOOR_THEN_RESERVE_CURE'):
        raise ValueError('Explicit supported maturity policy required')
    if inputs['terminal_release_instruction'] not in ('BLOCK_IF_TERMINAL','HOLD_PENDING_FINAL_INSTRUCTION','DECLARED_FINAL_DISTRIBUTION_COMPLETE'):
        raise ValueError('Explicit terminal distribution instruction required')
    if not isinstance(inputs['payment_date'],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',inputs['payment_date']):
        raise ValueError('ISO payment date required')
    payment=date.fromisoformat(inputs['payment_date'])
    if type(inputs['reviewer_ytd_year']) is not int or inputs['reviewer_ytd_year']!=payment.year:
        raise ValueError('Fee YTD ledger must be explicitly reset to payment calendar year')
    if type(inputs['reviewer_is_sponsor_affiliate']) is not bool:
        raise ValueError('Explicit reviewer affiliation required')
    if (not isinstance(inputs['beginning_balances'],dict) or not isinstance(inputs['interest_due'],dict)
        or set(inputs['beginning_balances'])!=set(SLOTS) or set(inputs['interest_due'])!=set(SLOTS)):
        raise ValueError('Exactly seven issued balance and interest-due entries required')
    original={s:money(inputs['beginning_balances'][s]) for s in SLOTS}
    balances=original.copy();dues={s:money(inputs['interest_due'][s]) for s in SLOTS}
    if not sum(original.values()) and inputs['terminal_release_instruction']=='BLOCK_IF_TERMINAL':
        raise ValueError('All-notes-paid reserve release/final distribution instruction required')
    matured=[]
    for s,final in zip(SLOTS,FINALS):
        if payment>=date.fromisoformat(final) and original[s]>0:
            if inputs['maturity_policy']=='BLOCK_IF_OUTSTANDING':
                raise ValueError('Outstanding final-maturity/reserve cure requires declared policy')
            matured.append(s)
    cash=money(inputs['available_funds']);reserve=money(inputs['reserve_beginning'])
    pool=money(inputs['ending_pool']);oc=money(inputs['oc_target'])
    reserve_required=money(inputs['reserve_required']);fee_due=money(inputs['reviewer_fee_due'])
    fee_ytd=money(inputs['reviewer_paid_ytd']);redeposit=money(inputs['certificate_redeposit'])
    principal_paid={s:Decimal('0.00') for s in SLOTS};interest_paid=principal_paid.copy()
    ledger=[];invariants=[]
    def step(priority,name,due,eligible_reserve,internal_credit=False):
        nonlocal cash,reserve
        due=money(due);before_cash=cash;before_reserve=reserve
        from_cash=min(due,cash);cash-=from_cash
        draw=min(due-from_cash,reserve) if eligible_reserve else Decimal('0.00')
        reserve-=draw
        paid=from_cash+draw
        if internal_credit:reserve+=paid
        row={'sequence':len(ledger)+1,'priority':priority,'name':name,'due':str(due),'paid':str(paid),'shortfall':str(due-paid),
            'from_available_funds':str(from_cash),'reserve_draw':str(draw),'reserve_credit':str(paid if internal_credit else Decimal('0.00')),
            'cash_before':str(before_cash),'cash_after':str(cash),'reserve_before':str(before_reserve),'reserve_after':str(reserve),
            'external_distribution':not internal_credit}
        ledger.append(row)
        delta_cash=before_cash-from_cash-cash
        delta_reserve=before_reserve-draw+(paid if internal_credit else 0)-reserve
        invariants.append({'priority':priority,'cash_delta':str(delta_cash),'reserve_delta':str(delta_reserve),
            'pass':delta_cash==0 and delta_reserve==0 and cash>=0 and reserve>=0 and paid<=due})
        return paid
    def principal(priority,name,due,reserve_eligible):
        due=min(max(Decimal(0),due),sum(balances.values()))
        paid=step(priority,name,due,reserve_eligible)
        allocation=allocate_principal(str(paid),{s:str(v) for s,v in balances.items()})
        if Decimal(allocation['unallocated'])!=0:raise ValueError('Unallocated funded principal')
        for s in SLOTS:
            principal_paid[s]+=Decimal(allocation['payments'][s]);balances[s]=Decimal(allocation['ending_balances'][s])
        ledger[-1]['principal_by_tranche']=allocation['payments']
        return paid
    def pay_interest(priority,name,slots):
        subset={s:str(dues[s]) for s in slots}
        paid=step(priority,name,sum(dues[s] for s in slots),True)
        allocation=proportional(str(paid),subset)
        for s,v in allocation.items():interest_paid[s]+=v
        ledger[-1]['interest_by_tranche']={s:str(v) for s,v in allocation.items()}
        return paid
    low_fee_due=min(fee_due,max(Decimal(0),Decimal('150000.00')-fee_ytd))
    fee_low=step(1,'reviewer_within_annual_cap',low_fee_due,not inputs['reviewer_is_sponsor_affiliate'])
    pay_interest(2,'class_a_interest',SLOTS[:5])
    first=principal(3,'first_priority_principal',sum(original[s] for s in SLOTS[:5])-pool,True)
    pay_interest(4,'class_b_interest',('B',))
    second=principal(5,'second_priority_principal',sum(original[s] for s in SLOTS[:6])-pool-first,True)
    pay_interest(6,'class_c_interest',('C',))
    third=principal(7,'third_priority_principal',sum(original.values())-pool-first-second,True)
    reserve_deposit=step(8,'reserve_replenishment',max(Decimal(0),reserve_required-reserve),False,True)
    principal_total_due=min(sum(original.values()),max(Decimal(0),sum(original.values())-pool+oc))
    if matured:
        # Declared policy: clearing a mature class under sequential principal requires clearing its senior groups.
        mature_index=max(SLOTS.index(s) for s in matured)
        principal_total_due=max(principal_total_due,sum(original[s] for s in SLOTS[:mature_index+1]))
    principal(9,'regular_principal',max(Decimal(0),principal_total_due-first-second-third),False)
    maturity_cures=[]
    for group in (('A-1',),('A-2a','A-2b'),('A-3',),('A-4',),('B',),('C',)):
        eligible=[s for s in group if s in matured and balances[s]>0]
        if not eligible:continue
        paid=step(9,'declared_maturity_reserve_cure_'+'_'.join(group),sum(balances[s] for s in eligible),True)
        isolated={s:str(balances[s] if s in eligible else Decimal('0.00')) for s in SLOTS}
        allocation=allocate_principal(str(paid),isolated)
        for s in eligible:
            principal_paid[s]+=Decimal(allocation['payments'][s]);balances[s]=Decimal(allocation['ending_balances'][s])
        ledger[-1]['principal_by_tranche']=allocation['payments']
        maturity_cures.append({'slots':eligible,'paid':str(paid),'unpaid':str(sum(balances[s] for s in eligible))})
    if not sum(balances.values()) and inputs['terminal_release_instruction']=='BLOCK_IF_TERMINAL':
        raise ValueError('All-notes-paid reserve release/final distribution instruction required')
    fee_high=step(10,'remaining_reviewer_fee',fee_due-fee_low,False)
    residual=step(11,'certificate_residual',cash,False)
    if redeposit>residual:raise ValueError('Certificate redeposit exceeds residual; no funding inferred')
    certificate_paid=residual-redeposit
    all_settled=(not sum(balances.values()) and not sum(dues[s]-interest_paid[s] for s in SLOTS) and fee_due==fee_low+fee_high)
    release=Decimal('0.00');terminal='NOT_TERMINAL' if sum(balances.values()) else 'PENDING_FINAL_DISTRIBUTION_INSTRUCTION'
    if inputs['terminal_release_instruction']=='DECLARED_FINAL_DISTRIBUTION_COMPLETE':
        if not all_settled or redeposit:
            raise ValueError('Final distribution instruction requires all obligations settled and no collection redeposit')
        release=step(12,'declared_final_reserve_release_to_depositor',reserve,True)
        terminal='DECLARED_RELEASE_TO_DEPOSITOR'
    external=sum(interest_paid.values())+sum(principal_paid.values())+fee_low+fee_high+certificate_paid+redeposit+release
    delta=money(inputs['available_funds'])+money(inputs['reserve_beginning'])-external-reserve
    balance_delta=sum(original.values())-sum(principal_paid.values())-sum(balances.values())
    if delta!=0 or balance_delta!=0 or cash!=0 or not all(c['pass'] for c in invariants):
        raise ValueError('Waterfall conservation failure')
    return {'input_basis':inputs['input_basis'],'regime':inputs['regime'],'payment_date':inputs['payment_date'],
        'ledger':ledger,'step_invariants':invariants,'cash_conservation_delta':str(delta),'note_balance_delta':str(balance_delta),
        'principal_paid':{s:str(v) for s,v in principal_paid.items()},'interest_paid':{s:str(v) for s,v in interest_paid.items()},
        'ending_balances':{s:str(v) for s,v in balances.items()},
        'interest_unpaid':{s:str(dues[s]-interest_paid[s]) for s in SLOTS},
        'reviewer_fee_unpaid':str(fee_due-fee_low-fee_high),'reviewer_paid_ytd_ending':str(fee_ytd+fee_low+fee_high),
        'reserve_ending':str(reserve),'reserve_deposit':str(reserve_deposit),
        'reserve_draw_total':str(sum(Decimal(r['reserve_draw']) for r in ledger)),
        'certificate_paid':str(certificate_paid),'collection_account_redeposit':str(redeposit),
        'principal_total_due':str(principal_total_due),
        'maturity_policy':inputs['maturity_policy'],'maturity_cures':maturity_cures,
        'terminal_release_instruction':inputs['terminal_release_instruction'],'terminal_state':terminal,
        'reserve_release_to_depositor':str(release),
        'qualification':{'legal_regime_certified':False,'full_contractual_waterfall':False,'loss_allocated':False},
        'limits':['Available funds already net of servicing; sponsor-affiliate fees cannot draw reserve',
            'Interest due inputs must include externally established carryover; no automatic interest-on-shortfall accrual',
            'Final maturity uses explicitly declared sequential-floor then reserve-cure placement; ordering not executed-agreement certified',
            'Terminal reserve release requires explicit final-distribution instruction and settled obligations; pending instruction holds reserve',
            'Acceleration rejects rather than use pre-acceleration; no legal regime or final-distribution certification',
            'Pro-rata cent conventions declared: A-2 HALF_UP/residual; A-interest largest remainder/stable tranche order',
            'Step shortfall is unfunded priority amount, not automatic payment default/loss; overlapping priority shortfalls must not be summed',
            'Redeposit is declared instruction amount; final reserve release is separately paid to depositor']}


def methods():
    return {name:sha256(Path(__file__).with_name(name+'.py')) for name in
        ('abs_waterfall','abs_contract','abs_servicer','workspace')}


def replay_evidence(root,terms_id):
    term=verify_terms(root,terms_id)
    if term['failed_checks'] or term['unsupported_interest_periods']:
        raise ValueError('Reconciled term inputs required')
    case=verify_case(root,term['case_id']);folder=contained(root,'artifacts/private/'+case['case_id'])
    rows=pq.read_table(folder/'reported_metrics.parquet').to_pylist()
    metrics={(r['collection_end'],r['section'],r['slot'],r['metric']):r for r in rows}
    raw=pq.read_table(folder/'source_cells.parquet').to_pylist()
    cells={(r['file'],r['sheet'],r['row'],r['column']):r for r in raw}
    periods=[];checks=[];year=None;ytd=Decimal('0.00')
    initial_end=case['periods'][0]['collection_end']
    initial_pool=metrics[(initial_end,'pool','','beginning_pool')]['value']
    previous_payment=date(2025,1,29)
    for p in case['periods']:
        end=p['collection_end'];payment=date.fromisoformat(p['distribution_date'])
        if year!=payment.year:year=payment.year;ytd=Decimal('0.00')
        def value(section,key,slot=''):
            m=metrics[(end,section,slot,key)]
            if m['value'] is None or m['status']!='VALUE':raise ValueError('Replay source input unavailable')
            return m['value']
        # Current reports do not establish total reviewer fee obligations/legal state.
        # Reject nonzero observed reviewer/redeposit/shortfall paths; zero fee due is a disclosed assumption.
        for key in ('line_65','line_78','line_80'):
            if Decimal(value('distribution',key))!=0:raise ValueError('Reviewer/redeposit evidence needs extended source mapping')
        for row in (85,216,221,226,231,236,241,246,251):
            c=cells[(p['file'],p['sheet'],row,2)]
            if c['cell_type']!=2 or Decimal(c['raw_value'])!=0:
                raise ValueError('Reported servicing/interest shortfall path needs full obligation history')
        balances={s:value('note_slot','beginning_balance',s) for s in SLOTS}
        actual_days=(payment-previous_payment).days;fixed_days=16 if end=='2025-01-31' else 30
        interest_dues={s:str(interest(s,balances[s],actual_days,fixed_days,value('note_slot','sofr_rate',s) if s=='A-2b' else None)) for s in SLOTS}
        inputs={'input_basis':'CONDITIONAL_REPORTED_REPLAY','regime':'PRE_ACCELERATION',
            'payment_date':p['distribution_date'],'available_funds':value('flow','available_funds'),
            'beginning_balances':balances,'interest_due':interest_dues,'ending_pool':value('pool','ending_pool'),
            'oc_target':str(target_oc(value('pool','ending_pool'),initial_pool)),
            'reserve_beginning':value('reserve','beginning_balance'),'reserve_required':value('reserve','required_reserve'),
            'reviewer_fee_due':'0.00','reviewer_paid_ytd':str(ytd),'reviewer_ytd_year':year,
            'reviewer_is_sponsor_affiliate':False,'certificate_redeposit':'0.00',
            'maturity_policy':'BLOCK_IF_OUTSTANDING','terminal_release_instruction':'BLOCK_IF_TERMINAL'}
        result=run(inputs);ytd=Decimal(result['reviewer_paid_ytd_ending'])
        def check(name,expected,observed,tolerance=Decimal('.01')):
            delta=Decimal(expected)-Decimal(observed)
            checks.append({'collection_end':end,'check':name,'expected':expected,'reported':observed,
                'delta':str(delta),'tolerance':str(tolerance),'pass':abs(delta)<=tolerance})
        mapping={1:65,2:66,3:67,4:68,5:69,6:70,7:71,8:76,9:77,10:78,11:79}
        for stage in result['ledger']:
            check('distribution_line_'+str(mapping[stage['priority']]),stage['paid'],value('distribution','line_'+str(mapping[stage['priority']])))
        for s in SLOTS:
            for key,result_key in [('interest_paid','interest_paid'),('payment_principal','principal_paid'),('ending_balance','ending_balances')]:
                check(key+'_'+s,result[result_key][s],value('note_slot',key,s))
        check('reserve_ending',result['reserve_ending'],value('reserve','ending_balance'))
        check('reserve_net_movement',str(Decimal(result['reserve_deposit'])-Decimal(result['reserve_draw_total'])),value('reserve','deposit_withdrawal'))
        check('cash_conservation',result['cash_conservation_delta'],'0.00',Decimal(0))
        check('note_balance_conservation',result['note_balance_delta'],'0.00',Decimal(0))
        periods.append({'collection_end':end,'inputs':inputs,'result':result})
        previous_payment=payment
    return {'terms_id':terms_id,'case_id':case['case_id'],'methods':methods(),
        'terms_receipt_sha256':sha256(root/'artifacts/private'/terms_id/'terms-complete.json'),
        'periods':periods,'checks':checks,'failed_checks':sum(not c['pass'] for c in checks),
        'visibility':'private','public_release_approved':False,
        'conditional_assumptions':['PRE_ACCELERATION declared for replay, not independently verified legal state',
            'Reviewer total fees due and year-to-date fees assumed zero; paid-zero does not prove due-zero',
            'No prior unpaid/carryover interest assumed; zero reported shortfalls are necessary, not sufficient legal evidence',
            'No sponsor affiliation/instructions, executed agreement/amendment or benchmark fixing certification'],
        'qualification':{'full_contractual_waterfall':False,'legal_regime_certified':False,
            'obligation_completeness_certified':False,'realized_loss_model':False}}


def build_replay(root,terms_id):
    report=replay_evidence(root,terms_id)
    identifier='abs-waterfall-'+uuid.uuid4().hex[:12]
    output=contained(root,'artifacts/private/'+identifier);output.mkdir(parents=True)
    report.update({'waterfall_id':identifier,'created_at':timestamp(),
        'status':'CONDITIONAL_REPORTED_REPLAY_RECONCILED' if not report['failed_checks'] else 'REPLAY_DIFFERENCES_FOUND'})
    write_new(output/'waterfall-complete.json',report)
    verify_replay(root,identifier)
    return report


def verify_replay(root,identifier):
    if not re.fullmatch(r'abs-waterfall-[0-9a-f]{12}',identifier):raise ValueError('Invalid waterfall ID')
    report=read_json(contained(root,'artifacts/private/'+identifier+'/waterfall-complete.json'))
    rebuilt=replay_evidence(root,report['terms_id'])
    status='CONDITIONAL_REPORTED_REPLAY_RECONCILED' if not rebuilt['failed_checks'] else 'REPLAY_DIFFERENCES_FOUND'
    if report.get('waterfall_id')!=identifier or report.get('status')!=status:
        raise ValueError('Waterfall status/identity mismatch')
    if {k:v for k,v in report.items() if k not in ('waterfall_id','created_at','status')}!=rebuilt:
        raise ValueError('Waterfall report differs from source/methods/assumptions')
    return report
