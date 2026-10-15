"""Streaming source-native profile; no fitting, target invention or imputation."""
import argparse,csv,json,re,time,uuid
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path
from credit_atlas.workspace import contained,read_json,sha256,write_new
parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);args=parser.parse_args()
if not re.fullmatch(r'lendingclub-source-[0-9a-f]{12}',args.source):raise ValueError('Invalid source ID')
root=Path.cwd();folder=contained(root,'data/private/retail/'+args.source);receipt=read_json(folder/'acquisition-complete.json')
for s in receipt['sources']:assert sha256(folder/s['file'])==s['sha256'] and (folder/s['file']).stat().st_size==s['bytes']
source=next(s for s in receipt['sources'] if s['file'].endswith('.csv'));path=folder/source['file']
assert source['publisher_hash_verified']
out=root/'artifacts/private'/('lendingclub-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
missing_tokens={'','NA','N/A','null','NULL','NaN','nan'}
numeric_fields=['loan_amnt','annual_inc','annual_inc_joint','dti','dti_joint','int_rate','installment','fico_range_low','fico_range_high','EmploymentLength','LoanStatus']
counts=Counter();cohorts=Counter();statuses=Counter();targets=Counter();joint=Counter();source_missing=Counter();numeric={k:{'present':0,'missing':0,'invalid':0,'zero':0,'negative':0,'min':None,'max':None,'sum':Decimal(0)} for k in numeric_fields}
first_issue=None;last_issue=None;invalid_dates=Counter();last=time.monotonic();rows=0
with path.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.reader(f);header=next(reader)
    if len(header)!=len(set(header)) or len(header)!=90:raise ValueError('Unexpected source header')
    index={name:i for i,name in enumerate(header)}
    for row in reader:
        rows+=1
        if len(row)!=len(header):raise ValueError('Malformed CSV width at source record '+str(rows))
        clean=[value.strip() for value in row]
        for name,value in zip(header,clean):
            if value in missing_tokens:source_missing[name]+=1
        status=clean[index['loan_status']];target=clean[index['LoanStatus']];issue=clean[index['issue_d']]
        statuses[status]+=1;targets[(status,target)]+=1;joint[clean[index['application_type']]]+=1
        match=re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})',issue)
        if match:
            from datetime import date
            try:period=date(int(match[3]),int(match[1]),int(match[2])).isoformat()
            except ValueError:period=None
        else:period=None
        if period:
            first_issue=min(first_issue,period) if first_issue else period;last_issue=max(last_issue,period) if last_issue else period
            cohorts[(period[:7],status)]+=1
        else:invalid_dates[issue]+=1
        for name in numeric_fields:
            value=clean[index[name]];stat=numeric[name]
            if value in missing_tokens:stat['missing']+=1;continue
            try:v=Decimal(value.removesuffix('%'))
            except InvalidOperation:stat['invalid']+=1;continue
            if not v.is_finite():stat['invalid']+=1;continue
            stat['present']+=1;stat['sum']+=v;stat['zero']+=v==0;stat['negative']+=v<0
            stat['min']=v if stat['min'] is None else min(v,stat['min']);stat['max']=v if stat['max'] is None else max(v,stat['max'])
        if time.monotonic()-last>12:print('profiled records',rows,flush=True);last=time.monotonic()
for stat in numeric.values():
    for key in ['sum','min','max']:stat[key]=str(stat[key]) if stat[key] is not None else None
doc={'source_id':args.source,'source_receipt_sha256':sha256(folder/'acquisition-complete.json'),'source_csv_sha256':source['sha256'],
    'dataset':receipt['dataset'],'rows':rows,'columns':header,'raw_cell_positions':rows*len(header),
    'missing_tokens':sorted(missing_tokens),'missing_counts':{name:source_missing[name] for name in header},
    'numeric_source_profiles':numeric,'issue_date_range':[first_issue,last_issue],'invalid_issue_dates':dict(invalid_dates),
    'monthly_source_status_counts':[{'issue_month':month,'source_loan_status':status,'records':count} for (month,status),count in sorted(cohorts.items())],
    'source_status_counts':dict(statuses),'source_status_encoded_cross_counts':[{'source_loan_status':s,'encoded_LoanStatus_raw':t,'records':n} for (s,t),n in sorted(targets.items())],
    'application_type_counts':dict(joint),'field_readiness':{
      'application_decision_date_present':False,'rejected_application_population_present':False,'event_date_present':False,
      'fixed_horizon_target_qualified':False,'application_time_feature_availability_qualified':False,
      'lendingclub_original_file_fidelity_verified':False,'oot_validation_performed':False},
    'candidate_model_exclusions':['loan_status','LoanStatus','id','grade','SubGrade','int_rate','installment'],
    'model_training_performed':False,'visibility':'private','public_release_approved':False,
    'limitations':['Contributor-merged/prepared dataset; publisher hash proves published bytes, not original LendingClub fidelity.',
       'Issue date is a booking date, not a verified application decision timestamp.',
       'Status and encoded LoanStatus are outcome fields; neither may be used as a predictor.',
       'No rejection population or event date/fixed horizon; terminal status is not a validated 12-month PD target.',
       'Grade/rate/installment are decision or contract outputs; application availability requires separate review.',
       'Contributor describes expired loans; selection on resolution/maturity must be audited before temporal modelling.',
       'Raw missingness/numeric profiles do not establish field semantics, monetary units or income verification.']}
write_new(out/'profile.json',doc)
write_new(out/'receipt.json',{'status':'SOURCE_PROFILE_BUILT','profile_sha256':sha256(out/'profile.json'),'rows':rows,'columns':len(header),
    'source_csv_sha256':source['sha256'],'model_training_performed':False})
print(out);print(sha256(out/'profile.json'));print(rows,len(header),doc['source_status_counts'],doc['issue_date_range'])
