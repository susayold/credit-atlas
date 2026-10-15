"""Reuse the isolated read-only native Excel audit; preserve both source files."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4
from credit_atlas.workspace import sha256

root=Path(__file__).resolve().parents[1]
folder=root/'artifacts/private'/('native-excel-qa-affordability-'+uuid4().hex[:12]);folder.mkdir()
template=root/'apps/excel/templates/CreditAtlas-Affordability-Input.xlsx'
qa=root/'artifacts/private/affordability-template-roundtrip-20261012/qa-filled.xlsx'
books=[]
expected=[]
for source,filled in [(template,False),(qa,True)]:
    copy=folder/source.name;shutil.copyfile(source,copy)
    cells=[];values={}
    for row in range(2,11):
        address='B'+str(row);cells.append({'sheet':'AffordabilityControl','cell':address})
    vals=['qa-case','2026-10-12','USD','individual','qa-person',1,'qa-policy',0.4,500]
    for row,value in enumerate(vals,2):values[('AffordabilityControl','B'+str(row))]=value if filled else None
    for row in range(11,16):
        cells.append({'sheet':'AffordabilityControl','cell':'B'+str(row)})
        values[('AffordabilityControl','B'+str(row))]='true' if filled else 'false'
    for row,value in enumerate([60000,4000,1500,1500,500],2):
        cells.append({'sheet':'AffordabilityItems','cell':'C'+str(row)})
        values[('AffordabilityItems','C'+str(row))]=value if filled else None
    books.append({'source':str(source),'copy':str(copy),'source_sha256':sha256(source),'cells':cells})
    expected.append(values)
plan=folder/'plan.json';plan.write_text(json.dumps({'output_folder':str(folder),'books':books},indent=2),encoding='utf-8')
env=dict(os.environ);env['PSModulePath']=r'C:\Windows\System32\WindowsPowerShell\v1.0\Modules'
subprocess.run([r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe','-NoProfile','-File',str(root/'scripts/audit_native_excel.ps1'),'-PlanPath',str(plan)],env=env,check=True,timeout=120)
r=json.loads((folder/'native-results.json').read_text(encoding='utf-8-sig'))
assert r['originals_unchanged'] and r['copies_not_saved'] and len(r['books'])==2
count=0
for book,values in zip(r['books'],expected):
    for cell in book['values']:
        assert cell['value']==values[(cell['sheet'],cell['cell'])] and not cell['has_formula']
        assert '####' not in cell['text']
        count+=1
(folder/'receipt.json').write_text(json.dumps({'status':'PASS','cells_checked':count,'books':2,'excel_version':r['excel_version'],'source_hashes':[b['source_sha256'] for b in books],'originals_unchanged':True,'copies_not_saved':True,'scope':'Native read-only open/calculation,value/blank/text/no-formula parity;not document verification'},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','output':str(folder),'cells_checked':count}))
