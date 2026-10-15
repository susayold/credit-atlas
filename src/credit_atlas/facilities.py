"""Disclosed facility calendars; commitments are not principal or available liquidity."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path
import re
from .workspace import read_json,sha256,contained

def catalog(root):
    candidates=[]
    for p in (root/'artifacts/private').glob('ford-facilities-*/catalog-complete.json'):
        if re.fullmatch(r'ford-facilities-[0-9a-f]{12}',p.parent.name):
            r=read_json(p);candidates.append((r['created_at'],p,r))
    if not candidates:raise ValueError('No acquired facility catalog available')
    _,path,receipt=max(candidates,key=lambda x:x[0])
    data=read_json(path.parent/'catalog.json')
    if receipt['catalog_id']!=path.parent.name or sha256(path.parent/'catalog.json')!=receipt['catalog_sha256'] or sha256(root/'scripts/build_ford_facility_catalog.py')!=receipt['builder_sha256']:
        raise ValueError('Facility catalog or extraction method changed')
    for s in data['sources'].values():
        if not re.fullmatch(r'sec-documents-[0-9a-f]{12}',s['folder']):raise ValueError('Invalid document folder')
        folder=contained(root,'data/private/sec-documents/'+s['folder'])
        pdf=contained(root,'data/private/sec-documents/'+s['folder']+'/'+s['file'])
        r=read_json(folder/'acquisition.json')
        if r['status']!='ACQUIRED' or r['url']!=s['url'] or r['file']!=s['file'] or r['sha256']!=s['pdf_sha256'] or sha256(pdf)!=s['pdf_sha256'] or sha256(folder/'pages.json')!=s['pages_sha256']:
            raise ValueError('Acquired facility document changed')
    for row in data['versions']+[data['covenant']]:
        for e in row['evidence']:
            s=data['sources'][e['source_key']]
            pages=read_json(contained(root,'data/private/sec-documents/'+s['folder']+'/pages.json'))
            text=re.sub(r'\s+',' ',pages[e['pdf_page']-1]['text'])
            if text!=e['page_text'] or not all(a in text for a in e['anchors']):raise ValueError('Facility page evidence changed')
    return data,receipt

def select(data,cutoff):
    """Both effective and filing dates constrain selection; no prospective terms."""
    date.fromisoformat(cutoff)
    selected={}
    for row in data['versions']:
        if row['effective_date']<=cutoff and row['filing_date']<=cutoff:
            key=row['facility_id']
            if key not in selected or (row['effective_date'],row['filing_date'])>(selected[key]['effective_date'],selected[key]['filing_date']):selected[key]=row
    result=[]
    for key,row in sorted(selected.items()):
        item=deepcopy(row)
        prior=sorted([r for r in data['versions'] if r['facility_id']==key and r['effective_date']<row['effective_date'] and r['filing_date']<=cutoff],key=lambda r:r['effective_date'])
        item['prior_version']=({k:prior[-1][k] for k in ['effective_date','commitment_usd_exact','loan_maturity_date','availability_end_date']} if prior else None)
        boundary=row['availability_end_date'] or row['loan_maturity_date']
        item['scheduled_boundary_date']=boundary
        item['scheduled_boundary_type']='draw availability ends' if row['availability_end_date'] else 'revolving maturity'
        item['days_to_scheduled_boundary']=(date.fromisoformat(boundary)-date.fromisoformat(cutoff)).days
        item['calendar_status']='scheduled boundary passed' if boundary<cutoff else 'scheduled boundary today' if boundary==cutoff else 'scheduled boundary ahead'
        result.append(item)
    return result

def report(views,identifier,query):
    if set(query)-{'view_id','cik','asof'} or query.get('view_id',identifier)!=identifier:raise ValueError('Invalid facility scope')
    cutoff=query.get('asof','2026-10-10')
    if not isinstance(cutoff,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',cutoff):raise ValueError('ISO facility cutoff required')
    date.fromisoformat(cutoff)
    snapshot=views.view(identifier);cik=query.get('cik','0000320193')
    entity=next((e for e in snapshot['entities'] if e['cik']==cik),None)
    if entity is None:raise ValueError('Unknown SEC issuer CIK')
    data,receipt=catalog(views.root)
    supported=cik==data['cik'];rows=select(data,cutoff) if supported else []
    cov=deepcopy(data['covenant']) if supported and data['covenant']['effective_date']<=cutoff and data['covenant']['filing_date']<=cutoff else None
    return {'view_id':identifier,'entity':entity,'filters':{'cik':cik,'asof':cutoff},'catalog_id':receipt['catalog_id'],'catalog_sha256':receipt['catalog_sha256'],'status':'DISCLOSED_VERSIONS_AVAILABLE' if rows else 'NO_ACQUIRED_FACILITY_VERSION','rows':rows,'sources':{k:v for k,v in data['sources'].items() if supported and v['filing_date']<=cutoff},'covenant':cov,
        'summary':{'selected_facility_tranches':len(rows),'disclosed_commitment_total_usd_exact':str(sum((Decimal(r['commitment_usd_exact']) for r in rows),Decimal(0))) if rows else None,'outstanding_principal_usd_exact':None,'actual_available_liquidity_usd_exact':None,'dscr':None},'qualification':data['qualification'],'method_source_sha256':sha256(Path(__file__)),
        'limitations':['Selected acquired disclosures only; not a complete issuer debt inventory or verified latest amendment chain.','Disclosed commitments are not drawn principal, undrawn availability or EAD; totals exclude local facilities and other instruments.','Cutoff uses filing/effective dates at day granularity; this is not point-in-time historical availability qualification.','Calendar status concerns the stated version only; it does not prove current facility activity, repayment or default.','Available Liquidity excludes foreign subsidiary holdings, restricted cash and FMCC amounts under contract definitions. Company-wide liquidity cannot substitute for covenant actuals.','Headroom/compliance and DSCR remain unavailable without qualified contract inputs and full term review.','Selected redline clauses have page evidence; omitted/redacted portions and full exhibits still require legal review.'],'visibility':'private','public_release_approved':False}
