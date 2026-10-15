import argparse
import json
import uuid
from pathlib import Path
from decimal import Decimal
import numpy as np
import pyarrow.parquet as pq
from sklearn.metrics import roc_auc_score,brier_score_loss
from credit_atlas.retail_subgroups import guard
from credit_atlas.retail_subgroups_saved import verify_saved_subgroups as verify
from credit_atlas.workspace import app_root,read_json,sha256,timestamp,write_new

def run(root,identifier):
    folder,receipt,report=verify(root,identifier);plan=report['assumptions']
    rows=pq.read_table(folder/'private-validation-subgroups.parquet').to_pylist(); checks=0
    def check(value):
        nonlocal checks
        assert value,'Independent subgroup mismatch';checks+=1
    def numeric(value):return int(value['numerator'])/int(value['denominator']) if value is not None else None
    def classify(dimension,row):
        value=row[{'sex':'SEX','education':'EDUCATION','marriage':'MARRIAGE','age_band':'AGE'}[dimension]]
        if value is None or not np.isfinite(value) or value!=int(value):return 'UNAVAILABLE_OR_INVALID'
        if dimension!='age_band':return 'source_code_'+str(int(value))
        for lower,upper,name in [(18,30,'under_30'),(30,40,'30_39'),(40,50,'40_49'),(50,121,'50_plus')]:
            if lower<=value<upper:return name
        return 'UNAVAILABLE_OR_INVALID'
    for summary in [report['overall'],*report['groups']]:
        selected=rows if 'dimension' not in summary else [r for r in rows if classify(summary['dimension'],r)==summary['bucket']]
        y=np.asarray([r['target'] for r in selected]);p=np.asarray([r['probability'] for r in selected]);n=len(y);events=int(y.sum())
        check(n==summary['records']);check(events==summary['events']);check(n-events==summary['non_events'])
        if n>=plan['minimum_records']:
            check(abs(numeric(summary['mean_probability'])-p.mean())<1e-12)
            check(abs(numeric(summary['event_rate'])-y.mean())<1e-12)
            check(abs(numeric(summary['mean_prediction_minus_event_rate'])-(p.mean()-y.mean()))<1e-12)
            check(abs(numeric(summary['brier_score'])-brier_score_loss(y,p,labels=[0,1]))<1e-12)
            if min(events,n-events)>=plan['minimum_class_records']:check(abs(numeric(summary['roc_auc'])-roc_auc_score(y,p))<1e-12)
            else:check(summary['roc_auc'] is None)
        else:check(all(summary[k] is None for k in ('event_rate','mean_probability','brier_score','roc_auc')))
        rule=report['policy_rule'];actions=[]
        for probability in p:
            actions.append(rule['constant_action'] if 'constant_action' in rule else 'decline' if Decimal(str(float(probability)))>=Decimal(rule['upper_threshold']) else 'review' if Decimal(str(float(probability)))>=Decimal(rule['lower_threshold']) else 'accept')
        for action in summary['actions']:
            mask=np.asarray([a==action['action'] for a in actions]);check(int(mask.sum())==action['records']);check(int(y[mask].sum())==action['events'])
        flagged=np.asarray([a=='decline' for a in actions]);check(int(y[flagged].sum())==summary['high_risk_events']);check(int((1-y[flagged]).sum())==summary['high_risk_non_events'])
        for key,denominator,numerator in [('high_risk_event_capture',events,int(y[flagged].sum())),('high_risk_non_event_flag_rate',n-events,int((1-y[flagged]).sum()))]:
            if n>=plan['minimum_records'] and denominator>=plan['minimum_class_records']:check(abs(numeric(summary[key])-numerator/denominator)<1e-12)
            else:check(summary[key] is None)
    for dimension in plan['dimensions']:
        selected=[r for r in report['groups'] if r['dimension']==dimension];check(sum(r['records'] for r in selected)==len(rows));check(sum(r['events'] for r in selected)==report['overall']['events'])
    guard(root,receipt['inputs_sha256'])
    before=read_json(root/'artifacts/private/retail-subgroups-holdout-guard-before-20261010.json')
    check(sha256(root/'artifacts/private/retail-holdout-access.sqlite')==before['sha256']);check(not any(report['qualification'].values()))
    output=root/'artifacts/private'/('retail-subgroups-audit-'+uuid.uuid4().hex[:12]+'.json')
    write_new(output,{'status':'PASS','subgroups_id':identifier,'checks':checks,'completed_at':timestamp(),'method_sha256':sha256(Path(__file__)),
        'subgroup_receipt_sha256':sha256(folder/'subgroups-complete.json'),'holdout_ledger_unchanged':True,'visibility':'private','public_release_approved':False})
    return {'status':'PASS','checks':checks,'receipt':str(output)}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--subgroups-id',required=True);args=parser.parse_args();print(json.dumps(run(app_root(),args.subgroups_id),indent=2))
