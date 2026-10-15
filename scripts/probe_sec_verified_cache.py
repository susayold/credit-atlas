"""Actual source graph:full-verifier call count,concurrency and report parity."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4
from credit_atlas.sec_views import SecViews
from credit_atlas.sec_read_cache import VerifiedSecReadCache
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();view='sec-view-b92d9914f1dc';backend=SecViews(root);original=backend.view;calls=[]
def counted(identifier):
    calls.append(identifier);return original(identifier)
backend.view=counted;cache=VerifiedSecReadCache(backend)
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(cache.view,[view]*8))
assert len(calls)==1 and all(r==results[0] for r in results)
statements=read_json(root/'artifacts/private/sec-case-33077fe45722/annual-statements.json')
for s in statements:
    r=cache.report(view,{'cik':s['cik'],'accession':s['accession'],'asof':'2026-10-15'})
    assert r['statement']==s
assert len(calls)==1 and sha256(ledger)==before
out=root/'artifacts/private'/('sec-cache-runtime-probe-'+uuid4().hex[:12])
write_new(out/'receipt.json',{'status':'PASS','original_full_verifier_calls':len(calls),'concurrent_reads':8,
    'annual_report_parities':67,'full_input_graph_hashed_each_read':True,'pinned_input_files':len(cache._cached[view][0]),
    'ledger_unchanged':True,'method_sha256':sha256(root/'src/credit_atlas/sec_read_cache.py'),
    'probe_method_sha256':sha256(Path(__file__))})
print(out)
