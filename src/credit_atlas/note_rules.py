"""Acquired base-indentured rules; no inferred jurisdiction or payment calendar."""
from pathlib import Path
from datetime import date
import re
from .workspace import read_json,sha256,contained

def verified_rules(root):
    candidates=[]
    for p in (root/'artifacts/private').glob('apple-note-rules-*/rules-complete.json'):
        if re.fullmatch(r'apple-note-rules-[0-9a-f]{12}',p.parent.name):
            receipt=read_json(p);candidates.append((receipt['created_at'],p,receipt))
    if not candidates:raise ValueError('No acquired note rule book')
    _,p,r=max(candidates,key=lambda x:x[0]);data=read_json(p.parent/'rules.json')
    if r['rules_id']!=p.parent.name or sha256(p.parent/'rules.json')!=r['rules_sha256'] or sha256(root/'scripts/build_apple_note_rules.py')!=r['builder_sha256']:raise ValueError('Note rule book or method changed')
    s=data['source']
    if not re.fullmatch(r'sec-documents-[0-9a-f]{12}',s['folder']):raise ValueError('Invalid rule source folder')
    folder=contained(root,'data/private/sec-documents/'+s['folder']);acq=read_json(folder/'acquisition.json')
    if acq['status']!='ACQUIRED' or any(acq[k]!=s[k] for k in ['url','file','feed_sha256','feed_url','issuer_filing_id','filing_date']) or acq['sha256']!=s['pdf_sha256'] or sha256(contained(root,'data/private/sec-documents/'+s['folder']+'/'+s['file']))!=s['pdf_sha256'] or sha256(folder/'pages.json')!=s['pages_sha256'] or sha256(folder/'issuer-feed.json')!=s['feed_sha256']:raise ValueError('Acquired rule source changed')
    feed=read_json(folder/'issuer-feed.json')['GetEdgarFilingListResult']
    item=next((x for x in feed if x['FilingId']==s['issuer_filing_id']),None)
    if not item or item['StockSymbol']!=data['cik'] or item['FilingTypeMnemonic']!='S-3ASR' or item['FilingDate']!='11/01/2024 00:00:00' or not any(d['Url']==s['url'] and d['DocumentType']=='CONVPDF' for d in item['DocumentList']):raise ValueError('Issuer feed document linkage changed')
    pages=read_json(folder/'pages.json')
    for rule in data['rules']:
        text=re.sub(r'\s+',' ',pages[rule['pdf_page']-1]['text'])
        if text!=rule['page_text'] or not all(a in text for a in rule['anchors']):raise ValueError('Rule clause evidence changed')
    return data,r

def report(views,identifier,query):
    if set(query)-{'view_id','cik','asof'} or query.get('view_id',identifier)!=identifier:raise ValueError('Invalid note rule filters')
    cutoff=query.get('asof','2026-10-10')
    if not isinstance(cutoff,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',cutoff):raise ValueError('ISO rule cutoff required')
    date.fromisoformat(cutoff);snapshot=views.view(identifier);cik=query.get('cik','0000320193');entity=next((e for e in snapshot['entities'] if e['cik']==cik),None)
    if entity is None:raise ValueError('Unknown note rule issuer')
    data,receipt=verified_rules(views.root);supported=cik==data['cik'] and data['source']['filing_date']<=cutoff
    return {'view_id':identifier,'entity':entity,'filters':{'cik':cik,'asof':cutoff},'rules_id':receipt['rules_id'],'rules_sha256':receipt['rules_sha256'],'status':'ACQUIRED_BASE_RULES' if supported else 'NO_ACQUIRED_BASE_RULES_AS_OF','source':data['source'] if supported else None,'rules':data['rules'] if supported else [],'qualification':data['qualification'],'remaining_inputs':data['remaining_inputs'],'method_source_sha256':sha256(Path(__file__)),'limitations':['Base indenture clauses only; series-specific overrides, amendments and applicability require review.','This rule book does not infer New York/Chicago payment jurisdiction from governing law or trustee address.','No bank-closure calendar, current outstanding balance or actual payment record is supplied; adjusted dates remain unqualified.'],'visibility':'private','public_release_approved':False}
