from pathlib import Path
from pypdf import PdfReader
import json
folder=Path('data/private/sec-documents/sec-documents-6f8e86a15804');r=PdfReader(folder/'ford-term-loan-20250728.pdf');pages=[p.extract_text() for p in r.pages];(folder/'pages.json').write_text(json.dumps([{'page':i+1,'text':t} for i,t in enumerate(pages)],ensure_ascii=False),encoding='utf8');print('PAGES',len(pages));print(pages[0][:1000]);print('HITS',[(i+1,t.lower().find('liquidity')) for i,t in enumerate(pages) if 'liquidity' in t.lower()]);print(pages[1][:2300])
