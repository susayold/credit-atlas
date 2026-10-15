"""Managed retail source projection; stocks and unspecified-duration flows stay separate."""
from datetime import date, timedelta
from decimal import Decimal, localcontext
from .pool_history import verified_source, workbook, SOURCE_ID, RECEIPT_SHA

FIELDS = {
    'receivables': (5, 'USD_thousands', 'stock'),
    'average_portfolio': (6, 'USD_thousands', 'period_average'),
    'contracts': (8, 'contracts', 'stock'),
    'average_contracts': (10, 'contracts', 'period_average'),
    'repossessions': (12, 'contracts', 'flow'),
    'reported_repos_rate': (14, 'fraction', 'reported_rate'),
    'gross_chargeoffs': (17, 'USD_thousands', 'flow'),
    'recoveries_signed': (18, 'USD_thousands', 'flow'),
    'net_chargeoffs': (19, 'USD_thousands', 'flow'),
    'reported_net_loss_rate': (22, 'fraction', 'reported_rate'),
}
for prefix, start, unit, kind in [('delinq_count',31,'contracts','stock'),
                                 ('reported_count_rate',38,'fraction','reported_rate'),
                                 ('delinq_amount',45,'USD_thousands','stock'),
                                 ('reported_amount_rate',52,'fraction','reported_rate')]:
    for offset, bucket in enumerate(['31_60','61_90','91_120','121_plus','total']):
        FIELDS[prefix+'_'+bucket] = (start+offset,unit,kind)


def project(sheets):
    if len(sheets)!=1: raise ValueError('Managed sheet inventory changed')
    sheet,cells=next(iter(sheets.items()))
    if cells['A1']['value']!='Historical Net Loss Experience - Retail' or cells['A2']['value']!='(Dollar Amount in Thousands)':
        raise ValueError('Managed source title/units changed')
    if cells['C3']['value']!='At June 30,' or cells['E3']['value']!='For the 12 months ended':
        raise ValueError('Managed period headers changed')
    periods=[]
    with localcontext() as ctx:
        ctx.prec=50
        for col in 'CDEFGHI':
            serial=Decimal(cells[col+'26']['value'])
            if serial!=serial.to_integral_value():raise ValueError('Invalid source date')
            end=date(1899,12,30)+timedelta(days=int(serial))
            year=int(cells[col+'4']['value'].strip())
            if end.year!=year or (end.month,end.day)!=((6,30) if col in 'CD' else (12,31)):
                raise ValueError('Managed source dates disagree')
            values={};checks=[]
            for key,(row,unit,kind) in FIELDS.items():
                coord=col+str(row);cell=cells.get(coord,{})
                raw=cell.get('value')
                if raw is not None:
                    if cell.get('type')!='n':raise ValueError('Non-numeric managed value')
                    value=Decimal(raw)
                    if not value.is_finite():raise ValueError('Non-finite managed value')
                    if unit=='fraction' and not 0<=value<=1:raise ValueError('Invalid managed fraction')
                    if key=='recoveries_signed' and value>0:raise ValueError('Recovery sign changed')
                    if key!='recoveries_signed' and value<0:raise ValueError('Negative managed value')
                values[key]={'value_exact':raw,'status':'VALUE' if raw is not None else 'SOURCE_BLANK',
                    'unit':unit,'kind':kind,'sheet':sheet,'cell':coord,
                    'source_label':cells.get('A'+str(row),{}).get('value'), 'cached_formula':cell.get('formula')}
            def val(key):
                raw=values[key]['value_exact'];return Decimal(raw) if raw is not None else None
            def check(name, keys, calculated, reported, tolerance):
                ready=all(val(k) is not None for k in keys) and reported is not None
                delta=calculated-reported if ready else None
                checks.append({'name':name,'input_cells':[values[k]['cell'] for k in keys],
                    'calculated_exact':str(calculated) if ready else None,
                    'reported_exact':str(reported) if reported is not None else None,
                    'delta_exact':str(delta) if delta is not None else None,'tolerance_exact':str(tolerance),
                    'status':'PASS' if ready and abs(delta)<=tolerance else 'DIFFERENCE' if ready else 'UNAVAILABLE'})
            for key,row in [('receivables',27),('contracts',28)]:
                raw=cells.get(col+str(row),{}).get('value')
                check('duplicate_'+key,[key],val(key),Decimal(raw) if raw is not None else None,Decimal(0))
            for prefix,tol in [('delinq_count',Decimal(0)),('delinq_amount',Decimal('0.000001'))]:
                keys=[prefix+'_'+b for b in ['31_60','61_90','91_120','121_plus']]
                check(prefix+'_sum',keys,sum((val(k) or Decimal(0)) for k in keys),val(prefix+'_total'),tol)
            keys=['gross_chargeoffs','recoveries_signed','net_chargeoffs']
            check('net_loss_bridge',keys,(val(keys[0]) or Decimal(0))+(val(keys[1]) or Decimal(0)),val(keys[2]),Decimal('0.000001'))
            for prefix,rate,denom in [('delinq_count','reported_count_rate','contracts'),('delinq_amount','reported_amount_rate','receivables')]:
                for bucket in ['31_60','61_90','91_120','121_plus','total']:
                    keys=[prefix+'_'+bucket,denom,rate+'_'+bucket]
                    denominator=val(denom)
                    calc=val(keys[0])/denominator if denominator and val(keys[0]) is not None else None
                    check(rate+'_'+bucket,keys,calc,val(keys[2]),Decimal('0.000050000000001')) if calc is not None else checks.append({'name':rate+'_'+bucket,'status':'UNAVAILABLE'})
            ratios={}
            for name,num,denom in [('period_net_loss_fraction','net_chargeoffs','average_portfolio'),('period_repos_fraction','repossessions','average_contracts')]:
                n,d=val(num),val(denom)
                ratios[name]={'value_exact':str(n/d) if n is not None and d else None,
                    'input_cells':[values[num]['cell'],values[denom]['cell']],
                    'annualized':False,'flow_duration_qualified':col not in 'CD'}
            periods.append({'column':col,'end_date':end.isoformat(),'header_year':year,
                'flow_period':'publisher duration unspecified' if col in 'CD' else '12 months ended',
                'values':values,'checks':checks,'derived_ratios':ratios})
    return periods


def report(root,query):
    if query:raise ValueError('Managed pool supports source inventory only; no scope filters')
    folder,receipt=verified_source(root)
    periods=project(workbook(folder/'ManagedPool-Retail.xlsx'))
    return {'source_id':SOURCE_ID,'source_receipt_sha256':RECEIPT_SHA,'source':receipt,
        'periods':periods,'field_count':len(FIELDS),
        'limitations':['Dollar amounts remain USD thousands; no silent conversion to dollars.',
            'June columns say At June 30. Flow start/duration and annualization convention are not qualified; raw derived fractions are never annualized.',
            'Reported rates retained separately from recomputed raw fractions. Rounded delinquency rates use 0.005 percentage-point tolerance.',
            'Recoveries are signed negative; net losses = gross charge-offs + signed recoveries. This is not loan-level LGD.',
            'Stock balances across dates must not be summed. Duplicate receivable/contract disclosures used only for reconciliation.',
            'Workbook caches not recalculated; not a representative borrower dataset, PD model or forecast.'],
        'source_notes':[{'cell':key,'text':cells['value']} for key,cells in next(iter(workbook(folder/'ManagedPool-Retail.xlsx').values())).items() if key in ('A57','A58')],
        'visibility':'private','public_release_approved':False}
