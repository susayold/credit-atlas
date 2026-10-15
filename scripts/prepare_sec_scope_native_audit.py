"""Prepare every exported cell/formula for read-only native recalculation."""
import argparse,json,shutil,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from uuid import uuid4
from credit_atlas.workspace import read_json,sha256,write_new,contained

p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('--expected-scopes',type=int,default=36);a=p.parse_args();root=Path.cwd().resolve()
source_receipt=contained(root,a.receipt);receipt=read_json(source_receipt);assert receipt['status']=='PASS' and len(receipt['scopes'])==a.expected_scopes
out=root/'artifacts/private'/('native-excel-qa-sec-'+uuid4().hex[:12]);out.mkdir()
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
books=[]
for i,scope in enumerate(receipt['scopes']):
    path=contained(root,scope['workbook']);assert sha256(path)==scope['sha256']
    dest=out/f'{i:02d}.xlsx';shutil.copyfile(path,dest);cells=[]
    with zipfile.ZipFile(path) as z:
        assert not any('externalLinks' in n or 'vbaProject' in n for n in z.namelist())
        strings=[''.join(t.text or '' for t in x.iter('{'+ns['s']+'}t')) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
        relations={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',ns):
            name=relations[sheet.get('{'+rel+'}id')];name=name.lstrip('/') if name.startswith('/') else 'xl/'+name
            for c in ET.fromstring(z.read(name)).findall('.//s:sheetData/s:row/s:c',ns):
                value=c.findtext('s:v',None,ns);formula=c.findtext('s:f',None,ns);kind=c.get('t','n')
                if kind=='s' and value is not None:value=strings[int(value)]
                if kind=='inlineStr':value=''.join(t.text or '' for t in c.findall('s:is//s:t',ns))
                if value is None and formula is None:continue
                assert kind!='e'
                cells.append({'sheet':sheet.get('name'),'cell':c.get('r'),'expected':value,'kind':kind,'formula':formula})
    books.append({'source':str(path),'copy':str(dest),'source_sha256':scope['sha256'],'cells':cells})
write_new(out/'plan.json',{'books':books,'output_folder':str(out),'source_receipt_sha256':sha256(source_receipt)})
print(out/'plan.json')
