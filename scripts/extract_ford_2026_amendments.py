from pathlib import Path
from pypdf import PdfReader
import hashlib,json
root=Path(__file__).resolve().parents[1]
folder=root/'data/private/sec-documents/sec-documents-b46630da17d1'
r=json.loads((folder/'acquisition.json').read_text(encoding='utf8'))
p=folder/r['file']
assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
pages=[{'page':i+1,'text':page.extract_text()} for i,page in enumerate(PdfReader(p).pages)]
assert 'FORD MOTOR COMPANY' in pages[0]['text'] and 'April 15, 2026' in pages[0]['text']
(folder/'pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf8')
(folder/'identity-check.json').write_text(json.dumps({'status':'IDENTITY_CHECK_PASS','cik':'0000037996','report_date':'2026-04-15','pages':len(pages),'source_sha256':r['sha256'],'full_legal_reviewed':False},indent=2),encoding='utf8')
for page in pages:
    if page['page']<=6 or any(s in page['text'] for s in ['Availability Termination Date','7.1. Financial Condition','"Available Liquidity"']):
        print(page['page'],page['text'][:6500])
print('PAGES',len(pages))
