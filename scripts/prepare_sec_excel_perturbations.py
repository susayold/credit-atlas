import re,shutil
from pathlib import Path
from uuid import uuid4
from audit_sec_excel_metadata import cells
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();m=root/'artifacts/private/sec-workbook-scope-audit-1133f2bb3c7b/receipt.json';receipt=read_json(m)
out=root/'artifacts/private'/('native-excel-qa-sec-perturb-'+uuid4().hex[:12]);out.mkdir();books=[]
for i,s in enumerate(receipt['scopes']):
    source=root/s['workbook'];a,f=cells(source);row=max(int(k[1:]) for k,v in a.items() if k.startswith('B') and v=='Current ratio')
    import zipfile,xml.etree.ElementTree as ET
    with zipfile.ZipFile(source) as z:
        formulas={c.attrib['r']:c.findtext('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}f') for c in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')}
    n=re.findall(r"'Facts'!D([0-9]+)",formulas['E'+str(row)])[0];d=re.findall(r"'Facts'!D([0-9]+)",formulas['F'+str(row)])[0]
    assert a['S'+str(row)]=='supported' and f['D'+d]>0
    copy=out/f'{i:02d}.xlsx';shutil.copyfile(source,copy)
    books.append({'copy':str(copy),'source':str(source),'sha256':sha256(source),'numerator_cell':'D'+n,'denominator_cell':'D'+d,
        'output_cell':'I'+str(row),'summary_cell':'B10','cases':[
        {'name':'blank numerator','target':'numerator','value':None,'expected':'Unavailable'},
        {'name':'zero numerator','target':'numerator','value':0,'expected':0},
        {'name':'negative numerator','target':'numerator','value':-7,'expected':float(-7/f['D'+d])},
        {'name':'text numerator','target':'numerator','value':'QA nonnumeric','expected':'Unavailable'},
        {'name':'zero denominator','target':'denominator','value':0,'expected':'Unavailable'},
        {'name':'negative denominator','target':'denominator','value':-7,'expected':'Unavailable'}]})
write_new(out/'plan.json',{'output_folder':str(out),'books':books,'source_receipt_sha256':sha256(m)})
print(out/'plan.json')
