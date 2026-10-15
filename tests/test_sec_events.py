from copy import deepcopy
import pytest
from credit_atlas.sec_events import parse_items,document_url,rows,report
from tests.test_sec_financials import acquired
from tests.test_sec_views import view

def test_codes_and_legacy():
 assert parse_items('1.01,2.03,1.01')==['1.01','2.03']
 assert parse_items('5,7')==[] and parse_items(None)==[]
 with pytest.raises(ValueError):parse_items(123)
 with pytest.raises(ValueError):parse_items('x'*1001)

@pytest.mark.parametrize('path',['../a.htm','/a.htm','a//b.htm','a\\b.htm','./a.htm'])
def test_path_rejects(path):
 with pytest.raises(ValueError):document_url('0000320193','0001193125-26-000001',path)

def test_document_quote():
 assert document_url('0000320193','0001193125-26-000001','a b.htm').endswith('/a%20b.htm')
 assert document_url('0000320193','0001193125-26-000001','') is None

def test_report_verified_lineage_and_cutoff(view):
 root,case,receipt,views=view;r=report(views,receipt['view_id'],{'from':'2026-01-01','asof':'2026-02-01'})
 assert r['summary']['matched_unique_filings']==1 and len(r['rows'])==1
 assert r['rows'][0]['source_occurrences']==[{'source_file':'submissions-CIK0000320193.json','source_ordinal':0}]
 assert r['rows'][0]['items_raw'] is None and not any(r['qualification'].values())
 assert len(r['source_capture']['view_receipt_sha256'])==64
 assert report(views,receipt['view_id'],{'asof':'1900-01-01'})['rows']==[]

@pytest.mark.parametrize('query',[{'from':'2027-01-01'},{'asof':'2026-02-30'},{'limit':'1000'},{'offset':'-1'},{'cik':'other'},{'form_group':'evil'},{'item':'2.03,1.01'},{'accession':'x'},{'view_id':'wrong'}])
def test_invalid(view,query):
 with pytest.raises(ValueError):report(view[3],view[2]['view_id'],query)

def test_paging_and_overlapping_codes(tmp_path,monkeypatch):
 import credit_atlas.sec_events as e
 class Views:
  root=tmp_path
  def view(self,identifier):return {'source_id':'source','case_id':'case','entities':[{'cik':'0000320193'}]}
 path=tmp_path/'artifacts/private/view/view-complete.json';path.parent.mkdir(parents=True);path.write_text('{}')
 monkeypatch.setattr(e,'verify_source',lambda *a:(tmp_path,{}))
 rs=[{'filing_date':'2026-02-01','accession':str(i),'form':'8-K/A' if i==0 else '8-K','item_codes':['1.01','2.03']} for i in range(60)]
 monkeypatch.setattr(e,'rows',lambda *a:(rs,[]))
 r=e.report(Views(),'view',{'from':'2026-01-01','asof':'2026-02-01','limit':'25'});p=e.report(Views(),'view',{'from':'2026-01-01','asof':'2026-02-01','limit':'25','offset':'25'})
 assert r['summary']==p['summary'] and r['summary']['item_counts']=={'1.01':60,'2.03':60} and r['summary']['amendments']==1
 assert len(r['rows'])==25 and not {x['accession'] for x in r['rows']} & {x['accession'] for x in p['rows']}
 assert r['page']['has_next']

def test_http_export_and_query_guards(view):
 import json,threading
 from http.server import ThreadingHTTPServer
 from types import SimpleNamespace
 from urllib.request import urlopen,Request
 from urllib.error import HTTPError
 from credit_atlas.server import handler_for
 root,_,receipt,views=view;s=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=root,sec_views=views)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start();base='http://127.0.0.1:'+str(s.server_port);endpoint='/api/sec-events-report?view_id='+receipt['view_id']+'&asof=2026-02-01'
 try:
  with urlopen(base+endpoint) as r:
   assert r.headers['Cache-Control']=='no-store' and 'attachment' in r.headers['Content-Disposition'];assert json.load(r)['summary']['matched_unique_filings']==1
  for suffix in ['&asof=2026-03-01','&accession=evil','&offset=-1']:
   with pytest.raises(HTTPError) as e:urlopen(base+endpoint+suffix)
   assert e.value.code==400
  with pytest.raises(HTTPError) as e:urlopen(Request(base+endpoint,headers={'Origin':'https://other.example'}))
  assert e.value.code==403
 finally:s.shutdown();s.server_close();t.join(5)
