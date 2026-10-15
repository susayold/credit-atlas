from pathlib import Path
from pypdf import PdfReader
import json
folder=Path('data/private/sec-documents/sec-documents-563b8f103cfd');r=PdfReader(folder/'ford-annual-report-2025.pdf');pages=[{'page':i+1,'text':p.extract_text()} for i,p in enumerate(r.pages)];(folder/'pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf8');assert 'FORD MOTOR COMPANY' in ''.join(p['text'] for p in pages[:5]);print('PAGES',len(pages));hits=[]
for x in pages:
 t=x['text'];n=t.lower().find('available liquidity');
 if n>=0:hits.append({'page':x['page'],'snippet':t[max(0,n-250):n+1000]})
(folder/'liquidity-candidates.json').write_text(json.dumps({'status':'CANDIDATES_REQUIRE_CONTRACT_SCOPE_REVIEW','candidates':hits},ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(hits[:5],ensure_ascii=False));(folder/'identity-check.json').write_text(json.dumps({'status':'IDENTITY_CHECK_PASS','cik':'0000037996','issuer':'Ford Motor Company','report_year':2025,'pages':len(pages),'full_legal_reviewed':False},indent=2))
