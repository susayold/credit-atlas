"""Read issuer static-pool curves at native collection-age grain."""
from pathlib import PurePosixPath
from decimal import Decimal
import json,re,zipfile
from xml.etree import ElementTree as ET
from .workspace import contained,read_json,sha256

SOURCE_ID='pool-history-source-757ce3631134'
RECEIPT_SHA='5f3276105710f49a38e027d38e95d3a73e8a72f9fea59c63ac7dbb4540fab98d'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
METRICS={'delinquency':('Delinquencies','61+ day delinquency share'),
         'loss':('Cumulative Losses','Reported cumulative net losses'),
         'speed':('ABS Speed','Reported ABS speed')}


def workbook(path):
    with zipfile.ZipFile(path) as z:
        if sum(x.file_size for x in z.infolist())>128*1024**2:raise ValueError('Oversize workbook')
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        manifest=ET.fromstring(z.read('xl/workbook.xml'))
        rels={x.get('Id'):x.get('Target') for x in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        sheets={}
        for sheet in manifest.findall('s:sheets/s:sheet',NS):
            target=rels[sheet.get('{'+NS['r']+'}id')]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            if '..' in PurePosixPath(target).parts:raise ValueError('Unsafe workbook relationship')
            cells={}
            for cell in ET.fromstring(z.read(target)).findall('.//s:sheetData/s:row/s:c',NS):
                value=cell.find('s:v',NS);raw=value.text if value is not None else None
                kind=cell.get('t','n');text=raw
                if kind=='s' and raw is not None:text=shared[int(raw)]
                if kind=='inlineStr':text=''.join(cell.find('s:is',NS).itertext())
                cells[cell.get('r')]={'raw':raw,'value':text,'type':kind,'formula':cell.findtext('s:f',None,NS)}
            sheets[sheet.get('name')]=cells
        return sheets


def verified_source(root):
    folder=contained(root,'data/private/structured/'+SOURCE_ID)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT_SHA:raise ValueError('Pool-history acquisition receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for item in receipt['sources']:
        path=contained(root,'data/private/structured/'+SOURCE_ID+'/'+item['file'])
        if path.stat().st_size!=item['bytes'] or sha256(path)!=item['sha256']:raise ValueError('Pool-history source bytes changed')
    return folder,receipt


def curves(sheets):
    rows=[];definitions={}
    for metric,(sheet,title) in METRICS.items():
        cells=sheets[sheet]
        if cells.get('A3',{}).get('value')!='Collection Period':raise ValueError('Static-pool header changed')
        headers={re.sub(r'\d+$','',coord):cell['value'] for coord,cell in cells.items()
                 if re.fullmatch(r'[A-Z]+3',coord) and re.fullmatch(r'WOART 20\d\d-[A-Z]',str(cell['value']))}
        if len(headers)!=len(set(headers.values())) or not headers:raise ValueError('Ambiguous cohort headers')
        notes=[{'cell':coord,'text':cell['value']} for coord,cell in cells.items()
               if re.fullmatch('A[0-9]+',coord) and cell['type'] in ('s','inlineStr') and int(coord[1:])>3 and cell['value']]
        definitions[metric]={'sheet':sheet,'title':title,'source_title':cells['A1']['value'],'notes':notes}
        for coord,age in cells.items():
            if not re.fullmatch('A[0-9]+',coord) or age['type']!='n' or age['value'] is None:continue
            number=Decimal(age['value'])
            if not number.is_finite() or number!=number.to_integral_value() or number<=0:raise ValueError('Invalid collection age')
            for col,deal in headers.items():
                key=col+coord[1:];cell=cells.get(key,{'value':None,'raw':None,'type':'n','formula':None})
                value=cell['value']
                if value is not None:
                    if cell['type']!='n':raise ValueError('Non-numeric static pool rate')
                    rate=Decimal(value)
                    if not rate.is_finite() or not Decimal(-1)<=rate<=Decimal(1):raise ValueError('Invalid static pool fraction')
                rows.append({'metric':metric,'deal':deal,'collection_age':int(number),'value_exact':value,
                    'status':'VALUE' if value is not None else 'SOURCE_BLANK','sheet':sheet,'cell':key,'raw_value':cell['raw'],
                    'cached_formula':cell['formula']})
    if len({(r['metric'],r['deal'],r['collection_age']) for r in rows})!=len(rows):raise ValueError('Duplicate cohort age')
    return rows,definitions


def report(root,query):
    if set(query)-{'metric','deal'}:raise ValueError('Only static-pool metric/deal filters supported')
    metric=query.get('metric','loss')
    if metric not in METRICS:raise ValueError('Unsupported static-pool metric')
    folder,source=verified_source(root);sheets=workbook(folder/'StaticPool-WOART.xlsx')
    all_rows,definitions=curves(sheets)
    deals=sorted({r['deal'] for r in all_rows});selected=query.get('deal', 'WOART 2025-A')
    if selected not in deals:raise ValueError('Deal absent from static-pool source')
    rows=[r for r in all_rows if r['metric']==metric and r['deal']==selected]
    summaries=[]
    for deal in deals:
        present=sorted([r for r in all_rows if r['metric']==metric and r['deal']==deal and r['value_exact'] is not None],key=lambda r:r['collection_age'])
        latest=present[-1] if present else None
        ages={r['collection_age']:r for r in present}
        summaries.append({'deal':deal,'observed_ages':len(present),'latest_age':latest['collection_age'] if latest else None,
            'latest_value_exact':latest['value_exact'] if latest else None,
            'age12_value_exact':ages.get(12,{}).get('value_exact'),'age24_value_exact':ages.get(24,{}).get('value_exact'),
            'declining_steps':sum(Decimal(y['value_exact'])<Decimal(x['value_exact']) for x,y in zip(present,present[1:]))})
    managed=workbook(folder/'ManagedPool-Retail.xlsx')
    return {'source_id':SOURCE_ID,'source_receipt_sha256':RECEIPT_SHA,'source':source,
        'filters':{'metric':metric,'deal':selected},'metric_options':{k:v[1] for k,v in METRICS.items()},'deal_options':deals,
        'rows':rows,'cohort_summary':summaries,'definition':definitions[metric],
        'inventory':{'static_sheet_names':list(sheets),'managed_sheet_names':list(managed),
            'projected_metrics':len(METRICS),'cohorts':len(deals),'source_age_cells':len(all_rows),
            'populated_age_cells':sum(r['value_exact'] is not None for r in all_rows),
            'blank_age_cells':sum(r['value_exact'] is None for r in all_rows)},
        'limitations':['Collection age is the publisher period index, not a calendar date or a loan-level horizon.',
            'Blank source cells remain missing; no forward fill, zero fill or extrapolation. Deals with unavailable age12/24 excluded from those comparisons.',
            '61+ delinquency uses the publisher pool-balance definition, not borrower-count PD. ABS speed includes prepayments and defaults, not pure default probability.',
            'Reported cumulative net-loss denominator/components not independently qualified here; not LGD, PD×LGD or forecast loss.',
            'Managed workbook has a separate stock/flow adapter; six legacy individual-deal tabs remain unnormalized and are not in these three cohort curves.',
            'Source formula caches not recalculated; historical availability, risk calibration and full legal assumptions unqualified.'],
        'qualification':{'loan_level':False,'forecast':False,'lgd':False,'historical_availability':False,'formula_recalculated':False},
        'visibility':'private','public_release_approved':False}
