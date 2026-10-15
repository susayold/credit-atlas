"""Read-only source membership and independent matrix-product checks for B11."""
import argparse
import json
from pathlib import Path

import duckdb

from .labels import create_labels
from .source import sha256


def verify(root, run):
    manifest = json.loads((run/'run-complete.json').read_text())
    if manifest.get('status') != 'VINTAGE_DEVELOPMENT_COMPLETE':
        raise ValueError('Completed vintage run required')
    canonical = root/'artifacts/private'/manifest['canonical_run']
    if sha256(canonical/'run-complete.json') != manifest['canonical_manifest_sha256']:
        raise ValueError('Canonical receipt changed')
    for name, expected in manifest['inputs_sha256'].items():
        if sha256(canonical/name) != expected:
            raise ValueError('Canonical input changed')
    for name, expected in manifest['outputs_sha256'].items():
        if sha256(run/name) != expected:
            raise ValueError('Vintage artifact changed')
    summary = json.loads((run/'summary.json').read_text())
    membership = []
    with duckdb.connect() as db:
        for name in ('dim_loan','fact_loan_month'):
            db.read_parquet(str(canonical/(name+'.parquet'))).create_view(name)
        db.read_parquet(str(run/'vintage_ledger.parquet')).create_view('saved')
        for horizon in manifest['horizons']:
            create_labels(db,root/'sql',{**manifest['cohort_config'],'horizon_months':horizon})
            difference = db.execute('''SELECT COUNT(*) FROM (
                (SELECT loan_id FROM saved EXCEPT ALL SELECT loan_id FROM labels WHERE eligibility_reason='eligible')
                UNION ALL
                (SELECT loan_id FROM labels WHERE eligibility_reason='eligible' EXCEPT ALL SELECT loan_id FROM saved))''').fetchone()[0]
            if difference:
                raise ValueError('Eligible loan identities changed')
            for cause, outcome in [('d3','d3_event'),('prepayment','prepayment'),('other_exit','other_exit')]:
                difference = db.execute('''SELECT COUNT(*) FROM (
                    (SELECT loan_id FROM saved WHERE endpoint=? AND stop_age<=?
                     EXCEPT ALL SELECT loan_id FROM labels WHERE outcome=?) UNION ALL
                    (SELECT loan_id FROM labels WHERE outcome=? EXCEPT ALL
                     SELECT loan_id FROM saved WHERE endpoint=? AND stop_age<=?))''',
                    [cause,horizon,outcome,outcome,cause,horizon]).fetchone()[0]
                if difference:
                    raise ValueError('Horizon first-event membership mismatch')
                membership.append(dict(horizon=horizon,cause=cause,identity_differences=difference))
            db.execute('DROP TABLE labels')
            db.execute('DROP TABLE observation')

        # Independently form and multiply a four-state transition matrix at each age.
        for cohort in summary['cohorts']:
            year, segment = cohort['origination_year'], cohort['segment']
            predicate = {'all':'TRUE','relief':'is_relief_refinance IS TRUE',
                         'non_relief':'is_relief_refinance IS FALSE',
                         'unknown_relief':'is_relief_refinance IS NULL'}[segment]
            ledger = db.execute(f'''SELECT stop_age,endpoint,calendar_age FROM saved
                WHERE origination_year=? AND {predicate}''',[year]).fetchall()
            if len(ledger) != cohort['eligible_loans']:
                raise ValueError('Cohort denominator mismatch')
            state = [1.,0.,0.,0.]
            rows = [r for r in summary['curves'] if r['origination_year']==year and r['segment']==segment]
            if [r['observation_age'] for r in rows] != list(range(1,manifest['max_age']+1)):
                raise ValueError('Curve ages incomplete or duplicated')
            for row in rows:
                age = row['observation_age']
                risk = sum(stop>=age for stop,_,_ in ledger)
                events = [sum(stop==age and endpoint==cause for stop,endpoint,_ in ledger)
                          for cause in ('d3','prepayment','other_exit')]
                if row['at_risk'] != risk:
                    raise ValueError('At-risk denominator mismatch')
                mature = len(ledger)>0 and all(calendar>=age for _,_,calendar in ledger)
                supported = len(ledger)>0 and (risk>0 or state[0]<=1e-14)
                if risk:
                    transition = [[1-sum(events)/risk, *[n/risk for n in events]],
                                  [0,1,0,0],[0,0,1,0],[0,0,0,1]]
                    state = [sum(state[i]*transition[i][j] for i in range(4)) for j in range(4)]
                for j,cause in enumerate(('d3','prepayment','other_exit'),1):
                    actual = row['cif_'+cause]
                    if not mature or not supported:
                        if actual is not None:
                            raise ValueError('Unsupported cell is not null')
                    elif actual is None or abs(actual-state[j])>1e-12:
                        raise ValueError('Independent matrix-product mismatch')
                for cause in ('d3','prepayment','other_exit'):
                    count = sum(stop<=age and endpoint==cause for stop,endpoint,_ in ledger)
                    if row['observed_'+cause+'_count'] != count:
                        raise ValueError('Cumulative first-event count mismatch')
        for row in summary['horizons']:
            matches = [r for r in summary['curves'] if all(r[k]==row[k] for k in
                       ('origination_year','segment','observation_age'))]
            if len(matches)!=1 or any(row[k]!=v for k,v in matches[0].items()):
                raise ValueError('Horizon and curve output mismatch')
    return dict(status='PASS',horizon_membership_checks=membership,
        independent_matrix_product=True,curves_checked=len(summary['curves']),
        limitation='Validates membership and point estimates, not independent bootstrap coverage or publication rights.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(Path(__file__).resolve().parents[2],args.run.resolve()),indent=2))
