"""Validation-only subgroup coverage, calibration and declared-policy diagnostics."""
import copy
import math
import re
import uuid
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from .retail_policy import verify as verify_policy,exact,number
from .retail_policy_views import lineage_pins,pinned_scores
from .workspace import contained,read_json,sha256,timestamp,write_new

ID=re.compile(r'retail-subgroups-[0-9a-f]{12}\Z')
DIMENSIONS={'sex':'SEX','education':'EDUCATION','marriage':'MARRIAGE','age_band':'AGE'}
KEYS={'schema_version','policy_id','freeze_id','case_id','dimensions','minimum_records','minimum_class_records','visibility','public_release_approved'}
FLAGS={'model_training_performed':False,'model_selection_performed':False,'final_test_scored':False,
    'final_test_predictors_materialized':False,'demographics_added_to_model':False,'production_qualified':False,
    'fairness_certified':False,'causal_effect_identified':False,'temporal_monitoring':False}

def methods():
    return {name:sha256(Path(__file__).with_name(name+'.py')) for name in ('retail_subgroups','retail_policy','retail_policy_views')}

def validate(plan):
    if not isinstance(plan,dict) or set(plan)!=KEYS or type(plan['schema_version']) is not int or plan['schema_version']!=1: raise ValueError('Exact subgroup schema required')
    if not isinstance(plan['policy_id'],str) or not re.fullmatch(r'retail-policy-[0-9a-f]{12}',plan['policy_id']) or not isinstance(plan['freeze_id'],str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}',plan['freeze_id']): raise ValueError('Bound policy/freeze required')
    if not isinstance(plan['case_id'],str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,39}',plan['case_id']): raise ValueError('Named policy case required')
    dims=plan['dimensions']
    if not isinstance(dims,list) or not dims or any(not isinstance(d,str) or d not in DIMENSIONS for d in dims) or len(set(dims))!=len(dims): raise ValueError('Unique supported dimensions required')
    if any(type(plan[k]) is not int or not 1<=plan[k]<=1000 for k in ('minimum_records','minimum_class_records')): raise ValueError('Declared support bounds required')
    if plan['visibility']!='private' or plan['public_release_approved'] is not False: raise ValueError('Private subgroup scope required')
    return copy.deepcopy(plan)

def bucket(dimension,value):
    if type(value) not in (int,float) or not math.isfinite(value) or value!=int(value): return 'UNAVAILABLE_OR_INVALID'
    value=int(value)
    if dimension=='age_band':
        if not 18<=value<=120: return 'UNAVAILABLE_OR_INVALID'
        return 'under_30' if value<30 else '30_39' if value<40 else '40_49' if value<50 else '50_plus'
    return 'source_code_'+str(value)

def auc(rows):
    by_score=defaultdict(lambda:[0,0])
    for r in rows: by_score[r['probability']][r['target']]+=1
    negatives=0; concordant=Fraction(0); positives=sum(r['target'] for r in rows)
    if not positives or positives==len(rows): return None
    for score,(n,p) in sorted(by_score.items()):
        concordant+=p*negatives+Fraction(p*n,2); negatives+=n
    return concordant/(positives*negatives)

def calculate(rows,plan,rule):
    plan=validate(plan)
    if not rows or len(rows)>50000: raise ValueError('Bounded validation cohort required')
    ids=set(); normalized=[]
    for row in rows:
        if set(row)!={'source_client_id','target','probability',*DIMENSIONS.values()} or type(row['source_client_id']) is not int or row['source_client_id'] in ids: raise ValueError('Unique joined validation identities required')
        ids.add(row['source_client_id'])
        p=row['probability']; y=row['target']
        if type(y) is not int or y not in (0,1) or type(p) not in (int,float) or not math.isfinite(p) or not 0<=p<=1: raise ValueError('Finite score and binary target required')
        if 'constant_action' in rule:
            action=rule['constant_action']
            if action not in ('accept','review','decline'): raise ValueError('Valid constant action required')
        else:
            lower=number(rule['lower_threshold'],True); upper=number(rule['upper_threshold'],True)
            if lower>upper: raise ValueError('Reversed policy thresholds')
            action='accept' if Fraction(str(p))<lower else 'review' if Fraction(str(p))<upper else 'decline'
        normalized.append({**row,'action':action})
    def summary(selected):
        n=len(selected); events=sum(r['target'] for r in selected); negatives=n-events
        probabilities=sum((Fraction(str(r['probability'])) for r in selected),Fraction(0))
        squared=sum(((Fraction(str(r['probability']))-r['target'])**2 for r in selected),Fraction(0))
        high_events=sum(r['target'] for r in selected if r['action']=='decline')
        high_non_events=sum(1-r['target'] for r in selected if r['action']=='decline')
        supported=n>=plan['minimum_records']; ranking=supported and min(events,negatives)>=plan['minimum_class_records']
        return {'records':n,'events':events,'non_events':negatives,'cohort_share':exact(Fraction(n,len(rows))),
            'descriptive_support':'SUPPORTED' if supported else 'INSUFFICIENT_RECORDS',
            'ranking_support':'SUPPORTED' if ranking else 'INSUFFICIENT_CLASS_SUPPORT',
            'event_rate':exact(Fraction(events,n)) if supported else None,
            'mean_probability':exact(probabilities/n) if supported else None,
            'brier_score':exact(squared/n) if supported else None,
            'mean_prediction_minus_event_rate':exact((probabilities-events)/n) if supported else None,
            'roc_auc':exact(auc(selected)) if ranking else None,
            'high_risk_events':high_events,'high_risk_non_events':high_non_events,
            'high_risk_event_capture':exact(Fraction(high_events,events)) if supported and events>=plan['minimum_class_records'] else None,
            'high_risk_non_event_flag_rate':exact(Fraction(high_non_events,negatives)) if supported and negatives>=plan['minimum_class_records'] else None,
            'actions':[{'action':a,'records':sum(r['action']==a for r in selected),
                'events':sum(r['target'] for r in selected if r['action']==a),
                'share':exact(Fraction(sum(r['action']==a for r in selected),n)) if supported else None} for a in ('accept','review','decline')]}
    groups=[]; coverage=[]
    for dimension in plan['dimensions']:
        by_bucket=defaultdict(list)
        for r in normalized: by_bucket[bucket(dimension,r[DIMENSIONS[dimension]])].append(r)
        selected=[{'dimension':dimension,'bucket':name,**summary(group)} for name,group in sorted(by_bucket.items())]
        if sum(r['records'] for r in selected)!=len(rows) or sum(r['events'] for r in selected)!=sum(r['target'] for r in normalized): raise ValueError('Subgroup reconciliation failed')
        groups+=selected; coverage.append({'dimension':dimension,'records':len(rows),'groups':len(selected),
            'unavailable_or_invalid_records':len(by_bucket.get('UNAVAILABLE_OR_INVALID',[])),
            'insufficient_support_groups':sum(r['descriptive_support']!='SUPPORTED' for r in selected)})
    return {'overall':summary(normalized),'groups':groups,'coverage':coverage,'assumptions':plan,'policy_rule':rule,
        'target':'source_default_payment_next_month','partition':'validation','qualification':copy.deepcopy(FLAGS),
        'definitions':{'age_bands':'18–29,30–39,40–49,50–120; missing/invalid retained separately',
            'category_codes':'Original numeric source codes retained; no inferred identity or merged categories',
            'ranking':'Mann–Whitney concordance with half credit for score ties',
            'high_risk':'Only decline is flagged positive; review is a separate action and excluded from decline counts',
            'uncertainty':'No confidence intervals or significance/multiple-comparison tests; support cutoffs are display guardrails'},
        'limitations':['Static historical booked-card validation cohort; no temporal drift inference.',
            'Validation already used for model selection; descriptive/exploratory subgroup results.',
            'Demographics excluded from model predictors; exclusion does not demonstrate fairness.',
            'Observed target rates do not identify outcomes after rejection/review/intervention.',
            'No legal compliance, fairness certification, causal attribute effect or production approval.']}

def source(root,plan):
    folder,receipt,report=verify_policy(root,plan['policy_id'])
    if report['freeze_id']!=plan['freeze_id']: raise ValueError('Subgroup frozen-model mismatch')
    case=next((r for r in report['cases'] if r['id']==plan['case_id']),None)
    if case is None: raise ValueError('Policy case unavailable')
    pins=lineage_pins(root,report)
    pins.update({str((folder/name).relative_to(root)):d for name,d in receipt['outputs_sha256'].items()})
    pins[str((folder/'policy-complete.json').relative_to(root))]=sha256(folder/'policy-complete.json')
    scores=pinned_scores(root,report); clients=contained(root,'artifacts/private/'+report['case_id']+'/clients.parquet')
    with duckdb.connect(config={'threads':2,'memory_limit':'256MB'}) as db:
        db.register('validation_scores',pa.Table.from_pylist(scores))
        rows=db.execute('SELECT s.*,c.SEX,c.EDUCATION,c.MARRIAGE,c.AGE FROM validation_scores s JOIN read_parquet(?) c USING(source_client_id) ORDER BY s.source_client_id',[str(clients)]).to_arrow_table().to_pylist()
    if len(rows)!=len(scores) or {(r['source_client_id'],r['target'],r['probability']) for r in rows}!={(r['source_client_id'],r['target'],r['probability']) for r in scores}: raise ValueError('Validation demographic join changed population')
    guard(root,pins)
    return rows,case['rule'],pins

def guard(root,pins):
    if any(sha256(contained(root,p))!=h for p,h in pins.items()): raise ValueError('Subgroup input evidence changed')

def build(root,plan):
    root=root.resolve(); plan=validate(plan)
    if root.drive.upper()!='D:': raise ValueError('Private D: workspace required')
    rows,rule,pins=source(root,plan); method=methods(); report=calculate(rows,plan,rule)
    folder=contained(root,'artifacts/private/retail-subgroups-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
    write_new(folder/'assumptions.json',plan);write_new(folder/'report.json',report)
    pq.write_table(pa.Table.from_pylist(rows),folder/'private-validation-subgroups.parquet',compression='zstd')
    guard(root,pins)
    if method!=methods(): raise ValueError('Subgroup method changed')
    write_new(folder/'subgroups-complete.json',{'schema_version':1,'status':'RETAIL_VALIDATION_SUBGROUPS_COMPLETE','subgroups_id':folder.name,
        'completed_at':timestamp(),'policy_id':plan['policy_id'],'freeze_id':plan['freeze_id'],'methods':method,'inputs_sha256':pins,
        'outputs_sha256':{n:sha256(folder/n) for n in ('assumptions.json','report.json','private-validation-subgroups.parquet')},
        'visibility':'private','public_release_approved':False,**FLAGS})
    return {'subgroups_id':folder.name,'status':'RETAIL_VALIDATION_SUBGROUPS_COMPLETE','records':len(rows)}

def verify(root,identifier):
    if not isinstance(identifier,str) or not ID.fullmatch(identifier): raise ValueError('Valid subgroup ID required')
    folder=contained(root,'artifacts/private/'+identifier);receipt=read_json(folder/'subgroups-complete.json')
    if receipt.get('status')!='RETAIL_VALIDATION_SUBGROUPS_COMPLETE' or receipt.get('schema_version')!=1 or receipt.get('subgroups_id')!=identifier or receipt.get('methods')!=methods() or receipt.get('visibility')!='private' or receipt.get('public_release_approved') is not False or any(receipt.get(k) is not v for k,v in FLAGS.items()): raise ValueError('Subgroup contract changed')
    if set(receipt['outputs_sha256'])!={'assumptions.json','report.json','private-validation-subgroups.parquet'}: raise ValueError('Complete subgroup payload required')
    guard(root,{**receipt['inputs_sha256'],**{str((folder/n).relative_to(root)):h for n,h in receipt['outputs_sha256'].items()}})
    plan=validate(read_json(folder/'assumptions.json'));rows,rule,pins=source(root,plan)
    if plan['policy_id']!=receipt['policy_id'] or plan['freeze_id']!=receipt['freeze_id'] or pins!=receipt['inputs_sha256']: raise ValueError('Subgroup source binding changed')
    report=read_json(folder/'report.json')
    if pq.read_table(folder/'private-validation-subgroups.parquet').to_pylist()!=rows or report!=calculate(rows,plan,rule): raise ValueError('Subgroups do not replay from selected validation population')
    return folder,receipt,report
