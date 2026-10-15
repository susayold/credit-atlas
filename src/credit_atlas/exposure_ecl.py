"""Declared research staging and probability-weighted discounted cash shortfalls."""
import json
import re
import shutil
import uuid
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from .exposure_scenarios import exact as scenario_exact,methods as scenario_methods,read_plan,source
from .exposure_imports import text
from .exposure_movements import guard
from .workspace import contained,read_json,sha256,timestamp,write_new

PLAN_KEYS={'schema_version','name','version','basis','source_import_id','eligible_source_states',
    'benchmark_comparison_basis','cash_convention','staging_policy','segments','scenarios','visibility','public_release_approved'}
SEGMENT_KEYS={'remaining_months','monthly_effective_rate','principal_due_factors','benchmark_hazards',
    'assessment_hazards','declared_dpd','declared_credit_impaired','qualitative_sicr','poci','revolving','cure_under_review'}


def methods(): return {**scenario_methods(),'exposure_ecl':sha256(Path(__file__))}


def exact(value):
    value=Fraction(value)
    if max(value.numerator.bit_length(),value.denominator.bit_length())>13000:
        raise ValueError('Exact rational output exceeds research serialization bound')
    return scenario_exact(value)


def fraction(value):
    if not isinstance(value,str) or not re.fullmatch(r'(?:0|[1-9]\d{0,3})(?:\.\d{1,6})?',value):
        raise ValueError('Bounded decimal string, at most six fractional digits required')
    return Fraction(value)


def unit(value):
    result=fraction(value)
    if result>1: raise ValueError('Probability/rate/factor fraction must be in [0,1]')
    return result


def curve(values,months):
    if not isinstance(values,list) or len(values)!=months: raise ValueError('Exact remaining-month curve required')
    return [unit(v) for v in values]


def cumulative(hazards):
    survival=Fraction(1)
    for hazard in hazards: survival*=1-hazard
    return 1-survival


def stage(segment,policy):
    benchmark=cumulative([unit(v) for v in segment['benchmark_hazards']])
    current=cumulative([unit(v) for v in segment['assessment_hazards']])
    ratio=current/benchmark if benchmark else None
    zero_increase=benchmark==0 and current>0
    quantitative=(current>benchmark and ratio is not None and ratio>=fraction(policy['relative_pd_ratio'])
                  and current-benchmark>=unit(policy['absolute_pd_increase']))
    reasons=[]
    if segment['declared_credit_impaired']: reasons.append('DECLARED_CREDIT_IMPAIRED')
    if segment['declared_dpd']>=policy['default_dpd_gte']: reasons.append('DECLARED_DPD_DEFAULT_BACKSTOP')
    if reasons: result=3
    else:
        if segment['declared_dpd']>policy['sicr_dpd_gt']: reasons.append('DECLARED_DPD_SICR_BACKSTOP')
        if segment['qualitative_sicr']: reasons.append('DECLARED_QUALITATIVE_SICR')
        if quantitative: reasons.append('DECLARED_RELATIVE_AND_ABSOLUTE_PD_INCREASE')
        if zero_increase: reasons.append('DECLARED_POSITIVE_PD_FROM_ZERO_BENCHMARK')
        result=2 if reasons else 1
    return {'stage':result,'reasons':reasons or ['NO_DECLARED_SICR_TRIGGER'],'benchmark_lifetime_pd':exact(benchmark),
        'assessment_lifetime_pd':exact(current),'pd_ratio':exact(ratio) if ratio is not None else None,
        'ratio_status':'FINITE' if benchmark else ('POSITIVE_FROM_ZERO' if current else 'BOTH_ZERO'),
        'event_horizon_months':0 if result==3 else (min(12,segment['remaining_months']) if result==1 else segment['remaining_months'])}


def validate(plan,rows,metadata):
    if (not isinstance(plan,dict) or set(plan)!=PLAN_KEYS or type(plan['schema_version']) is not int or plan['schema_version']!=1
        or not all(text(plan[k]) for k in ('name','version')) or plan['basis']!='declared_research_cashflows_and_assessments'
        or plan['benchmark_comparison_basis']!='same_remaining_horizon_declared_benchmark'
        or plan['cash_convention']!='default_at_start_of_month_contractual_cash_at_end'
        or plan['visibility']!='private' or plan['public_release_approved'] is not False or metadata['risk_contract'] is not None):
        raise ValueError('Explicit research cash-flow/staging contract required; source risks cannot be overwritten')
    states=plan['eligible_source_states']
    if not isinstance(states,list) or not states or len(states)!=len(set(states)) or any(v not in ('CURRENT','DECLARED_PERFORMING') for v in states):
        raise ValueError('Explicit supported source-state eligibility required')
    selected=[r for r in rows if r['source_state'] in states]
    if not selected or any(r['representation']!='DIRECT_ASSET' for r in rows): raise ValueError('Eligible direct asset observations required')
    policy=plan['staging_policy']
    if (not isinstance(policy,dict) or set(policy)!={'relative_pd_ratio','absolute_pd_increase','sicr_dpd_gt','default_dpd_gte','zero_benchmark_policy'}
        or type(policy['sicr_dpd_gt']) is not int or policy['sicr_dpd_gt']!=30
        or type(policy['default_dpd_gte']) is not int or policy['default_dpd_gte']!=90
        or policy['zero_benchmark_policy']!='any_positive_to_stage2' or fraction(policy['relative_pd_ratio'])<1):
        raise ValueError('Explicit supported SICR/default snapshot policy required')
    unit(policy['absolute_pd_increase'])
    segments=plan['segments']
    if not isinstance(segments,dict) or set(segments)!={r['segment'] for r in selected}: raise ValueError('Exact eligible-segment coverage required')
    for s in segments.values():
        if (not isinstance(s,dict) or set(s)!=SEGMENT_KEYS or type(s['remaining_months']) is not int or not 1<=s['remaining_months']<=120
            or type(s['declared_dpd']) is not int or not 0<=s['declared_dpd']<=36500
            or any(type(s[k]) is not bool for k in ('declared_credit_impaired','qualitative_sicr','poci','revolving','cure_under_review'))
            or any(s[k] for k in ('poci','revolving','cure_under_review'))):
            raise ValueError('Fixed-term declared snapshot supported; POCI/revolving/cure require separate policies')
        months=s['remaining_months']; unit(s['monthly_effective_rate'])
        if sum(curve(s['principal_due_factors'],months),Fraction(0))!=1: raise ValueError('Principal repayment schedule must sum exactly to one')
        curve(s['benchmark_hazards'],months); curve(s['assessment_hazards'],months)
    scenarios=plan['scenarios']
    if not isinstance(scenarios,list) or not 1<=len(scenarios)<=8: raise ValueError('One to eight probability-weighted scenarios required')
    ids=set(); weights=Fraction(0)
    for scenario in scenarios:
        if (not isinstance(scenario,dict) or set(scenario)!={'id','label','weight','segments'} or not text(scenario['label'])
            or not isinstance(scenario['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,39}',scenario['id']) or scenario['id'] in ids
            or not isinstance(scenario['segments'],dict) or set(scenario['segments'])!=set(segments)):
            raise ValueError('Unique weighted scenario with complete segment curves required')
        ids.add(scenario['id']); weights+=unit(scenario['weight'])
        for key,inputs in scenario['segments'].items():
            if not isinstance(inputs,dict) or set(inputs)!={'conditional_default_hazards','recovery_profile'}: raise ValueError('Conditional hazard/recovery profile required')
            curve(inputs['conditional_default_hazards'],segments[key]['remaining_months'])
            profile=inputs['recovery_profile']
            if not isinstance(profile,list) or not 1<=len(profile)<=12: raise ValueError('One to twelve declared recovery/cost cash events required')
            recovered=Fraction(0)
            for event in profile:
                if (not isinstance(event,dict) or set(event)!={'lag_months','recovery_fraction','collection_cost_fraction'}
                    or type(event['lag_months']) is not int or not 0<=event['lag_months']<=120):
                    raise ValueError('Recovery timing/fraction/cost contract required')
                recovery=unit(event['recovery_fraction']); cost=unit(event['collection_cost_fraction']); recovered+=recovery
                if cost>recovery: raise ValueError('Negative net recovery unsupported')
            if recovered>1: raise ValueError('Gross recovery fractions exceed remaining principal')
    if weights!=1: raise ValueError('Scenario weights must sum exactly to one; no silent normalization')
    return selected


def per_unit(segment,inputs,assessment):
    months=segment['remaining_months']; rate=unit(segment['monthly_effective_rate'])
    principals=curve(segment['principal_due_factors'],months); outstanding=Fraction(1); schedule=[]
    for month,principal in enumerate(principals,1):
        schedule.append({'month':month,'opening_principal_factor':outstanding,'principal_due_factor':principal,
            'interest_due_factor':outstanding*rate,'contractual_cash_factor':principal+outstanding*rate})
        outstanding-=principal
    contract_pv=sum((row['contractual_cash_factor']/(1+rate)**row['month'] for row in schedule),Fraction(0))
    if contract_pv!=1: raise ValueError('Contract schedule does not reconcile to declared unit principal at monthly EIR')
    stage_number=assessment['stage']; survival=Fraction(1); events=[]; recovery_profile=inputs['recovery_profile']
    hazards=curve(inputs['conditional_default_hazards'],months)
    candidates=[(0,Fraction(1),Fraction(0))] if stage_number==3 else []
    if stage_number!=3:
        for month,hazard in enumerate(hazards,1):
            marginal=survival*hazard; survival*=1-hazard
            candidates.append((month,marginal,survival))
    for month,marginal,post_survival in candidates:
        start=max(0,month-1); balance=Fraction(1) if month==0 else schedule[month-1]['opening_principal_factor']
        contractual=sum((row['contractual_cash_factor']/(1+rate)**row['month'] for row in schedule if row['month']>=month),Fraction(0))
        recovery=sum((balance*(unit(event['recovery_fraction'])-unit(event['collection_cost_fraction']))/(1+rate)**(start+event['lag_months']) for event in recovery_profile),Fraction(0))
        loss=contractual-recovery
        if loss<0: raise ValueError('Negative expected cash shortfall unsupported')
        included=stage_number!=1 or month<=12
        events.append({'default_month':month,'marginal_default_probability':exact(marginal),'survival_after_month':exact(post_survival),
            'remaining_principal_factor':exact(balance),'contractual_tail_pv_factor':exact(contractual),
            'net_recovery_pv_factor':exact(recovery),'loss_pv_factor':exact(loss),
            'weighted_loss_pv_factor':exact(marginal*loss),'included_in_selected_horizon':included})
    def f(value): return Fraction(int(value['numerator']),int(value['denominator']))
    lifetime=sum((f(e['weighted_loss_pv_factor']) for e in events),Fraction(0))
    selected=sum((f(e['weighted_loss_pv_factor']) for e in events if e['included_in_selected_horizon']),Fraction(0))
    return {'contract_schedule':[{k:exact(v) if isinstance(v,Fraction) else v for k,v in row.items()} for row in schedule],
        'contract_pv_per_unit':exact(contract_pv),'default_events':events,'selected_ecl_per_unit':exact(selected),
        'lifetime_ecl_per_unit':exact(lifetime),'no_default_survival':exact(0 if stage_number==3 else survival)}


def rational(value): return Fraction(int(value['numerator']),int(value['denominator']))


def project(rows,metadata,plan):
    selected=validate(plan,rows,metadata)
    assessments={key:stage(s,plan['staging_policy']) for key,s in plan['segments'].items()}
    coverage=defaultdict(lambda:[0,0,Fraction(0),Fraction(0)])
    groups=defaultdict(lambda:[0,Fraction(0)])
    for row in rows:
        eligible=row['source_state'] in plan['eligible_source_states']; value=Fraction(row['reported_amount_major_exact']); c=row['currency']
        coverage[c][0]+=1; coverage[c][2]+=value
        if eligible:
            coverage[c][1]+=1; coverage[c][3]+=value
            for dim,bucket in [('total','ALL'),('stage',str(assessments[row['segment']]['stage'])),('segment',row['segment']),('region',row['region'])]:
                groups[(c,dim,bucket,row['segment'])][0]+=1; groups[(c,dim,bucket,row['segment'])][1]+=value
    results=[]; weighted=defaultdict(lambda:[0,Fraction(0),Fraction(0),Fraction(0)])
    for scenario in plan['scenarios']:
        unit_results={k:per_unit(s,scenario['segments'][k],assessments[k]) for k,s in plan['segments'].items()}
        buckets=defaultdict(lambda:[0,Fraction(0),Fraction(0),Fraction(0)])
        for (c,dim,bucket,segment),(n,value) in groups.items():
            result=unit_results[segment]; item=buckets[(c,dim,bucket)]; item[0]+=n; item[1]+=value
            item[2]+=value*rational(result['selected_ecl_per_unit']); item[3]+=value*rational(result['lifetime_ecl_per_unit'])
        serialized=[]
        for (c,dim,bucket),(n,value,selected_loss,lifetime) in sorted(buckets.items()):
            serialized.append({'currency':c,'dimension':dim,'bucket':bucket,'records':n,'reported_amount':exact(value),
                'research_ecl':exact(selected_loss),'lifetime_loss_reference':exact(lifetime)})
            target=weighted[(c,dim,bucket)]; target[0]=n; target[1]=value
            target[2]+=unit(scenario['weight'])*selected_loss; target[3]+=unit(scenario['weight'])*lifetime
        results.append({'id':scenario['id'],'label':scenario['label'],'weight':scenario['weight'],'segments':unit_results,'aggregates':serialized})
    return {'source_import_id':plan['source_import_id'],'as_of':metadata['as_of'],'date_grain':metadata['date_grain'],
        'name':plan['name'],'version':plan['version'],'basis':plan['basis'],'assumptions':plan,'stage_assessments':assessments,
        'scope':[{'currency':c,'source_records':n,'eligible_records':e,'excluded_records':n-e,'source_amount':exact(v),
            'eligible_amount':exact(a),'excluded_amount':exact(v-a)} for c,(n,e,v,a) in sorted(coverage.items())],
        'scenarios':results,'probability_weighted_aggregates':[{'currency':c,'dimension':d,'bucket':b,'records':n,
            'reported_amount':exact(v),'research_ecl':exact(ecl),'lifetime_loss_reference':exact(life)} for (c,d,b),(n,v,ecl,life) in sorted(weighted.items())],
        'contract':{'accounting_compliance':False,'observed_contract_cashflows':False,'observed_effective_interest_rate':False,
            'calibrated_pd_or_recovery':False,'observed_origination_risk_comparison':False,'source_risk_overwritten':False,
            'fx_conversion':False,'stage1':'Default events up to month 12; all associated future contractual/recovery cash retained',
            'stage2':'All remaining-term default events','stage3':'Declared default at reporting date, probability one at month zero',
            'interest':'Opening principal × declared monthly effective rate, end-month cash',
            'recovery':'Net recovery/cost fractions of remaining principal, discounted at default-start plus lag',
            'limitations':'Fixed-term snapshot only; no POCI, revolving, cure/forbearance or accounting qualification'},
        'global_cross_currency_total':None,'visibility':'private','public_release_approved':False}


def build(root,relative):
    path=contained(root,relative); digest=sha256(path); plan=read_plan(path); frozen=methods()
    rows,metadata,pins=source(root,plan['source_import_id']); report=project(rows,metadata,plan)
    identifier='exposure-ecl-'+uuid.uuid4().hex[:12]; folder=contained(root,'artifacts/private/'+identifier); folder.mkdir(parents=True)
    shutil.copyfile(path,folder/'assumptions.json'); write_new(folder/'report.json',report); guard(root,pins)
    if methods()!=frozen or sha256(path)!=digest or sha256(folder/'assumptions.json')!=digest: raise ValueError('ECL inputs/methods changed during build')
    receipt={'ecl_id':identifier,'source_import_id':plan['source_import_id'],'status':'DECLARED_CASH_SHORTFALL_RESEARCH',
        'methods':frozen,'inputs_sha256':pins,'outputs_sha256':{n:sha256(folder/n) for n in ('assumptions.json','report.json')},
        'completed_at':timestamp(),'visibility':'private','public_release_approved':False}
    write_new(folder/'ecl-complete.json',receipt); return receipt


def verify(root,identifier):
    if not isinstance(identifier,str) or not re.fullmatch('exposure-ecl-[0-9a-f]{12}',identifier): raise ValueError('Invalid ECL ID')
    folder=contained(root,'artifacts/private/'+identifier); receipt=read_json(folder/'ecl-complete.json')
    if (receipt['ecl_id']!=identifier or receipt['methods']!=methods() or receipt['status']!='DECLARED_CASH_SHORTFALL_RESEARCH'
        or receipt['visibility']!='private' or receipt['public_release_approved'] is not False
        or set(receipt['outputs_sha256'])!={'assumptions.json','report.json'}): raise ValueError('ECL receipt contract changed')
    for n,d in receipt['outputs_sha256'].items():
        if sha256(folder/n)!=d: raise ValueError('ECL payload changed')
    plan=read_plan(folder/'assumptions.json')
    if plan['source_import_id']!=receipt['source_import_id']: raise ValueError('ECL source binding changed')
    rows,metadata,pins=source(root,plan['source_import_id'])
    if pins!=receipt['inputs_sha256']: raise ValueError('ECL source pins changed')
    expected=project(rows,metadata,plan); report=read_json(folder/'report.json'); guard(root,pins)
    if methods()!=receipt['methods'] or json.dumps(report,sort_keys=True)!=json.dumps(expected,sort_keys=True): raise ValueError('ECL source rederivation differs')
    return folder,receipt,report
