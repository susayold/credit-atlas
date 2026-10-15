"""Published resolved-loan source explorer; not an application or PD model."""
import re
from collections import Counter
from decimal import Decimal,localcontext
from .workspace import contained,read_json,sha256
SOURCE='lendingclub-source-2a2766348144'
RECEIPT='36f28b6635bd35b10759fb98dd1bfb55faf54199107996e9959eb0dc4bc86603'
PROFILE='lendingclub-profile-28db23b7bd0a'
PROFILE_SHA='0ab0d8179811cec4499a83fd727e1d5cf7597f37b9b703f64af10774d9ed9e36'

def report(root,query):
    if set(query)-{'from','to','status','field'} or any(not isinstance(v,str) for v in query.values()):raise ValueError('Invalid LendingClub scope')
    start=query.get('from','2016-01');end=query.get('to','2020-06');status=query.get('status','all');field=query.get('field','annual_inc')
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',start) or not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',end) or not '2016-01'<=start<=end<='2020-06':raise ValueError('Invalid LendingClub month range')
    if status not in {'all','Fully Paid','Charged Off'}:raise ValueError('Invalid LendingClub source status')
    folder=contained(root,'data/private/retail/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('LendingClub receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for s in receipt['sources']:
        p=contained(folder,s['file'])
        if p.stat().st_size!=s['bytes'] or sha256(p)!=s['sha256']:raise ValueError('LendingClub source changed')
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('LendingClub profile changed')
    doc=read_json(path)
    if field not in doc['columns']:raise ValueError('Invalid LendingClub source field')
    rows=[r for r in doc['monthly_source_status_counts'] if start<=r['issue_month']<=end]
    selected=[r for r in rows if status=='all' or r['source_loan_status']==status]
    counts=Counter();timeline={}
    for r in rows:
        counts[r['source_loan_status']]+=r['records'];timeline.setdefault(r['issue_month'],{})[r['source_loan_status']]=r['records']
    total=sum(counts.values());bad=counts['Charged Off']
    with localcontext() as ctx:
        ctx.prec=50
        share=str(Decimal(bad)/Decimal(total)) if total else None
    from .lendingclub_dictionary import report as dictionary_report
    dictionary=dictionary_report(root,field)
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'profile_sha256':PROFILE_SHA,'sources':receipt['sources'],
        'dataset':{'name':receipt['dataset']['name'],'doi':receipt['dataset']['doi'],'publish_date':receipt['dataset']['publish_date'],
                   'licence':receipt['dataset']['licence'],'url':'https://data.mendeley.com/datasets/mvvd3dnfyz/1'},
        'filters':{'from':start,'to':end,'status':status,'field':field},'whole_source_records':doc['rows'],'columns':doc['columns'],
        'raw_cell_positions':doc['raw_cell_positions'],'issue_date_range':doc['issue_date_range'],
        'selected_records':sum(r['records'] for r in selected),'selected_month_status_rows':selected,
        'window_all_status_records':total,'window_source_status_counts':dict(counts),
        'window_terminal_charged_off_share_decimal50':share,'share_population':'All published resolved-loan rows in selected booking-month window, independent of source-status filter; not booked-population PD',
        'timeline':[{'issue_month':m,'source_fully_paid_records':v.get('Fully Paid'),
            'source_charged_off_records':v.get('Charged Off'),'observed_source_records':sum(v.values())} for m,v in sorted(timeline.items())],
        'absent_month_status_semantics':'Absent source aggregate stays null in timeline; not certified zero events or population completeness',
        'quality_scope':'whole_source_not_filtered_by_month_or_status','selected_field':{'name':field,'missing':doc['missing_counts'][field],
            'numeric_profile':doc['numeric_source_profiles'].get(field),'scope':'whole_source'},
        'missingness':[{'field':name,'missing':doc['missing_counts'][name],'records':doc['rows'],'scope':'whole_source'} for name in doc['columns']],
        'numeric_source_profiles':doc['numeric_source_profiles'],'source_status_encoded_cross_counts':doc['source_status_encoded_cross_counts'],
        'application_type_counts':doc['application_type_counts'],'candidate_model_exclusions':sorted(set(doc['candidate_model_exclusions'])|set(dictionary['candidate_exclusions_pending_review'])),
        'dictionary':dictionary,
        'field_readiness':doc['field_readiness'],'limitations':doc['limitations'],'model_training_performed':False,
        'visibility':'private','public_release_approved':False}
