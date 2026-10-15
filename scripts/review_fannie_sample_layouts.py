"""Read-only publisher PDF extraction and selected-page rendering."""
import hashlib,json,uuid
from pathlib import Path
from pypdf import PdfReader
import pypdfium2 as pdfium
root=Path(__file__).resolve().parents[1]
source=root/'data/private/mortgage/fannie-public-samples-4d84128d3cb6'
receipt=json.loads((source/'acquisition-complete.json').read_text())
out=root/'artifacts/private'/('fannie-layout-review-'+uuid.uuid4().hex[:12]);out.mkdir()
records=[]
for entry in receipt['sources']:
    if entry['kind']!='layout':continue
    path=source/entry['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
    pdf=PdfReader(path);pages=[p.extract_text() for p in pdf.pages];assert len(pages)==11
    (out/(entry['family']+'-text.json')).write_text(json.dumps({'source_sha256':entry['sha256'],'pages':[{'page':i+1,'text':text} for i,text in enumerate(pages)]},ensure_ascii=False,indent=2),encoding='utf-8')
    selected=[2] if entry['family']=='single-family' else [11]
    document=pdfium.PdfDocument(path)
    for page in selected:
        image=document[page-1].render(scale=1.5).to_pil()
        image.save(out/(entry['family']+'-page-'+str(page)+'.png'))
    document.close()
    records.append({'file':entry['file'],'pages':len(pages),'selected_rendered_pages':selected,'source_sha256':entry['sha256']})
(out/'receipt.json').write_text(json.dumps({'status':'EXTRACTED_SELECTED_PAGES_RENDERED','documents':records,'full_schema_compatibility_qualified':False,'no_source_pdf_modified':True},indent=2),encoding='utf-8')
print(out)
