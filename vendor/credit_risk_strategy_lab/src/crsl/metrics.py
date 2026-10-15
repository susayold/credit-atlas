"""Shared metric definitions and reconciliation for derived monthly sample tables."""
import math

REGISTRY={
 'active_loans':{'unit':'loans','grain':'reporting_month','formula':'count of rows with no terminal_type',
   'denominator':None,'limitation':'Observed annual sample; not the Freddie Mac universe.'},
 'observed_active_upb':{'unit':'USD','grain':'reporting_month','formula':'sum known current_upb for nonterminal rows',
   'denominator':None,'limitation':'Missing balances are reported separately; do not sum stocks across months as originations.'},
 'd3_count_share':{'unit':'fraction','grain':'reporting_month','formula':'d3_active_loans / state_usable_active_loans',
   'denominator':'state_usable_active_loans','limitation':'Monthly numeric D3 state prevalence, not default12m incidence; REO reported separately.'},
 'd3_balance_share':{'unit':'fraction','grain':'reporting_month','formula':'known d3_active_upb / state_usable_active_upb',
   'denominator':'state_usable_active_upb','limitation':'Known-balance share; coverage must accompany it. Not loan-count weighted.'},
 'unknown_active_loans':{'unit':'loans','grain':'reporting_month','formula':'count nonterminal UNKNOWN states',
   'denominator':None,'limitation':'Unknown is not current or zero risk.'},
 'missing_active_balance_loans':{'unit':'loans','grain':'reporting_month','formula':'count nonterminal null current_upb',
   'denominator':None,'limitation':'Observed active UPB is partial when this count is nonzero.'},
}
for definition in REGISTRY.values():
    definition.update(evidence_class='derived_observed_sample',sql_owner='sql/portfolio_monthly.sql',
                      as_of='source reporting month in latest release',horizon='point-in-time stock',
                      uncertainty='descriptive sample metric; no population confidence interval claimed',
                      zero_denominator='unavailable, never zero',minimum_support='positive denominator for rates; sparse publication controlled separately')

def ratio(numerator,denominator):
    if denominator is None or denominator==0: return None
    if numerator is None: return None
    n=float(numerator);d=float(denominator)
    if not math.isfinite(n) or not math.isfinite(d) or d<0 or n<0 or n>d:
        raise ValueError('Invalid nonnegative share inputs')
    return n/d

def validate_monthly(rows):
    seen=set();count=0
    for row in rows:
        month=row['period']
        if month in seen: raise ValueError('Duplicate reporting month')
        seen.add(month);count+=1
        counts=['reported_loans','active_loans','terminal_loans','state_usable_active_loans',
                'unknown_active_loans','d3_active_loans','reo_active_loans','missing_active_balance_loans']
        if any(type(row[c]) is not int or row[c]<0 for c in counts):
            raise ValueError('Counts must be nonnegative integers')
        if row['active_loans']+row['terminal_loans']!=row['reported_loans']:
            raise ValueError('Active/terminal reconciliation failed')
        if row['state_usable_active_loans']+row['unknown_active_loans']!=row['active_loans']:
            raise ValueError('Usable/unknown denominator reconciliation failed')
        if row['d3_active_loans']+row['reo_active_loans']>row['state_usable_active_loans']:
            raise ValueError('D3/REO counts exceed usable population')
        if row['missing_active_balance_loans']>row['active_loans']:
            raise ValueError('Missing balance count exceeds active count')
        expected={'d3_count_share':ratio(row['d3_active_loans'],row['state_usable_active_loans']),
          'd3_balance_share':ratio(row['d3_active_upb'] if row['d3_active_upb'] is not None else 0,row['state_usable_active_upb'])}
        for field,value in expected.items():
            actual=row[field]
            if value is None:
                if actual is not None: raise ValueError('Undefined rate hidden as a number')
            elif actual is None or not math.isclose(float(actual),value,rel_tol=1e-10,abs_tol=1e-12):
                raise ValueError('Rate does not match canonical numerator/denominator')
    if count==0: raise ValueError('Empty monthly output; do not report fabricated zeros')
    return {'status':'PASS','months_checked':count,'checks':['unique_month','stock_count_reconciliation',
       'usable_state_denominator','d3_reo_exclusive_counts','missing_balance_count','rate_formula','undefined_rate_null']}

def run(root,portfolio_run):
    import json
    import uuid
    import duckdb
    from .source import sha256,utc_now,write_json_new
    manifest=json.loads((portfolio_run/'run-complete.json').read_text())
    if manifest.get('status')!='PORTFOLIO_MARTS_COMPLETE': raise ValueError('Completed portfolio run required')
    path=portfolio_run/'monthly.parquet'
    if sha256(path)!=manifest['outputs_sha256'][path.name]: raise ValueError('Portfolio output changed')
    with duckdb.connect() as db:
        result=validate_monthly(db.read_parquet(str(path)).arrow().read_all().to_pylist())
    output=root/'artifacts/private'/('metrics-'+uuid.uuid4().hex[:12]);output.mkdir()
    write_json_new(output/'registry.json',REGISTRY)
    write_json_new(output/'validation.json',{**result,'portfolio_run':portfolio_run.name,
      'validated_at':utc_now(),'monthly_sha256':sha256(path),'visibility':'private','public_release_approved':False})
    return output

if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--portfolio-run',type=Path,required=True)
    args=parser.parse_args();print(run(Path(__file__).resolve().parents[2],args.portfolio_run.resolve()))
