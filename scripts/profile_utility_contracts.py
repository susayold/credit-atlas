"""Locate official-statement identity/clauses without declaring compliance."""
import json,uuid
from pathlib import Path
from pypdf import PdfReader
root=Path.cwd();source=root/'data/private/business/utility-contract-source-cac5d22ec69d'
out=root/'artifacts/private'/('utility-contract-discovery-'+uuid.uuid4().hex[:12]);out.mkdir()
docs=[]
for name in ['water-official-statement.pdf','wastewater-official-statement.pdf']:
    reader=PdfReader(source/name);pages=[]
    for i,p in enumerate(reader.pages):
        text=p.extract_text();norm=' '.join(text.split())
        if i<3 or any(phrase in norm for phrase in ['Rate Covenant','1.1 times','1.25 times','Section 5.04','1.2 times','policy target','1.6 times']):
            pages.append({'physical_page':i+1,'text':text})
    docs.append({'file':name,'pages':len(reader.pages),'selected_pages':pages})
(out/'profile.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf8')
print(out)
for d in docs:
    print(d['file'],d['pages']);print(' '.join(d['selected_pages'][0]['text'].split())[:1800])
    for p in d['selected_pages']:
        norm=' '.join(p['text'].split())
        for phrase in ['1.1 times','1.25 times','1.2 times','1.6 times','Rate Covenant']:
            n=norm.find(phrase)
            if n>=0:print(p['physical_page'],phrase,norm[max(0,n-120):n+900])
