"""Source-wide Decimal audit; independently calculate signed and magnitude loss ratios."""
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.workspace import contained,sha256

ROOT=Path.cwd();CASE='d01-a24484b21a21'
out=ROOT/'artifacts/private'/('observed-loss-source-audit-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
manifest=json.loads((ROOT/f'artifacts/private/{CASE}/case-complete.json').read_text())
snap=json.loads((ROOT/f'artifacts/private/{CASE}/snapshot.json').read_text())['snapshot']['loss_summary']
fact=contained(ROOT,manifest['canonical_run'])/'fact_loan_month.parquet'
loss=contained(ROOT,next(x['path'] for x in manifest['verified_inputs'] if x['path'].endswith('loss_audit.parquet')))
fields=['actual_loss','removal_upb','net_sales_proceeds','delinquent_accrued_interest','total_expenses','mi_recoveries','non_mi_recoveries','legal_costs','maintenance_costs','taxes_insurance','misc_expenses']
components=fields[1:7];expenses=fields[7:]
c=duckdb.connect();c.execute("SET memory_limit='512MB'");c.execute('SET threads=2')
rawcols=','.join('raw_'+f for f in fields)
records=c.execute(f"SELECT loan_id,period,zero_balance_code,zero_balance_date,defect_settlement_date,{','.join(fields)},{rawcols} FROM read_parquet(?) WHERE raw_zero_balance_code IN ('02','03','09','15')",[str(fact)]).fetchall()
cols=[x[0] for x in c.description];source=[dict(zip(cols,r)) for r in records]
canonical_parity=0
for r in source:
    for f in fields:
        raw=r['raw_'+f].strip()
        expected=Decimal(raw) if raw else None
        assert r[f]==expected,f
        canonical_parity+=1
groups={}
for r in source:groups.setdefault(r['loan_id'],[]).append(r)
selected=[min(group,key=lambda r:(r['zero_balance_date'] or r['period'],r['period'])) for group in groups.values()]
saved_rows=c.execute('SELECT * FROM read_parquet(?)',[str(loss)]).fetchall();saved_cols=[x[0] for x in c.description]
saved={(r[0],r[1]):dict(zip(saved_cols,r)) for r in saved_rows}
rowchecks=0;availability=Counter();bridge={f:Decimal(0) for f in components};component_complete=0;expense_checked=0;loss_checked=0;partial=0
reported=[];signed=[];magnitude=[];loss_residuals=[];expense_residuals=[];zero_missing=0
for r in selected:
    s=saved[(r['loan_id'],r['period'])]
    for f in fields[:7]+['zero_balance_code','zero_balance_date','defect_settlement_date']:
        assert s[f]==r[f];rowchecks+=1
    reason='reported' if r['actual_loss'] is not None else 'withheld_defect' if r['defect_settlement_date'] is not None else 'recent_disposition' if r['zero_balance_date'] is not None and r['zero_balance_date']>=date(2026,1,1) else 'unexplained_missing'
    assert s['availability_reason']==reason
    availability[reason]+=1
    complete=all(r[f] is not None for f in components)
    if complete:
        component_complete+=1
        for f in components:bridge[f]+=r[f]
    else:partial+=1
    residual=r['actual_loss']-sum((r[f] for f in components),Decimal(0)) if complete and r['actual_loss'] is not None else None
    assert s['loss_residual']==residual
    if residual is not None:loss_checked+=1;loss_residuals.append(residual)
    eres=r['total_expenses']-sum((r[f] for f in expenses),Decimal(0)) if r['total_expenses'] is not None and all(r[f] is not None for f in expenses) else None
    assert s['expense_residual']==eres
    if eres is not None:expense_checked+=1;expense_residuals.append(eres)
    if r['actual_loss'] is not None:
        reported.append(r['actual_loss'])
        if r['removal_upb'] is None or r['removal_upb']==0:zero_missing+=1
        else:
            signed.append(r['actual_loss']/abs(r['removal_upb']))
            magnitude.append(abs(r['actual_loss'])/abs(r['removal_upb']))
assert len(saved)==len(source)
assert len(selected)==snap['terminal_loans']==381
assert len(reported)==snap['reported_loss_loans']==374
assert len(selected)-len(reported)==snap['unresolved_terminal_loans']==7
assert dict(sorted(availability.items()))==snap['availability']
assert component_complete==snap['component_bridge_complete_rows'] and partial==snap['partial_component_rows']
assert len(signed)==snap['severity_observation_loans'] and zero_missing==snap['zero_or_missing_denominator_loans']
assert loss_checked==snap['loss_formula_checked_rows']
assert sum(len(g)-1 for g in groups.values())==snap['duplicate_terminal_rows_removed']
assert abs(float(sum(reported))-snap['reported_loss_sum_usd'])<1e-6
for f,v in bridge.items():assert abs(float(v)-snap['component_bridge'][f])<1e-6
assert abs(float(sum(magnitude)/len(magnitude))-snap['severity_mean_uncapped'])<1e-12
assert snap['expected_loss_dollars'] is None and snap['research_ready'] is False and snap['gate_status']=='blocked'
differences=[]
if expense_checked!=snap['expense_formula_checked_rows']:differences.append({'field':'expense_formula_checked_rows','saved_summary':snap['expense_formula_checked_rows'],'source_recomputed':expense_checked,'reason':'Saved loss_audit output omits four expense fields;summary cannot recompute expense residual although source audit has it'})
if any(v<0 for v in signed):differences.append({'field':'severity_*_uncapped','saved_method':'abs(actual_loss)/abs(removal_upb)','signed_method':'actual_loss/abs(removal_upb)','negative_reported_loss_loans':sum(v<0 for v in reported),'negative_signed_ratios':sum(v<0 for v in signed),'reason':'Existing values are magnitude ratios;must label explicitly and expose signed ratios separately'})
assert sha256(ledger)==before
result={'status':'SOURCE_AUDIT_PASS_WITH_PRESENTATION_GAPS','requirement':'P2.09','source_terminal_rows':len(source),'distinct_selected_loans':len(selected),'canonical_decimal_parity_checks':canonical_parity,'saved_row_field_checks':rowchecks,'reported_loss_loans':len(reported),'unresolved':len(selected)-len(reported),'availability':dict(availability),'component_complete_rows':component_complete,'loss_formula_checked_rows':loss_checked,'max_abs_loss_residual_exact':str(max(map(abs,loss_residuals))),'expense_formula_checked_rows':expense_checked,'max_abs_expense_residual_exact':str(max(map(abs,expense_residuals))),'reported_loss_sum_exact':str(sum(reported)),'signed_component_sum_exact':{f:str(v) for f,v in bridge.items()},'signed_ratio':{'mean':str(sum(signed)/len(signed)),'min':str(min(signed)),'max':str(max(signed))},'magnitude_ratio':{'mean':str(sum(magnitude)/len(magnitude)),'min':str(min(magnitude)),'max':str(max(magnitude))},'gaps':differences,'source_inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p)} for p in [fact,loss,ROOT/f'artifacts/private/{CASE}/snapshot.json',ROOT/'vendor/credit_risk_strategy_lab/data/private/source_documents/release47/guide.pdf']],'method_sha256':sha256(Path(__file__)),'ledger_unchanged':True,'full_completion_proven':False}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':result['status'],'expense_rows':expense_checked,'negative_loss_loans':sum(v<0 for v in reported),'gaps':len(differences)}))
