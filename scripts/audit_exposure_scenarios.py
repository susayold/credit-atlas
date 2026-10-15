"""Independent original-CSV Decimal(90) stress/EL/attribution projection."""
import argparse
import csv
import json
import uuid
from collections import defaultdict
from decimal import Decimal,localcontext
from pathlib import Path

from credit_atlas.exposure_movements import guard
from credit_atlas.exposure_scenarios import verify
from credit_atlas.workspace import app_root,contained,read_json,sha256,timestamp,write_new


def audit(root,identifier):
    folder,receipt,report=verify(root,identifier); plan=read_json(folder/'assumptions.json')
    pins={**receipt['inputs_sha256'],**{str((folder/n).relative_to(root)):d for n,d in receipt['outputs_sha256'].items()},
        str((folder/'scenario-complete.json').relative_to(root)):sha256(folder/'scenario-complete.json')}
    with contained(root,'artifacts/private/'+receipt['source_import_id']+'/source.csv').open(encoding='utf-8-sig',newline='') as stream:
        source=list(csv.DictReader(stream))
    checks=[]
    def check(name,actual,expected): checks.append({'name':name,'passed':actual==expected})
    with localcontext() as context:
        context.prec=90
        def rational(value): return Decimal(value['numerator'])/Decimal(value['denominator'])
        def near(name,actual,expected):
            difference=abs(rational(actual)-expected)
            checks.append({'name':name,'passed':difference<=max(Decimal(1),abs(expected))*Decimal('1e-44')})
        for row in source: row['amount']=Decimal(row['reported_amount'])*{'major':1,'thousand':1000,'million':1000000}[row['amount_unit']]
        eligible=[r for r in source if r['source_state'] in plan['eligible_source_states']]
        check('eligible_plus_excluded_total',sum(r['eligible_records']+r['excluded_records'] for r in report['scope']),len(source))
        for scope in report['scope']:
            rows=[r for r in source if r['currency']==scope['currency']]; accepted=[r for r in rows if r['source_state'] in plan['eligible_source_states']]
            excluded=[r for r in rows if r['source_state'] not in plan['eligible_source_states']]
            for prefix,subset in [('source',rows),('eligible',accepted),('excluded',excluded)]:
                check(scope['currency']+':'+prefix+'_count',scope[prefix+'_records'],len(subset))
                near(scope['currency']+':'+prefix+'_amount',scope[prefix+'_amount'],sum((r['amount'] for r in subset),Decimal(0)))
        expected_exclusions=defaultdict(lambda:[0,Decimal(0)])
        for row in source:
            if row['source_state'] not in plan['eligible_source_states']:
                expected_exclusions[(row['currency'],row['source_state'])][0]+=1
                expected_exclusions[(row['currency'],row['source_state'])][1]+=row['amount']
        check('exclusion_keyset',{(r['currency'],r['source_state']) for r in report['exclusions']},set(expected_exclusions))
        for row in report['exclusions']:
            n,value=expected_exclusions[(row['currency'],row['source_state'])]
            check('exclusion_count:'+row['source_state'],row['records'],n); near('exclusion_amount:'+row['source_state'],row['reported_amount'],value)
        expected_scenarios=[{'id':'baseline','pd_odds_multiplier':'1','lgd_addition':'0','ead_multiplier':'1'}]+plan['scenarios']
        check('scenario_id_order',[r['id'] for r in report['scenarios']],[r['id'] for r in expected_scenarios])
        for expected,actual in zip(expected_scenarios,report['scenarios']):
            projected=[]
            for row in eligible:
                a=plan['segment_assumptions'][row['segment']]; p=Decimal(a['pd']); l=Decimal(a['lgd']); e=row['amount']*Decimal(a['ead_factor'])
                # Use inverse-odds form rather than primary rational numerator formula.
                if p==0: sp=Decimal(0)
                elif p==1: sp=Decimal(1)
                else: sp=1/(1+(1/p-1)/Decimal(expected['pd_odds_multiplier']))
                sl_raw=l+Decimal(expected['lgd_addition']); sl=min(Decimal(1),max(Decimal(0),sl_raw)); se=e*Decimal(expected['ead_multiplier'])
                base=p*l*e; after_pd=sp*l*e; after_lgd=sp*sl*e; final=sp*sl*se
                projected.append((row,{'reported_amount':row['amount'],'declared_ead':se,'research_el':final,'baseline_research_el':base,
                    'pd_effect':after_pd-base,'lgd_effect':after_lgd-after_pd,'ead_effect':final-after_lgd,
                    'el_change':final-base,'attribution_residual':Decimal(0)},sl_raw!=sl))
            expected_keys={(r['currency'],d,r[d] if d!='total' else 'ALL') for r,_,_ in projected for d in ('total','segment','region','source_state')}
            check(actual['id']+':group_keyset',{(r['currency'],r['dimension'],r['bucket']) for r in actual['aggregates']},expected_keys)
            for group in actual['aggregates']:
                values=[v for r,v,_ in projected if r['currency']==group['currency'] and (group['dimension']=='total' or r[group['dimension']]==group['bucket'])]
                selected=[(r,clip) for r,_,clip in projected if r['currency']==group['currency'] and (group['dimension']=='total' or r[group['dimension']]==group['bucket'])]
                prefix=':'.join([actual['id'],group['currency'],group['dimension'],group['bucket']])
                check(prefix+':records',group['records'],len(values))
                check(prefix+':zero',group['zero_source_amount_records'],sum(r['amount']==0 for r,_ in selected))
                check(prefix+':clip',group['lgd_clipped_records'],sum(clip for _,clip in selected))
                for key in values[0]: near(prefix+':'+key,group[key],sum((v[key] for v in values),Decimal(0)))
    guard(root,pins)
    audit_id='exposure-scenario-audit-'+uuid.uuid4().hex[:12]
    result={'audit_id':audit_id,'scenario_id':identifier,'status':'PASS' if all(r['passed'] for r in checks) else 'FAIL',
        'checks':checks,'tolerance':'relative 1e-44 with absolute 1e-44 floor','completed_at':timestamp(),
        'script_sha256':sha256(Path(__file__)),'scenario_receipt_sha256':pins[str((folder/'scenario-complete.json').relative_to(root))],
        'visibility':'private','public_release_approved':False}
    write_new(contained(root,'artifacts/private/'+audit_id+'/audit-complete.json'),result)
    if result['status']!='PASS': raise ValueError('Independent scenario audit failed')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--scenario-id',required=True)
    result=audit(app_root(),parser.parse_args().scenario_id)
    print(json.dumps({'audit_id':result['audit_id'],'status':result['status'],'checks':len(result['checks'])}))
