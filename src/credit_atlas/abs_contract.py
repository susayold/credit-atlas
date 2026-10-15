"""Reviewed WOART 2025-A prospectus terms and bounded reported-term checks."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from copy import deepcopy
import re
import uuid

import pyarrow.parquet as pq

from .abs_servicer import verify_case, verify_source
from .workspace import contained, read_json, sha256, timestamp, write_new

PDF_SHA = 'dc34695537492fd7f452e3dd735d4938e76eedde87f441e127e94875e708e653'
SLOTS = ('A-1','A-2a','A-2b','A-3','A-4','B','C')
FACES = ('241400000.00','309760000.00','110000000.00','419760000.00','89300000.00','36760000.00','18380000.00')
COUPONS = ('0.04411','0.0449',None,'0.0473','0.0486','0.0508','0.0517')
FINALS = ('2026-02-17','2028-04-17','2028-04-17','2030-03-15','2030-11-15','2030-11-15','2031-10-15')
PAGES = {'issued_notes':[1], 'interest':[93,94], 'principal_order':[95,110],
         'review_trigger':[100], 'servicing':[105], 'pre_acceleration':[107,108],
         'reserve':[110,111,151], 'oc':[111,151], 'priority_principal':[150,151]}


def number(value):
    if not isinstance(value,(str,Decimal)):
        raise ValueError('Decimal or exact numeric string required')
    value=Decimal(value)
    if not value.is_finite():raise ValueError('Finite input required')
    return value


def money(value):
    value=number(value)
    if value<0 or value!=value.quantize(Decimal('.01')):
        raise ValueError('Nonnegative cent amount required')
    return value


def cents(value):
    return number(value).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)


def terms():
    return {'version':'WOART_2025_A_PROSPECTUS_2025_01_22','source_pdf_sha256':PDF_SHA,
        'source_url':'https://www.worldomni.com/abs/WOART_2025-A_Final_Prospectus.pdf',
        'review_basis':'Selected original prospectus pages read and cover/day-count/glossary rendered; not final agreement or amendment certification',
        'evidence_pdf_pages_one_based':deepcopy(PAGES),'currency':'USD','closing_date':'2025-01-29',
        'first_payment_date':'2025-02-18','tranches':[{'slot':s,'initial_face':f,'fixed_coupon':c,
            'day_count':'ACT/360' if s in ('A-1','A-2b') else '30/360',
            'sofr_spread':'0.0033' if s=='A-2b' else None,'coupon_floor':'0' if s=='A-2b' else None,
            'final_scheduled_payment_date':end} for s,f,c,end in zip(SLOTS,FACES,COUPONS,FINALS)],
        'principal_groups':[['A-1'],['A-2a','A-2b'],['A-3'],['A-4'],['B'],['C']],
        'reserve_initial':'3063404.27','reserve_base_fraction':'0.0025','reserve_discretionary_increase_possible':True,
        'oc_pool_fraction':'0.009','oc_initial_pool_floor_fraction':'0.005',
        'delinquency_review_threshold':'0.047','threshold_comparison':'strictly greater',
        'delinquency_denominator':'ending gross receivables, before YSOA deduction',
        'servicing_annual_fraction':'0.01','initial_servicing_proration':'Not numerically specified by implemented convention; not inferred from observed fee',
        'unsupported':['Benchmark fixing/publication and fallback changes','Final executed agreements and amendments',
            'Acceleration/event legal-state certification','Interest carryover and unpaid obligations',
            'Reserve draws, final-maturity cures and complete contractual waterfall',
            'Loan-level YSOA reconstruction','Initial servicing-fee proration calculation']}


def coupon(slot, benchmark=None):
    if slot not in SLOTS:raise ValueError('Unissued/unknown tranche')
    if slot=='A-2b':
        if benchmark is None:raise ValueError('Reported benchmark required')
        return max(Decimal(0),number(benchmark)+Decimal('.0033'))
    if benchmark is not None:raise ValueError('Fixed tranche cannot take benchmark input')
    return Decimal(COUPONS[SLOTS.index(slot)])


def interest(slot,balance,actual_days,fixed_days,benchmark=None):
    for value in (actual_days,fixed_days):
        if type(value) is not int or value<=0:raise ValueError('Positive integer accrual days required')
    days=actual_days if slot in ('A-1','A-2b') else fixed_days
    return cents(money(balance)*coupon(slot,benchmark)*Decimal(days)/Decimal(360))


def target_oc(ending_pool,initial_pool):
    return cents(max(money(ending_pool)*Decimal('.009'),money(initial_pool)*Decimal('.005')))


def allocate_principal(amount,balances):
    """Allocate a supplied funded amount; this does not calculate due amounts."""
    if set(balances)!=set(SLOTS):raise ValueError('Exactly seven issued balances required')
    original={s:money(balances[s]) for s in SLOTS}
    remaining=money(amount);payments={s:Decimal('0.00') for s in SLOTS}
    for group in terms()['principal_groups']:
        total=sum(original[s] for s in group)
        allocation=min(remaining,total)
        if len(group)==1:
            payments[group[0]]=allocation
        elif total:
            first,second=group
            # Explicit cent tie convention; residual goes to the other A-2 class.
            payments[first]=min(original[first],cents(allocation*original[first]/total))
            payments[second]=allocation-payments[first]
            if payments[second]>original[second]:
                payments[second]=original[second];payments[first]=allocation-payments[second]
        remaining-=allocation
    if sum(payments.values())+remaining!=money(amount):raise ValueError('Principal conservation failure')
    return {'payments':{s:str(payments[s]) for s in SLOTS},
        'ending_balances':{s:str(original[s]-payments[s]) for s in SLOTS},'unallocated':str(remaining)}


def methods():
    return {name:sha256(Path(__file__).with_name(name+'.py')) for name in ('abs_contract','abs_servicer','workspace')}


def evidence(root,case_id):
    case=verify_case(root,case_id)
    source,_=verify_source(root,case['source_id'])
    pdf=source/'WOART_2025-A_Final_Prospectus.pdf'
    if sha256(pdf)!=PDF_SHA:raise ValueError('Unsupported prospectus document version')
    folder=contained(root,'artifacts/private/'+case_id)
    metrics=pq.read_table(folder/'reported_metrics.parquet').to_pylist()
    index={(m['collection_end'],m['section'],m['slot'],m['metric']):m for m in metrics}
    raw=pq.read_table(folder/'source_cells.parquet').to_pylist()
    cells={(r['file'],r['sheet'],r['row'],r['column']):r for r in raw}
    checks=[];period_reports=[]
    initial=case['periods'][0]
    if initial['collection_end']!='2025-01-31':raise ValueError('Initial period required to establish source pool base')
    initial_pool=Decimal(index[(initial['collection_end'],'pool','','beginning_pool')]['value'])
    previous_payment=date.fromisoformat(terms()['closing_date'])
    for p in case['periods']:
        end=p['collection_end'];payment=date.fromisoformat(p['distribution_date'])
        actual_days=(payment-previous_payment).days;fixed_days=16 if end=='2025-01-31' else 30
        def n(section,key,slot=''):
            m=index[(end,section,slot,key)]
            if m['status']!='VALUE' or m['value'] is None:raise ValueError('Term input unavailable')
            return Decimal(m['value'])
        def check(name,expected,observed,tolerance=Decimal('.01'),pages=None):
            delta=observed-expected
            checks.append({'collection_end':end,'check':name,'expected':str(expected),'observed':str(observed),
                'delta':str(delta),'tolerance':str(tolerance),'pass':abs(delta)<=tolerance,'evidence_pdf_pages':pages or []})
        check('actual_days',Decimal(actual_days),n('pool','days_actual_360'),Decimal(0),PAGES['interest'])
        check('fixed_days',Decimal(fixed_days),n('pool','days_30_360'),Decimal(0),PAGES['interest'])
        balances={s:str(n('note_slot','beginning_balance',s)) for s in SLOTS}
        principal=allocate_principal(str(n('notes_total','total_principal_paid')),balances)
        unsupported_interest=[]
        for s,shortfall_row in zip(SLOTS,(221,226,231,236,241,246,251)):
            benchmark=str(n('note_slot','sofr_rate',s)) if s=='A-2b' else None
            expected_coupon=coupon(s,benchmark)
            check('coupon_'+s,expected_coupon,n('note_slot','coupon',s),Decimal('0.000000000001'),[1])
            carry=cells[(p['file'],p['sheet'],shortfall_row,2)]
            if carry['cell_type']!=2 or Decimal(carry['raw_value'])!=0:
                unsupported_interest.append(s)
            else:
                check('base_interest_'+s,interest(s,balances[s],actual_days,fixed_days,benchmark),
                    n('note_slot','interest_paid',s),pages=PAGES['interest'])
            check('funded_principal_allocation_'+s,Decimal(principal['payments'][s]),n('note_slot','payment_principal',s),pages=PAGES['principal_order'])
            if end=='2025-01-31':check('initial_face_'+s,Decimal(FACES[SLOTS.index(s)]),n('note_slot','beginning_balance',s),pages=[1])
        check('funded_principal_unallocated',Decimal(0),Decimal(principal['unallocated']),pages=PAGES['principal_order'])
        ending_pool=n('pool','ending_pool');ending_ysoa=n('pool','ending_ysoa')
        check('oc_target',target_oc(str(ending_pool),str(initial_pool)),n('pool','oc_target'),pages=PAGES['oc'])
        check('oc_actual',ending_pool-n('notes_total','ending_balance'),n('pool','oc_actual'),pages=[111])
        check('reserve_source_initial',Decimal(terms()['reserve_initial']),n('reserve','required_reserve'),pages=PAGES['reserve'])
        check('reserve_base_formula',cents(initial_pool*Decimal('.0025')),n('reserve','required_reserve'),pages=[151])
        numerator=sum(n('pool',k) for k in ('delinquent_61_90','delinquent_91_120','delinquent_121_plus'))
        gross=ending_pool+ending_ysoa
        if gross<=0:raise ValueError('Positive gross delinquency denominator required')
        ratio=numerator/gross
        check('reported_delinquency_fraction',ratio.quantize(Decimal('.0001'),rounding=ROUND_HALF_UP),
            n('pool','delinquent_61_plus_ratio'),Decimal(0),[100])
        flag=index[(end,'pool','','delinquency_trigger')]['value']
        expected_flag='YES' if ratio>Decimal('.047') else 'NO'
        checks.append({'collection_end':end,'check':'review_trigger','expected':expected_flag,'observed':flag,
            'pass':flag==expected_flag,'evidence_pdf_pages':[100]})
        if end!='2025-01-31':
            check('standard_month_servicing_fee',cents(n('pool','beginning_receivables')*Decimal('.01')/Decimal(12)),
                -n('flow','servicing_fee_signed'),pages=[105])
        period_reports.append({'collection_end':end,'distribution_date':p['distribution_date'],
            'actual_days':actual_days,'fixed_days':fixed_days,'funded_principal_allocation':principal,
            'delinquency_numerator_usd':str(numerator),'delinquency_denominator_usd':str(gross),
            'review_trigger_expected':expected_flag,'unsupported_interest_slots':unsupported_interest,
            'basis':'Prospectus base-interest/funded-principal and enhancement checks; legal regime and amendments not certified'})
        previous_payment=payment
    return {'case_id':case_id,'source_id':case['source_id'],'terms':terms(),'checks':checks,'period_reports':period_reports,
        'failed_checks':sum(not c['pass'] for c in checks),'unsupported_interest_periods':sum(bool(p['unsupported_interest_slots']) for p in period_reports),
        'case_receipt_sha256':sha256(folder/'case-complete.json'),'methods':methods(),
        'visibility':'private','public_release_approved':False,
        'qualification':{'full_contractual_waterfall':False,'loan_level_projection':False,'benchmark_fixing_independently_verified':False,
            'legal_regime_certified':False,'executed_agreements_and_amendments_verified':False}}


def build(root,case_id):
    report=evidence(root,case_id)
    identifier='abs-terms-'+uuid.uuid4().hex[:12]
    folder=contained(root,'artifacts/private/'+identifier);folder.mkdir(parents=True)
    report.update({'terms_id':identifier,'created_at':timestamp(),
        'status':'RECONCILED_REVIEWED_PROSPECTUS_TERMS' if report['failed_checks']==0 and report['unsupported_interest_periods']==0 else 'TERM_RECONCILIATION_INCOMPLETE'})
    write_new(folder/'terms-complete.json',report)
    verify(root,identifier)
    return report


def verify(root,identifier):
    if not re.fullmatch(r'abs-terms-[0-9a-f]{12}',identifier):raise ValueError('Invalid terms ID')
    report=read_json(contained(root,'artifacts/private/'+identifier+'/terms-complete.json'))
    rebuilt=evidence(root,report['case_id'])
    expected_status='RECONCILED_REVIEWED_PROSPECTUS_TERMS' if rebuilt['failed_checks']==0 and rebuilt['unsupported_interest_periods']==0 else 'TERM_RECONCILIATION_INCOMPLETE'
    if report.get('terms_id')!=identifier or report.get('status')!=expected_status:
        raise ValueError('Terms identity/status mismatch')
    if {k:v for k,v in report.items() if k not in ('terms_id','created_at','status')}!=rebuilt:
        raise ValueError('Term report differs from original source/implementation')
    return report
