"""Explicit concept annual coverage proxies from verified SEC facts."""
from datetime import date
from decimal import Decimal,localcontext
from pathlib import Path
import pyarrow.parquet as pq
from .sec_trends import report as trend_report
from .workspace import contained,read_json,sha256

INTEREST_CONCEPTS=('InterestExpenseNonoperating','InterestExpense','InterestExpenseDebt')


def field(statement,facts,concept):
    candidates=[r for r in facts if r['cik']==statement['cik'] and r['accession']==statement['accession'] and r['taxonomy']=='us-gaap' and r['concept']==concept and r['unit']=='USD' and r['end_date']==statement['report_date'] and r['filed_date']==statement['filing_date'] and r['form']==statement['form'] and r['start_date'] is not None and 330<=(date.fromisoformat(r['end_date'])-date.fromisoformat(r['start_date'])).days+1<=400]
    signatures={(r['start_date'],r['end_date'],Decimal(r['value_exact'])) for r in candidates}
    status='missing' if not candidates else 'ambiguous' if len(signatures)!=1 else 'supported'
    return {'concept':concept,'taxonomy':'us-gaap','unit':'USD','status':status,
            'value_exact':candidates[0]['value_exact'] if status=='supported' else None,
            'start_date':candidates[0]['start_date'] if status=='supported' else None,'end_date':statement['report_date'],
            'evidence':[{k:r[k] for k in ('taxonomy','concept','unit','source_ordinal','start_date','end_date','value_exact','filed_date','form','accession')} for r in candidates]}


def ratio(n,d):
    status='supported'
    if n['status']!='supported' or d['status']!='supported':status='missing_or_ambiguous_input'
    elif (n['start_date'],n['end_date'])!=(d['start_date'],d['end_date']):status='period_mismatch'
    elif Decimal(d['value_exact'])<=0:status='nonpositive_interest_expense'
    with localcontext() as ctx:
        ctx.prec=60
        value=format(Decimal(n['value_exact'])/Decimal(d['value_exact']),'f') if status=='supported' else None
    return {'status':status,'value_exact':value,'unit':'times','formula':n['concept']+' / '+d['concept']}


def report(views,key,query):
    if set(query)-{'view_id','cik','asof','years','interest_concept'}:raise ValueError('Invalid SEC coverage filters')
    concept=query.get('interest_concept','InterestExpenseNonoperating')
    if concept not in INTEREST_CONCEPTS:raise ValueError('Explicit supported interest expense concept required')
    trend=trend_report(views,key,{k:v for k,v in query.items() if k!='interest_concept'})
    folder=contained(views.root,'artifacts/private/'+trend['case_id'])
    facts=pq.read_table(folder/'facts.parquet').to_pylist()
    definitions=read_json(folder/'concepts.json')[trend['filters']['cik']]
    periods=[]
    for p in trend['periods']:
        s=p['statement'];fields={}
        if s:
            fields={name:field(s,facts,tag) for name,tag in [('operating_income','OperatingIncomeLoss'),('operating_cashflow','NetCashProvidedByUsedInOperatingActivities'),('interest_expense',concept),('interest_paid','InterestPaid'),('interest_paid_net','InterestPaidNet')]}
            ratios={name:ratio(fields[n],fields['interest_expense']) for name,n in [('operating_income_coverage','operating_income'),('reported_ocf_coverage','operating_cashflow')]}
        else:ratios={name:{'status':'no_unique_original_statement','value_exact':None,'unit':'times'} for name in ['operating_income_coverage','reported_ocf_coverage']}
        periods.append({'report_date':p['report_date'],'selection_status':p['selection_status'],'filings':p['filings'],
                        'accession':s['accession'] if s else None,'filing_date':s['filing_date'] if s else None,
                        'fields':fields,'ratios':ratios})
    tags=['OperatingIncomeLoss','NetCashProvidedByUsedInOperatingActivities',concept,'InterestPaid','InterestPaidNet']
    return {'view_id':key,'case_id':trend['case_id'],'source_id':trend['source_id'],'entity':trend['entity'],'method_source_sha256':sha256(Path(__file__)),
            'filters':{**trend['filters'],'interest_concept':concept},'periods':periods,
            'concept_definitions':{tag:definitions.get('us-gaap:'+tag,{'label':None,'description':None,'units':[]}) for tag in tags},
            'support':{'report_periods':len(periods),'supported_operating_income_coverage':sum(p['ratios']['operating_income_coverage']['status']=='supported' for p in periods),'supported_reported_ocf_coverage':sum(p['ratios']['reported_ocf_coverage']['status']=='supported' for p in periods)},
            'selection_rule':trend['selection_rule'],
            'concept_rule':'Selected expense concept is explicit; no fallback, summing aliases, netting interest income or substituting cash interest paid.',
            'qualification':{'standard_ebit_icr_qualified':False,'dscr_available':False,'covenant_compliance_available':False,'issuer_pd_qualified':False,'historical_availability_qualified':False},
            'source_capture':{**trend['source_capture'],'facts_sha256':sha256(folder/'facts.parquet'),'concepts_sha256':sha256(folder/'concepts.json')},
            'references':[{'title':'Federal Reserve: EBIT interest coverage definition','url':'https://www.federalreserve.gov/econres/notes/feds-notes/information-in-interest-coverage-ratios-of-the-us-nonfinancial-corporate-sector-20190110.html'},
                          {'title':'SEC XBRL APIs','url':'https://www.sec.gov/search-filings/edgar-application-programming-interfaces'}],
            'limitations':trend['limitations']+['Operating income proxy excludes nonoperating items; it is not automatically contractual EBIT/EBITDA.',
                'Reported OCF may already reflect interest payments under source accounting policy; no add-back or debt-service cash availability is inferred.',
                'InterestPaid and InterestPaidNet have different capitalized-interest/classification conventions and remain separate observations.',
                'Negative supported numerators are retained. Missing/ambiguous/nonpositive expense denominators remain unavailable.',
                'Consolidated captive-finance operations can make industrial-company coverage comparisons misleading; inspect issuer scope and filing notes.'],
            'visibility':'private','public_release_approved':False}
