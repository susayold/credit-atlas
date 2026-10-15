"""Separate funded-month/rejected-application source views, never approval/PD."""
import re
from collections import Counter
from .workspace import contained,read_json,sha256
SOURCE='lendingclub-full-source-3954d375d972'
RECEIPT='8c75b6f45be94ccc7e610f3be8aa1f51246b48bc69331dea8db518c69f657d55'
PROFILE='lendingclub-full-profile-f4168e8d746c'
PROFILE_SHA='f8be3a2f137172f019d4cce743c173c03176f1fb5d3e3b54e67350ee34f60098'

def report(root,query):
    if set(query)-{'kind','from','to','category'} or any(not isinstance(v,str) for v in query.values()):raise ValueError('Invalid full LendingClub source scope')
    kind=query.get('kind','accepted');start=query.get('from','2007-06' if kind=='accepted' else '2007-05');end=query.get('to','2018-12');category=query.get('category','all')
    if kind not in {'accepted','rejected'}:raise ValueError('Invalid full LendingClub source kind')
    if any(not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',x) for x in [start,end]) or not '2007-05'<=start<=end<='2018-12':raise ValueError('Invalid full LendingClub month window')
    folder=contained(root,'data/private/retail/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('Full LendingClub receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for source in receipt['sources']:
        p=contained(folder,source['file'])
        if p.stat().st_size!=source['bytes'] or sha256(p)!=source['sha256']:raise ValueError('Full LendingClub source changed')
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('Full LendingClub profile changed')
    doc=read_json(path);p=next(x for x in doc['profiles'] if x['kind']==kind)
    raw_category='' if category=='__missing__' else category
    if category!='all' and raw_category not in p['source_category_counts']:raise ValueError('Invalid source category for selected kind')
    window=[r for r in p['month_category_counts'] if start<=r['month']<=end]
    selected=[r for r in window if category=='all' or r['source_category']==raw_category]
    counts=Counter();monthly=Counter()
    for r in selected:counts[r['source_category']]+=r['records'];monthly[r['month']]+=r['records']
    from .lendingclub_temporal import report as temporal_report
    temporal=temporal_report(root,kind,start,end,category)
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'profile_sha256':PROFILE_SHA,'sources':receipt['sources'],
        'publisher':{'ref':receipt['dataset_ref'],'version':receipt['dataset_version'],'license_assertion':receipt['dataset_metadata']['licenseName'],
                     'url':'https://www.kaggle.com/datasets/'+receipt['dataset_ref']},
        'filters':{'kind':kind,'from':start,'to':end,'category':category},'grain':p['date_grain'],'date_column':p['date_column'],
        'category_column':p['category_column'],'source_records':p['rows'],'selected_records':sum(monthly.values()),
        'window_all_category_records':sum(r['records'] for r in window),'selected_category_counts':dict(counts),'category_catalog':list(p['source_category_counts']),
        'timeline':[{'month':m,'observed_records':n} for m,n in sorted(monthly.items())],'selected_month_category_rows':selected,
        'whole_source_category_counts':p['source_category_counts'],'source_records_with_unavailable_date':sum(p['invalid_or_missing_date_counts'].values()),
        'source_records_with_missing_category':p['source_category_counts'].get('',0),'columns':p['columns'],
        'missingness':[{'field':name,'missing':p['missing_counts'][name],'records':p['rows'],'scope':'whole_selected_source_file_not_filtered_by_month_or_category'} for name in p['columns']],
        'raw_cell_positions':p['raw_cell_positions'],'gzip_integrity_verified':p['gzip_full_integrity_verified'],
        'scope_note':'Monthly aggregation preserves separate source date grains. Missing-date records are whole-source controls,not silently allocated to a month.',
        'approval_rate':None,'fixed_horizon_pd':None,'rejected_repayment_labels_available':False,'temporal_evidence':temporal,
        'source_approval_rate_qualified':False,'fixed_horizon_target_qualified':False,'application_time_features_qualified':False,
        'original_issuer_fidelity_verified':False,'issuer_redistribution_rights_verified':False,'rights_note':receipt['rights_note'],
        'model_training_performed':False,'visibility':'private','public_release_approved':False,'limitations':doc['limitations']}
