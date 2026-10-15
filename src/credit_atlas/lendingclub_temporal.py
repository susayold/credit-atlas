"""Temporal evidence distinct from certified cutoff/label/maturity readiness."""
from .workspace import contained,read_json,sha256
PROFILE='lendingclub-temporal-profile-1333a9b4a286'
PROFILE_SHA='8b4b6cbee90ef9b9ff09f29f62a183c28a000cf0cb9725e23582ecc7ec529425'

def report(root,kind,start,end,category):
    if kind=='rejected':return {'applicable':False,'reason':'Accepted-loan payment/term evidence does not apply to rejected applications.','certified_observation_cutoff':None,'fixed_horizon_pd12_labels':None}
    if kind!='accepted':raise ValueError('Invalid temporal source kind')
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('LendingClub temporal profile changed')
    doc=read_json(path);file=contained(root,'data/private/retail/'+doc['source_id']+'/'+doc['source_file']['file'])
    if sha256(file)!=doc['source_file']['sha256']:raise ValueError('LendingClub temporal source changed')
    raw='' if category=='__missing__' else category
    rows=[r for r in doc['cohort_term_payment_span'] if r['issue_month'] is not None and start<=r['issue_month']<=end and (category=='all' or r['source_loan_status']==raw)]
    metrics=['records','last_payment_month_available','last_payment_span_at_least_12m','last_payment_before_booking','last_credit_pull_before_booking']
    return {'applicable':True,'profile_sha256':PROFILE_SHA,'date_profile_scope':'whole_accepted_source_not_window_filtered',
        'date_profiles':doc['date_profiles'],'cohort_scope':{'from':start,'to':end,'category':category},'cohorts':rows,
        'summary':{k:sum(r[k] for r in rows) for k in metrics},'whole_source_unavailable_booking_month':doc['unavailable_booking_month'],
        'whole_source_missing_member_id':doc['missing_member_id'],'certified_observation_cutoff':None,'fixed_horizon_pd12_labels':None,
        'maturity_qualified':False,'application_feature_timing_qualified':False,'model_training_performed':False,
        'requirements':['Certified observation cutoff with source version/availability evidence',
            'First-event and exit/censoring history for an explicit default definition/horizon',
            'Application/decision-time feature values and borrower-group identity',
            'Mature cohort support,precommitted entity-safe temporal splits and intended-use review'],
        'interpretations':doc['interpretations']+['Credit pull before booking can be consistent with pre-funding evaluation;chronology counts do not alone prove a data error.']}
