"""Real memo handler/UI with isolated DB, conflict and source-outage proofs."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from uuid import uuid4
import hashlib
import json
import threading
from credit_atlas.corporate_memos import CorporateMemos, encoded
from credit_atlas.service import ResearchService
from credit_atlas.server import handler_for
from credit_atlas.workspace import read_json, sha256, write_new
from browser_corporate_memo_qa import run as browser_run

ROOT = Path(__file__).resolve().parents[1]
out = ROOT/'artifacts/private'/('corporate-memo-http-audit-'+uuid4().hex[:12]);out.mkdir()
protected = [ROOT/'artifacts/private'/name for name in ['retail-holdout-access.sqlite','bankruptcy-holdout-access.sqlite','corporate-memos.sqlite3']]
before = {str(p.relative_to(ROOT)):sha256(p) for p in protected if p.exists()}
service = ResearchService(ROOT, review_path=out/'qa-reviews.sqlite3')
stores=[]
def factory(s):
    store=CorporateMemos(SimpleNamespace(root=out,sec_views=s.sec_views));stores.append(store);return store
with patch('credit_atlas.server.CorporateMemos',side_effect=factory):
    handler=handler_for(service)
server=ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base='http://127.0.0.1:'+str(server.server_port)
def request(path, payload=None, origin=None):
    headers={'Origin':base if origin is None else origin,'X-CreditAtlas-Client':'local'}
    if payload is not None:headers['Content-Type']='application/json'
    req=Request(base+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers)
    try:
        with urlopen(req,timeout=120) as r:return r.status,json.load(r)
    except HTTPError as e:return e.code,json.load(e)
try:
    browser=browser_run(base);assert browser['status']=='PASS'
    receipt=read_json(Path(browser['receipt']));assert len(stores)==1
    store=stores[0];checks=[]
    for key in receipt['archived_qa_ids']:
        code,saved=request('/api/corporate-memo-report?id='+key);assert code==200
        memo=saved['memo'];capture=memo['capture'];evidence=capture['evidence']
        assert capture['evidence_sha256']==hashlib.sha256(encoded(evidence).encode()).hexdigest()
        assert len(saved['history'])==2 and all(h['capture']==capture for h in saved['history'])
        assert capture['requested_scope']['debt_scope']=='debt_and_capital_lease'
        payload={k:memo[k] for k in ['id','revision','title','owner','status','sections']};payload['status']='reviewed'
        code,revised=request('/api/corporate-memos',payload);assert code==200 and revised['revision']==3 and revised['capture']==capture
        code,conflict=request('/api/corporate-memos',payload);assert code==409
        code,current=request('/api/corporate-memo-report?id='+key);assert code==200 and len(current['history'])==3
        assert current['memo']['capture']==capture
        injected={**payload,'revision':3,'scope':capture['requested_scope']};assert request('/api/corporate-memos',injected)[0]==400
        injected={**payload,'revision':3,'capture':{'approved':True}};assert request('/api/corporate-memos',injected)[0]==400
        oversized={**payload,'revision':3,'capture':capture};assert request('/api/corporate-memos',oversized)[0]==413
        assert request('/api/corporate-memos',payload,origin='https://invalid.example')[0]==403
        assert request('/api/corporate-memo-report?id='+key+'&unexpected=1')[0]==400
        query='/api/corporate-memos?view_id='+capture['resolved_scope']['view_id']+'&cik='+capture['resolved_scope']['cik']
        scope_listing=request(query)[1];assert any(r['id']==key for r in scope_listing['memos'])
        with patch.object(service.sec_views,'report',side_effect=ValueError('Controlled source outage')):
            assert request('/api/corporate-memo-report?id='+key)==(200,current)
            assert request(query)[1]==scope_listing
            revised_payload={k:current['memo'][k] for k in ['id','revision','title','owner','status','sections']};revised_payload['status']='archived'
            code,archived=request('/api/corporate-memos',revised_payload);assert code==200 and archived['revision']==4 and archived['capture']==capture
            new={k:memo[k] for k in ['title','owner','sections']};new.update(status='draft',scope=capture['requested_scope'])
            assert request('/api/corporate-memos',new)[0]==400
        code,final=request('/api/corporate-memo-report?id='+key);assert code==200 and len(final['history'])==4
        assert all(h['capture']==capture for h in final['history'])
        write_new(out/(key+'.json'),final)
        checks.append({'cik':capture['resolved_scope']['cik'],'id':key,'revisions':4,'evidence_sha256':capture['evidence_sha256']})
    assert all(sha256(ROOT/p)==h for p,h in before.items())
    write_new(out/'receipt.json',{'status':'PASS','cases':checks,'browser_receipt':str(Path(browser['receipt']).relative_to(ROOT)),
        'browser_receipt_sha256':sha256(Path(browser['receipt'])),'isolated_store':str(store.path.relative_to(ROOT)),
        'protected_sha256_unchanged':before,'self_declared_review_only':True,'synthetic_narrative':True,
        'method_sha256':sha256(Path(__file__)),'runtime_methods_sha256':{str(p.relative_to(ROOT)):sha256(p) for p in [ROOT/'src/credit_atlas/corporate_memos.py',ROOT/'src/credit_atlas/server.py',ROOT/'apps/web/corporate-memos.js',ROOT/'scripts/browser_corporate_memo_qa.py']}})
    print(out)
except Exception as error:
    write_new(out/'failed.json',{'status':'FAIL','exception_type':type(error).__name__,
              'cases_completed':locals().get('checks',[])})
    raise
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)
