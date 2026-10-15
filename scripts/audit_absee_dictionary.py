"""Independent XML paragraph/PDF/coverage audit, run with bundled PDF Python."""
import json,hashlib,re,uuid
from pathlib import Path
from xml.etree import ElementTree as ET
from pypdf import PdfReader
import pypdfium2 as pdfium

root=Path.cwd();folder=root/'data/private/structured/schedule-al-1b72bcb43754'
doc=json.loads((root/'artifacts/private/absee-dictionary-6cc1ca9b700d/dictionary.json').read_text(encoding='utf8'))
profile=json.loads((root/'artifacts/private/absee-profile-63397e5ebbc6/profile.json').read_text())
receipt=json.loads((folder/'acquisition-complete.json').read_text())
out=root/'artifacts/private'/('absee-dictionary-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
hashes={x['file']:hashlib.sha256((folder/x['file']).read_bytes()).hexdigest()==x['sha256'] for x in receipt['sources']}
paragraphs=[' '.join(''.join(p.itertext()).split()) for p in ET.parse(folder/'CFR-2025-title17-vol3-sec229-1125.xml').iter('P')]
pdf=folder/'CFR-2025-title17-vol3-sec229-1125.pdf';reader=PdfReader(pdf)
texts=[p.extract_text() for p in reader.pages]
normalize=lambda x:re.sub('[^a-z0-9]','',x.lower())
start=next(i for i,t in enumerate(texts) if 'Item 3. Automobile loans.' in t)
end=next(i for i,t in enumerate(texts[start:],start) if 'Item 4. Automobile leases.' in t)
def body(text):
    text=text.split('VerDate',1)[0]
    return re.sub(r'(?m)^.*(?:Securities and Exchange Commission|17 CFR Ch\. II).*$|^\d+\s*$','',text)
joined=normalize(' '.join(body(t) for t in texts[start:end+1]))
checks=[]
for row in doc['fields']:
    active=[p for p in profile['periods'] if row['field'] in p['columns']]
    evidence=paragraphs[row['xml_paragraph_index']]
    # A page-bound prefix verifies the acquired PDF independently of XML indexing.
    prefix=normalize(evidence)[:120]
    pages=[i+1 for i in range(start,end+1) if prefix in normalize(texts[i])]
    if not pages:
        pages=[i+1 for i in range(start,end) if prefix in normalize(body(texts[i])+body(texts[i+1]))]
    checks.append({'field':row['field'],'clause':row['schedule_al_item'],
                   'xml_paragraph_matches':evidence==row['definition'],
                   'pdf_definition_prefix_pages':pages,
                   'full_pdf_definition_matches':normalize(evidence) in joined,
                   'coverage_matches':row['present_periods']==len(active) and row['absent_periods']==11-len(active)
                     and row['present_schema_rows']==sum(p['rows'] for p in active)
                     and row['missing_present_schema_rows']==sum(p['missing_by_field'][row['field']] for p in active)})
pass_checks=all(x['xml_paragraph_matches'] and x['pdf_definition_prefix_pages'] and x['full_pdf_definition_matches'] and x['coverage_matches'] for x in checks)
with pdfium.PdfDocument(str(pdf)) as p:
    for i in range(start,end+1):
        page=p[i];bitmap=page.render(scale=1.4);bitmap.to_pil().save(out/f'source-page-{i+1}.png');bitmap.close();page.close()
r={'status':'PASS' if all(hashes.values()) and pass_checks else 'ISSUES_FOUND',
   'source_hash_checks':hashes,'fields_checked':len(checks),'checks':checks,'pdf_pages':len(reader.pages),
   'auto_loan_pdf_pages':list(range(start+1,end+2)),
   'scope':'Full definition PDF/XML cross-check and aggregate profile coverage; not full XSD/value fidelity',
   'xsd_verified':False,'mirror_fidelity_verified':False,'model_ready':False}
(out/'receipt.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(out);print(r['status']);print([x['field'] for x in checks if not x['pdf_definition_prefix_pages'] or not x['full_pdf_definition_matches']])
