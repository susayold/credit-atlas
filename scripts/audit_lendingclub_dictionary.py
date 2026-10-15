"""Independent OOXML cell audit of issuer dictionary and prepared-field coverage."""
import hashlib,json,posixpath,uuid,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
root=Path.cwd();profile=root/'artifacts/private/lendingclub-dictionary-profile-9b8a25e34bf8/profile.json'
doc=json.loads(profile.read_text(encoding='utf8'));source=root/'data/private/retail'/doc['source_id']/doc['source']['file']
assert hashlib.sha256(source.read_bytes()).hexdigest()==doc['source']['sha256']
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};rel_ns='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
expected=[];issues=[]
with zipfile.ZipFile(source) as z:
    strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
    relationships={x.get('Id'):x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    for sheet in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets',ns):
        target=relationships[sheet.get(rel_ns)];path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
        for row in ET.fromstring(z.read(path)).findall('s:sheetData/s:row',ns):
            number=int(row.get('r'));cells={}
            for c in row:
                value=c.findtext('s:v',None,ns)
                if c.get('t')=='s' and value is not None:cells[c.get('r')]=strings[int(value)]
            a=cells.get('A'+str(number));b=cells.get('B'+str(number))
            if number!=1 and a and a.strip() and b and b.strip():expected.append({'sheet':sheet.get('name'),'row':number,'source_field':a.strip(),'source_description':b.strip(),'field_cell':'A'+str(number),'description_cell':'B'+str(number)})
if expected!=doc['definitions']:issues.append('literal definition cells differ')
loan={r['source_field']:r for r in expected if r['sheet']=='LoanStats'}
source_profile=json.loads((root/'artifacts/private/lendingclub-profile-28db23b7bd0a/profile.json').read_text(encoding='utf8'))
if [r['prepared_field'] for r in doc['column_review']]!=source_profile['columns']:issues.append('prepared columns differ')
exact=sum(name in loan for name in source_profile['columns'])
if exact!=doc['coverage']['exact_names']:issues.append('exact name coverage')
for row in doc['column_review']:
    definition=row['issuer_definition']
    if definition and loan.get(definition['source_field'])!=definition:issues.append('source definition mismatch '+row['prepared_field'])
    if row['application_time_qualified'] or row['contributor_transform_qualified']:issues.append('unproven qualification '+row['prepared_field'])
out=root/'artifacts/private'/('lendingclub-dictionary-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
result={'status':'PASS' if not issues else 'ISSUES_FOUND','issues':issues,'definitions_checked':len(expected),'literal_cells_checked':len(expected)*2,
    'prepared_columns_checked':len(doc['column_review']),'exact_names':exact,'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
    'scope':'Literal OOXML definitions/cell addresses and prepared-column mapping guards;not historical availability or contributor transform certification'}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(out);print(result)
if issues:raise SystemExit(1)
