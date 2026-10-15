"""Allowlisted aggregate evidence for local research views; no loan-level export."""
import json

from .source import sha256
from .evidence_checks import require, require_hash
from .verify_vintage import verify

FIELDS = ('origination_year','segment','observation_age','source_loans','eligible_loans',
    'excluded_loans','excluded_share','at_risk','calendar_mature_loans','maturity_complete',
    'observed_d3_count','observed_prepayment_count','observed_other_exit_count',
    'unknown_before_horizon','unknown_share','cif_d3','cif_prepayment','cif_other_exit',
    'sparse_d3','ci_lower','ci_upper','ci_level','ci_method','ci_status','resamples')


def project_rows(summary):
    rows=[]
    for row in summary['horizons']:
        require(row['segment'] in ('all','relief','non_relief','unknown_relief'), 'Unexpected segment')
        require(row['observation_age'] in (6,12,24), 'Unexpected horizon')
        projected={key:row[key] for key in FIELDS}
        if not projected['maturity_complete']:
            require(projected['cif_d3'] is None and projected['ci_lower'] is None
                    and projected['ci_upper'] is None, 'Immature evidence must remain unavailable')
        rows.append(projected)
    keys=[(r['origination_year'],r['segment'],r['observation_age']) for r in rows]
    require(len(keys)==len(set(keys)), 'Duplicate cohort horizon')
    return rows


def load(root, canonical_run, vintage_run):
    """Supplement an older display only when its actual canonical bytes match."""
    receipt=json.loads((vintage_run/'run-complete.json').read_text())
    canonical=json.loads((canonical_run/'run-complete.json').read_text())
    require(canonical.get('status')=='CANONICAL_COMPLETE', 'Canonical evidence incomplete')
    for filename in ('dim_loan.parquet','fact_loan_month.parquet'):
        require_hash(canonical_run/filename,canonical['outputs_sha256'][filename])
        require(canonical['outputs_sha256'][filename]==receipt['inputs_sha256'][filename],
                'Vintage and displayed data use different source records')
    checked=verify(root,vintage_run)
    require(checked['status']=='PASS', 'Vintage verification failed')
    summary=json.loads((vintage_run/'summary.json').read_text())
    return dict(status='verified_development',visibility='private',public_release_approved=False,
        vintage_run=vintage_run.name,canonical_run=receipt['canonical_run'],
        display_canonical_run=canonical_run.name,canonical_bytes_match=True,
        summary_sha256=sha256(vintage_run/'summary.json'),rows=project_rows(summary),
        limitation='One-vintage descriptive evidence; not model performance or causal program effects.')
