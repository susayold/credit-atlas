"""Declared decision-cost scenarios on saved development validation scores only."""
import copy
import hashlib
import math
import re
import uuid
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa
from .retail_freeze import verify_freeze
from .workspace import contained,read_json,sha256,timestamp,write_new

ID=re.compile(r'retail-policy-[0-9a-f]{12}\Z')
ACTIONS=('accept','review','decline')
KEYS={'schema_version','freeze_id','cost_unit','cost_matrix','review_capacity','cases','visibility','public_release_approved'}
FLAGS={'model_training_performed':False,'model_selection_performed':False,'final_test_scored':False,
       'final_test_predictors_materialized':False,'threshold_optimized':False,'production_qualified':False,
       'temporal_out_of_time':False,'counterfactual_policy_effect_identified':False}

def methods():
    return {'retail_policy':sha256(Path(__file__))}

def number(value,probability=False):
    if not isinstance(value,str) or not re.fullmatch(r'(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,18})?',value):
        raise ValueError('Bounded nonnegative decimal text required')
    result=Fraction(value)
    if probability and result>1: raise ValueError('Threshold must be between zero and one')
    return result

def validate(plan):
    if not isinstance(plan,dict) or set(plan)!=KEYS or type(plan['schema_version']) is not int or plan['schema_version']!=1:
        raise ValueError('Exact retail policy schema required')
    if not isinstance(plan['freeze_id'],str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}',plan['freeze_id']):
        raise ValueError('Valid frozen retail model required')
    if plan['cost_unit']!='declared_cost_units' or plan['visibility']!='private' or plan['public_release_approved'] is not False:
        raise ValueError('Private declared-cost research contract required')
    capacity=plan['review_capacity']
    if capacity is not None and (type(capacity) is not int or not 0<=capacity<=50000): raise ValueError('Bounded review capacity required')
    costs=plan['cost_matrix']
    if not isinstance(costs,dict) or set(costs)!=set(ACTIONS): raise ValueError('Three action cost rows required')
    for row in costs.values():
        if not isinstance(row,dict) or set(row)!={'non_event','event'}: raise ValueError('Complete two-outcome cost matrix required')
        for value in row.values(): number(value)
    cases=plan['cases']
    if not isinstance(cases,list) or not 1<=len(cases)<=8: raise ValueError('One to eight declared policy cases required')
    names=[]
    for case in cases:
        if not isinstance(case,dict) or set(case)!={'id','lower_threshold','upper_threshold'} or not isinstance(case['id'],str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,39}',case['id']):
            raise ValueError('Exact named threshold case required')
        if number(case['lower_threshold'],True)>number(case['upper_threshold'],True): raise ValueError('Threshold order is reversed')
        names.append(case['id'])
    if len(set(names))!=len(names) or set(names)&{'accept_all','review_all','decline_all'}: raise ValueError('Unique nonreserved case IDs required')
    return copy.deepcopy(plan)

def exact(value):
    if value is None: return None
    with localcontext() as context:
        context.prec=50; decimal=Decimal(value.numerator)/Decimal(value.denominator)
    return {'numerator':str(value.numerator),'denominator':str(value.denominator),'decimal_50':str(decimal)}

def calculate(scores,plan):
    plan=validate(plan)
    if not scores or len(scores)>50000: raise ValueError('Bounded validation population required')
    ids=set(); prepared=[]
    for row in scores:
        if set(row)!={'source_client_id','target','probability'} or type(row['source_client_id']) is not int or row['source_client_id'] in ids:
            raise ValueError('Unique private validation identities required')
        ids.add(row['source_client_id'])
        if type(row['target']) is not int or row['target'] not in (0,1) or type(row['probability']) not in (int,float) or not math.isfinite(row['probability']) or not 0<=row['probability']<=1:
            raise ValueError('Binary events and finite probabilities required')
        prepared.append((row['target'],Fraction(str(row['probability']))))
    costs={action:{key:number(value) for key,value in row.items()} for action,row in plan['cost_matrix'].items()}
    cases=[{'id':action+'_all','constant_action':action} for action in ACTIONS]+plan['cases']
    reports=[]
    for case in cases:
        buckets={action:{'records':0,'events':0,'probability':Fraction(0),'expected':Fraction(0),'retrospective':Fraction(0)} for action in ACTIONS}
        lower=number(case['lower_threshold'],True) if 'lower_threshold' in case else None
        upper=number(case['upper_threshold'],True) if 'upper_threshold' in case else None
        for target,p in prepared:
            action=case['constant_action'] if 'constant_action' in case else ('accept' if p<lower else 'review' if p<upper else 'decline')
            bucket=buckets[action]; bucket['records']+=1; bucket['events']+=target; bucket['probability']+=p
            bucket['expected']+=(1-p)*costs[action]['non_event']+p*costs[action]['event']
            bucket['retrospective']+=costs[action]['event' if target else 'non_event']
        rows=[]
        for action,b in buckets.items():
            n=b['records']; rows.append({'action':action,'records':n,'events':b['events'],'non_events':n-b['events'],
                'action_share':exact(Fraction(n,len(prepared))),'event_rate':exact(Fraction(b['events'],n)) if n else None,
                'mean_probability':exact(b['probability']/n) if n else None,
                'expected_declared_cost':exact(b['expected']),'retrospective_cost_proxy':exact(b['retrospective'])})
        expected=sum((b['expected'] for b in buckets.values()),Fraction(0)); retrospective=sum((b['retrospective'] for b in buckets.values()),Fraction(0))
        reviews=buckets['review']['records']; capacity=plan['review_capacity']
        reports.append({'id':case['id'],'rule':copy.deepcopy(case),'actions':rows,
            'expected_declared_cost':exact(expected),'retrospective_cost_proxy':exact(retrospective),
            'expected_minus_retrospective':exact(expected-retrospective),'review_records':reviews,
            'review_capacity':capacity,'review_capacity_exceeded':None if capacity is None else reviews>capacity,
            'review_overflow_records':None if capacity is None else max(0,reviews-capacity)})
    return {'records':len(prepared),'events':sum(target for target,_ in prepared),'cases':reports,
        'partition':'validation','target':'source_default_payment_next_month','cost_unit':'declared_cost_units',
        'threshold_rule':'accept p < lower; review lower <= p < upper; decline p >= upper; ties remain together',
        'capacity_rule':'Flag excess review demand; no records dropped or silently reassigned',
        'assumptions':plan,'qualification':copy.deepcopy(FLAGS),
        'limitations':['Historical Taiwan booked-card cohort; no observed application approve/reject actions.',
            'Costs are user-declared outcome proxies, not observed cash losses, income, EAD or LGD.',
            'Review costs encode an assumed outcome matrix; reviewer effectiveness is not identified.',
            'Retrospective target rates do not identify outcomes after hypothetical rejection or intervention.',
            'Fixed development validation cohort already used for model selection; comparisons are exploratory.',
            'No threshold optimization, final holdout access, causal uplift or production policy approval.']}

def source(root,freeze_id):
    folder,frozen,digest,_,_=verify_freeze(root,freeze_id)
    assessment=contained(root,'artifacts/private/'+frozen['assessment_id'])
    score_path=assessment/'private-validation-scores.parquet'; raw=score_path.read_bytes()
    score_digest=hashlib.sha256(raw).hexdigest()
    if score_digest!=read_json(assessment/'assessment-complete.json')['outputs_sha256'][score_path.name]:
        raise ValueError('Validation score snapshot changed')
    rows=pq.read_table(pa.BufferReader(raw)).to_pylist()
    column=frozen['selected_variant']+'_probability'
    scores=[{'source_client_id':row['source_client_id'],'target':row['target'],'probability':row[column]}
        for row in rows if row['model']==frozen['selected_model']]
    inputs={str((folder/'freeze-complete.json').relative_to(root)):digest,
        str(score_path.relative_to(root)):score_digest}
    return scores,{'freeze_id':freeze_id,'case_id':frozen['case_id'],'assessment_id':frozen['assessment_id'],
        'selected_model':frozen['selected_model'],'selected_variant':frozen['selected_variant'],'inputs_sha256':inputs}

def build(root,plan):
    root=root.resolve(); plan=validate(plan)
    if root.drive.upper()!='D:': raise ValueError('Private D: workspace required')
    scores,lineage=source(root,plan['freeze_id']); method=methods(); report=calculate(scores,plan)|lineage
    folder=contained(root,'artifacts/private/retail-policy-'+uuid.uuid4().hex[:12]); folder.mkdir(parents=True)
    write_new(folder/'assumptions.json',plan); write_new(folder/'report.json',report)
    _,current=source(root,plan['freeze_id'])
    if current!=lineage or method!=methods(): raise ValueError('Policy source/method changed during build')
    receipt={'schema_version':1,'status':'RETAIL_DECLARED_POLICY_COMPLETE','policy_id':folder.name,
        'completed_at':timestamp(),'freeze_id':plan['freeze_id'],'methods':method,'inputs_sha256':lineage['inputs_sha256'],
        'outputs_sha256':{name:sha256(folder/name) for name in ('assumptions.json','report.json')},
        'visibility':'private','public_release_approved':False,**FLAGS}
    write_new(folder/'policy-complete.json',receipt)
    return {'policy_id':folder.name,'status':receipt['status'],'records':report['records']}

def verify(root,identifier):
    if not isinstance(identifier,str) or not ID.fullmatch(identifier): raise ValueError('Valid retail policy ID required')
    folder=contained(root,'artifacts/private/'+identifier); receipt=read_json(folder/'policy-complete.json')
    if receipt.get('schema_version')!=1 or receipt.get('policy_id')!=identifier or receipt.get('status')!='RETAIL_DECLARED_POLICY_COMPLETE' or receipt.get('methods')!=methods() or receipt.get('visibility')!='private' or receipt.get('public_release_approved') is not False or any(receipt.get(k) is not v for k,v in FLAGS.items()):
        raise ValueError('Policy contract changed')
    if set(receipt['outputs_sha256'])!={'assumptions.json','report.json'}: raise ValueError('Complete policy output set required')
    for name,digest in receipt['outputs_sha256'].items():
        if sha256(folder/name)!=digest: raise ValueError('Policy payload changed')
    plan=validate(read_json(folder/'assumptions.json'))
    if plan['freeze_id']!=receipt['freeze_id']: raise ValueError('Policy freeze binding changed')
    scores,lineage=source(root,plan['freeze_id'])
    if lineage['inputs_sha256']!=receipt['inputs_sha256']: raise ValueError('Policy input lineage changed')
    expected=calculate(scores,plan)|lineage; report=read_json(folder/'report.json')
    if report!=expected: raise ValueError('Policy does not replay from validation scores')
    return folder,receipt,report
