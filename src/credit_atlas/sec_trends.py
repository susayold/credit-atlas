"""Comparable annual issuer ratios from an existing verified SEC view."""
from datetime import date
from decimal import Decimal, localcontext
import re
from pathlib import Path
from .workspace import contained, read_json, sha256

RATIOS={'current_ratio':('Current ratio','decimal'),
        'liabilities_assets':('Liabilities / assets','share'),
        'net_income_margin':('Net income / revenue','share'),
        'operating_cashflow_revenue':('Operating cashflow / revenue','share')}


def mapping(statement,ratio):
    r=statement['ratios'][ratio]
    return {field:sorted({(e['taxonomy'],e['concept'],e['unit']) for e in statement['fields'][field]['evidence']})
            for field in (r['numerator'],r['denominator'])}


def comparison(current,prior,ratio):
    result={'baseline_report_date':prior['report_date'] if prior else None,'status':'NO_PRIOR_PERIOD',
            'absolute_delta_exact':None,'relative_delta_exact':None}
    if prior is None:return result
    gap=(date.fromisoformat(current['report_date'])-date.fromisoformat(prior['report_date'])).days
    if not 330<=gap<=400:return {**result,'status':'NOT_ADJACENT_ANNUAL_PERIOD'}
    c,p=current['ratios'][ratio],prior['ratios'][ratio]
    if c['status']!='supported' or p['status']!='supported':return {**result,'status':'UNSUPPORTED_RATIO_INPUT'}
    if mapping(current,ratio)!=mapping(prior,ratio):return {**result,'status':'CONCEPT_MAPPING_CHANGED'}
    for field in (c['numerator'],c['denominator']):
        x,y=current['fields'][field],prior['fields'][field]
        if x['kind']!=y['kind'] or x['unit']!=y['unit']:return {**result,'status':'FIELD_CONTRACT_CHANGED'}
        if x['kind']=='annual_duration':
            days=lambda f:(date.fromisoformat(f['end_date'])-date.fromisoformat(f['start_date'])).days+1
            if abs(days(x)-days(y))>7:return {**result,'status':'ANNUAL_DURATION_CHANGED'}
    with localcontext() as ctx:
        ctx.prec=60
        actual,base=Decimal(c['value_exact']),Decimal(p['value_exact'])
        delta=actual-base
        # Relative movement around zero/negative profit margins is not a growth rate.
        return {**result,'status':'COMPARABLE','absolute_delta_exact':format(delta,'f'),
                'relative_delta_exact':format(delta/base,'f') if base>0 else None,
                'relative_status':'SUPPORTED' if base>0 else 'NONPOSITIVE_BASELINE',
                'baseline_value_exact':p['value_exact'],'baseline_accession':prior['accession'],
                'concept_mapping':mapping(current,ratio),'report_gap_days':gap}


def derive_trend(statements,years):
    groups={}
    for s in statements:groups.setdefault(s['report_date'],[]).append(s)
    periods=[];prior=None
    # One original 10-K per report period; retain amendment/duplicate ambiguity explicitly.
    for period,rs in sorted(groups.items()):
        originals=[s for s in rs if s['form']=='10-K']
        selected=originals[0] if len(originals)==1 else None
        row={'report_date':period,'selection_status':'ONE_ORIGINAL_10K' if selected else 'NO_UNIQUE_ORIGINAL_10K',
             'filings':[{'accession':s['accession'],'form':s['form'],'filing_date':s['filing_date'],'filing_url':s['filing_url']} for s in rs],
             'statement':selected,'baseline_statement':prior,'comparisons':{}}
        if selected:
            row['comparisons']={key:comparison(selected,prior,key) for key in RATIOS}
            for key,c in row['comparisons'].items():c['driver_bridge']=driver_bridge(selected,prior,key,c)
        # Missing/ambiguous period breaks linkage; never skip it to get an older usable value.
        prior=selected
        periods.append(row)
    return periods[-years:]


def driver_bridge(current,prior,ratio,gate=None):
    """Ordered arithmetic attribution; numerator first, denominator second."""
    gate=gate or comparison(current,prior,ratio)
    result={'status':gate['status'],'order':'numerator_then_denominator',
            'numerator_effect_exact':None,'denominator_effect_exact':None,
            'total_change_exact':None,'rounding_residual_exact':None,
            'interpretation':'Arithmetic attribution, not evidence of economic causality.'}
    if gate['status']!='COMPARABLE':return result
    c,p=current['ratios'][ratio],prior['ratios'][ratio]
    numerator,denominator=c['numerator'],c['denominator']
    n1=Decimal(current['fields'][numerator]['value_exact']);n0=Decimal(prior['fields'][numerator]['value_exact'])
    d1=Decimal(current['fields'][denominator]['value_exact']);d0=Decimal(prior['fields'][denominator]['value_exact'])
    if min(d0,d1)<=0:return {**result,'status':'NONPOSITIVE_DENOMINATOR'}
    with localcontext() as ctx:
        ctx.prec=60
        actual,baseline=n1/d1,n0/d0
        counterfactual=n1/d0
        neffect=counterfactual-baseline;deffect=actual-counterfactual
        total=actual-baseline;residual=total-(neffect+deffect)
        return {**result,'status':'SUPPORTED','numerator_field':numerator,'denominator_field':denominator,
                'inputs_exact':{'prior_numerator':str(n0),'current_numerator':str(n1),'prior_denominator':str(d0),'current_denominator':str(d1)},
                'baseline_ratio_exact':format(baseline,'f'),'counterfactual_ratio_exact':format(counterfactual,'f'),
                'current_ratio_exact':format(actual,'f'),'numerator_effect_exact':format(neffect,'f'),
                'denominator_effect_exact':format(deffect,'f'),'total_change_exact':format(total,'f'),
                'rounding_residual_exact':format(residual,'f'),
                'formulas':{'numerator_effect':'N1/D0 - N0/D0','denominator_effect':'N1/D1 - N1/D0','total_change':'N1/D1 - N0/D0'}}


def report(views,identifier,query):
    if set(query)-{'view_id','cik','asof','years'} or query.get('view_id',identifier)!=identifier:
        raise ValueError('Invalid SEC trend filters')
    asof=query.get('asof','2026-10-10')
    if not isinstance(asof,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',asof):raise ValueError('SEC ISO cutoff required')
    date.fromisoformat(asof)
    years=query.get('years','5')
    if years not in {'3','5','10'}:raise ValueError('SEC trend window must be 3, 5 or 10 periods')
    snapshot=views.view(identifier)
    cik=query.get('cik','0000320193');entity=next((e for e in snapshot['entities'] if e['cik']==cik),None)
    if entity is None:raise ValueError('Unknown SEC CIK')
    folder=contained(views.root,'artifacts/private/'+snapshot['case_id'])
    statements=[s for s in read_json(folder/'annual-statements.json') if s['cik']==cik and s['filing_date']<=asof]
    periods=derive_trend(statements,int(years))
    return {'view_id':identifier,'case_id':snapshot['case_id'],'source_id':snapshot['source_id'],'method_source_sha256':sha256(Path(__file__)),
            'filters':{'cik':cik,'asof':asof,'years':years},'entity':entity,'periods':periods,
            'status':'ANNUAL_RATIO_TREND' if periods else 'NO_SOURCE_PERIODS_BEFORE_CUTOFF',
            'ratio_definitions':{k:{'label':label,'unit':unit} for k,(label,unit) in RATIOS.items()},
            'selection_rule':'Exactly one original 10-K per report date; amendments listed separately, not folded into original values. Ambiguous periods break comparison linkage.',
            'comparison_rule':'Adjacent annual report dates 330–400 days apart, supported same-concept USD facts and annual duration difference at most 7 days. Relative delta needs a positive baseline.',
            'qualification':{'historical_availability_qualified':False,'borrower_pd_qualified':False,'dscr_available':False,'covenant_compliance_available':False},
            'source_capture':{'annual_statements_sha256':sha256(folder/'annual-statements.json'),
                              'view_receipt_sha256':sha256(contained(views.root,'artifacts/private/'+identifier+'/view-complete.json'))},
            'limitations':snapshot['limitations']+['Period counts are report periods, not a guarantee of uninterrupted calendar years.',
                'Concept consistency is a comparability screen; accounting restatements/sector differences still require filing review.',
                'Four descriptive ratios do not establish debt-service coverage or covenant compliance.',
                'Driver bridges use numerator-first arithmetic attribution; effects depend on order and do not identify economic causes. Decimal rounding residuals are reported.'],
            'visibility':'private','public_release_approved':False}
