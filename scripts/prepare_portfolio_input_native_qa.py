"""Read-only template XML audit plan; authoring/layout remain unchanged."""
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree as ET
import json,shutil,zipfile
from credit_atlas.workspace import sha256

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'apps/excel/templates/CreditAtlas-Portfolio-Input.xlsx'
out=ROOT/'artifacts/private'/('native-excel-qa-input-'+uuid4().hex[:12]);out.mkdir()
dest=out/'portfolio-input.xlsx';shutil.copyfile(source,dest)
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
cells=[]
with zipfile.ZipFile(source) as z:
    shared=[''.join(t.text or '' for t in x.iter('{'+ns['s']+'}t')) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
    targets={x.get('Id'):x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',ns):
        if sheet.get('name') not in ['InputPositions','InputControl']:continue
        target=targets[sheet.get('{'+rel+'}id')];target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        for c in ET.fromstring(z.read(target)).findall('.//s:sheetData/s:row/s:c',ns):
            kind=c.get('t','n');value=c.findtext('s:v',None,ns);formula=c.findtext('s:f',None,ns)
            if kind=='s' and value is not None:value=shared[int(value)]
            elif kind=='inlineStr':value=''.join(t.text or '' for t in c.findall('s:is//s:t',ns))
            if value is None and formula is None:continue
            cells.append({'sheet':sheet.get('name'),'cell':c.attrib['r'],'expected':value,'kind':kind,'formula':formula})
assert cells and not any(c['formula'] is not None for c in cells)
plan={'output_folder':str(out),'books':[{'source':str(source),'copy':str(dest),'source_sha256':sha256(source),'cells':cells}]}
(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out)
