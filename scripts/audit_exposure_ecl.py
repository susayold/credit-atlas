"""Independent Fraction balance/discount identity and original-CSV ECL audit."""
import argparse
import csv
import json
import uuid
from fractions import Fraction
from math import prod
from pathlib import Path

from credit_atlas.exposure_ecl import verify
from credit_atlas.exposure_movements import guard
from credit_atlas.workspace import app_root,contained,read_json,sha256,timestamp,write_new


def audit(root,identifier):
    folder,receipt,report=verify(root,identifier); plan=read_json(folder/'assumptions.json'); checks=[]
    pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(root)):d for n,d in receipt['outputs_sha256'].items()},
        str((folder/'ecl-complete.json').relative_to(root)):sha256(folder/'ecl-complete.json')}
    def check(name,actual,expected): checks.append({'name':name,'passed':actual==expected})
    def f(value): return Fraction(int(value['numerator']),int(value['denominator']))
    stages={}; expected_unit={}
    policy=plan['staging_policy']
    for key,s in plan['segments'].items():
        old=1-prod((1-Fraction(v) for v in s['benchmark_hazards']),start=Fraction(1))
        new=1-prod((1-Fraction(v) for v in s['assessment_hazards']),start=Fraction(1))
        default=s['declared_credit_impaired'] or s['declared_dpd']>=90
        sicr=(s['qualitative_sicr'] or s['declared_dpd']>30 or (old==0 and new>0)
            or (old>0 and new>old and new>=old*Fraction(policy['relative_pd_ratio']) and new-old>=Fraction(policy['absolute_pd_increase'])))
        stage=3 if default else (2 if sicr else 1); stages[key]=stage
        check(key+':stage',report['stage_assessments'][key]['stage'],stage)
        check(key+':benchmark_pd',f(report['stage_assessments'][key]['benchmark_lifetime_pd']),old)
        check(key+':assessment_pd',f(report['stage_assessments'][key]['assessment_lifetime_pd']),new)
    for scenario,actual in zip(plan['scenarios'],report['scenarios']):
        check('scenario_id:'+scenario['id'],actual['id'],scenario['id'])
        for key,s in plan['segments'].items():
            unit_result=actual['segments'][key]; rate=Fraction(s['monthly_effective_rate']); due=[Fraction(v) for v in s['principal_due_factors']]
            opening=[1-sum(due[:i],Fraction(0)) for i in range(len(due))]
            cash=[p+b*rate for p,b in zip(due,opening)]
            check(scenario['id']+':'+key+':contract_par',sum((value/(1+rate)**(i+1) for i,value in enumerate(cash)),Fraction(0)),Fraction(1))
            check(scenario['id']+':'+key+':cash_schedule',[(r['month'],f(r['opening_principal_factor']),f(r['contractual_cash_factor'])) for r in unit_result['contract_schedule']],
                [(i+1,b,c) for i,(b,c) in enumerate(zip(opening,cash))])
            hazards=[Fraction(v) for v in scenario['segments'][key]['conditional_default_hazards']]; profile=scenario['segments'][key]['recovery_profile']
            expected_months=[0] if stages[key]==3 else list(range(1,len(due)+1))
            check(scenario['id']+':'+key+':event_months',[e['default_month'] for e in unit_result['default_events']],expected_months)
            selected=Fraction(0); lifetime=Fraction(0)
            for event,t in zip(unit_result['default_events'],expected_months):
                prior=prod((1-h for h in hazards[:t-1]),start=Fraction(1)) if t else Fraction(1)
                marginal=prior*hazards[t-1] if t else Fraction(1); survival=prior*(1-hazards[t-1]) if t else Fraction(0)
                balance=opening[t-1] if t else Fraction(1); start=max(0,t-1)
                # Independent par cash-flow identity: discounted tail = opening balance / discount(start).
                contract=balance/(1+rate)**start
                recovery=balance*sum(((Fraction(p['recovery_fraction'])-Fraction(p['collection_cost_fraction']))/(1+rate)**(start+p['lag_months']) for p in profile),Fraction(0))
                loss=contract-recovery; weighted=marginal*loss; included=stages[key]!=1 or t<=12
                expected={'marginal_default_probability':marginal,'survival_after_month':survival,'remaining_principal_factor':balance,
                    'contractual_tail_pv_factor':contract,'net_recovery_pv_factor':recovery,'loss_pv_factor':loss,'weighted_loss_pv_factor':weighted}
                prefix=':'.join([scenario['id'],key,str(t)])
                for field,value in expected.items(): check(prefix+':'+field,f(event[field]),value)
                check(prefix+':horizon',event['included_in_selected_horizon'],included)
                lifetime+=weighted
                if included: selected+=weighted
            check(scenario['id']+':'+key+':selected',f(unit_result['selected_ecl_per_unit']),selected)
            check(scenario['id']+':'+key+':lifetime',f(unit_result['lifetime_ecl_per_unit']),lifetime)
            expected_unit[(scenario['id'],key)]=(selected,lifetime)
    with contained(root,'artifacts/private/'+receipt['source_import_id']+'/source.csv').open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    for row in rows: row['amount']=Fraction(row['reported_amount'])*{'major':1,'thousand':1000,'million':1000000}[row['amount_unit']]
    selected=[r for r in rows if r['source_state'] in plan['eligible_source_states']]
    check('source_plus_exclusions',sum(r['source_records'] for r in report['scope']),len(rows))
    for scope in report['scope']:
        source_rows=[r for r in rows if r['currency']==scope['currency']]; eligible_rows=[r for r in selected if r['currency']==scope['currency']]
        check(scope['currency']+':source_count',scope['source_records'],len(source_rows)); check(scope['currency']+':eligible_count',scope['eligible_records'],len(eligible_rows))
        check(scope['currency']+':excluded_count',scope['excluded_records'],len(source_rows)-len(eligible_rows))
        for field,subset in [('source_amount',source_rows),('eligible_amount',eligible_rows)]: check(scope['currency']+':'+field,f(scope[field]),sum((r['amount'] for r in subset),Fraction(0)))
    expected_keys={(r['currency'],d,b) for r in selected for d,b in [('total','ALL'),('stage',str(stages[r['segment']])),('segment',r['segment']),('region',r['region'])]}
    projections=[(s['id'],s['aggregates']) for s in report['scenarios']]+[('weighted',report['probability_weighted_aggregates'])]
    for scenario_id,aggregates in projections:
        check(scenario_id+':group_keyset',{(r['currency'],r['dimension'],r['bucket']) for r in aggregates},expected_keys)
        for group in aggregates:
            dim=group['dimension']; bucket=group['bucket']
            subset=[r for r in selected if r['currency']==group['currency'] and (dim=='total' or (str(stages[r['segment']]) if dim=='stage' else r[dim])==bucket)]
            values=[Fraction(0),Fraction(0)]
            for row in subset:
                for sid,weight in ([(scenario_id,Fraction(1))] if scenario_id!='weighted' else [(s['id'],Fraction(s['weight'])) for s in plan['scenarios']]):
                    losses=expected_unit[(sid,row['segment'])]
                    for i in (0,1): values[i]+=row['amount']*weight*losses[i]
            prefix=':'.join([scenario_id,group['currency'],dim,bucket])
            check(prefix+':records',group['records'],len(subset)); check(prefix+':amount',f(group['reported_amount']),sum((r['amount'] for r in subset),Fraction(0)))
            check(prefix+':ecl',f(group['research_ecl']),values[0]); check(prefix+':lifetime',f(group['lifetime_loss_reference']),values[1])
    guard(root,pins); audit_id='exposure-ecl-audit-'+uuid.uuid4().hex[:12]
    result={'audit_id':audit_id,'ecl_id':identifier,'status':'PASS' if all(r['passed'] for r in checks) else 'FAIL','checks':checks,
        'completed_at':timestamp(),'script_sha256':sha256(Path(__file__)),'ecl_receipt_sha256':pins[str((folder/'ecl-complete.json').relative_to(root))],
        'visibility':'private','public_release_approved':False}
    write_new(contained(root,'artifacts/private/'+audit_id+'/audit-complete.json'),result)
    if result['status']!='PASS': raise ValueError('Independent ECL audit failed')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ecl-id',required=True); result=audit(app_root(),parser.parse_args().ecl_id)
    print(json.dumps({'audit_id':result['audit_id'],'status':result['status'],'checks':len(result['checks'])}))
