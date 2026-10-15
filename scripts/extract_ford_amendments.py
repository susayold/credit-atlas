from pathlib import Path
from pypdf import PdfReader
import json
folder=Path('data/private/sec-documents/sec-documents-a1aa8dad9beb');p=folder/'ford-credit-amendments-20250417.pdf';r=PdfReader(p);pages=[{'page':i+1,'text':page.extract_text()} for i,page in enumerate(r.pages)];(folder/'pages.json').write_text(json.dumps(pages,ensure_ascii=False),encoding='utf8');assert len(pages)==171 and 'April 17, 2025' in pages[0]['text'] and 'FORD MOTOR COMPANY' in pages[0]['text'];(folder/'identity-check.json').write_text(json.dumps({'status':'IDENTITY_CHECK_PASS','cik':'0000037996','report_date':'2025-04-17','pages':len(pages),'full_legal_reviewed':False},indent=2));print(len(pages),folder)
