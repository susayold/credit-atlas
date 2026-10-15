from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json,shutil,threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import pytest
from credit_atlas.facilities import catalog,select,report
from credit_atlas.server import handler_for

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def acquired(tmp_path):
    data,receipt=catalog(ROOT)
    for s in data['sources'].values():shutil.copytree(ROOT/'data/private/sec-documents'/s['folder'],tmp_path/'data/private/sec-documents'/s['folder'])
    folder=receipt['catalog_id']
    shutil.copytree(ROOT/'artifacts/private'/folder,tmp_path/'artifacts/private'/folder)
    (tmp_path/'scripts').mkdir();shutil.copyfile(ROOT/'scripts/build_ford_facility_catalog.py',tmp_path/'scripts/build_ford_facility_catalog.py')
    views=SimpleNamespace(root=tmp_path,view=lambda _: {'entities':[{'cik':'0000037996','ticker':'F'},{'cik':'0000320193','ticker':'AAPL'}]})
    return views,data,receipt

def test_cutoff_selection_and_distinct_availability(acquired):
    _,data,_=acquired
    assert select(data,'2025-04-16')==[]
    assert len(select(data,'2025-07-27'))==4
    assert len(select(data,'2025-07-28'))==5
    old={r['facility_id']:r for r in select(data,'2026-04-14')};new={r['facility_id']:r for r in select(data,'2026-04-15')}
    assert old['364_day']['loan_maturity_date']=='2026-04-16' and new['364_day']['loan_maturity_date']=='2027-04-14'
    assert old['delayed_draw']['availability_end_date']=='2026-07-28' and new['delayed_draw']['availability_end_date']=='2026-12-31'
    assert old['delayed_draw']['loan_maturity_date']==new['delayed_draw']['loan_maturity_date']=='2028-12-31'
    assert new['corporate_short']['loan_maturity_date']=='2029-04-13' and new['corporate_long']['loan_maturity_date']=='2031-04-15'
    assert all(r['outstanding_principal_usd_exact'] is None and r['undrawn_commitment_usd_exact'] is None for r in new.values())

def test_filing_date_is_independent_of_effective_date(acquired):
    data=deepcopy(acquired[1]);data['versions'][0]['filing_date']='2025-05-01'
    assert not any(r['facility_id']==data['versions'][0]['facility_id'] for r in select(data,'2025-04-30'))

def test_exact_totals_missing_boundaries_and_cov(acquired):
    views,_,_=acquired
    r=report(views,'view',{'cik':'0000037996','asof':'2026-10-11'})
    assert r['summary']['disclosed_commitment_total_usd_exact']=='21000000000'
    assert r['summary']['dscr'] is None and r['summary']['actual_available_liquidity_usd_exact'] is None
    assert not any(r['qualification'].values())
    assert r['covenant']['minimum_usd_exact']=='4000000000' and r['covenant']['headroom_usd_exact'] is None
    assert {e['pdf_page'] for e in r['covenant']['evidence']}=={39,132}
    old=report(views,'view',{'cik':'0000037996','asof':'2025-04-17'})
    assert old['summary']['disclosed_commitment_total_usd_exact']=='18000000000' and old['covenant'] is None
    assert set(old['sources'])=={'amendments_2025'}
    other=report(views,'view',{'cik':'0000320193'});assert other['rows']==[] and other['sources']=={} and other['summary']['disclosed_commitment_total_usd_exact'] is None
    far=report(views,'view',{'cik':'0000037996','asof':'2032-01-01'});assert all(r['calendar_status']=='scheduled boundary passed' for r in far['rows'])

@pytest.mark.parametrize('query',[{'asof':'2026-02-30'},{'asof':'2026'},{'cik':'unknown'},{'view_id':'wrong'},{'actual':'5'},{'accession':'x'}])
def test_scope_rejected(acquired,query):
    with pytest.raises(ValueError):report(acquired[0],'view',query)

@pytest.mark.parametrize('target',['pdf','pages','catalog','builder','acquisition'])
def test_evidence_mutation_rejected(acquired,target):
    views,data,receipt=acquired;root=views.root;s=next(iter(data['sources'].values()));folder=root/'data/private/sec-documents'/s['folder']
    p={'pdf':folder/s['file'],'pages':folder/'pages.json','catalog':root/'artifacts/private'/receipt['catalog_id']/'catalog.json','builder':root/'scripts/build_ford_facility_catalog.py','acquisition':folder/'acquisition.json'}[target]
    if target=='acquisition':r=json.loads(p.read_text());r['url']='https://wrong.example';p.write_text(json.dumps(r))
    else:p.write_bytes(p.read_bytes()+b' ')
    with pytest.raises(ValueError):catalog(root)

def test_http_private_export_and_guards(acquired):
    views,_,_=acquired;s=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=views.root,sec_views=views)));t=threading.Thread(target=s.serve_forever,daemon=True);t.start();base='http://127.0.0.1:'+str(s.server_port);endpoint='/api/sec-facilities-report?view_id=view&cik=0000037996&asof=2026-10-11'
    try:
        with urlopen(base+endpoint) as r:
            assert r.headers['Cache-Control']=='no-store' and 'attachment' in r.headers['Content-Disposition']
            assert json.load(r)['summary']['disclosed_commitment_total_usd_exact']=='21000000000'
        for tail in ['&asof=2026-10-10','&actual=10']:
            with pytest.raises(HTTPError) as e:urlopen(base+endpoint+tail)
            assert e.value.code==400
        with pytest.raises(HTTPError) as e:urlopen(Request(base+endpoint,headers={'Origin':'https://other.example'}))
        assert e.value.code==403
    finally:s.shutdown();s.server_close();t.join(5)
