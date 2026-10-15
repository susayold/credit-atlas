"""Issuer descriptions with unproven prepared aliases/timing kept explicit."""
from .workspace import contained,read_json,sha256
SOURCE='lendingclub-dictionary-source-65e0222b7c42'
RECEIPT='2c38861ef1b62a92dc79c1d37195ccf6f1e5885ef8f0f17c15d3c830061460ca'
PROFILE='lendingclub-dictionary-profile-9b8a25e34bf8'
PROFILE_SHA='bf8415ed612602d0941b44ffffda81b912daa05832f7a4729ab594335a7072a3'

def report(root,field):
    folder=contained(root,'data/private/retail/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('LendingClub dictionary receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for s in receipt['sources']:
        p=contained(folder,s['file'])
        if p.stat().st_size!=s['bytes'] or sha256(p)!=s['sha256']:raise ValueError('LendingClub dictionary source changed')
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('LendingClub dictionary profile changed')
    doc=read_json(path);selected=next((r for r in doc['column_review'] if r['prepared_field']==field),None)
    if selected is None:raise ValueError('Unknown LendingClub dictionary field')
    excluded=[r['prepared_field'] for r in doc['column_review'] if r['proposed_role']!='candidate_requires_application_asof_evidence' or r['definition_mapping']!='exact_name']
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'profile_sha256':PROFILE_SHA,'source':doc['source'],
        'coverage':doc['coverage'],'selected_field':selected,'column_review':doc['column_review'],'workbook_metadata':doc['workbook_metadata'],
        'candidate_exclusions_pending_review':excluded,'origin_identity_references':receipt['successor_identity_references'],
        'application_time_features_qualified':False,'contributor_preprocessing_verified':False,'workbook_metadata_is_publication_vintage':False,
        'public_release_approved':False,'limitations':['Dictionary workbook metadata is not an original publication/availability timestamp.',
            'Exact field-name match proves definition correspondence only;prepared values and decision-time availability still need provenance.',
            'Proposed aliases and transformed encodings are not certified original fields.',
            'DTI excludes mortgage and requested LC loan;annual income is self-reported,not verified disposable income.',
            'Requested amount may be reduced by the credit department;do not silently use it as the original application amount.',
            'Dictionary does not supply the missing event dates,rejected population or full booked-cohort denominator.']}
