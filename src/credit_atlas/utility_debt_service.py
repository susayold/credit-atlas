"""Issuer-reported utility debt service, separate lien scopes and rounding evidence."""
import re
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_HALF_UP
from .workspace import contained,read_json,sha256

SOURCE='utility-debt-source-51fc6939e77e'
RECEIPT='422e0503926a71b4f0944b606e9d0bd86f0952b039599bd8f2a48d4677387a48'
PROFILE='utility-debt-profile-9b7023d435f2'
PROFILE_SHA='7f159bed4a7e979f8c3afc98d623e8f8aa8c9c46b95920926dec2a9ff5bfacba'

def context(root):
    folder=contained(root,'data/private/business/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('Utility receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for s in receipt['sources']:
        p=contained(folder,s['file'])
        if p.stat().st_size!=s['bytes'] or sha256(p)!=s['sha256']:raise ValueError('Utility source changed')
    return folder,receipt

def values(text,start,end):
    starts=list(re.finditer(re.escape(start)+r'(?!\s+COVERAGE)',text))
    if len(starts)!=1:raise ValueError('Ambiguous utility source label: '+start)
    segment=text[starts[0].end():]
    if end not in segment:raise ValueError('Missing utility source end: '+end)
    segment=segment.split(end,1)[0]
    segment=re.sub(r'^\s*\(\d+\)\s*:?', '',segment)
    segment=re.sub(r'(?<=\d)\(\d{1,2}\)','',segment)
    matches=re.findall(r'\(?-?\d[\d,]*(?:\.\d+)?\)?',segment)
    if len(matches)!=5:raise ValueError('Expected five annual source cells: '+start)
    return [str(-Decimal(v[1:-1].replace(',','')) if v.startswith('(') and v.endswith(')') else Decimal(v.replace(',',''))) for v in matches]

def parse_continuing(text,system,edition,physical_page):
    t=' '.join(text.split());prefix='WATER' if system=='water' else 'WASTEWATER'
    if f'TABLE {7 if system=="water" else 13}:' not in t or prefix+' SYSTEM HISTORICAL OPERATING RESULTS' not in t:raise ValueError('Wrong source table identity')
    years=re.search(r'FISCAL YEARS (\d{4}) THROUGH (\d{4})',t)
    if not years or int(years[2])!=edition or int(years[1])!=edition-4:raise ValueError('Unexpected source years')
    # Labels differ between Water and Wastewater; every distinction is explicit.
    revenue_total='TOTAL WATER REVENUES' if system=='water' else 'TOTAL WASTEWATER REVENUE'
    revenue_after=prefix+' REVENUES AFTER RATE STABILIZATION TRANSFER'
    maintenance='TOTAL '+prefix+' OPERATION '+('&' if system=='wastewater' else '&')+' MAINTENANCE COSTS'
    total_debt='TOTAL PARITY AND SUBORDINATE DEBT SERVICE'
    total_ratio=('TOTAL ' if system=='water' else '')+'PARITY AND SUBORDINATE DEBT SERVICE COVERAGE'
    end='________________' if system=='water' else '(1) Calculated'
    anchors={
      'revenue_before_transfers':(revenue_total,'RATE STABILIZATION FUND'),
      'stabilization_deposits':('Deposits to the Rate Stabilization Fund','Withdrawals from Rate Stabilization'),
      'stabilization_withdrawals':('Fund for Inclusion in Revenues',revenue_after),
      'revenue_after_transfers':(revenue_after,prefix+' OPERATION & MAINTENANCE COSTS'),
      'operating_expenses':('Operating Expenses','(Less Tax Receipts)'),
      'tax_expense_offset':('(Less Tax Receipts)',maintenance),
      'operation_maintenance':(maintenance,'NET '+prefix+' REVENUES'),
      'net_revenues':('NET '+prefix+' REVENUES','PARITY DEBT SERVICE'),
      'parity_debt_service':('TOTAL PARITY DEBT SERVICE','PARITY DEBT SERVICE COVERAGE'),
      'reported_parity_dscr':('PARITY DEBT SERVICE COVERAGE','SUBORDINATE '+prefix+' SYSTEM'),
      'subordinate_debt_service':('DEBT SERVICE'+('(11)' if system=='water' else '(7)'),total_debt),
      'total_debt_service':(total_debt,total_ratio),
      'reported_total_dscr':(total_ratio,end)}
    fields={key:values(t,*bounds) for key,bounds in anchors.items()}
    rows=[]
    for i,year in enumerate(range(edition-4,edition+1)):
        row={'edition':edition,'system':system,'year':year,'file':f'ebmud-continuing-{edition}.pdf',
             'physical_page':physical_page,'table':7 if system=='water' else 13,
             'unit':'USD; reported ratios in times','values':{k:v[i] for k,v in fields.items()},
             'statement_type':'Unaudited continuing disclosure; issuer-reported indenture calculations'}
        v={k:Decimal(x) for k,x in row['values'].items()}
        with localcontext() as ctx:
            ctx.prec=50
            ratio=v['net_revenues']/v['parity_debt_service'];total=v['net_revenues']/v['total_debt_service']
            row['checks']={
                'revenue_bridge_residual_usd':str(v['revenue_after_transfers']-v['revenue_before_transfers']-v['stabilization_deposits']-v['stabilization_withdrawals']),
                'maintenance_bridge_residual_usd':str(v['operation_maintenance']-v['operating_expenses']-v['tax_expense_offset']),
                'net_revenue_bridge_residual_usd':str(v['net_revenues']-v['revenue_after_transfers']+v['operation_maintenance']),
                'debt_service_bridge_residual_usd':str(v['total_debt_service']-v['parity_debt_service']-v['subordinate_debt_service']),
                'recomputed_parity_dscr_decimal50':str(ratio),'recomputed_total_dscr_decimal50':str(total),
                'parity_matches_reported_2dp':ratio.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)==v['reported_parity_dscr'],
                'total_matches_reported_2dp':total.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)==v['reported_total_dscr']}
        rows.append(row)
    return rows

def parse_acfr(text,system,edition,physical_page):
    t=' '.join(text.split())
    if 'Ten-Year Summary of Net Revenue and Debt Service Coverage' not in t or ('Water System' if system=='water' else 'Wastewater System') not in t or '(in Millions)' not in t:raise ValueError('Wrong ACFR table identity')
    # Isolate table cells from notes; optional source footnote after year.
    body=t.split('(1) Gross Revenue',1)[0].replace('$','')
    number=r'(\d+\.\d+)'
    pattern=r'(?<!\d)(20\d{2})(?:\s*\(\d+\))?\s+'+r'\s+'.join([number]*5)
    cells=re.findall(pattern,body)
    if len(cells)!=10 or {int(r[0]) for r in cells}!=set(range(edition-9,edition+1)):raise ValueError('Incomplete ten-year ACFR table')
    return [{'edition':edition,'system':system,'year':int(r[0]),'file':f'ebmud-acfr-{edition}.pdf','physical_page':physical_page,
             'statement_type':'Unaudited statistical section of ACFR; historical reported values',
             'unit':'USD million; source rounded amounts, reported ratios in times',
             'values':dict(zip(['revenue_after_transfers','operation_maintenance','net_revenues','parity_debt_service','reported_parity_dscr'],r[1:]))}
            for r in cells]


def dscr_driver(current,prior,basis):
    """Exact numerator-first accounting bridge, separate from causal inference."""
    if basis not in {'parity','total'}:raise ValueError('Invalid DSCR driver basis')
    if prior is None:return {'status':'NO_PRIOR_CALENDAR_YEAR','basis':basis,'effects':[],'baseline':None}
    if current['year']!=prior['year']+1 or current['edition']!=prior['edition'] or current['system']!=prior['system']:
        raise ValueError('DSCR driver requires adjacent years in the same source edition/system')
    denominator=basis+'_debt_service'
    a={k:Fraction(v) for k,v in current['values'].items()};b={k:Fraction(v) for k,v in prior['values'].items()}
    if a[denominator]<=0 or b[denominator]<=0:raise ValueError('DSCR driver needs positive debt-service denominators')
    n1,n0=a['net_revenues'],b['net_revenues'];d1,d0=a[denominator],b[denominator]
    r1,r0=a['revenue_after_transfers'],b['revenue_after_transfers'];m1,m0=a['operation_maintenance'],b['operation_maintenance']
    e1,e0=n1-r1+m1,n0-r0+m0
    def exact(value):
        with localcontext() as ctx:
            ctx.prec=50
            return {'numerator':str(value.numerator),'denominator':str(value.denominator),
                    'decimal50':str(Decimal(value.numerator)/Decimal(value.denominator))}
    def effect(key,label,delta,value):return {'key':key,'label':label,'source_change_usd':str(delta.numerator) if delta.denominator==1 else None,'effect_times':exact(value)}
    effects=[effect('revenue','Revenue after stabilization',(r1-r0),(r1-r0)/d0),
             effect('maintenance','Operation & maintenance',(m1-m0),-(m1-m0)/d0),
             effect('source_residual','Source net-revenue bridge residual',(e1-e0),(e1-e0)/d0),
             effect('debt_service','Selected debt-service denominator',(d1-d0),n1/d1-n1/d0)]
    total=sum((Fraction(int(x['effect_times']['numerator']),int(x['effect_times']['denominator'])) for x in effects),Fraction(0))
    delta=n1/d1-n0/d0
    if total!=delta:raise ValueError('DSCR driver reconciliation failed')
    return {'status':'SUPPORTED_ADJACENT_YEAR_BRIDGE','basis':basis,'unit':'DSCR times; source changes in USD',
        'method':'Revenue, maintenance and source residual at prior debt service, then denominator at current net revenues; order dependent accounting attribution, not causal explanation',
        'baseline':{'year':prior['year'],'file':prior['file'],'physical_page':prior['physical_page'],'values':prior['values']},
        'current':{'year':current['year'],'file':current['file'],'physical_page':current['physical_page'],'values':current['values']},
        'prior_ratio':exact(n0/d0),'numerator_first_counterfactual_ratio':exact(n1/d0),'current_ratio':exact(n1/d1),
        'ratio_change':exact(delta),'effects':effects,'sum_effects':exact(total),'exact_residual':exact(delta-total),
        'reconciles_exactly':True,'causal_attribution_qualified':False,'legal_compliance_qualified':False}


def report(root,query):
    """Source-bound historical assessment; never infer covenant compliance."""
    if set(query)-{'edition','year','system','basis'} or any(not isinstance(v,str) for v in query.values()):
        raise ValueError('Invalid utility debt scope')
    edition=query.get('edition','2025');year=query.get('year',edition)
    system=query.get('system','water');basis=query.get('basis','total')
    if edition not in {'2024','2025'} or not re.fullmatch(r'20\d{2}',year) or system not in {'water','wastewater'} or basis not in {'parity','total'}:
        raise ValueError('Invalid utility debt scope')
    edition=int(edition);year=int(year)
    if not edition-4<=year<=edition:raise ValueError('Year outside utility edition')
    _,receipt=context(root)
    path=contained(root,'artifacts/private/'+PROFILE+'/profile.json')
    if sha256(path)!=PROFILE_SHA:raise ValueError('Utility normalized profile changed')
    doc=read_json(path)
    rows=sorted([r for r in doc['continuing_rows'] if r['edition']==edition and r['system']==system],key=lambda r:r['year'])
    current=next(r for r in rows if r['year']==year)
    prior=next((r for r in rows if r['year']==year-1),None)
    previous_edition=next((r for r in doc['continuing_rows'] if r['edition']==edition-1 and r['system']==system and r['year']==year),None)
    ratio_key='recomputed_'+basis+'_dscr_decimal50'
    denominator=basis+'_debt_service'
    comparisons=[]
    for r in doc['acfr_rounded_rows']:
        if r['system']!=system or r['year']!=year:continue
        for field,rounded in r['values'].items():
            if field=='reported_parity_dscr':
                derived=current['values'][field];unit='times'
            else:
                derived=str((Decimal(current['values'][field])/Decimal(1000000)).quantize(Decimal('.1'),rounding=ROUND_HALF_UP));unit='USD million rounded to 0.1'
            comparisons.append({'acfr_edition':r['edition'],'field':field,'acfr_source_value':rounded,
                'continuing_value_at_acfr_precision':derived,'matches':Decimal(rounded)==Decimal(derived),
                'unit':unit,'file':r['file'],'physical_page':r['physical_page']})
    driver=dscr_driver(current,prior,basis)
    delta=driver['ratio_change']['decimal50'] if prior else None
    from .utility_contracts import report as contract_report
    legal=contract_report(root,system)
    return {'issuer':'East Bay Municipal Utility District','edition':edition,'year':year,'system':system,'basis':basis,
        'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'profile_sha256':PROFILE_SHA,
        'sources':receipt['sources'],'selected':current,'timeline':rows,
        'numerator_field':'net_revenues','denominator_field':denominator,
        'actual_dscr_decimal50':current['checks'][ratio_key],
        'reported_dscr':current['values']['reported_'+basis+'_dscr'],
        'prior_year_dscr_decimal50':prior['checks'][ratio_key] if prior else None,'year_change_decimal50':delta,
        'previous_edition_same_year':previous_edition,'acfr_precision_comparisons':comparisons,'dscr_driver':driver,
        'source_page_evidence':[e for e in doc['source_page_evidence'] if e['file']==current['file'] and e['system']==system],
        'threshold':None,'headroom':None,'compliance':None,'legal_evidence':legal,
        'contractual_compliance_qualified':False,'borrower_pd_lgd_calibrated':False,
        'original_publication_vintages_complete':False,'visibility':'private','public_release_approved':False,
        'limitations':['Unaudited issuer-reported historical calculations, not an independent financial-statement audit.',
            'Parity and total debt-service denominators are distinct; no EBIT/interest substitution.',
            'Raw one-dollar bridge residuals and cross-document differences are retained.',
            'ACFR statistical tables use rounded million-dollar amounts; no invented dollar precision.',
            'Full indenture/amendment chain and applicable test requirements have not been qualified.',
            'Municipal utility case; does not establish corporate or mortgage model qualification.']}
