"""Export only bounded aggregate evidence to the local private website."""
import json
import argparse
import datetime
import decimal
import duckdb
from pathlib import Path
from crsl.evidence_checks import require, require_hash, require_outcome_totals
from crsl.vintage_export import load as load_vintage
from crsl.losses import summarize as summarize_losses
from crsl.segmented_transition_export import load as load_segmented_transitions
from crsl.portfolio_profile_export import load as load_portfolio_profile


def serial(value):
    """Keep the browser snapshot JSON-safe for DuckDB numeric values."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    raise TypeError(type(value).__name__)
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pipeline-run',type=Path,default=root/'artifacts/private/pipeline-ca9d8efec1e7')
parser.add_argument('--vintage-run',type=Path)
parser.add_argument('--segmented-run',type=Path)
parser.add_argument('--profile-run',type=Path)
args=parser.parse_args()
pipeline=args.pipeline_run.resolve()
manifest=json.loads((pipeline/'run-complete.json').read_text())
require(manifest['status']=='DEVELOPMENT_PIPELINE_COMPLETE', 'Pipeline incomplete')
require(all(r['status']=='PASS' for r in manifest['stages']), 'Pipeline stage failed')
require_hash(Path(manifest['source_run'])/'run-complete.json', manifest['source_manifest_sha256'])
runs={r['stage']:root/'artifacts/private'/r['output_run'] for r in manifest['stages']}
labels=json.loads((runs['labels']/'summary.json').read_text())
metrics=json.loads((runs['metrics']/'validation.json').read_text())
audit=json.loads((runs['audit']/'findings.json').read_text())
source=json.loads((Path(manifest['source_run'])/'result.json').read_text())
require(metrics['status']=='PASS', 'Metric validation failed')
require_hash(runs['portfolio']/'monthly.parquet', metrics['monthly_sha256'])
lm=json.loads((runs['labels']/'run-complete.json').read_text())
require_hash(runs['labels']/'labels.parquet', lm['outputs_sha256']['labels.parquet'])
am=json.loads((runs['audit']/'run-complete.json').read_text())
require_hash(runs['audit']/'findings.json', am['outputs_sha256']['findings.json'])
pm=json.loads((runs['portfolio']/'run-complete.json').read_text())
require_hash(runs['portfolio']/'monthly.parquet', pm['outputs_sha256']['monthly.parquet'])
require_hash(runs['portfolio']/'transition_matrix.parquet', pm['outputs_sha256']['transition_matrix.parquet'])
with duckdb.connect() as db:
    db.read_parquet(str(runs['labels']/'labels.parquet')).create_view('labels')
    verified_outcomes=[{'outcome':o,'loans':n} for o,n in db.execute('SELECT outcome,COUNT(*) FROM labels GROUP BY 1 ORDER BY 1').fetchall()]
    db.read_parquet(str(runs['portfolio']/'monthly.parquet')).create_view('monthly')
    db.read_parquet(str(runs['portfolio']/'transition_matrix.parquet')).create_view('transitions')
    db.read_parquet(str(runs['audit']/'loss_audit.parquet')).create_view('loss_audit')
    monthly_rows=[{'period':str(r[0]),'active_loans':r[1],'state_usable_active_loans':r[2],
        'd3_active_loans':r[3],'unknown_active_loans':r[4],'observed_active_upb':float(r[5]) if r[5] is not None else None,
        'state_usable_active_upb':float(r[6]) if r[6] is not None else None,'d3_active_upb':float(r[7]) if r[7] is not None else None,
        'd3_count_share':float(r[8]) if r[8] is not None else None,'d3_balance_share':float(r[9]) if r[9] is not None else None} for r in db.execute('''
        SELECT period,active_loans,state_usable_active_loans,d3_active_loans,
          unknown_active_loans,observed_active_upb,state_usable_active_upb,
          d3_active_upb,d3_count_share,d3_balance_share FROM monthly ORDER BY period''').fetchall()]
    transition_rows=[{'origin':r[0],'destination':r[1],'pairs':r[2],'opening_upb':float(r[3]) if r[3] is not None else None,
        'missing_balance_pairs':r[4],'count_probability':float(r[5]) if r[5] is not None else None,
        'opening_balance_probability':float(r[6]) if r[6] is not None else None} for r in db.execute('''
        SELECT origin,destination,pairs,opening_upb,missing_balance_pairs,
          count_probability,opening_balance_probability FROM transitions
        ORDER BY origin,destination''').fetchall()]
    loss_summary=summarize_losses(db.execute('SELECT * FROM loss_audit ORDER BY loan_id,period').to_arrow_table().to_pylist())
require(verified_outcomes==[{'outcome':r['outcome'],'loans':r['loans']} for r in labels['outcomes']], 'Label summary differs from Parquet')
payload={'visibility':'private','public_release_approved':False,'pipeline_run':pipeline.name,
 'loans':source['summary']['origination_loans'],'monthly_rows':source['summary']['performance_rows'],
 'months':metrics['months_checked'],'outcomes':verified_outcomes,'monthly':monthly_rows,
 'transitions':transition_rows,
 'loss_reported':audit['loss_reconciliation'][0]['reported'],'loss_summary':loss_summary}
require_outcome_totals(payload['outcomes'], payload['loans'])
vintage_run=args.vintage_run or runs.get('vintage')
payload['vintage_evidence']=(load_vintage(root,runs['canonical'],vintage_run.resolve())
    if vintage_run else {'status':'unavailable','reason':'No verified vintage run supplied'})
segmented_run=args.segmented_run
payload['segmented_transitions']=(load_segmented_transitions(root,segmented_run.resolve())
    if segmented_run else {'status':'unavailable','reason':'No verified segmented transition run supplied'})
if payload['segmented_transitions'].get('status')=='verified_development':
    require(payload['segmented_transitions']['canonical_run']==runs['canonical'].name,
        'Segmented transition mart uses a different canonical run')
profile_run=args.profile_run
payload['portfolio_profile']=(load_portfolio_profile(root,runs['canonical'],profile_run.resolve())
    if profile_run else {'status':'unavailable','reason':'No verified portfolio profile run supplied'})
if payload['portfolio_profile'].get('status')=='verified_development':
    require(payload['portfolio_profile']['canonical_run']==runs['canonical'].name,
        'Portfolio profile uses a different canonical run')
(root/'site/dist/data.json').write_text(json.dumps(payload,default=serial,ensure_ascii=False,indent=2),encoding='utf-8')
print('Private aggregate snapshot exported; no raw identifiers, no hosting approval.')
