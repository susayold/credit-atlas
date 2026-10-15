"""Read saved XML, prepare disposable copies and native calculation comparisons."""
import json,uuid,zipfile,shutil,argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import sha256
parser=argparse.ArgumentParser();parser.add_argument('--sec-source',type=Path);args=parser.parse_args()
root=Path.cwd();out=root/'artifacts/private'/('native-excel-qa-'+uuid.uuid4().hex[:12]);out.mkdir()
paths=['retail-source-quality-qa-594921ea7ac8/kpi.xlsx',
       'sec-workbook-qa-03d578d3b62d/ui-export.xlsx',
       'sec-debt-xlsx-qa-de64508d62d6/MSFT.xlsx',
       'sec-debt-xlsx-qa-de64508d62d6/AAPL.xlsx',
       'sec-debt-xlsx-qa-de64508d62d6/AAPL-lease.xlsx',
       'excel-export-b7da6c34e771/portfolio.xlsx']
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};rns='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
books=[]
for index,relative in enumerate(paths):
    path=args.sec_source.resolve() if index==1 and args.sec_source else root/'artifacts/private'/relative
    dest=out/(str(index)+'-'+path.name);shutil.copyfile(path,dest)
    cells=[]
    with zipfile.ZipFile(path) as z:
        if any('externalLinks' in n or 'vbaProject' in n for n in z.namelist()):raise ValueError('External/macro workbook out of scope')
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        rels={x.get('Id'):x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',ns):
            target=rels[sheet.get('{'+rns+'}id')];target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            for c in ET.fromstring(z.read(target)).findall('.//s:sheetData/s:row/s:c',ns):
                formula=c.findtext('s:f',None,ns);value=c.findtext('s:v',None,ns);kind=c.get('t','n')
                if kind=='s' and value is not None:value=strings[int(value)]
                if kind=='inlineStr':value=''.join(x.text or '' for x in c.findall('s:is//s:t',ns))
                if formula is None and value is None:continue
                cells.append({'sheet':sheet.get('name'),'cell':c.get('r'),'expected':value,'kind':kind,'formula':formula})
    books.append({'source':str(path),'copy':str(dest),'source_sha256':sha256(path),'cells':cells})
(out/'plan.json').write_text(json.dumps({'books':books,'output_folder':str(out)},indent=2),encoding='utf8')
print(out)
