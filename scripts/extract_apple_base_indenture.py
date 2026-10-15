from pathlib import Path
from pypdf import PdfReader
import re,json,hashlib
root=Path(__file__).resolve().parents[1];folder=root/'data/private/sec-documents/sec-documents-480342e5f2e5';r=json.loads((folder/'acquisition.json').read_text(encoding='utf8'));p=folder/r['file']
assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'] and hashlib.sha256((folder/r['feed_file']).read_bytes()).hexdigest()==r['feed_sha256']
pages=[{'page':i+1,'text':x.extract_text()} for i,x in enumerate(PdfReader(p).pages)]
text=' '.join(re.sub(r'\s+',' ',x['text']) for x in pages)
assert 'Apple Inc.' in text and 'November 1, 2024' in text and 'INDENTURE' in text and 'Legal Holidays' in text
(folder/'pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf8')
(folder/'identity-check.json').write_text(json.dumps({'status':'IDENTITY_CHECK_PASS','cik':'0000320193','filing_date':'2024-11-01','pages':len(pages),'full_legal_reviewed':False},indent=2),encoding='utf8')
for page in pages:
    t=re.sub(r'\s+',' ',page['text'])
    if any(s in t for s in ['“Business Day” means','Section 113. Legal Holidays.','“Place of Payment” means','Borough of Manhattan']):print(page['page'],t)
print('PAGES',len(pages))
