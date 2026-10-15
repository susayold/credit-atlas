"""Whole-source signed diagnostics supplement; never mutate frozen summaries."""
from decimal import Decimal

import duckdb

from .workspace import contained

COMPONENTS=('removal_upb','net_sales_proceeds','delinquent_accrued_interest','total_expenses','mi_recoveries','non_mi_recoveries')
EXPENSES=('legal_costs','maintenance_costs','taxes_insurance','misc_expenses')


def report(service,query):
    if set(query)!={'run'}:raise ValueError('Observed loss details require run only;whole source scope')
    case=service.case(query['run']);manifest=case['manifest']
    path=contained(service.root,manifest['canonical_run'])/'fact_loan_month.parquet'
    with duckdb.connect() as con:
        con.execute("SET memory_limit='256MB'");con.execute('SET threads=2')
        data=con.execute(f"SELECT loan_id,period,zero_balance_date,actual_loss,{','.join(COMPONENTS+EXPENSES)} FROM read_parquet(?) WHERE zero_balance_code IN ('02','03','09','15')",[str(path)]).fetchall()
        columns=[x[0] for x in con.description]
    groups={}
    for row in data:
        r=dict(zip(columns,row));groups.setdefault(r['loan_id'],[]).append(r)
    records=[min(g,key=lambda r:(r['zero_balance_date'] or r['period'],r['period'])) for g in groups.values()]
    expense_residuals=[];signed=[];magnitude=[];loss_residuals=[];missing=0
    field_quality={f:{'known':0,'missing':0,'negative':0,'zero':0,'positive':0} for f in ('actual_loss',)+COMPONENTS+EXPENSES}
    for r in records:
        for f,q in field_quality.items():
            v=r[f]
            if v is None:q['missing']+=1
            else:
                q['known']+=1;q['negative' if v<0 else 'zero' if v==0 else 'positive']+=1
        if r['total_expenses'] is not None and all(r[f] is not None for f in EXPENSES):
            expense_residuals.append(r['total_expenses']-sum((r[f] for f in EXPENSES),Decimal(0)))
        if r['actual_loss'] is not None:
            if all(r[f] is not None for f in COMPONENTS):loss_residuals.append(r['actual_loss']-sum((r[f] for f in COMPONENTS),Decimal(0)))
            if r['removal_upb'] is None or r['removal_upb']==0:missing+=1
            else:
                signed.append(r['actual_loss']/abs(r['removal_upb']))
                magnitude.append(abs(r['actual_loss'])/abs(r['removal_upb']))
    def ratio(values):
        return {'observations':len(values),'mean_exact':str(sum(values)/len(values)) if values else None,'min_exact':str(min(values)) if values else None,'max_exact':str(max(values)) if values else None}
    service.case(query['run'])
    return {'schema_version':'observed-loss-details-v1','case_id':manifest['case_id'],'pipeline_run':manifest['pipeline_run'],
            'scope':'whole_source_sample_loss_codes_02_03_09_15','filters_applied':[],
            'selected_terminal_loans':len(records),'duplicate_terminal_rows_removed':len(data)-len(records),
            'signed_ratio':ratio(signed),'magnitude_ratio':ratio(magnitude),'ratio_missing_or_zero_denominator':missing,
            'loss_formula':{'checked_rows':len(loss_residuals),'max_abs_residual_exact':str(max(map(abs,loss_residuals))) if loss_residuals else None},
            'expense_formula':{'checked_rows':len(expense_residuals),'max_abs_residual_exact':str(max(map(abs,expense_residuals))) if expense_residuals else None},
            'field_quality':field_quality,'visibility':'private','public_release_approved':False,'expected_loss_dollars':None,
            'limitations':['Signed ratio = actual_loss / abs(removal_upb);negative gains stay negative;not qualified LGD.',
                           'Magnitude ratio = abs(actual_loss) / abs(removal_upb);this is the legacy frozen severity summary convention.',
                           'Expense reconciliation uses four canonical expense fields omitted from the legacy loss summary input.',
                           'Release47 signed components are added;January2026 guide uses an older sign convention.',
                           'Whole-source loss scope ignores portfolio segment/date/horizon selectors;missing is not zero.',
                           'No recovery cashflow timing,representative LGD or accounting ECL is inferred.']}
