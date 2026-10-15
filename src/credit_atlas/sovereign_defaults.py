"""Dated sovereign default stock editions; never a PD or a historical vintage panel."""
import json,re,zipfile
from decimal import Decimal,localcontext
from xml.etree import ElementTree as ET
from .workspace import contained,read_json,sha256

SOURCE='sovereign-default-source-001afb29b84a'
RECEIPT='1f5821cfeaeda3bfbc696fbdfeb1098cf15934b6ef2866f22759e5f10c3956a9'
ARCHIVE='sovereign-archive-source-e0310b79a4da'
ARCHIVE_RECEIPT='21ba37b2a39d743dff6b835042044bff572f5d0eb14794254ab9eaabc87166e6'
COMPONENTS=['IMF','IBRD','IDA','IADB','PARIS_CLUB','CHINA','OTHER_OFFICIAL_CREDITORS',
            'PRIVATE_CREDITORS','FC_BANK_LOANS','FC_BONDS','LC_DEBT']
MONEY=['TOTAL',*COMPONENTS,'FISCAL_ARREARS']
METRICS={k:{'label':k.replace('_',' ').title(),'unit':'USD million, nominal stock'} for k in MONEY}
METRICS.update({k:{'label':k.replace('_',' ').title(),'unit':'sovereigns'} for k in ['TOTAL_NUMB_SOVEREIGNS','TOTAL_DEF_SOVEREIGNS']})
METRICS['DEFRATE_SOVEREIGNS']={'label':'Source sovereign participation rate','unit':'percent; descriptive stock participation, not PD'}
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def workbook_cells(path):
    """Literal/cached XML values only. Do not recalculate or follow external links."""
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist())>100*1024**2:raise ValueError('Workbook size bound exceeded')
        strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)] if 'xl/sharedStrings.xml' in z.namelist() else []
        rels={x.get('Id'):x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        books=[]
        for s in ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',NS):
            target=rels[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            if '..' in target.split('/'):raise ValueError('Invalid worksheet path')
            rows={}
            for r in ET.fromstring(z.read(target)).findall('.//s:sheetData/s:row',NS):
                row={}
                for c in r.findall('s:c',NS):
                    kind=c.get('t','n');value=c.findtext('s:v',None,NS)
                    if kind=='s' and value is not None:value=strings[int(value)]
                    if kind=='inlineStr':value=''.join(c.find('s:is',NS).itertext())
                    row[re.sub(r'\d+$','',c.get('r'))]={'value':value,'kind':kind,'formula':c.findtext('s:f',None,NS),'cell':c.get('r')}
                rows[int(r.get('r'))]=row
            books.append({'name':s.get('name'),'rows':rows})
        return books

def numeric(cell):
    if not cell or cell['value'] is None:return None
    if cell['kind']!='n':raise ValueError('Expected numeric source value')
    value=Decimal(cell['value'])
    if not value.is_finite():raise ValueError('Nonfinite source value')
    return str(value)

def acquire_context(root):
    folder=contained(root,'data/private/country/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('Sovereign source receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for x in receipt['sources']:
        p=contained(folder,x['file'])
        if p.stat().st_size!=x['bytes'] or sha256(p)!=x['sha256']:raise ValueError('Sovereign source changed')
    return folder,receipt

def archive_context(root):
    folder=contained(root,'data/private/country/'+ARCHIVE)
    if sha256(folder/'acquisition-complete.json')!=ARCHIVE_RECEIPT:raise ValueError('Sovereign archive receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for x in receipt['sources']:
        p=contained(folder,x['file'])
        if p.stat().st_size!=x['bytes'] or sha256(p)!=x['sha256']:raise ValueError('Sovereign archive source changed')
    return folder,receipt

def build(root):
    folder,receipt=acquire_context(root);archive,archive_receipt=archive_context(root);editions=[]
    for edition,last in [(2023,2022),(2024,2023),(2025,2024),(2026,2025)]:
        filename='BoC-BoE-Database-2023-08-29.xlsx' if edition==2023 else f'BoC-BoE-Database-{edition}.xlsx'
        source_folder=archive if edition<2025 else folder
        summary,flat=workbook_cells(source_folder/filename)
        header_row=63 if edition==2023 else 65
        header=flat['rows'].get(header_row,{})
        columns={c['value']:column for column,c in header.items() if c['value'] is not None}
        key='k3' if edition==2026 else 'k'
        metric_headers={m:f'DEBT_{m}_{edition}' for m in METRICS};schema_warnings=[]
        if edition==2023:
            metric_headers['IADB']=None
            schema_warnings.append('2023 flat sheet has no IADB column. Preserve schema absence as null; do not backfill summary values into country records.')
        if edition==2024:
            metric_headers['TOTAL']='DEBT_TOTAL_2023'
            schema_warnings.append('2024 flat TOTAL column is labelled DEBT_TOTAL_2023. Explicit source-specific alias; all World years checked against 2024 summary totals.')
            schema_warnings.append('2024 contains ****, ***/***** variants and whitespace source markers. Four-star legend means unavailable; other variants remain uninterpreted nonnumeric markers. All stay null with raw text retained.')
            if not any(c['value']=='**** -- values for debt in default unavailable' for r in summary['rows'].values() for c in r.values()):raise ValueError('Missing source marker legend')
        required=[key,'DEBT_COUNTRY','DEBT_COUNTRY_GROUP','DEBT_YEAR',*[h for h in metric_headers.values() if h]]
        if not set(required)<=columns.keys():raise ValueError('Unexpected sovereign observation schema')
        records=[];entities={};seen=set();checks=[]
        for n,r in sorted(flat['rows'].items()):
            if n<=header_row or not r.get(columns[key],{}).get('value'):continue
            raw_key=r[columns[key]]['value'];year_value=numeric(r.get(columns['DEBT_YEAR']))
            if year_value is None:raise ValueError('Missing reference year')
            year=int(Decimal(year_value))
            if Decimal(year_value)!=year or not 1960<=year<=last or not raw_key.endswith('_'+str(year)):raise ValueError('Inconsistent source year/key')
            entity=raw_key.rsplit('_',1)[0]
            if not re.fullmatch(r'[A-Z]{3,8}',entity) or (entity,year) in seen:raise ValueError('Invalid or duplicate entity/year')
            seen.add((entity,year))
            name=r[columns['DEBT_COUNTRY']]['value'];group=r[columns['DEBT_COUNTRY_GROUP']]['value']
            info={'id':entity,'name':name,'source_group':group,'is_world':entity=='WORLD'}
            if entity in entities and entities[entity]!=info:raise ValueError('Entity metadata changed within edition')
            entities[entity]=info
            values={};markers={}
            for m,h in metric_headers.items():
                c=r.get(columns[h]) if h else None
                if edition==2024 and c and c['kind']=='s' and re.fullmatch(r'(\*{3,5})?',(c['value'] or '').strip()):
                    values[m]=None;markers[m]={'raw':c['value'],'status':'source_unavailable' if len(c['value'].strip())==4 else 'uninterpreted_source_marker','cell':c['cell']}
                else:values[m]=numeric(c)
            records.append({'entity':entity,'year':year,'values':values,'raw_non_numeric_values':markers,'source_row':n})
        expected=(last-1960+1)*len(entities)
        if len(records)!=expected or len(entities)!=(158 if edition==2023 else 167):raise ValueError('Incomplete edition panel')
        # Both official editions label the latest reference year "YYYYp".
        # The workbook explicitly defines p as provisional; retain that status.
        provisional_legend=any(c['value']=='p -- Provisional' for r in summary['rows'].values() for c in r.values())
        year_columns={};year_headers=[]
        for column,c in summary['rows'][1].items():
            match=re.fullmatch(r'(\d{4})(p?)',c['value'] or '')
            if not match:continue
            reference_year=int(match[1]);provisional=bool(match[2])
            if not 1960<=reference_year<=last:continue
            if reference_year in year_columns or (provisional and not provisional_legend):raise ValueError('Invalid source year header')
            year_columns[reference_year]=column
            year_headers.append({'year':reference_year,'source_label':c['value'],'source_cell':c['cell'],'provisional':provisional})
        if set(year_columns)!=set(range(1960,last+1)):raise ValueError('Incomplete summary year headers')
        for row in records:
            if row['entity']!='WORLD':continue
            for summary_row,metric in [(7,'TOTAL'),(41,'TOTAL_DEF_SOVEREIGNS')]:
                c=summary['rows'][summary_row].get(year_columns[row['year']]);value=numeric(c)
                delta=None if value is None or row['values'][metric] is None else str(Decimal(value)-Decimal(row['values'][metric]))
                tolerance=Decimal('.005') if metric=='TOTAL' else Decimal(0)
                checks.append({'year':row['year'],'metric':metric,'summary_exact':value,'flat_exact':row['values'][metric],
                               'delta_exact':delta,'matches_at_flat_precision':delta is not None and abs(Decimal(delta))<=tolerance,
                               'summary_cell':c['cell'] if c else None,'summary_has_formula':bool(c and c['formula'])})
        update=next(c['value'] for r in summary['rows'].values() for c in r.values() if isinstance(c['value'],str) and c['value'].startswith('Last Update:'))
        editions.append({'edition':edition,'first_year':1960,'last_year':last,'source_update_text':update,'file':filename,
                         'source_id':ARCHIVE if edition<2025 else SOURCE,'header_row':header_row,
                         'schema_warnings':schema_warnings,'metric_source_headers':metric_headers,
                         'sheet':flat['name'],'summary_sheet':summary['name'],'metric_columns':{m:columns[h] if h else None for m,h in metric_headers.items()},
                         'records':records,'year_headers':year_headers,'entities':sorted(entities.values(),key=lambda x:x['id']),
                         'source_summary_comparisons':checks})
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'archive_source_id':ARCHIVE,'archive_receipt_sha256':ARCHIVE_RECEIPT,
            'sources':receipt['sources']+archive_receipt['sources'],'metrics':METRICS,'editions':editions,
            'visibility':'private','public_release_approved':False,'historical_publication_vintages_complete':False,
            'pd_lgd_calibrated':False,'macro_stress_linkage_qualified':False}

def scoped(doc,query):
    if not isinstance(query,dict) or set(query)-{'edition','entity','year','metric','from','to'} or any(not isinstance(v,str) for v in query.values()):raise ValueError('Bounded sovereign filters required')
    edition=query.get('edition','2026');entity=query.get('entity','WORLD');metric=query.get('metric','TOTAL')
    if edition not in {str(e['edition']) for e in doc['editions']} or metric not in METRICS:raise ValueError('Unknown sovereign edition/metric')
    selected=next(e for e in doc['editions'] if e['edition']==int(edition));last=selected['last_year']
    def year(key,default):
        value=query.get(key,str(default))
        if not re.fullmatch(r'\d{4}',value) or not 1960<=int(value)<=last:raise ValueError('Year outside selected edition')
        return int(value)
    y=year('year',last);first=year('from',1960);end=year('to',last)
    if first>end:raise ValueError('Invalid sovereign timeline range')
    info=next((x for x in selected['entities'] if x['id']==entity),None)
    if info is None:raise ValueError('Unknown source entity')
    records={(r['entity'],r['year']):r for r in selected['records']}
    current=records[(entity,y)];prior=records.get((entity,y-1))
    older=next((e for e in doc['editions'] if e['edition']==int(edition)-1),None)
    old=next((r for r in older['records'] if r['entity']==entity and r['year']==y),None) if older else None
    def difference(a,b):return str(Decimal(a)-Decimal(b)) if a is not None and b is not None else None
    actual=current['values'][metric]
    world=records[('WORLD',y)]['values']['TOTAL']
    peers=[]
    for e in selected['entities']:
        if e['is_world']:continue
        r=records[(e['id'],y)];value=r['values'][metric]
        share=str(Decimal(value)/Decimal(world)) if metric=='TOTAL' and value is not None and world is not None and Decimal(world)>0 else None
        peers.append({**e,'value_exact':value,'world_default_stock_share_fraction_exact':share,'source_row':r['source_row']})
    peers.sort(key=lambda x:(x['value_exact'] is None,-Decimal(x['value_exact']) if x['value_exact'] is not None else 0,x['id']))
    timeline=[{'year':r['year'],'value_exact':r['values'][metric],'source_row':r['source_row']} for r in selected['records'] if r['entity']==entity and first<=r['year']<=end]
    with localcontext() as ctx:
        ctx.prec=50
        component_values=[current['values'][k] for k in COMPONENTS]
        subtotal=sum((Decimal(v) for v in component_values),Decimal(0)) if all(v is not None for v in component_values) else None
        residual=None if subtotal is None or current['values']['TOTAL'] is None else str(Decimal(current['values']['TOTAL'])-subtotal)
        known=[records[(e['id'],y)]['values']['TOTAL'] for e in selected['entities'] if not e['is_world']]
        known_sum=sum((Decimal(v) for v in known if v is not None),Decimal(0))
    return {'source_id':doc['source_id'],'source_receipt_sha256':doc['source_receipt_sha256'],
        'archive_source_id':doc['archive_source_id'],'archive_receipt_sha256':doc['archive_receipt_sha256'],
        'edition_catalog':[{'edition':e['edition'],'first_year':e['first_year'],'last_year':e['last_year'],
                            'entities':len(e['entities']),'entity_options':e['entities'],
                            'unavailable_metrics':[m for m,c in e['metric_columns'].items() if c is None],
                            'source_update_text':e['source_update_text']} for e in doc['editions']],
        'filters':{'edition':edition,'entity':entity,'year':str(y),'metric':metric,'from':str(first),'to':str(end)},
        'entity':info,'entities':selected['entities'],'metrics':METRICS,'source_update_text':selected['source_update_text'],
        'reference_year_header':next(h for h in selected['year_headers'] if h['year']==y),
        'source_cell':{'source_id':selected['source_id'],'file':selected['file'],'sheet':selected['sheet'],
                       'source_header':selected['metric_source_headers'][metric],
                       'cell':selected['metric_columns'][metric]+str(current['source_row']) if selected['metric_columns'][metric] else None},
        'schema_warnings':selected['schema_warnings'],
        'metric_column_present':selected['metric_columns'][metric] is not None,
        'selected_source_marker':current.get('raw_non_numeric_values',{}).get(metric),
        'unit':METRICS[metric]['unit'],'actual_exact':actual,
        'prior_year_same_edition_exact':prior['values'][metric] if prior else None,
        'year_change_same_edition_exact':difference(actual,prior['values'][metric]) if prior else None,
        'prior_edition_same_year_exact':old['values'][metric] if old else None,
        'prior_edition':older['edition'] if older else None,
        'edition_revision_same_year_exact':difference(actual,old['values'][metric]) if old else None,
        'timeline':timeline,'peers':peers,'components':[{'metric':k,'value_exact':current['values'][k]} for k in COMPONENTS],
        'component_residual_exact':residual,'domestic_arrears_exact':current['values']['FISCAL_ARREARS'],
        'world_source_sovereigns_in_default_exact':records[('WORLD',y)]['values']['TOTAL_DEF_SOVEREIGNS'],
        'world_source_sovereign_universe_exact':records[('WORLD',y)]['values']['TOTAL_NUMB_SOVEREIGNS'],
        'country_panel':{'entities':len(known),'known_total_entities':sum(v is not None for v in known),
                         'positive_total_entities':sum(v is not None and Decimal(v)>0 for v in known),
                         'known_total_sum_exact':str(known_sum),
                         'world_minus_known_country_sum_exact':difference(world,str(known_sum))},
        'source_summary_comparisons':[r for r in selected['source_summary_comparisons'] if r['year']==y],
        'sources':doc['sources'],'historical_publication_vintages_complete':False,'pd_lgd_calibrated':False,
        'macro_stress_linkage_qualified':False,'visibility':'private','public_release_approved':False,
        'limitations':['Nominal annual stocks in default are not new-default flows, realized loss, PD, LGD or default probabilities.',
            'Four downloaded editions allow revision comparisons, not complete historical publication availability; retrieved bytes do not prove original release-day availability; no OOT model is fit.',
            'Source country panel sizes differ by edition and are not the World sovereign denominator. Source World rows and country sums stay separate; missing does not become zero.',
            'Domestic arrears are a separate source stock; they are not added to conventional debt in default.',
            'Read literal Debt sheet values; source summary formula caches/external links are not recalculated. Summary discrepancies are retained.',
            'Amounts preserve saved XML numeric text and source USD-million units. No conversion to bond prices or institution exposures.']}

PROFILE='artifacts/private/sovereign-default-profile-08270bdda389/profile.json'
PROFILE_SHA='578e9aaad6b34e157829ca3f4007fc1210b9b2e627c677c2bec9f30d253e7d83'

def report(root,query):
    acquire_context(root)
    archive_context(root)
    if PROFILE is None:raise ValueError('Sovereign normalized profile not configured')
    p=contained(root,PROFILE)
    if sha256(p)!=PROFILE_SHA:raise ValueError('Sovereign normalized profile changed')
    return scoped(read_json(p),query)
