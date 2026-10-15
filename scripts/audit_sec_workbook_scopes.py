"""All supported issuer/window/expense XLSX exports and independent XML checks."""
import json
from pathlib import Path
from urllib.request import Request,urlopen
from uuid import uuid4
from browser_sec_workbook_qa import audit as audit_xlsx
from credit_atlas.workspace import read_json,sha256,write_new,timestamp

root=Path.cwd().resolve();base='http://127.0.0.1:8770'
out=root/'artifacts/private'/('sec-workbook-scope-audit-'+uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
methods={name:sha256(root/'src/credit_atlas'/f'{name}.py') for name in ['sec_workbook','sec_trends','sec_coverage','sec_read_cache','server']}
builder=sha256(root/'scripts/build_sec_workbook.mjs');scopes=[]
for cik in ['0000320193','0000789019','0000037996','0001467858']:
    for years in ['3','5','10']:
        for concept in ['InterestExpenseNonoperating','InterestExpense','InterestExpenseDebt']:
            query={'view_id':'sec-view-b92d9914f1dc','cik':cik,'asof':'2026-10-15','years':years,'interest_concept':concept}
            existing=set((root/'artifacts/private').glob('sec-workbook-*/CreditAtlas-SEC.xlsx'))
            request=Request(base+'/api/sec-workbook',data=json.dumps(query).encode(),headers={'Origin':base,'X-CreditAtlas-Client':'local','Content-Type':'application/json'})
            with urlopen(request,timeout=240) as response:
                assert response.status==200 and 'attachment' in response.headers['Content-Disposition']
                path=out/(cik+'-'+years+'-'+concept+'.xlsx');path.write_bytes(response.read())
            digest=sha256(path)
            candidates=set((root/'artifacts/private').glob('sec-workbook-*/CreditAtlas-SEC.xlsx'))-existing
            matches=[f for f in candidates if sha256(f)==digest]
            assert matches,'No immutable server capture matches downloaded workbook'
            capture=sorted(matches)[0].parent/'report.json';doc=read_json(capture)
            assert doc['coverage']['filters']=={k:v for k,v in query.items() if k!='view_id'}
            assert doc['trend']['filters']=={k:v for k,v in query.items() if k not in {'view_id','interest_concept'}}
            assert doc['visibility']=='private' and not doc['public_release_approved']
            metrics=audit_xlsx(path,doc,require_missing_guard=True)
            scopes.append({'query':query,'workbook':str(path.relative_to(root)),'sha256':digest,
                'capture':str(capture.relative_to(root)),'capture_sha256':sha256(capture),'metrics':metrics})
            write_new(out/f'case-{len(scopes):02d}.json',scopes[-1])
            print(json.dumps({'scopes_passed':len(scopes),'cik':cik,'years':years,'concept':concept}),flush=True)
assert sha256(ledger)==before and sha256(root/'scripts/build_sec_workbook.mjs')==builder
assert all(sha256(root/'src/credit_atlas'/f'{n}.py')==h for n,h in methods.items())
write_new(out/'receipt.json',{'status':'PASS','completed_at':timestamp(),'scopes':scopes,
    'ledger_unchanged':True,'methods_sha256':methods,'builder_sha256':builder,
    'audit_helper_sha256':sha256(root/'scripts/browser_sec_workbook_qa.py'),
    'method_sha256':sha256(Path(__file__)),'full_completion_proven':False,
    'remaining':'Full Facts metadata/date/summary/cell audit,native recalculation and visual/browser acceptance'})
print(out)
