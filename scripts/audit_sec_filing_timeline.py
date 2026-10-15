"""Whole saved filing metadata corpus vs actual API pages and filters."""
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode, quote
from uuid import uuid4
import json
import re
from credit_atlas.workspace import read_json, sha256, write_new

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/private/sec/sec-source-13cf03606e0c'
source=read_json(SOURCE/'acquisition-complete.json');view='sec-view-b92d9914f1dc'
graph={str((SOURCE/'acquisition-complete.json').relative_to(ROOT)):sha256(SOURCE/'acquisition-complete.json')}
forms={'all':{'8-K','8-K/A','10-K','10-K/A','10-Q','10-Q/A'},'current':{'8-K','8-K/A'},'annual':{'10-K','10-K/A'},'quarterly':{'10-Q','10-Q/A'}}
nullable=lambda value:None if value in ('',None) else value
out=ROOT/'artifacts/private'/('sec-filing-timeline-audit-'+uuid4().hex[:12]);out.mkdir()
scopes=[];page_calls=0;row_checks=0
def api(query):
    with urlopen('http://127.0.0.1:8770/api/sec-events?'+urlencode({'view_id':view,**query}),timeout=120) as response:
        assert response.headers['Cache-Control']=='no-store'
        return json.load(response)
for entity in source['entities']:
    cik=entity['cik'];raw={};occurrences=defaultdict(list)
    for item in source['files']:
        if item['cik']!=cik or item['kind'] not in {'submissions','history'}:continue
        path=SOURCE/item['file'];assert sha256(path)==item['sha256'];graph[str(path.relative_to(ROOT))]=item['sha256']
        data=read_json(path);columns=data['filings']['recent'] if item['kind']=='submissions' else data
        for i,accession in enumerate(columns['accessionNumber']):
            get=lambda name:columns.get(name,[None]*len(columns['accessionNumber']))[i]
            record={'cik':cik,'accession':accession,'filing_date':get('filingDate'),'report_date':nullable(get('reportDate')),
                'acceptance_datetime':nullable(get('acceptanceDateTime')),'form':get('form'),'primary_document':get('primaryDocument'),
                'is_xbrl':None if get('isXBRL') is None else bool(get('isXBRL')),'items_raw':get('items'),
                'document_description':get('primaryDocDescription')}
            if accession in raw:assert raw[accession]==record
            raw[accession]=record;occurrences[accession].append({'source_file':item['file'],'source_ordinal':i})
    eligible=[r for r in raw.values() if r['form'] in forms['all'] and '1900-01-01'<=r['filing_date']<='2026-10-15']
    ordered=sorted(eligible,key=lambda r:(r['filing_date'],r['accession']),reverse=True)
    query={'cik':cik,'from':'1900-01-01','asof':'2026-10-15','form_group':'all','item':'all','limit':'100'}
    returned=[];summaries=[]
    for offset in range(0,max(1,len(ordered)),100):
        response=api({**query,'offset':str(offset)});page_calls+=1;summaries.append(response['summary'])
        assert response['source_id']==source['source_id'] and not any(response['qualification'].values())
        assert response['page']=={'matched_filings':len(ordered),'returned':len(ordered[offset:offset+100]),'has_next':offset+len(response['rows'])<len(ordered)}
        for actual,expected in zip(response['rows'],ordered[offset:offset+100]):
            assert all(actual[key]==value for key,value in expected.items())
            assert actual['occurrences']==len(occurrences[expected['accession']]) and actual['source_occurrences']==occurrences[expected['accession']]
            codes=sorted(set(re.findall(r'(?<!\d)[1-9]\.\d{2}(?!\d)',expected['items_raw'] or '')))
            assert actual['item_codes']==codes
            base='https://www.sec.gov/Archives/edgar/data/'+str(int(cik))+'/'+expected['accession'].replace('-','')+'/'
            assert actual['filing_index_url']==base+expected['accession']+'-index.html'
            expected_url=base+quote(expected['primary_document'],safe='/') if expected['primary_document'] else None
            assert actual['primary_document_url']==expected_url
            row_checks+=1
        returned.extend(response['rows'])
    assert len(returned)==len(ordered) and len({r['accession'] for r in returned})==len(ordered)
    assert all(summary==summaries[0] for summary in summaries)
    summary=summaries[0];assert summary['form_counts']==dict(Counter(r['form'] for r in ordered))
    assert summary['amendments']==sum(r['form'].endswith('/A') for r in ordered)
    expected_items=Counter(code for r in ordered if r['form'] in forms['current'] for code in sorted(set(re.findall(r'(?<!\d)[1-9]\.\d{2}(?!\d)',r['items_raw'] or ''))))
    assert summary['item_counts']==dict(sorted(expected_items.items()))
    for group,item in [('current','all'),('annual','all'),('quarterly','all'),('current','1.01'),('current','2.02'),('current','2.03')]:
        selected=[r for r in ordered if r['form'] in forms[group] and (item=='all' or item in sorted(set(re.findall(r'(?<!\d)[1-9]\.\d{2}(?!\d)',r['items_raw'] or ''))))]
        response=api({**query,'form_group':group,'item':item,'offset':'0'});page_calls+=1
        assert response['summary']['matched_unique_filings']==len(selected)
        assert [r['accession'] for r in response['rows']]==[r['accession'] for r in selected[:100]]
    scopes.append({'cik':cik,'all_metadata_unique_filings':len(raw),'selected_timeline_filings':len(ordered),'filter_scopes':7})
assert all(sha256(ROOT/path)==digest for path,digest in graph.items())
write_new(out/'receipt.json',{'status':'PASS','scopes':scopes,'row_metadata_checks':row_checks,'http_page_calls':page_calls,
    'inputs_sha256':graph,'method_sha256':sha256(Path(__file__)),'timeline_method_sha256':sha256(ROOT/'src/credit_atlas/sec_events.py'),
    'qualification_note':'Filing date/form/item metadata only; no full-text legal/default event qualification or intraday/PIT claim.'})
print(out)
