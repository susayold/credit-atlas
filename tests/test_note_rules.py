from pathlib import Path
from types import SimpleNamespace
import json,shutil,threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import pytest
from credit_atlas.note_rules import verified_rules,report
from credit_atlas.server import handler_for
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def acquired(tmp_path):
 data,r=verified_rules(ROOT);s=data['source'];shutil.copytree(ROOT/'data/private/sec-documents'/s['folder'],tmp_path/'data/private/sec-documents'/s['folder']);shutil.copytree(ROOT/'artifacts/private'/r['rules_id'],tmp_path/'artifacts/private'/r['rules_id']);(tmp_path/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/build_apple_note_rules.py',tmp_path/'scripts/build_apple_note_rules.py')
 v=SimpleNamespace(root=tmp_path,view=lambda _: {'entities':[{'cik':'0000320193','ticker':'AAPL'},{'cik':'0000037996','ticker':'F'}]});return v,data,r

def test_source_cutoff_and_scope(acquired):
 v,_,_=acquired;r=report(v,'view',{'asof':'2024-11-01'});assert len(r['rules'])==5 and not any(r['qualification'].values());assert {x['pdf_page'] for x in r['rules']}=={38,40,45,46,72}
 assert report(v,'view',{'asof':'2024-10-31'})['source'] is None
 assert report(v,'view',{'cik':'0000037996'})['rules']==[]
 assert 'series_payment_place_verified' in r['qualification'] and not r['qualification']['series_payment_place_verified']

@pytest.mark.parametrize('query',[{'asof':'2026-02-30'},{'asof':'2026'},{'cik':'wrong'},{'view_id':'wrong'},{'calendar':'NYC'}])
def test_filters_reject(acquired,query):
 with pytest.raises(ValueError):report(acquired[0],'view',query)

@pytest.mark.parametrize('target',['pdf','pages','feed','catalog','builder','acquisition'])
def test_source_mutation_rejected(acquired,target):
 v,data,r=acquired;s=data['source'];f=v.root/'data/private/sec-documents'/s['folder'];p={'pdf':f/s['file'],'pages':f/'pages.json','feed':f/'issuer-feed.json','catalog':v.root/'artifacts/private'/r['rules_id']/'rules.json','builder':v.root/'scripts/build_apple_note_rules.py','acquisition':f/'acquisition.json'}[target]
 if target=='acquisition':j=json.loads(p.read_text());j['issuer_filing_id']+=1;p.write_text(json.dumps(j))
 else:p.write_bytes(p.read_bytes()+b' ')
 with pytest.raises(ValueError):verified_rules(v.root)

def test_http_private_export(acquired):
 v,_,_=acquired;s=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=v.root,sec_views=v)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start();base='http://127.0.0.1:'+str(s.server_port);endpoint='/api/sec-note-rules-report?view_id=view&asof=2026-10-11'
 try:
  with urlopen(base+endpoint) as r:
   assert r.headers['Cache-Control']=='no-store' and 'attachment' in r.headers['Content-Disposition'];assert len(json.load(r)['rules'])==5
  for tail in ['&asof=2026-10-10','&calendar=NYC']:
   with pytest.raises(HTTPError) as e:urlopen(base+endpoint+tail)
   assert e.value.code==400
  with pytest.raises(HTTPError) as e:urlopen(Request(base+endpoint,headers={'Origin':'https://other.example'}))
  assert e.value.code==403
 finally:s.shutdown();s.server_close();t.join(5)
