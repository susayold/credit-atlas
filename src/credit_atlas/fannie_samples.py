"""Source-scoped public format samples, never a qualified mortgage model dataset."""
from copy import deepcopy
from .workspace import contained,read_json,sha256

PROFILE='fannie-public-profile-fafc20762187'
PROFILE_SHA='e2575f225eeffc6d99beee07f5165c1b3a7c1a34e85d3c09f1f5d2c2ebed128e'

def report(root,query):
    if not isinstance(query,dict) or set(query)-{'family'} or not isinstance(query.get('family','all'),str) or query.get('family','all') not in {'all','single-family','multifamily'}:
        raise ValueError('Invalid Fannie sample scope')
    family=query.get('family','all')
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('Fannie source profile changed')
    doc=read_json(path)
    source=contained(root,'data/private/mortgage/'+doc['source_id'])
    if sha256(source/'acquisition-complete.json')!=doc['source_receipt_sha256']:raise ValueError('Fannie source receipt changed')
    for file in doc['sources']:
        if sha256(contained(root,str((source/file['file']).relative_to(root))))!=file['sha256']:raise ValueError('Fannie sample source changed')
    result=deepcopy(doc);result['profiles']=[p for p in doc['profiles'] if family=='all' or p['family']==family]
    result['sources']=[s for s in doc['sources'] if family=='all' or s['family']==family]
    result['filters']={'family':family};result['profile_sha256']=PROFILE_SHA
    if family=='single-family':result['multifamily_link_support']=None
    result['summary']={'sample_files':len(result['profiles']),'source_rows':sum(p['rows'] for p in result['profiles']),'source_positions':sum(p['source_positions'] for p in result['profiles']),
                       'rows_are_not_unique_borrowers':True,'added_freddie_annual_vintages':0,'mortgage_model_training_performed':False}
    return result
