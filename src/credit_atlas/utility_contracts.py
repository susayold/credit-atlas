"""Dated official-statement descriptions; no automatic legal applicability."""
from .workspace import contained,read_json,sha256
SOURCE='utility-contract-source-cac5d22ec69d'
RECEIPT='99a9782c07621805b5a437a389953d097bec71e389382493c225e8d59fa3eeb1'
PROFILE='utility-contract-profile-05bce98c9db8'
PROFILE_SHA='c31ab0fc82e030f38c5c457d7b95731059ebdd8a1ba322fb8671e52dd8b083f5'

def report(root,system):
    if system not in {'water','wastewater'}:raise ValueError('Invalid utility contract system')
    folder=contained(root,'data/private/business/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('Utility contract receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for s in receipt['sources']:
        path=contained(folder,s['file'])
        if path.stat().st_size!=s['bytes'] or sha256(path)!=s['sha256']:raise ValueError('Utility contract source changed')
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('Utility contract normalized profile changed')
    doc=read_json(path);item=next(s for s in doc['systems'] if s['system']==system)
    source=next(s for s in receipt['sources'] if s['file']==item['file'])
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'profile_sha256':PROFILE_SHA,
        'source':source,'description':item,'contractual_compliance_qualified':False,
        'full_executed_indenture_chain_acquired':False,'applicable_historical_threshold':None,
        'qualified_headroom':None,'compliance':None,'public_release_approved':False,'visibility':'private',
        'required_inputs':['Executed indenture and all applicable supplements with effective-date evidence',
            'Trustee-filed District certificate/consent evidence for the springing amendments',
            'Applicable fiscal-year rate-setting/test scope and adjusted numerator/debt-service reconciliation',
            'Certificates/actions relevant to default/cure exceptions; historical scope separate from 2026 disclosures'],
        'limitations':['1.1x reported covenant and 1.6x Board policy target are different measures.',
            'March/April 2026 statement descriptions are not automatically applicable to historical 2020–2025 tests.',
            'Appendix H is a color redline containing both deletions and additions; raw extracted text is not clean operative wording.',
            'Consent estimates and contemplated bond delivery do not prove the required certificate was filed.',
            'A ratio below a threshold alone does not establish a contractual Event of Default.']}
