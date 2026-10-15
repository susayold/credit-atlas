"""Full saved ratio arithmetic and independent source-period HTTP trend gates."""
import json
from collections import Counter,defaultdict
from datetime import date
from decimal import Decimal,localcontext
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4
from credit_atlas.workspace import read_json,sha256,write_new

DEFINITIONS={'current_ratio':('current_assets','current_liabilities',False),
 'liabilities_assets':('liabilities','assets',False),'net_income_margin':('net_income','revenue',True),
 'operating_cashflow_revenue':('operating_cashflow','revenue',True)}


def dec_ratio(n,d):
    fraction=Fraction(n)/Fraction(d)
    with localcontext() as c:
        c.prec=60
        return Decimal(fraction.numerator)/Decimal(fraction.denominator)


def field_mapping(s,key):
    n,d,_=DEFINITIONS[key]
    return {f:sorted({(e['taxonomy'],e['concept'],e['unit']) for e in s['fields'][f]['evidence']}) for f in [n,d]}


def gate(current,previous,key):
    if previous is None:return 'NO_PRIOR_PERIOD'
    gap=(date.fromisoformat(current['report_date'])-date.fromisoformat(previous['report_date'])).days
    if gap<330 or gap>400:return 'NOT_ADJACENT_ANNUAL_PERIOD'
    if any(s['ratios'][key]['status']!='supported' for s in [current,previous]):return 'UNSUPPORTED_RATIO_INPUT'
    if field_mapping(current,key)!=field_mapping(previous,key):return 'CONCEPT_MAPPING_CHANGED'
    for f in DEFINITIONS[key][:2]:
        x=current['fields'][f];y=previous['fields'][f]
        if (x['kind'],x['unit'])!=(y['kind'],y['unit']):return 'FIELD_CONTRACT_CHANGED'
        if x['kind']=='annual_duration':
            length=lambda v:(date.fromisoformat(v['end_date'])-date.fromisoformat(v['start_date'])).days+1
            if abs(length(x)-length(y))>7:return 'ANNUAL_DURATION_CHANGED'
    return 'COMPARABLE'


def check_change(row,current,previous,key):
    expected=gate(current,previous,key);assert row['status']==expected
    assert row['baseline_report_date']==(previous['report_date'] if previous else None)
    bridge=row['driver_bridge'];assert bridge['order']=='numerator_then_denominator'
    if expected!='COMPARABLE':
        assert row['absolute_delta_exact'] is row['relative_delta_exact'] is None
        assert bridge['status']==expected and bridge['numerator_effect_exact'] is bridge['denominator_effect_exact'] is None
        return False
    with localcontext() as ctx:
        ctx.prec=60
        actual=Decimal(current['ratios'][key]['value_exact']);base=Decimal(previous['ratios'][key]['value_exact'])
        delta=actual-base
        assert Decimal(row['absolute_delta_exact'])==delta
        assert row['baseline_accession']==previous['accession'] and Decimal(row['baseline_value_exact'])==base
        assert row['relative_status']==('SUPPORTED' if base>0 else 'NONPOSITIVE_BASELINE')
        assert (Decimal(row['relative_delta_exact']) if row['relative_delta_exact'] is not None else None)==(delta/base if base>0 else None)
        mapping={f:[list(v) for v in values] for f,values in field_mapping(current,key).items()}
        assert row['concept_mapping']==mapping
        n,d,_=DEFINITIONS[key]
        n0=previous['fields'][n]['value_exact'];n1=current['fields'][n]['value_exact']
        d0=previous['fields'][d]['value_exact'];d1=current['fields'][d]['value_exact']
        assert bridge['inputs_exact']=={'prior_numerator':n0,'current_numerator':n1,'prior_denominator':d0,'current_denominator':d1}
        r0=dec_ratio(n0,d0);r1=dec_ratio(n1,d1);cf=dec_ratio(n1,d0)
        values={'baseline_ratio_exact':r0,'current_ratio_exact':r1,'counterfactual_ratio_exact':cf,
                'numerator_effect_exact':cf-r0,'denominator_effect_exact':r1-cf,'total_change_exact':r1-r0}
        assert bridge['status']=='SUPPORTED'
        for f,v in values.items():assert Decimal(bridge[f])==v
        residual=(r1-r0)-((cf-r0)+(r1-cf));assert Decimal(bridge['rounding_residual_exact'])==residual
        # An exact-rational identity additionally validates ordered attribution independently of Decimal.
        exact0=Fraction(n0)/Fraction(d0);exact1=Fraction(n1)/Fraction(d1);exactcf=Fraction(n1)/Fraction(d0)
        for f,v in [('numerator_effect_exact',exactcf-exact0),('denominator_effect_exact',exact1-exactcf),('total_change_exact',exact1-exact0)]:
            tolerance=max(abs(v),Fraction(1))*Fraction(1,10**57)
            assert abs(Fraction(bridge[f])-v)<tolerance
    return True


def audit(root):
    case=root/'artifacts/private/sec-case-33077fe45722'
    path=case/'annual-statements.json';pin=sha256(path);statements=read_json(path)
    certificate=root/'artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json'
    validated=read_json(certificate);assert validated['status']=='PASS'
    assert all(sha256(root/p)==digest for p,digest in validated['inputs_sha256'].items())
    ratio_states=Counter();gates=Counter();bridge_count=0;scopes=[]
    for s in statements:
        for key,(n,d,aligned) in DEFINITIONS.items():
            nf=s['fields'][n];df=s['fields'][d];r=s['ratios'][key]
            status='supported'
            if nf['status']!='supported' or df['status']!='supported':status='missing_or_ambiguous_input'
            elif aligned and nf['start_date']!=df['start_date']:status='period_mismatch'
            elif Decimal(df['value_exact'])<=0:status='nonpositive_denominator'
            assert r['status']==status and r['numerator']==n and r['denominator']==d
            assert r['unit']=='ratio (not percent)'
            if status=='supported':assert Decimal(r['value_exact'])==dec_ratio(nf['value_exact'],df['value_exact'])
            else:assert r['value_exact'] is None
            ratio_states[status]+=1
    for cik in sorted({s['cik'] for s in statements}):
        for cutoff in ['2000-01-01','2010-01-01','2018-01-01','2026-10-15']:
            source=defaultdict(list)
            for s in statements:
                if s['cik']==cik and s['filing_date']<=cutoff:source[s['report_date']].append(s)
            periods=[];prior=None
            for report_date,filings in sorted(source.items()):
                original=[s for s in filings if s['form']=='10-K'];selected=original[0] if len(original)==1 else None
                periods.append((report_date,filings,selected,prior));prior=selected
            for years in ['3','5','10']:
                query={'view_id':'sec-view-b92d9914f1dc','cik':cik,'asof':cutoff,'years':years}
                with urlopen('http://127.0.0.1:8770/api/sec-trend?'+urlencode(query),timeout=120) as response:r=json.load(response)
                assert not any(r['qualification'].values()) and not r['public_release_approved']
                expected=periods[-int(years):];assert len(r['periods'])==len(expected)
                for row,(period,filings,selected,baseline) in zip(r['periods'],expected):
                    assert row['report_date']==period and row['statement']==selected and row['baseline_statement']==baseline
                    assert row['selection_status']==('ONE_ORIGINAL_10K' if selected else 'NO_UNIQUE_ORIGINAL_10K')
                    assert row['filings']==[{k:s[k] for k in ['accession','form','filing_date','filing_url']} for s in filings]
                    if selected:
                        for key in DEFINITIONS:
                            bridge_count+=check_change(row['comparisons'][key],selected,baseline,key)
                            gates[row['comparisons'][key]['status']]+=1
                    else:assert row['comparisons']=={}
                assert r['source_capture']['annual_statements_sha256']==pin
                scopes.append({'cik':cik,'cutoff':cutoff,'years':years,'periods':len(expected)})
        print({'cik':cik,'scopes_passed':len(scopes)},flush=True)
    assert sha256(path)==pin
    out=root/'artifacts/private'/('sec-ratio-trend-audit-'+uuid4().hex[:12])
    write_new(out/'receipt.json',{'status':'PASS','source_statements':67,'ratio_cells_checked':268,
        'ratio_states':dict(ratio_states),'http_scopes':scopes,'comparison_gates':dict(gates),
        'supported_bridges_checked':bridge_count,'source_statement_sha256':pin,
        'normalization_audit_sha256':sha256(certificate),'method_sha256':sha256(Path(__file__)),
        'source_method_sha256':sha256(root/'src/credit_atlas/sec_trends.py'),
        'full_completion_proven':False,'remaining':'Coverage candidate/expense arithmetic and current app/Excel scope acceptance'})
    print(out)


if __name__=='__main__':audit(Path.cwd().resolve())
