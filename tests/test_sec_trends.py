import copy
from decimal import Decimal
import pytest
import json
import threading
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from credit_atlas.sec_trends import comparison, derive_trend, report
from credit_atlas.sec_financials import fact_rows, statement
from tests.test_sec_financials import filing, payload, acquired
from tests.test_sec_views import view


def annual(year=2025):
    f=filing();f['report_date']=f'{year}-12-31';f['filing_date']=f'{year+1}-02-01'
    p=payload('0000320193')
    for field in p['facts']['us-gaap'].values():
        for x in field['units']['USD']:
            x['end']=f['report_date'];x['filed']=f['filing_date']
            if 'start' in x:x['start']=f'{year}-01-01'
    rows,_=fact_rows(p,'0000320193');return statement(f,rows)


def test_exact_delta_and_positive_baseline():
    current,prior=annual(),annual(2024)
    current['ratios']['current_ratio']['value_exact']='1.125'
    c=comparison(current,prior,'current_ratio')
    assert c['status']=='COMPARABLE' and Decimal(c['absolute_delta_exact'])==Decimal('.125')
    assert Decimal(c['relative_delta_exact'])==Decimal('.125')
    for base in ['0','-0.1']:
        prior['ratios']['net_income_margin']['value_exact']=base
        c=comparison(current,prior,'net_income_margin')
        assert c['status']=='COMPARABLE' and c['relative_delta_exact'] is None and c['relative_status']=='NONPOSITIVE_BASELINE'


@pytest.mark.parametrize('case,status',[('gap','NOT_ADJACENT_ANNUAL_PERIOD'),('missing','UNSUPPORTED_RATIO_INPUT'),('mapping','CONCEPT_MAPPING_CHANGED'),('duration','ANNUAL_DURATION_CHANGED')])
def test_comparison_gates(case,status):
    current,prior=annual(),annual(2024)
    if case=='gap':prior['report_date']='2023-12-31'
    if case=='missing':current['ratios']['net_income_margin']['status']='missing_or_ambiguous_input'
    if case=='mapping':prior['fields']['revenue']['evidence'][0]['concept']='DifferentRevenueConcept'
    if case=='duration':prior['fields']['revenue']['start_date']='2024-02-01'
    c=comparison(current,prior,'net_income_margin')
    assert c['status']==status and c['absolute_delta_exact'] is None


def test_ambiguous_original_and_amendment_not_silently_selected():
    a,b,c=annual(2023),annual(2024),annual(2025)
    duplicate=copy.deepcopy(b);duplicate['accession']='0001193125-25-000002'
    amendment=copy.deepcopy(c);amendment['form']='10-K/A'
    periods=derive_trend([a,b,duplicate,c,amendment],3)
    assert periods[1]['selection_status']=='NO_UNIQUE_ORIGINAL_10K' and periods[1]['statement'] is None
    assert periods[2]['statement']['form']=='10-K' and len(periods[2]['filings'])==2
    assert periods[2]['comparisons']['current_ratio']['status']=='NO_PRIOR_PERIOD'
    assert derive_trend([amendment],3)[0]['statement'] is None


def test_verified_view_cutoff_scope_and_lineage(view):
    _,_,receipt,views=view
    r=report(views,receipt['view_id'],{'cik':'0000320193','asof':'2026-02-01','years':'3'})
    assert len(r['periods'])==1 and len(r['source_capture']['annual_statements_sha256'])==64
    assert not any(r['qualification'].values())
    assert report(views,receipt['view_id'],{'asof':'2026-01-31'})['periods']==[]


@pytest.mark.parametrize('query',[{'years':'100'},{'years':5},{'asof':'2026-02-30'},{'cik':'../bad'},{'accession':'unused'}])
def test_bad_filters(view,query):
    with pytest.raises(ValueError):report(view[3],view[2]['view_id'],query)


def test_real_http_trend_attachment_and_filters(view):
    from credit_atlas.server import handler_for
    root,_,receipt,views=view
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(SimpleNamespace(root=root,sec_views=views)))
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    url=f'http://127.0.0.1:{server.server_port}/api/sec-trend-report?view_id='+receipt['view_id']+'&asof=2026-02-01&years=3'
    try:
        with urlopen(url) as response:
            assert response.headers['Cache-Control']=='no-store' and 'SEC-trend.json' in response.headers['Content-Disposition']
            assert len(json.load(response)['periods'])==1
        for bad,status in [(Request(url,headers={'Origin':'https://evil.example'}),403),(url+'&pd=1',400),(url+'&years=5',400)]:
            with pytest.raises(HTTPError) as e:urlopen(bad)
            assert e.value.code==status
    finally:server.shutdown();server.server_close();worker.join(timeout=5)
