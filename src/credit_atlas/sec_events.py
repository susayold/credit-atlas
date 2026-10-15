"""Verified issuer filing timeline; item metadata is not a confirmed credit event."""
from collections import Counter
from datetime import date,timedelta
from pathlib import Path
import re
from urllib.parse import quote
from .sec_financials import normalize_filings
from .sec_sources import verify_source,filing_columns
from .workspace import read_json,sha256,contained

FORM_GROUPS={'all':{'8-K','8-K/A','10-K','10-K/A','10-Q','10-Q/A'},'current':{'8-K','8-K/A'},'annual':{'10-K','10-K/A'},'quarterly':{'10-Q','10-Q/A'}}
ITEM_HINTS={'1.01':'Material agreement filing: inspect terms and exhibits.',
            '2.02':'Financial results filing: inspect results and reconciliations.',
            '2.03':'Financial obligation filing: inspect obligation/arrangement terms.'}


def parse_items(value):
    if value is None:return []
    if not isinstance(value,str) or len(value)>1000:raise ValueError('Invalid bounded SEC item metadata')
    return sorted(set(re.findall(r'(?<!\d)[1-9]\.\d{2}(?!\d)',value)))


def document_url(cik,accession,primary):
    base=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/'
    if not primary:return None
    if primary.startswith('/') or '\\' in primary or any(x in {'.','..',''} for x in primary.split('/')):raise ValueError('Invalid SEC primary document path')
    return base+quote(primary,safe='/')


def rows(folder,receipt,cik):
    canonical,_=normalize_filings(folder,receipt,cik)
    metadata={};occurrences={};captures=[]
    for source in receipt['files']:
        if source['cik']!=cik or source['kind'] not in {'submissions','history'}:continue
        payload=read_json(folder/source['file']);columns=payload['filings']['recent'] if source['kind']=='submissions' else payload
        captures.append({k:source[k] for k in ['file','url','sha256','retrieved_at']})
        for ordinal in range(filing_columns(columns)):
            accession=columns['accessionNumber'][ordinal]
            item={k:columns.get(k,[None]*len(columns['accessionNumber']))[ordinal] for k in ['items','primaryDocDescription']}
            parse_items(item['items'])
            if item['primaryDocDescription'] is not None and (not isinstance(item['primaryDocDescription'],str) or len(item['primaryDocDescription'])>4096):raise ValueError('Invalid filing description')
            if accession in metadata and metadata[accession]!=item:raise ValueError('Conflicting SEC item/description metadata')
            metadata[accession]=item
            occurrences.setdefault(accession,[]).append({'source_file':source['file'],'source_ordinal':ordinal})
    result=[]
    for filing in canonical:
        if filing['form'] not in FORM_GROUPS['all']:continue
        accession=filing['accession'];items=metadata[accession]['items'];codes=parse_items(items)
        modern=filing['form'] in FORM_GROUPS['current'] and filing['filing_date']>='2004-08-23'
        result.append({**filing,'items_raw':items,'item_codes':codes,
                       'item_hints':{code:ITEM_HINTS.get(code) for code in codes} if modern else {},
                       'item_label_scope':'Modern reference hints; read source form/exhibits' if modern else 'Historical/non-8K items require source-form review',
                       'document_description':metadata[accession]['primaryDocDescription'],
                       'filing_index_url':f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{accession}-index.html',
                       'primary_document_url':document_url(cik,accession,filing['primary_document']),
                       'source_occurrences':occurrences[accession]})
    return sorted(result,key=lambda x:(x['filing_date'],x['accession']),reverse=True),captures


def report(views,identifier,query):
    if set(query)-{'view_id','cik','asof','from','form_group','item','limit','offset'} or query.get('view_id',identifier)!=identifier:raise ValueError('Invalid issuer filing filters')
    asof=query.get('asof','2026-10-10')
    if not isinstance(asof,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',asof):raise ValueError('ISO filing cutoff required')
    end=date.fromisoformat(asof);start=query.get('from',str(end-timedelta(days=365)))
    if not isinstance(start,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',start) or date.fromisoformat(start)>end:raise ValueError('Valid filing date range required')
    group=query.get('form_group','all');item=query.get('item','all')
    if group not in FORM_GROUPS or not isinstance(item,str) or item!='all' and not re.fullmatch(r'[1-9]\.\d{2}',item):raise ValueError('Invalid form/item filter')
    limit=query.get('limit','50');offset=query.get('offset','0')
    if limit not in {'25','50','100'} or not isinstance(offset,str) or not re.fullmatch(r'\d{1,6}',offset):raise ValueError('Bounded filing page required')
    snapshot=views.view(identifier);cik=query.get('cik','0000320193')
    entity=next((x for x in snapshot['entities'] if x['cik']==cik),None)
    if entity is None:raise ValueError('Unknown SEC issuer CIK')
    folder,receipt=verify_source(views.root,snapshot['source_id']);all_rows,captures=rows(folder,receipt,cik)
    eligible=[r for r in all_rows if start<=r['filing_date']<=asof]
    selected=[r for r in eligible if r['form'] in FORM_GROUPS[group] and (item=='all' or r['form'] in FORM_GROUPS['current'] and item in r['item_codes'])]
    count=len(selected);page=selected[int(offset):int(offset)+int(limit)]
    items=Counter(code for r in selected if r['form'] in FORM_GROUPS['current'] for code in r['item_codes'])
    current=[r for r in selected if r['form'] in FORM_GROUPS['current']]
    return {'view_id':identifier,'case_id':snapshot['case_id'],'source_id':snapshot['source_id'],'entity':entity,
            'filters':{'cik':cik,'asof':asof,'from':start,'form_group':group,'item':item,'limit':limit,'offset':offset},
            'rows':page,'page':{'matched_filings':count,'returned':len(page),'has_next':int(offset)+len(page)<count},
            'summary':{'date_range_supported_filings':len(eligible),'matched_unique_filings':count,'form_counts':dict(Counter(r['form'] for r in selected)),
                       'item_counts':dict(sorted(items.items())),'current_reports_with_item_codes':sum(bool(r['item_codes']) for r in current),
                       'current_reports':len(current),'amendments':sum(r['form'].endswith('/A') for r in selected),
                       'source_first_filing_date':min((r['filing_date'] for r in all_rows),default=None),'source_last_filing_date':max((r['filing_date'] for r in all_rows),default=None)},
            'source_capture':{'submissions_files':captures,'view_receipt_sha256':sha256(contained(views.root,'artifacts/private/'+identifier+'/view-complete.json'))},
            'method_source_sha256':sha256(Path(__file__)),
            'qualification':{'full_text_reviewed':False,'legal_terms_extracted':False,'default_event_qualified':False,'historical_availability_qualified':False,'issuer_pd_qualified':False},
            'references':[{'title':'SEC Form 8-K','url':'https://www.sec.gov/file/form8-kpdf'}],
            'limitations':['Timeline contains selected forms in saved submissions metadata, not all corporate events or a live feed.',
                'Date filters use filing dates inclusively; report dates and acceptance timestamps are retained separately. No intraday availability is inferred.',
                'Amendments are separate accessions; they are not automatically replacements or linked to an original event.',
                'An 8-K item code is a document-discovery hint, not proof of default, covenant breach, borrowing amount or financial condition.',
                'Item counts overlap when one filing has multiple items; do not sum item counts to obtain unique events.',
                'Missing/legacy item metadata is retained; no absent-code record is classified as absence of credit events.',
                'Links are constructed from verified CIK/accession/document metadata. Full filing/exhibit contents have not been acquired or reviewed.'],
            'visibility':'private','public_release_approved':False}
