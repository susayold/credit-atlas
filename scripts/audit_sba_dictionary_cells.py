"""Independent coordinate-level dictionary inspection without adapter imports."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4
from credit_atlas.workspace import read_json, sha256, write_new

root = Path.cwd().resolve();case = root/'artifacts/private/business-sba-21c568f10f7d'
receipt = read_json(case/'business-complete.json');source = root/'data/private/public-suite'/receipt['suite_id']
raw = source/'sba-dictionary.xlsx';assert sha256(raw) == receipt['dictionary_source_sha256']
dictionary = read_json(case/'dictionary.json');ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
checked = []
with zipfile.ZipFile(raw) as archive:
    assert archive.testzip() is None
    shared = [''.join(t.text or '' for t in s.iter(ns+'t')) for s in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
    rels = {r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
    worksheets = {}
    for sheet in ET.fromstring(archive.read('xl/workbook.xml')).iter(ns+'sheet'):
        target = rels[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
        name = target.lstrip('/') if target.startswith('/') else 'xl/'+target
        cells = {}
        for c in ET.fromstring(archive.read(name)).iter(ns+'c'):
            assert c.find(ns+'f') is None
            v = c.find(ns+'v');kind = c.attrib.get('t')
            text = shared[int(v.text)] if kind == 's' else ''.join(t.text or '' for t in c.iter(ns+'t')) if kind == 'inlineStr' else v.text if v is not None else ''
            if text.strip():cells[c.attrib['r']] = text
        worksheets[sheet.attrib['name']] = cells
    for program, entries in dictionary.items():
        names = {e['sheet'] for e in entries};assert len(names) == 1
        sheet_name = next(iter(names));cells = worksheets[sheet_name]
        for e in entries:
            assert cells[e['field_cell']] == e['field'] and cells[e['definition_cell']] == e['definition']
        raw_fields = {coord:text for coord,text in cells.items() if coord.startswith('A') and text != 'Field Name'}
        assert raw_fields == {e['field_cell']:e['field'] for e in entries}
        checked.append({'program':program,'sheet':sheet_name,'fields':len(entries),'cells_checked':2*len(entries)})
assert sum(c['fields'] for c in checked) == 81
out = root/'artifacts/private'/('sba-dictionary-cells-audit-'+uuid4().hex[:12])
write_new(out/'receipt.json',{'status':'PASS','sheets':checked,'total_fields':81,'total_cells':162,
    'inputs_sha256':{str(raw.relative_to(root)):sha256(raw),str((case/'dictionary.json').relative_to(root)):sha256(case/'dictionary.json')},
    'method_sha256':sha256(Path(__file__)),'historical_march_subprogram_qualified':False})
print(json.dumps({'output':str(out),'status':'PASS','cells':162}))
