"""Real source,isolated QA memo store;immutable captured maturity scope/history."""
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from credit_atlas.corporate_memos import CorporateMemos,SECTIONS,encoded
from credit_atlas.sec_views import SecViews
from credit_atlas.sec_read_cache import VerifiedSecReadCache
from credit_atlas.reviews import ReviewConflict
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();out=root/'artifacts/private'/('maturity-memo-capture-qa-'+uuid4().hex[:12]);out.mkdir()
service=SimpleNamespace(root=out,sec_views=VerifiedSecReadCache(SecViews(root)));store=CorporateMemos(service)
manifest=root/'artifacts/private/maturity-workbook-scope-audit-46d6a12f8d2d/receipt.json';m=read_json(manifest);checks=[]
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
for s in m['scopes']:
 r=read_json(root/s['capture']);query={**s['query'],'accession':r['filters']['accession'],'years':'5'}
 payload={'title':'Synthetic QA maturity capture','owner':'QA audit','status':'draft',
          'sections':{k:'Synthetic QA only;not analyst decision' for k in SECTIONS},'scope':query}
 saved=store.save(payload);capture=json.loads(encoded(saved['capture']));e=capture['evidence'];debt=e['debt_maturities']
 assert debt['filters']=={**r['filters'],'asof':r['statement']['filing_date']}
 assert debt['buckets']==r['buckets'] and debt['summary']==r['summary']
 assert capture['resolved_scope']['trend_cutoff']==r['statement']['filing_date']
 assert e['annual_trend']['filters']['asof']==e['interest_coverage']['filters']['asof']==r['statement']['filing_date']
 assert capture['evidence_sha256']==hashlib.sha256(encoded(e).encode()).hexdigest() and not any(capture['qualification'].values())
 update={k:saved[k] for k in ['id','revision','title','owner','status','sections']};update['status']='reviewed'
 changed=store.save(update);report=store.report(saved['id'])
 assert len(report['history'])==2 and changed['capture']==capture and all(v['capture']==capture for v in report['history'])
 try:store.save(update)
 except ReviewConflict:pass
 else:raise AssertionError('Stale revision accepted')
 def unavailable(*_):raise ValueError('Controlled QA source outage')
 original=service.sec_views.report;service.sec_views.report=unavailable
 assert store.report(saved['id'])==report
 service.sec_views.report=original
 checks.append({'cik':query['cik'],'family':query['debt_scope'],'memo_id':saved['id'],'history_revisions':2})
assert sha256(ledger)==before
write_new(out/'receipt.json',{'status':'PASS','cases':checks,'isolated_store':str(store.path.relative_to(root)),
 'synthetic_narrative':True,'self_declared_review_only':True,'ledger_unchanged':True,
 'manifest_sha256':sha256(manifest),'method_sha256':sha256(Path(__file__)),
 'memo_method_sha256':sha256(root/'src/credit_atlas/corporate_memos.py')})
print(out)
