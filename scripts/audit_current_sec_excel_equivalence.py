"""Current exports vs native-verified baseline: every populated cell/formula."""
import argparse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4
from credit_atlas.workspace import read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def cells(path):
    with zipfile.ZipFile(path) as z:
        strings=[''.join(t.text or '' for t in x.iter('{'+NS['s']+'}t')) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
        result={}
        for name in sorted(z.namelist()):
            if not name.startswith('xl/worksheets/sheet') or not name.endswith('.xml'):continue
            for c in ET.fromstring(z.read(name)).findall('.//s:sheetData/s:row/s:c',NS):
                value=c.findtext('s:v',None,NS);kind=c.get('t','n')
                if kind=='s':value=strings[int(value)]
                elif kind=='inlineStr':value=''.join(t.text or '' for t in c.findall('s:is//s:t',NS))
                if value is None and c.find('s:f',NS) is None:continue
                result[(name,c.attrib['r'])]=(kind,value,c.findtext('s:f',None,NS))
        return result

parser=argparse.ArgumentParser();parser.add_argument('manifest');args=parser.parse_args()
manifest=ROOT/args.manifest;current=read_json(manifest)
baseline_path=ROOT/'artifacts/private/sec-workbook-scope-audit-1133f2bb3c7b/receipt.json';baseline=read_json(baseline_path)
native_path=ROOT/'artifacts/private/native-excel-qa-sec-1a75771ee189/receipt.json';native=read_json(native_path)
assert current['status']==baseline['status']==native['status']=='PASS' and native['failed_checks']==0 and native['copies_not_saved']
assert len(current['scopes'])==len(baseline['scopes'])==len(native['books'])==36
assert current['builder_sha256']==baseline['builder_sha256']==sha256(ROOT/'scripts/build_sec_workbook.mjs')
assert all(sha256(ROOT/'src/credit_atlas'/(n+'.py'))==h for n,h in current['methods_sha256'].items())
results=[];total=formulas=0
for new,old,book in zip(current['scopes'],baseline['scopes'],native['books']):
    assert new['query']==old['query']
    assert sha256(ROOT/new['workbook'])==new['sha256'] and sha256(ROOT/old['workbook'])==old['sha256']
    assert Path(book['source']).resolve()==(ROOT/old['workbook']).resolve()
    assert book['source_sha256'].lower()==old['sha256'].lower() and not book['failures']
    assert sha256(ROOT/new['capture'])==new['capture_sha256'] and sha256(ROOT/old['capture'])==old['capture_sha256']
    first,second=cells(ROOT/new['workbook']),cells(ROOT/old['workbook'])
    assert first==second, new['query']
    total+=len(first);formulas+=sum(v[2] is not None for v in first.values())
    results.append({'query':new['query'],'current_workbook':new['workbook'],'current_sha256':new['sha256'],
                    'baseline_workbook':old['workbook'],'baseline_sha256':old['sha256'],'cells':len(first)})
out=ROOT/'artifacts/private'/('sec-excel-equivalence-'+uuid4().hex[:12]);out.mkdir()
write_new(out/'receipt.json',{'status':'PASS','books':results,'populated_cells_identical':total,'formula_cells_identical':formulas,
    'current_manifest':str(manifest.relative_to(ROOT)),'current_manifest_sha256':sha256(manifest),
    'baseline_manifest_sha256':sha256(baseline_path),'native_receipt_sha256':sha256(native_path),'method_sha256':sha256(Path(__file__)),
    'scope':'All populated cell types/values/formulas and sheet coordinates identical to saved native-verified baseline. Reuses prior native calculation evidence for identical inputs/formulas; no new native run claimed.'})
print(out);print('Identical cells',total,'formulas',formulas)
