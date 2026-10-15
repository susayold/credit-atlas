from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal
import json,shutil,threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import pytest
from credit_atlas.note_schedules import catalog,contractual_path,report
from credit_atlas.server import handler_for
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def acquired(tmp_path):
 data,receipt=catalog(ROOT);s=data['source']
 shutil.copytree(ROOT/'data/private/sec-documents'/s['folder'],tmp_path/'data/private/sec-documents'/s['folder'])
 shutil.copytree(ROOT/'artifacts/private'/receipt['catalog_id'],tmp_path/'artifacts/private'/receipt['catalog_id'])
 (tmp_path/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/build_apple_note_catalog.py',tmp_path/'scripts/build_apple_note_catalog.py')
 views=SimpleNamespace(root=tmp_path,view=lambda _: {'entities':[{'cik':'0000320193','ticker':'AAPL'},{'cik':'0000037996','ticker':'F'}]})
 return views,data,receipt

def test_lifetime_schedule_invariants(acquired):
 _,data,_=acquired;interest=Decimal(0);principal=Decimal(0)
 for n,count,total in zip(data['notes'],[6,10,14,20],['180000000','210000000','315000000','475000000']):
  rows=contractual_path(n);assert len(rows)==count
  assert rows[0]['nominal_coupon_date']=='2025-11-12' and rows[-1]['nominal_coupon_date']==n['maturity_date']
  assert sum(Decimal(r['scheduled_interest_usd_exact']) for r in rows)==Decimal(total)
  assert sum(Decimal(r['scheduled_principal_usd_exact']) for r in rows)==Decimal(n['original_issue_principal_usd_exact'])
  assert all(r['adjusted_payment_date'] is None and r['days360']==180 for r in rows)
  assert all(Decimal(r['scheduled_principal_usd_exact'])==0 for r in rows[:-1])
  for r in rows:assert Decimal(r['scheduled_total_usd_exact'])==Decimal(r['scheduled_interest_usd_exact'])+Decimal(r['scheduled_principal_usd_exact'])
  interest+=sum(Decimal(r['scheduled_interest_usd_exact']) for r in rows);principal+=sum(Decimal(r['scheduled_principal_usd_exact']) for r in rows)
 assert interest==Decimal('1180000000') and principal==Decimal('4500000000')

def test_source_cutoff_and_future_nominal_window(acquired):
 v,_,_=acquired
 before=report(v,'view',{'asof':'2025-05-11'});assert before['notes']==[] and before['source'] is None and before['totals']['scheduled_total_usd_exact'] is None
 allrows=report(v,'view',{'asof':'2025-05-12'});assert len(allrows['rows'])==50
 late=report(v,'view',{'asof':'2026-10-11'});assert len(late['rows'])==42 and Decimal(late['totals']['scheduled_interest_usd_exact'])==Decimal('985500000')
 range_=report(v,'view',{'asof':'2025-11-12','end':'2026-05-12'});assert len(range_['rows'])==4 and {r['nominal_coupon_date'] for r in range_['rows']}=={'2026-05-12'}
 assert not any(late['qualification'].values()) and late['path_assumptions']['early_redemption'] is False
 assert all(n['current_outstanding_usd_exact'] is None for n in late['notes'])
 other=report(v,'view',{'cik':'0000037996'});assert other['notes']==[] and other['rows']==[]

def test_partition_totals_and_series_filter(acquired):
 v,_,_=acquired;r=report(v,'view',{'asof':'2025-05-12'})
 for f in r['totals']:assert Decimal(r['totals'][f])==sum(Decimal(a[f]) for a in r['annual'])
 parts=[report(v,'view',{'asof':'2025-05-12','note_id':n['note_id']}) for n in r['notes']]
 assert sum(Decimal(p['totals']['scheduled_total_usd_exact']) for p in parts)==Decimal('5680000000')
 assert report(v,'view',{'asof':'2035-05-12','end':'2036-01-01'})['totals']['scheduled_total_usd_exact']=='0'

@pytest.mark.parametrize('field,value',[('frequency',4),('first_coupon_date','2025-12-12'),('coupon_rate_exact','NaN'),('coupon_rate_exact','0'),('maturity_date','2030-04-12'),('original_issue_principal_usd_exact','-10')])
def test_unsupported_patterns_rejected(acquired,field,value):
 n=deepcopy(acquired[1]['notes'][0]);n[field]=value
 with pytest.raises(ValueError):contractual_path(n)

@pytest.mark.parametrize('query',[{'asof':'2026-02-30'},{'end':'2020-01-01'},{'end':'2099-01-01'},{'note_id':'wrong'},{'cik':'wrong'},{'view_id':'wrong'},{'outstanding':'5'}])
def test_filter_rejected(acquired,query):
 with pytest.raises(ValueError):report(acquired[0],'view',query)

@pytest.mark.parametrize('target',['pdf','pages','catalog','builder'])
def test_evidence_mutation(acquired,target):
 v,data,r=acquired;s=data['source'];folder=v.root/'data/private/sec-documents'/s['folder']
 p={'pdf':folder/s['file'],'pages':folder/'pages.json','catalog':v.root/'artifacts/private'/r['catalog_id']/'catalog.json','builder':v.root/'scripts/build_apple_note_catalog.py'}[target];p.write_bytes(p.read_bytes()+b' ')
 with pytest.raises(ValueError):catalog(v.root)

def test_http_export_and_guards(acquired):
 v,_,_=acquired;s=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=v.root,sec_views=v)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start();base='http://127.0.0.1:'+str(s.server_port);endpoint='/api/sec-note-schedule-report?view_id=view&asof=2025-05-12'
 try:
  with urlopen(base+endpoint) as r:
   assert r.headers['Cache-Control']=='no-store' and 'attachment' in r.headers['Content-Disposition'];assert len(json.load(r)['rows'])==50
  for tail in ['&asof=2026-10-10','&outstanding=10']:
   with pytest.raises(HTTPError) as e:urlopen(base+endpoint+tail)
   assert e.value.code==400
  with pytest.raises(HTTPError) as e:urlopen(Request(base+endpoint,headers={'Origin':'https://other.example'}))
  assert e.value.code==403
 finally:s.shutdown();s.server_close();t.join(5)
