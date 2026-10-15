"""Exact currency/dimension reconciliation using raw CSV and rational shares."""
from pathlib import Path
from fractions import Fraction
from collections import defaultdict
from urllib.request import urlopen
from urllib.parse import urlencode
from uuid import uuid4
import csv,json
from credit_atlas.workspace import read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
browser=ROOT/'artifacts/private/p4-acceptance-qa-b6a5a8af88d0/receipt.json';proof=read_json(browser);assert proof['status']=='PASS'
identifiers=['exposure-import-57b88e00bedb',proof['example_import_id']]
graph={str(browser.relative_to(ROOT)):sha256(browser)};results=[];cell_checks=0
for identifier in identifiers:
    folder=ROOT/'artifacts/private'/identifier;r=read_json(folder/'import-complete.json');keep=[folder/'import-complete.json']
    for name,digest in r['outputs_sha256'].items():assert sha256(folder/name)==digest;keep.append(folder/name)
    meta=read_json(folder/'metadata.json')
    for item in meta['source_lineage']:
        path=ROOT/item['path'];assert sha256(path)==item['sha256'];keep.append(path)
    graph.update({str(p.relative_to(ROOT)):sha256(p) for p in keep})
    with (folder/'source.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    totals=defaultdict(lambda:[0,Fraction(0),0]);groups=defaultdict(lambda:[0,Fraction(0)])
    for row in rows:
        assert row['pd']==row['lgd']==row['ead']=='' and meta['risk_contract'] is None
        amount=Fraction(row['reported_amount'])*{'major':1,'thousand':1000,'million':1000000}[row['amount_unit']]
        c=row['currency'];totals[c][0]+=1;totals[c][1]+=amount;totals[c][2]+=amount==0
        for dimension in ['region','segment','source_state','representation']:
            item=groups[(c,dimension,row[dimension])];item[0]+=1;item[1]+=amount
    for currency in ['all',*sorted(totals)]:
        for dimension in ['region','segment','source_state','representation']:
            query={'import_id':identifier,'currency':currency,'dimension':dimension}
            with urlopen('http://127.0.0.1:8770/api/exposure-report?'+urlencode(query),timeout=120) as response:
                assert response.headers['Cache-Control']=='no-store';report=json.load(response)
            assert report['filters']=={'currency':currency,'dimension':dimension}
            expected_currencies=[c for c in sorted(totals) if currency in ['all',c]]
            assert [r['currency'] for r in report['currencies']]==expected_currencies
            assert report['records']==sum(totals[c][0] for c in expected_currencies)
            assert report['global_cross_currency_total'] is None and report['risk_contract'] is None
            assert all(v is False for k,v in report['contract'].items() if isinstance(v,bool))
            for item in report['currencies']:
                count,amount,zeros=totals[item['currency']]
                assert item['records']==count and item['zero_amount_records']==zeros and Fraction(item['reported_amount_major_exact'])==amount
                assert item['research_el_major_exact'] is None and item['el_status']=='UNAVAILABLE_NO_RISK_INPUTS';cell_checks+=5
            expected_keys={key for key in groups if key[0] in expected_currencies and key[1]==dimension}
            assert {(r['currency'],r['dimension'],r['bucket']) for r in report['concentrations']}==expected_keys
            for item in report['concentrations']:
                key=(item['currency'],item['dimension'],item['bucket']);count,amount=groups[key]
                assert item['records']==count and Fraction(item['reported_amount_major_exact'])==amount and item['research_el_major_exact'] is None
                denominator=totals[key[0]][1]
                if denominator:assert item['amount_share'] is not None and abs(Fraction(item['amount_share'])-amount/denominator)<=Fraction(1,10**118)
                else:assert item['amount_share'] is None
                cell_checks+=4
            results.append({'import_id':identifier,'currency':currency,'dimension':dimension,'records':report['records'],'groups':len(expected_keys)})
assert all(sha256(ROOT/p)==h for p,h in graph.items())
out=ROOT/'artifacts/private'/('p4-inventory-scope-audit-'+uuid4().hex[:12]);out.mkdir()
write_new(out/'receipt.json',{'status':'PASS','scopes':results,'cell_checks':cell_checks,'inputs_sha256':graph,
    'method_sha256':sha256(Path(__file__)),'view_method_sha256':sha256(ROOT/'src/credit_atlas/exposure_views.py'),
    'interpretation':'One actual source-observation import and one explicitly synthetic EXAMPLE template import; all available currencies/four dimensions. No owned portfolio, FX global total, currentEAD, borrower concentration or calibrated PD claim.'})
print(out);print('scopes',len(results),'checks',cell_checks)
