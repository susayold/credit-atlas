"""Private diagnostic of repeated full SEC verification;no canonical mutations."""
import json
import traceback
from pathlib import Path
from uuid import uuid4
from credit_atlas.sec_views import SecViews
from credit_atlas.workspace import read_json, write_new, sha256

root=Path.cwd();out=root/'artifacts/private'/('sec-sequential-diagnostic-'+uuid4().hex[:12]);out.mkdir()
views=SecViews(root);statements=read_json(root/'artifacts/private/sec-case-33077fe45722/annual-statements.json')
completed=[]
for s in statements:
    query={'cik':s['cik'],'accession':s['accession'],'asof':'2026-10-14'}
    try:
        r=views.report('sec-view-b92d9914f1dc',query)
        assert r['statement']==s
        completed.append(query)
        if len(completed)%5==0:print(json.dumps({'reports_passed':len(completed)}),flush=True)
    except Exception as error:
        (out/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
        write_new(out/'receipt.json',{'status':'FAIL','completed_reports':len(completed),'failed_query':query,
            'exception_type':type(error).__name__,'method_sha256':sha256(Path(__file__))})
        print(json.dumps({'output':str(out),'status':'FAIL','exception_type':type(error).__name__}),flush=True)
        raise
write_new(out/'receipt.json',{'status':'PASS','completed_reports':len(completed),'queries':completed,
    'scope':'Single-process sequential production SecViews.report;not browser/runtime acceptance',
    'method_sha256':sha256(Path(__file__))})
print(json.dumps({'output':str(out),'status':'PASS','reports':len(completed)}),flush=True)
