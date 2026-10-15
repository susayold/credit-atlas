from pathlib import Path
from uuid import uuid4
import shutil
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();source=root/'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json';m=read_json(source)
out=root/'artifacts/private'/('native-excel-qa-maturity-cases-'+uuid4().hex[:12]);out.mkdir();cases=[]
for i,s in enumerate(m['scopes']):
 path=root/s['workbook'];assert sha256(path)==s['sha256'];copy=out/f'{i:02d}.xlsx';shutil.copyfile(path,copy)
 for name,nums,statuses,expected in [
  ('all zero',[0]*6,['supported']*6,[6,0,0,'Unavailable','COMPLETE_ZERO_SCHEDULE',0,'Unavailable']),
  ('all missing',[None]*6,['missing']*6,[0,'Unavailable','Unavailable','Unavailable','PARTIAL_DISCLOSED_SCHEDULE','Unavailable','Unavailable']),
  ('all positive',[1]*6,['supported']*6,[6,6,6,0.5,'COMPLETE_DISCLOSED_SCHEDULE',1,1/6]),
  ('partial',[1,None,1,1,1,1],['supported','missing','supported','supported','supported','supported'],[5,5,'Unavailable','Unavailable','PARTIAL_DISCLOSED_SCHEDULE',1,'Unavailable']),
  ('negative',[-1,1,1,1,1,1],['supported']*6,[6,4,'Unavailable','Unavailable','INVALID_NEGATIVE_BUCKET',-1,'Unavailable']),
  ('supported text',['QA text',1,1,1,1,1],['supported']*6,[6,5,'Unavailable','Unavailable','NUMERIC_INPUT_UNAVAILABLE','Unavailable','Unavailable'])]:
  changes=[]
  for row,(num,status) in enumerate(zip(nums,statuses),6):changes.extend([{'sheet':'Facts','cell':f'C{row}','value':num},{'sheet':'Facts','cell':f'E{row}','value':status}])
  checks=[{'sheet':'Maturities','cell':cell,'value':v} for cell,v in zip(['B16','B17','B18','B19','B20','B9','D9'],expected)]
  cases.append({'name':f'{i:02d} {name}','copy':str(copy),'changes':changes,'expected':checks})
write_new(out/'plan.json',{'output_folder':str(out),'cases':cases,'source_receipt_sha256':sha256(source),'synthetic_cases':True})
print(out/'plan.json')
