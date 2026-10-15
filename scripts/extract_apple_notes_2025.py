from pathlib import Path
import hashlib,json,re
from pypdf import PdfReader
root=Path(__file__).resolve().parents[1];folder=root/'data/private/sec-documents/sec-documents-fbf41f7fbac2'
receipt=json.loads((folder/'acquisition.json').read_text(encoding='utf8'));path=folder/receipt['file']
assert hashlib.sha256(path.read_bytes()).hexdigest()==receipt['sha256']
pages=[{'page':i+1,'text':p.extract_text()} for i,p in enumerate(PdfReader(path).pages)]
assert 'Apple Inc.' in pages[0]['text'] and 'May 5, 2025' in pages[0]['text']
assert 'May 12, 2025' in ' '.join(p['text'] for p in pages) and '4.750%' in ' '.join(p['text'] for p in pages)
(folder/'pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf8')
(folder/'identity-check.json').write_text(json.dumps({'status':'IDENTITY_CHECK_PASS','cik':'0000320193','earliest_event_report_date':'2025-05-05','certificate_date':'2025-05-12','pages':len(pages),'full_legal_reviewed':False},indent=2),encoding='utf8')
for page in pages:
 text=re.sub(r'\s+',' ',page['text'])
 if any(t in text for t in ['Title of Securities','Interest Payment Dates:','360-day year','CUSIP']):print(page['page'],text[:8000])
print('PAGES',len(pages))
