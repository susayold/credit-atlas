"""Filing-specific principal maturity disclosures; no inferred facility schedule."""
from decimal import Decimal,localcontext
from pathlib import Path
import pyarrow.parquet as pq
from .workspace import contained,read_json,sha256

SUFFIXES=[('year_1','Next fiscal year','InNextTwelveMonths'),('year_2','Second fiscal year','InYearTwo'),
          ('year_3','Third fiscal year','InYearThree'),('year_4','Fourth fiscal year','InYearFour'),
          ('year_5','Fifth fiscal year','InYearFive'),('after_5','After fifth fiscal year','AfterYearFive')]
CONCEPTS={
 'debt_only':{key:'LongTermDebtMaturitiesRepaymentsOfPrincipal'+suffix for key,_,suffix in SUFFIXES},
 'debt_and_capital_lease':{key:('LongTermDebtAndCapitalLeaseObligationsRepaymentsOfPrincipalInNextTwelveMonths' if key=='year_1' else 'LongTermDebtAndCapitalLeaseObligationsMaturitiesRepaymentsOfPrincipal'+suffix) for key,_,suffix in SUFFIXES}}


def field(statement,facts,concept):
    candidates=[r for r in facts if r['cik']==statement['cik'] and r['accession']==statement['accession'] and r['taxonomy']=='us-gaap'
                and r['concept']==concept and r['unit']=='USD' and r['start_date'] is None and r['end_date']==statement['report_date']
                and r['filed_date']==statement['filing_date'] and r['form']==statement['form']]
    signatures={Decimal(r['value_exact']) for r in candidates}
    status='missing' if not candidates else 'ambiguous' if len(signatures)!=1 else 'supported'
    return {'concept':concept,'taxonomy':'us-gaap','unit':'USD','status':status,
            'value_exact':candidates[0]['value_exact'] if status=='supported' else None,
            'end_date':statement['report_date'],'start_date':None,
            'evidence':[{k:r[k] for k in ['taxonomy','concept','unit','source_ordinal','start_date','end_date','value_exact','filed_date','form','accession']} for r in candidates]}


def summarize(buckets):
    supported=[b for b in buckets if b['field']['status']=='supported']
    negative=any(Decimal(b['field']['value_exact'])<0 for b in supported)
    complete=len(supported)==len(buckets) and bool(buckets) and not negative
    with localcontext() as ctx:
        ctx.prec=80
        subtotal=sum((Decimal(b['field']['value_exact']) for b in supported),Decimal(0))
        positive=complete and subtotal>0
        for b in buckets:b['share_of_disclosed_schedule_exact']=format(Decimal(b['field']['value_exact'])/subtotal,'f') if positive else None
        first_three=sum((Decimal(b['field']['value_exact']) for b in buckets if b['bucket'] in ['year_1','year_2','year_3'] and b['field']['status']=='supported'),Decimal(0))
        return {'status':'INVALID_NEGATIVE_BUCKET' if negative else 'COMPLETE_ZERO_SCHEDULE' if complete and subtotal==0 else 'COMPLETE_DISCLOSED_SCHEDULE' if complete else 'PARTIAL_DISCLOSED_SCHEDULE',
                'supported_buckets':len(supported),'requested_buckets':len(buckets),
                'supported_subtotal_exact':format(subtotal,'f') if supported else None,
                'disclosed_schedule_total_exact':format(subtotal,'f') if complete else None,
                'first_three_years_share_exact':format(first_three/subtotal,'f') if positive else None,
                'largest_buckets':[b['bucket'] for b in buckets if Decimal(b['field']['value_exact'])==max(Decimal(x['field']['value_exact']) for x in buckets)] if positive else [],
                'total_definition':'Sum of the six selected disclosed principal buckets; not total balance-sheet debt, debt service, EAD or present value.'}


def report(views,identifier,query):
    if set(query)-{'view_id','cik','accession','asof','debt_scope'}:raise ValueError('Invalid SEC maturity filters')
    scope=query.get('debt_scope','debt_only')
    if scope not in CONCEPTS:raise ValueError('Explicit supported SEC maturity scope required')
    source=views.report(identifier,{k:v for k,v in query.items() if k!='debt_scope'})
    folder=contained(views.root,'artifacts/private/'+source['case_id']);facts=pq.read_table(folder/'facts.parquet').to_pylist()
    definitions=read_json(folder/'concepts.json')[source['filters']['cik']]
    statement=source['statement'];buckets=[]
    for key,label,_ in SUFFIXES:
        tag=CONCEPTS[scope][key]
        f=field(statement,facts,tag) if statement else {'concept':tag,'taxonomy':'us-gaap','unit':'USD','status':'no_selected_statement','value_exact':None,'start_date':None,'end_date':None,'evidence':[]}
        buckets.append({'bucket':key,'label':label,'field':f,'definition':definitions.get('us-gaap:'+tag,{'label':None,'description':None,'units':[]})})
    summary=summarize(buckets)
    return {'view_id':identifier,'case_id':source['case_id'],'source_id':source['source_id'],'entity':source['entity'],
            'filters':{**source['filters'],'debt_scope':scope},'statement':{k:statement[k] for k in ['cik','accession','report_date','filing_date','form','filing_url']} if statement else None,
            'buckets':buckets,'summary':summary,'method_source_sha256':sha256(Path(__file__)),
            'source_capture':{'facts_sha256':sha256(folder/'facts.parquet'),'concepts_sha256':sha256(folder/'concepts.json'),
                              'annual_statements_sha256':sha256(folder/'annual-statements.json'),'view_receipt_sha256':sha256(contained(views.root,'artifacts/private/'+identifier+'/view-complete.json'))},
            'selection_rule':'Exact selected filing CIK/accession/form/filed date, report-end instant, USD and explicit concept family. No older filing, duration fact, rolling tag or lease/debt-family fallback.',
            'qualification':{'facility_schedule_available':False,'interest_payment_schedule_available':False,'dscr_available':False,'covenant_compliance_available':False,'historical_availability_qualified':False},
            'limitations':source['limitations']+['Buckets follow the source fiscal-year definitions; they are not exact payment dates or automatically rolling calendar-year buckets.',
                'A complete six-bucket disclosure does not establish full debt completeness, carrying-value reconciliation, facility identity or committed refinancing.',
                'Principal maturities exclude inferred interest payments and cash available for debt service. No DSCR or cash shortfall is inferred.',
                'After-year-five is open ended; no invented payment date, average maturity or duration.',
                'Debt-only and debt/capital-lease families stay separate; missing or ambiguous buckets are not zero. Negative buckets block totals/shares.'],
            'visibility':'private','public_release_approved':False}
