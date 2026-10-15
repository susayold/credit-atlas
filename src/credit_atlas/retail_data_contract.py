"""Project pinned pre-freeze source aggregates; never read client predictor rows."""
from .workspace import contained,read_json,sha256


def report(views,query):
    if set(query)!={'view_id'}:raise ValueError('Retail data contract requires view_id only')
    identifier=query['view_id'];snapshot=views.view(identifier)
    anchor=read_json(contained(views.root,'artifacts/private/'+identifier+'/view-complete.json'))
    pins={k.replace('\\','/'):v for k,v in anchor['inputs_sha256'].items()}
    base='artifacts/private/'+snapshot['retail']['case_id']+'/'
    def saved(relative):
        path=contained(views.root,relative)
        if relative not in pins or sha256(path)!=pins[relative]:raise ValueError('Retail contract aggregate changed or not pinned')
        return read_json(path)
    case=saved(base+'case-complete.json');quality=saved(base+'quality.json')
    protocol=saved(base+'protocol.json');reconciliation=saved(base+'reconciliation.json')
    sourcebase='data/private/public-suite/'+snapshot['suite_id']+'/'
    source=saved(sourcebase+'uci-retail-receipt.json');metadata=saved(sourcebase+'uci-retail-metadata.json')['data']
    if case['case_id']!=snapshot['retail']['case_id'] or case['suite_id']!=snapshot['suite_id']:
        raise ValueError('Retail case/suite scope mismatch')
    profile=source['profile'];n=quality['clients']
    if n!=case['clients'] or n!=profile['rows'] or quality['history_rows']!=6*n or case['history_rows']!=6*n:
        raise ValueError('Client/history population mismatch')
    if quality['target_counts']!=profile['target_counts'] or sum(quality['target_counts'].values())!=n:
        raise ValueError('Target aggregate mismatch')
    if quality['support']!=case['support'] or quality['support']!=snapshot['retail']['support']:
        raise ValueError('Split support mismatch')
    if sum(s['positive'] for s in quality['support'].values())!=quality['target_counts']['1'] or sum(s['negative'] for s in quality['support'].values())!=quality['target_counts']['0']:
        raise ValueError('Split/target population mismatch')
    if reconciliation['status']!='PASS' or reconciliation['differing_rows']!={'clients':0,'history':0}:
        raise ValueError('Saved source reconciliation not verified')
    if metadata['uci_id']!=350 or metadata['target_col']!=['Y'] or metadata['index_col']!=['ID']:
        raise ValueError('UCI source/target contract mismatch')
    names=[v['description'] for v in metadata['variables'] if v['role']=='Feature']
    allowlist=protocol['feature_allowlist']['numeric']+protocol['feature_allowlist']['categorical']
    if len(names)!=23 or len(set(allowlist))!=19 or not set(allowlist)<=set(names):raise ValueError('Feature mapping mismatch')
    if set(allowlist)&set(protocol['excluded_predictors']) or not {'source_client_id','target'}<=set(protocol['excluded_predictors']):raise ValueError('Source IDs/targets must not be predictors')
    mapping=[]
    for i in range(6):
        mapping.append({'reference_month':f'2005-{9-i:02d}','status_field':['PAY_0','PAY_2','PAY_3','PAY_4','PAY_5','PAY_6'][i],'status_source_field':f'X{6+i}','bill_field':f'BILL_AMT{i+1}','bill_source_field':f'X{12+i}','payment_field':f'PAY_AMT{i+1}','payment_source_field':f'X{18+i}'})
    categories=[]
    for f,counts in quality['source_category_counts'].items():
        if sum(counts.values())!=n:raise ValueError('Source category population mismatch')
        for code,count in sorted(counts.items(),key=lambda x:int(x[0])):
            if f.startswith('PAY_'):
                description='Pay duly (source dictionary)' if code=='-1' else 'Payment delay category;9 means nine months or above' if 1<=int(code)<=9 else 'Not fully defined by simplified source dictionary;preserved separately'
                qualified=code=='-1' or 1<=int(code)<=9
            else:
                qualified=not ((f=='EDUCATION' and code in {'0','5','6'}) or (f=='MARRIAGE' and code=='0'))
                description='Source category;not an inferred missing value' if qualified else 'Outside simplified source dictionary;retained,excluded from predictors'
            categories.append({'field':f,'code':code,'clients':count,'dictionary_qualified':qualified,'interpretation':description})
    return {'schema_version':'retail-data-contract-v1','view_id':identifier,'suite_id':snapshot['suite_id'],'case_id':case['case_id'],
            'scope':'Whole historical Taiwan acquisition;pre-freeze saved aggregates','clients':n,'history_rows':quality['history_rows'],'history_rows_per_client':6,
            'target':case['target'],'target_counts':quality['target_counts'],'support':quality['support'],'currency':quality['currency'],
            'history_mapping':mapping,'feature_mapping':[{'source_field':v['name'],'feature':v['description'],'predictor':v['description'] in allowlist} for v in metadata['variables'] if v['role']=='Feature'],
            'source_category_counts':categories,'negative_statement_cells_retained':quality['negative_statement_values_retained'],
            'excluded_predictors':protocol['excluded_predictors'],'protocol':protocol,'saved_reconciliation':reconciliation,
            'evidence_hashes':{relative:pins[relative] for relative in [base+'case-complete.json',base+'quality.json',base+'protocol.json',base+'reconciliation.json',sourcebase+'uci-retail-receipt.json',sourcebase+'uci-retail-metadata.json']},
            'visibility':'private','public_release_approved':False,'temporal_out_of_time':False,'qualified_for_production':False,
            'warnings':quality['warnings'],
            'limitations':['Saved pre-freeze reconciliation is hash-verified;client/history predictor rows are not reopened by this endpoint.',
                           '180000 history rows are six observations per client;only30000 source target labels.',
                           'Source-defined next-month default is not regulatory default,PD12 or application underwriting.',
                           'Parser missingness and dictionary-qualification are different;zero missingness does not resolve ambiguous codes.',
                           'Source reference months do not prove historical publication availability or Vietnam applicability.']}
