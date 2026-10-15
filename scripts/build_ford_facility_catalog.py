"""Curate disclosed facility versions with page-level evidence and source hashes."""
from pathlib import Path
import json,re,hashlib,uuid
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
base=root/'data/private/sec-documents'
sources={}
def source(key,folder,filing_date):
    p=base/folder;r=json.loads((p/'acquisition.json').read_text(encoding='utf8'))
    pages=json.loads((p/'pages.json').read_text(encoding='utf8'))
    assert r['status']=='ACQUIRED' and hashlib.sha256((p/r['file']).read_bytes()).hexdigest()==r['sha256']
    sources[key]={'folder':folder,'file':r['file'],'url':r['url'],'pdf_sha256':r['sha256'],'pages_sha256':hashlib.sha256((p/'pages.json').read_bytes()).hexdigest(),'filing_date':filing_date,'page_count':len(pages)}
    return pages
p25=source('amendments_2025','sec-documents-a1aa8dad9beb','2025-04-17')
pt=source('term_2025','sec-documents-6f8e86a15804','2025-07-28')
p26=source('amendments_2026','sec-documents-b46630da17d1','2026-04-15')
def evidence(key,pages,number,anchors):
    text=re.sub(r'\s+',' ',pages[number-1]['text'])
    assert all(a in text for a in anchors),(number,anchors)
    return {'source_key':key,'pdf_page':number,'anchors':anchors,'page_text':text}
e25=evidence('amendments_2025',p25,2,['$3.4 billion','$10.1 billion','April 17, 2030','$2.0 billion','$2.5 billion','April 16, 2026'])
et=evidence('term_2025',pt,2,['$3.0 billion','July 28, 2026','December 31, 2028'])
e26=evidence('amendments_2026',p26,2,['$3.4 billion','April 13, 2029','$10.1 billion','April 15, 2031','$2.0 billion','$2.5 billion','April 14, 2027','$3.0 billion'])
e26term=evidence('amendments_2026',p26,3,['31, 2026','December 31, 2028','$4 billion'])
rows=[]
def add(fid,title,amount,effective,maturity,ev,availability=None):
    rows.append({'facility_id':fid,'title':title,'commitment_usd_exact':amount,'effective_date':effective,'filing_date':sources[ev['source_key']]['filing_date'],'loan_maturity_date':maturity,'availability_end_date':availability,'outstanding_principal_usd_exact':None,'undrawn_commitment_usd_exact':None,'evidence':[ev]})
for d,ev,dates in [('2025-04-17',e25,['2028-04-17','2030-04-17','2028-04-17','2026-04-16']),('2026-04-15',e26,['2029-04-13','2031-04-15','2029-04-13','2027-04-14'])]:
    for fid,title,amount,maturity in zip(['corporate_short','corporate_long','supplemental','364_day'],['Corporate revolving — shorter tranche','Corporate revolving — longer tranche','Supplemental revolving','364-day revolving'],['3400000000','10100000000','2000000000','2500000000'],dates):add(fid,title,amount,d,maturity,ev)
add('delayed_draw','Delayed-draw term loan','3000000000','2025-07-28','2028-12-31',et,'2026-07-28')
add('delayed_draw','Delayed-draw term loan','3000000000','2026-04-15','2028-12-31',e26,'2026-12-31')
rows[-1]['evidence'].append(e26term)
covdef=evidence('amendments_2026',p26,39,['“Available Liquidity”','Foreign Subsidiaries','restricted cash'])
# Section 7.2 for the corporate facility is displayed in a redline exhibit.
matches=[p for p in p26 if '7.2 Available Liquidity.' in re.sub(r'\s+',' ',p['text']) and '$4,000,000,000 at any time' in re.sub(r'\s+',' ',p['text'])]
assert len(matches)==1
covtest=evidence('amendments_2026',p26,matches[0]['page'],['7.2 Available Liquidity.','$4,000,000,000 at any time'])
payload={'schema_version':1,'cik':'0000037996','issuer':'Ford Motor Company','sources':sources,'versions':rows,'covenant':{'facility_id':'corporate_revolving','effective_date':'2026-04-15','filing_date':'2026-04-15','operator':'>=','minimum_usd_exact':'4000000000','definition':'Total available revolving commitments plus consolidated cash/equivalents/marketable securities less FMCC amounts, excluding foreign subsidiaries and restricted cash; subject to full agreement definitions.','evidence':[covdef,covtest],'actual_usd_exact':None,'headroom_usd_exact':None,'compliance':None},'qualification':{'full_amendment_chain_reviewed':False,'full_legal_terms_reviewed':False,'historical_availability_qualified':False,'actual_debt_service_supported':False,'covenant_compliance_supported':False},'visibility':'private'}
folder=root/'artifacts/private'/('ford-facilities-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
out=folder/'catalog.json'
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
(folder/'catalog-complete.json').write_text(json.dumps({'catalog_id':folder.name,'created_at':datetime.now(timezone.utc).isoformat(),'catalog_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'visibility':'private'},indent=2),encoding='utf8')
print(out);print('versions',len(rows),'covenant pages',covdef['pdf_page'],covtest['pdf_page'])
