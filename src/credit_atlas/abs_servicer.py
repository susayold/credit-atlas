"""Source-specific reported ABS servicing evidence; no projected waterfall."""
import calendar
import math
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import xlrd

from .workspace import contained, read_json, sha256, timestamp, write_new

DEAL = 'World Omni Auto Receivables Trust 2025-A'
FILES = ('WOART_2025-A_2025.xls', 'WOART_2025-A_2026.xls')
CLASSES = ('A-1', 'A-2a', 'A-2b', 'A-3', 'A-4', 'B', 'C', 'D', 'E')
RAW_SCHEMA = pa.schema([('file', pa.string()), ('sheet', pa.string()), ('row', pa.int32()),
    ('column', pa.int32()), ('cell_type', pa.int8()), ('raw_value', pa.string()), ('number_format', pa.string())])
METRIC_SCHEMA = pa.schema([('file', pa.string()), ('sheet', pa.string()), ('collection_end', pa.string()),
    ('section', pa.string()), ('slot', pa.string()), ('metric', pa.string()), ('unit', pa.string()),
    ('value', pa.string()), ('status', pa.string()), ('row', pa.int32()), ('column', pa.int32()),
    ('label', pa.string()), ('raw_value', pa.string()), ('cell_type', pa.int8())])


def methods():
    return {name: sha256(Path(__file__).with_name(name + '.py')) for name in ('abs_servicer', 'workspace')}


def scalar(raw, cell_type, unit):
    if unit not in ('USD','accounts','days','text','ratio','months'):
        raise ValueError('Unsupported source unit')
    if cell_type in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK) or (cell_type == xlrd.XL_CELL_TEXT and raw == ''):
        return None, 'SOURCE_BLANK'
    if unit == 'text':
        if cell_type != xlrd.XL_CELL_TEXT:
            raise ValueError('Expected source text')
        return raw, 'VALUE'
    if cell_type != xlrd.XL_CELL_NUMBER:
        raise ValueError('Expected numeric source cache')
    number = Decimal(raw)
    if not number.is_finite():
        raise ValueError('Nonfinite source number')
    if unit == 'USD':
        rounded = number.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        if abs(number - rounded) > Decimal('.00001'):
            raise ValueError('Money cache has material sub-cent amount')
        return str(rounded), 'VALUE'
    if unit in ('accounts', 'days'):
        if number != number.to_integral_value() or number < 0:
            raise ValueError('Expected nonnegative integer source count')
        return str(int(number)), 'VALUE'
    return str(number), 'VALUE'


def date_interval(value):
    if not re.fullmatch(r'\d{2}/\d{2}/\d{2} - \d{2}/\d{2}/\d{2}', value):
        raise ValueError('Unsupported source interval')
    start, end = [datetime.strptime(part, '%m/%d/%y').date() for part in value.split(' - ')]
    if start > end:
        raise ValueError('Reversed source interval')
    return start, end


def verify_source(root, identifier):
    if not re.fullmatch(r'abs-source-[0-9a-f]{12}', identifier):
        raise ValueError('Invalid ABS source ID')
    folder = contained(root, 'data/private/structured/' + identifier)
    receipt = read_json(folder / 'acquisition-complete.json')
    expected = {'issuer-index.html', 'WOART_2025-A_Final_Prospectus.pdf', *FILES}
    if (receipt.get('source_id') != identifier or receipt.get('status') != 'ABS_ISSUER_SOURCE_COMPLETE'
            or receipt.get('deal') != DEAL or receipt.get('issuer_cik') != '0002046523'
            or receipt.get('visibility') != 'private' or receipt.get('public_release_approved') is not False
            or len(receipt.get('files', [])) != 4 or {f['file'] for f in receipt['files']} != expected
            or receipt['script_sha256'] != sha256(root / 'scripts/acquire_worldomni_abs.py')):
        raise ValueError('ABS source contract mismatch')
    for item in receipt['files']:
        path = contained(folder, item['file'])
        url = ('https://www.worldomni.com/asset_securities.html' if item['file'] == 'issuer-index.html'
               else 'https://www.worldomni.com/abs/' + item['file'])
        if item['url'] != url or item['http_status'] != 200 or path.stat().st_size != item['bytes'] or sha256(path) != item['sha256']:
            raise ValueError('ABS source evidence changed')
    return folder, receipt


def derive(root, source_id):
    folder, _ = verify_source(root, source_id)
    raw_rows, metrics, periods = [], [], []
    for filename in FILES:
        book = xlrd.open_workbook(folder / filename, formatting_info=True)
        if book.datemode != 0:
            raise ValueError('Unexpected source date epoch')
        for sheet in book.sheets():
            def label(row):
                return str(sheet.cell_value(row - 1, 0)).strip()
            def require(row, pattern):
                if not re.fullmatch(pattern, label(row)):
                    raise ValueError(f'Unsupported source label at {filename}/{sheet.name}/{row}')
            if label(1) != DEAL or label(2) != 'Monthly Servicer Certificate':
                raise ValueError('Deal/certificate mismatch')
            for row, name in {5:'Dates Covered',6:'Collections Period',7:'Interest Accrual Period',
                10:'Distribution Date',12:'Collateral Pool Balance Data',16:'Principal Payments',
                17:'Defaulted Receivables',18:'Repurchased Accounts',22:'Pool Statistics',
                28:'Delinquent Receivables:',56:'Flow of Funds',64:'Distributions of Available Funds',
                87:'Note Balances & Note Factors',93:'Total Class A, B, & C',
                152:'Interest & Principal Payments',213:'Distribution per $1,000 of Notes',
                272:'Account Balances',274:'Reserve Account'}.items():
                require(row, re.escape(name))
            start, end = date_interval(sheet.cell_value(5, 1))
            accrual_start, accrual_end = date_interval(sheet.cell_value(6, 1))
            year = int(filename[-8:-4])
            if end.year != year or sheet.name != calendar.month_abbr[end.month] or end.day != calendar.monthrange(year, end.month)[1]:
                raise ValueError('Workbook/month/collection date mismatch')
            if start.year != year or start.month != end.month:
                raise ValueError('Collection period crosses month')
            for row in (3, 10):
                if sheet.cell(row - 1, 0 if row == 3 else 1).ctype != xlrd.XL_CELL_DATE:
                    raise ValueError('Expected source date cell')
            report_date = xlrd.xldate_as_datetime(sheet.cell_value(2, 0), book.datemode).date()
            payment = xlrd.xldate_as_datetime(sheet.cell_value(9, 1), book.datemode).date()
            if report_date != end or payment <= end or payment != accrual_end + timedelta(days=1):
                raise ValueError('Report/collection/accrual/payment mismatch')
            previous_end = start.replace(day=1) - timedelta(days=1)
            first = start.isoformat() == '2025-01-03'
            for row, pattern in [(13,'Original Pool Balance' if first else 'Pool Balance at ' + previous_end.strftime('%m/%d/%y')),
                (14,'Original Yield Supplement Overcollateralization Amount' if first else 'Yield Supplement Overcollateralization Amount ' + previous_end.strftime('%m/%d/%y')),
                (15,'Aggregate Starting Principal Balance' if first else 'Receivables Balance ' + previous_end.strftime('%m/%d/%y')),
                (19,'Yield Supplement Overcollateralization Amount at ' + end.strftime('%m/%d/%y')),
                (20,'Pool Balance at ' + end.strftime('%m/%d/%y'))]:
                require(row, re.escape(pattern))
            for row in range(sheet.nrows):
                for col in range(sheet.ncols):
                    cell = sheet.cell(row, col)
                    if cell.ctype == xlrd.XL_CELL_EMPTY:
                        continue
                    if cell.ctype in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE) and not math.isfinite(cell.value):
                        raise ValueError('Nonfinite source cache')
                    xf = book.xf_list[cell.xf_index]
                    record = {'file':filename,'sheet':sheet.name,'row':row+1,'column':col+1,
                        'cell_type':cell.ctype,'raw_value':str(cell.value),
                        'number_format':book.format_map[xf.format_key].format_str}
                    raw_rows.append(record)
            def add(section, key, row, expected, unit='USD', col=2, slot=''):
                require(row, expected)
                cell = sheet.cell(row-1,col-1)
                raw = str(cell.value)
                value, status = scalar(raw, cell.ctype, unit)
                metrics.append({'file':filename,'sheet':sheet.name,'collection_end':end.isoformat(),
                    'section':section,'slot':slot,'metric':key,'unit':unit,'value':value,'status':status,
                    'row':row,'column':col,'label':label(row),'raw_value':raw,'cell_type':cell.ctype})
            pool = [(13,'beginning_pool',r'Original Pool Balance|Pool Balance at .+'),
                (14,'beginning_ysoa',r'(?:Original )?Yield Supplement Overcollateralization Amount.*'),
                (15,'beginning_receivables',r'Aggregate Starting Principal Balance|Receivables Balance .+'),
                (16,'principal_payments','Principal Payments'),(17,'defaulted_receivables','Defaulted Receivables'),
                (18,'repurchased_receivables','Repurchased Accounts'),(19,'ending_ysoa','Yield Supplement Overcollateralization Amount at .+'),
                (20,'ending_pool','Pool Balance at .+'),(25,'original_receivables','Aggregate Starting Principal Balance'),
                (29,'delinquent_31_60','Past Due 31-60 days'),(30,'delinquent_61_90','Past Due 61-90 days'),
                (31,'delinquent_91_120','Past Due 91-120 days'),(32,'delinquent_121_plus',r'Past Due 121\+ days'),
                (33,'delinquent_total','Total'),(39,'recoveries','Recoveries'),
                (40,'net_losses',re.escape('Aggregate Net Losses/(Gains) - '+end.strftime('%B %Y'))),
                (50,'oc_target','Overcollateralization Target Amount'),(51,'oc_actual','Actual Overcollateralization')]
            for row,key,pattern in pool:
                add('pool',key,row,pattern)
                if row in (13,15,16,17,18,20,25,29,30,31,32,33):
                    add('pool',key+'_accounts',row,pattern,'accounts',3)
            for row,key,name,unit in [(8,'days_30_360','30/360 Days','days'),(9,'days_actual_360','Actual/360 Days','days'),
                (23,'pool_factor','Pool Factor','ratio'),(24,'prepayment_abs_speed','Prepayment ABS Speed','ratio'),
                (35,'delinquent_31_plus_ratio',r'Total 31\+ Delinquent as % Aggregate Ending Principal Balance','ratio'),
                (36,'delinquent_61_plus_ratio',r'Total 61\+ Delinquent as % Aggregate Ending Principal Balance','ratio'),
                (37,'delinquency_trigger','Delinquency Trigger Occurred','text'),
                (48,'cumulative_net_loss_ratio','Cumulative Net Loss as a % of Aggregate Starting Principal Balance','ratio'),
                (52,'weighted_contract_rate','Weighted Average Contract Rate','ratio'),
                (53,'yield_adjusted_contract_rate','Weighted Average Contract Rate, Yield Adjusted','ratio'),
                (54,'weighted_remaining_term','Weighted Average Remaining Term','months')]:
                add('pool',key,row,name,unit)
            for row,key,name in [(58,'collections','Collections'),(59,'investment_earnings','Investment Earnings on Cash Accounts'),
                (60,'servicing_fee_signed','Servicing Fee'),(61,'collection_account_transfer','Transfer to Collection Account'),
                (62,'available_funds','Available Funds'),(82,'reported_total_distributions','Total Distributions of Available Funds')]:
                add('flow',key,row,name)
            distribution_labels=[('1','Asset Representation Reviewer Amounts (up to $150,000 per year)'),
                ('2','Class A Interest'),('3',"Noteholders' First Priority Principal Distributable Amount"),
                ('4','Class B Interest'),('5',"Noteholders' Second Priority Principal Distributable Amount"),
                ('6','Class C Interest'),('7',"Noteholders' Third Priority Principal Distributable Amount"),
                ('X','Class D Interest'),('X',"Noteholders' Fourth Priority Principal Distributable Amount"),
                ('X','Class E Interest'),('X',"Noteholders' Fifth Priority Principal Distributable Amount"),
                ('8','Required Reserve Account'),('9',"Noteholders' Principal Distributable Amount"),
                ('10','Asset Representation Reviewer Amounts (in excess of 1)'),('11','Distribution to Certificateholders'),
                ('12','Collection Account Redeposits')]
            for row,(priority,name) in enumerate(distribution_labels,65):
                add('distribution','line_'+str(row),row,re.escape('('+priority+')')+r'\s+'+re.escape(name))
            for row,key,name in [(94,'beginning_balance',r'Original Note Balance|Note Balance @ .+'),
                (95,'principal_paid','Principal Paid'),(96,'ending_balance',r'Note Balance @ .+'),
                (154,'interest_paid','Total Interest Paid'),(155,'total_principal_paid','Total Principal Paid'),
                (156,'total_paid','Total Paid')]:
                add('notes_total',key,row,name)
            for slot,bal,pay in zip(CLASSES,range(98,147,6),(158,164,170,177,183,189,195,201,207)):
                require(bal,re.escape('Class '+slot));require(pay,re.escape('Class '+slot))
                require(bal+1,re.escape('Original Note Balance' if first else 'Note Balance @ '+accrual_start.strftime('%m/%d/%y')))
                require(bal+3,re.escape('Note Balance @ '+payment.strftime('%m/%d/%y')))
                require(bal+4,re.escape('Note Factor @ '+payment.strftime('%m/%d/%y')))
                for offset,key,pattern,unit in [(1,'beginning_balance',r'Original Note Balance|Note Balance @ .+','USD'),
                    (2,'principal_paid','Principal Paid','USD'),(3,'ending_balance',r'Note Balance @ .+','USD'),
                    (4,'note_factor',r'Note Factor @ .+','ratio')]:
                    add('note_slot',key,bal+offset,pattern,unit,slot=slot)
                extra = 1 if slot=='A-2b' else 0
                if extra:
                    add('note_slot','sofr_rate',pay+1,'SOFR Rate','ratio',slot=slot)
                for offset,key,pattern,unit in [(1,'coupon','Coupon','ratio'),(2,'interest_paid','Interest Paid','USD'),
                    (3,'payment_principal','Principal Paid','USD'),(4,'total_paid',re.escape('Total Paid to '+slot+' Holders'),'USD')]:
                    add('note_slot',key,pay+offset+extra,pattern,unit,slot=slot)
            for row,key,name in [(275,'beginning_balance','Balance as of .+'),(276,'investment_earnings','Investment Earnings'),
                (277,'earnings_paid_signed','Investment Earnings Paid'),(278,'deposit_withdrawal',r'Deposit/\(Withdrawal\)'),
                (279,'ending_balance','Balance as of .+'),(280,'change','Change'),(282,'required_reserve','Required Reserve Amount')]:
                add('reserve',key,row,name)
            require(94,re.escape('Original Note Balance' if first else 'Note Balance @ '+accrual_start.strftime('%m/%d/%y')))
            require(96,re.escape('Note Balance @ '+payment.strftime('%m/%d/%y')))
            require(275,re.escape('Balance as of '+accrual_start.strftime('%m/%d/%y')))
            require(279,re.escape('Balance as of '+payment.strftime('%m/%d/%y')))
            periods.append({'file':filename,'sheet':sheet.name,'collection_start':start.isoformat(),'collection_end':end.isoformat(),
                'report_date':report_date.isoformat(),'accrual_start':accrual_start.isoformat(),
                'accrual_end':accrual_end.isoformat(),'distribution_date':payment.isoformat(),
                'source_rows':sheet.nrows,'source_columns':sheet.ncols})
    periods.sort(key=lambda p:p['collection_end'])
    if len(set(p['collection_end'] for p in periods)) != len(periods):
        raise ValueError('Duplicate ABS reporting period')
    checks = reconcile(metrics, periods)
    return raw_rows, metrics, periods, checks


def reconcile(metrics, periods):
    index = {}
    for m in metrics:
        key=(m['collection_end'],m['section'],m['slot'],m['metric'])
        if key in index:
            raise ValueError('Duplicate canonical metric')
        index[key]=m
    checks=[]
    previous=None
    for p in periods:
        end=p['collection_end']
        def n(section,key,slot=''):
            m=index[(end,section,slot,key)]
            if m['status']!='VALUE' or m['value'] is None:
                raise ValueError('Required reconciliation input unavailable')
            return Decimal(m['value'])
        def check(name,delta,tolerance=Decimal('.01')):
            checks.append({'collection_end':end,'check':name,'delta':str(delta),
                'tolerance':str(tolerance),'pass':abs(delta)<=tolerance})
        check('pool_money_rollforward',n('pool','beginning_receivables')-sum(n('pool',k) for k in
            ('principal_payments','defaulted_receivables','repurchased_receivables','ending_ysoa','ending_pool')))
        check('pool_accounts_rollforward',n('pool','beginning_receivables_accounts')-sum(n('pool',k) for k in
            ('principal_payments_accounts','defaulted_receivables_accounts','repurchased_receivables_accounts','ending_pool_accounts')),Decimal(0))
        check('beginning_pool_plus_ysoa',n('pool','beginning_receivables')-n('pool','beginning_pool')-n('pool','beginning_ysoa'))
        check('net_losses',n('pool','defaulted_receivables')-n('pool','recoveries')-n('pool','net_losses'))
        for suffix in ('','_accounts'):
            check('delinquency_detail'+suffix,sum(n('pool',k+suffix) for k in
                ('delinquent_31_60','delinquent_61_90','delinquent_91_120','delinquent_121_plus'))-n('pool','delinquent_total'+suffix),
                Decimal(0) if suffix else Decimal('.01'))
        check('available_funds',sum(n('flow',k) for k in ('collections','investment_earnings','servicing_fee_signed','collection_account_transfer'))-n('flow','available_funds'))
        check('distributions_total',sum(n('distribution','line_'+str(r)) for r in range(65,81))-n('flow','reported_total_distributions'))
        check('cash_conservation',n('flow','available_funds')-n('flow','reported_total_distributions'))
        check('total_note_rollforward',n('notes_total','beginning_balance')-n('notes_total','principal_paid')-n('notes_total','ending_balance'))
        check('total_note_payment',n('notes_total','interest_paid')+n('notes_total','total_principal_paid')-n('notes_total','total_paid'))
        check('distribution_principal_to_notes',sum(n('distribution','line_'+str(r)) for r in (67,69,71,73,75,77))-n('notes_total','total_principal_paid'))
        check('distribution_interest_to_notes',sum(n('distribution','line_'+str(r)) for r in (66,68,70,72,74))-n('notes_total','interest_paid'))
        for row,slots in [(66,CLASSES[:5]),(68,('B',)),(70,('C',)),(72,('D',)),(74,('E',))]:
            check('distribution_interest_line_'+str(row),n('distribution','line_'+str(row))-sum(n('note_slot','interest_paid',s) for s in slots))
        for key,totalkey in [('beginning_balance','beginning_balance'),('ending_balance','ending_balance'),
            ('principal_paid','principal_paid'),('payment_principal','total_principal_paid'),
            ('interest_paid','interest_paid'),('total_paid','total_paid')]:
            check('note_slots_sum_'+key,sum(n('note_slot',key,s) for s in CLASSES)-n('notes_total',totalkey))
        for s in CLASSES:
            check('note_rollforward_'+s,n('note_slot','beginning_balance',s)-n('note_slot','principal_paid',s)-n('note_slot','ending_balance',s))
            check('principal_cross_section_'+s,n('note_slot','principal_paid',s)-n('note_slot','payment_principal',s))
            check('note_payment_'+s,n('note_slot','interest_paid',s)+n('note_slot','payment_principal',s)-n('note_slot','total_paid',s))
        check('reserve_rollforward',n('reserve','beginning_balance')+sum(n('reserve',k) for k in
            ('investment_earnings','earnings_paid_signed','deposit_withdrawal'))-n('reserve','ending_balance'))
        check('reserve_change',n('reserve','ending_balance')-n('reserve','beginning_balance')-n('reserve','change'))
        if previous:
            prior_end=datetime.fromisoformat(previous['collection_end']).date()
            current_start=datetime.fromisoformat(p['collection_start']).date()
            if current_start!=prior_end+timedelta(days=1):
                raise ValueError('Missing/nonadjacent collection period; no inferred continuity')
            for section,begin,finish in [('pool','beginning_pool','ending_pool'),('pool','beginning_ysoa','ending_ysoa'),
                ('pool','beginning_receivables_accounts','ending_pool_accounts'),('notes_total','beginning_balance','ending_balance'),
                ('reserve','beginning_balance','ending_balance')]:
                prior=Decimal(index[(previous['collection_end'],section,'',finish)]['value'])
                check('continuity_'+section+'_'+begin,n(section,begin)-prior,Decimal(0) if 'accounts' in begin else Decimal('.01'))
        previous=p
    return checks


def prepare(root, source_id):
    root=root.resolve()
    raw,metrics,periods,checks=derive(root,source_id)
    identifier='abs-case-'+uuid.uuid4().hex[:12]
    folder=contained(root,'artifacts/private/'+identifier);folder.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(raw,schema=RAW_SCHEMA),folder/'source_cells.parquet',compression='zstd')
    pq.write_table(pa.Table.from_pylist(metrics,schema=METRIC_SCHEMA),folder/'reported_metrics.parquet',compression='zstd')
    receipt={'case_id':identifier,'source_id':source_id,'status':'ABS_REPORTED_CANONICAL_COMPLETE',
        'created_at':timestamp(),'methods':methods(),'reader':'xlrd '+xlrd.__version__,
        'source_receipt_sha256':sha256(root/'data/private/structured'/source_id/'acquisition-complete.json'),
        'files':[{ 'file':f,'sha256':sha256(folder/f),'rows':count } for f,count in
                 [('source_cells.parquet',len(raw)),('reported_metrics.parquet',len(metrics))]],
        'periods':periods,'checks':checks,'failed_checks':sum(not c['pass'] for c in checks),
        'visibility':'private','public_release_approved':False,
        'qualification':{'loan_level':False,'projected_waterfall':False,'terms_validated':False,
                         'formula_recalculated':False,'historical_availability_certified':False},
        'limits':['Reported source values only; checks are accounting reconciliations, not contractual waterfall replay',
                  'D/E are source template slots; source presence does not prove issued tranches',
                  'USD caches normalized to cents only within 0.00001 USD; raw representations retained',
                  'Styled blank cells retained separately; source blank coupon remains NULL']}
    write_new(folder/'case-complete.json',receipt)
    verify_case(root,identifier)
    return receipt


def verify_case(root, identifier):
    if not re.fullmatch(r'abs-case-[0-9a-f]{12}',identifier):
        raise ValueError('Invalid ABS case ID')
    folder=contained(root,'artifacts/private/'+identifier)
    receipt=read_json(folder/'case-complete.json')
    if (receipt.get('case_id')!=identifier or receipt.get('status')!='ABS_REPORTED_CANONICAL_COMPLETE'
        or receipt.get('methods')!=methods() or receipt.get('reader')!='xlrd '+xlrd.__version__
        or receipt.get('visibility')!='private' or receipt.get('public_release_approved') is not False
        or receipt.get('qualification')!={'loan_level':False,'projected_waterfall':False,'terms_validated':False,
            'formula_recalculated':False,'historical_availability_certified':False}):
        raise ValueError('ABS method/qualification mismatch')
    raw,metrics,periods,checks=derive(root,receipt['source_id'])
    if (receipt['source_receipt_sha256']!=sha256(root/'data/private/structured'/receipt['source_id']/'acquisition-complete.json')
        or receipt['periods']!=periods or receipt['checks']!=checks or receipt['failed_checks']!=sum(not c['pass'] for c in checks)):
        raise ValueError('ABS report differs from original source')
    expected=[('source_cells.parquet',raw,RAW_SCHEMA),('reported_metrics.parquet',metrics,METRIC_SCHEMA)]
    if len(receipt.get('files',[]))!=2:
        raise ValueError('ABS canonical files mismatch')
    for item,(name,rows,schema) in zip(receipt['files'],expected):
        path=folder/name
        table=pq.read_table(path)
        if item!={'file':name,'sha256':sha256(path),'rows':len(rows)} or table.schema!=schema or table.to_pylist()!=rows:
            raise ValueError('ABS canonical bytes/schema/values differ')
    return receipt
