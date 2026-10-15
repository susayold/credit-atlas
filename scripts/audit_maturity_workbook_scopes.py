"""Latest fourissuer/twofamily maturity Excel captures vs private JSON."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from uuid import uuid4
from browser_sec_debt_workbook_qa import audit
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();base='http://127.0.0.1:8770';out=root/'artifacts/private'/('maturity-workbook-scope-audit-'+uuid4().hex[:12]);out.mkdir()
scopes=[];ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
for cik in ['0000320193','0000789019','0000037996','0001467858']:
 for family in ['debt_only','debt_and_capital_lease']:
  query={'view_id':'sec-view-b92d9914f1dc','cik':cik,'asof':'2026-10-15','debt_scope':family}
  old=set((root/'artifacts/private').glob('sec-debt-workbook-*/CreditAtlas-Maturities.xlsx'))
  request=Request(base+'/api/sec-debt-workbook',data=json.dumps(query).encode(),headers={'Origin':base,'X-CreditAtlas-Client':'local','Content-Type':'application/json'})
  with urlopen(request,timeout=240) as response:
   assert response.status==200 and 'attachment' in response.headers['Content-Disposition']
   path=out/(cik+'-'+family+'.xlsx');path.write_bytes(response.read())
  matched=[p for p in set((root/'artifacts/private').glob('sec-debt-workbook-*/CreditAtlas-Maturities.xlsx'))-old if sha256(p)==sha256(path)]
  assert matched;capture=sorted(matched)[0].parent/'report.json';r=read_json(capture)
  assert all(r['filters'][k]==v for k,v in query.items() if k!='view_id')
  checked=audit(path,r);assert checked['formulas']==23
  scopes.append({'query':query,'workbook':str(path.relative_to(root)),'sha256':sha256(path),
   'capture':str(capture.relative_to(root)),'capture_sha256':sha256(capture),'metrics':checked})
  print({'scopes_passed':len(scopes),'family':family},flush=True)
assert sha256(ledger)==before
write_new(out/'receipt.json',{'status':'PASS','scopes':scopes,'ledger_unchanged':True,
 'method_sha256':sha256(Path(__file__)),'helper_sha256':sha256(root/'scripts/browser_sec_debt_workbook_qa.py'),
 'builder_sha256':sha256(root/'scripts/build_sec_debt_workbook.mjs'),
 'full_completion_proven':False,'remaining':'Full native metadata/formula/perturbation/render and memo capture acceptance'})
print(out)
