"""Synthetic first-event, maturity, competing-exit and uncertainty examples."""
from collections import Counter
from datetime import date
import json
from pathlib import Path
import shutil

import duckdb
import pytest

from crsl.vintage import bootstrap_intervals, create_ledger, curve, summarize
from crsl.vintage import run
from crsl.verify_vintage import verify
from crsl.source import sha256

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'configs/cohort.json').read_text())


def database(loans):
    db = duckdb.connect()
    db.execute('''CREATE TABLE dim_loan(loan_id VARCHAR, original_upb DECIMAL(18,2),
        origination_year INTEGER,is_relief_refinance BOOLEAN,first_payment_date DATE)''')
    db.execute('''CREATE TABLE fact_loan_month(loan_id VARCHAR,period DATE,loan_age INTEGER,
        delinquency_state VARCHAR,modification VARCHAR,terminal_type VARCHAR)''')
    for loan, specification in loans.items():
        months, changes = specification
        db.execute('INSERT INTO dim_loan VALUES (?,100000,2012,false,?)', [loan,date(2012,2,1)])
        for age in range(months):
            if changes.get(age) == 'gap':
                continue
            state, terminal = changes.get(age, ('CURRENT', None))
            db.execute('INSERT INTO fact_loan_month VALUES (?,?,?,?,NULL,?)',
                [loan,date(2012+age//12,1+age%12,1),age,state,terminal])
    return db


def test_competing_risk_is_not_one_minus_km_with_prepay_censored():
    # Four loans: prepay one at month 1, D3 one at month 2, two complete month 3.
    rows = curve({(1,'prepayment'):1,(2,'d3'):1,(3,'censored'):2},3)
    assert rows[1]['at_risk'] == 3
    assert rows[-1]['cif_d3'] == pytest.approx(.25)  # NOT 1/3
    assert rows[-1]['cif_prepayment'] == pytest.approx(.25)
    assert rows[-1]['event_free_probability'] == pytest.approx(.5)


def test_same_month_censor_is_after_events():
    rows = curve({(1,'d3'):1,(1,'censored'):1,(2,'prepayment'):2},2)
    assert rows[0]['cif_d3'] == .25
    assert rows[1]['cif_prepayment'] == .75
    assert rows[1]['event_free_probability'] == 0


def test_unobserved_tail_not_zero_or_carried_forward():
    rows = curve({(1,'censored'):3},3)
    assert rows[0]['cif_d3'] == 0
    assert rows[1]['cif_d3'] is None


def test_exhausted_event_risk_set_preserves_absorbing_probability():
    rows = curve({(1,'d3'):1,(1,'other_exit'):1},3)
    assert rows[-1]['cif_d3'] == .5
    assert rows[-1]['cif_other_exit'] == .5


@pytest.mark.parametrize('counts', [{(0,'d3'):1},{(1,'d3'):-1},{(1,'bad'):2},{(True,'d3'):1}])
def test_invalid_counts_rejected(counts):
    with pytest.raises(ValueError):
        curve(counts,3)


def test_first_event_gap_unknown_and_tie_ledger():
    with database({
        'repeat':(25,{2:('D3PLUS',None),5:('D3PLUS',None)}),
        'gap':(25,{2:'gap',4:('D3PLUS',None)}),
        'unknown':(25,{1:('UNKNOWN',None),5:('D3PLUS',None)}),
        'tie':(4,{3:('D3PLUS','PREPAID_OR_MATURED')}),
        'prepay':(3,{2:('CURRENT','PREPAID_OR_MATURED')}),
        'other':(5,{4:('CURRENT','OTHER_TERMINATION')}),
        'short':(5,{}),
        'entry':(25,{0:('D3PLUS',None)}),
    }) as db:
        create_ledger(db,ROOT/'sql',CONFIG)
        actual = {r[0]:r[1:] for r in db.execute('SELECT loan_id,stop_age,endpoint FROM vintage_ledger').fetchall()}
        assert actual == {'repeat':(2,'d3'),'gap':(1,'censored'),'unknown':(0,'censored'),
            'tie':(3,'d3'),'prepay':(2,'prepayment'),'other':(4,'other_exit'),'short':(4,'censored')}
        summary = summarize(db,24,[6,12,24],100,17)
        horizon = next(r for r in summary['horizons'] if r['segment']=='all' and r['observation_age']==12)
        assert horizon['source_loans']==8 and horizon['eligible_loans']==7
        assert horizon['observed_d3_count']==2 and horizon['unknown_before_horizon']==3
        stock = db.execute('SELECT d3_active_loans FROM vintage_stock WHERE observation_age=5').fetchone()[0]
        assert stock==2  # Current stock is deliberately not a first-event counter.


def test_calendar_immature_cells_are_null():
    with database({'young':(8,{2:('D3PLUS',None)}),'healthy':(8,{})}) as db:
        create_ledger(db,ROOT/'sql',CONFIG)
        summary = summarize(db,24,[6,12,24],100,17)
        rows = [r for r in summary['horizons'] if r['segment']=='all']
        assert rows[0]['cif_d3']==.5
        assert rows[1]['cif_d3'] is None and rows[1]['ci_lower'] is None
        assert not rows[1]['maturity_complete']
        assert rows[1]['observed_d3_count']==1


def test_cumulative_events_and_probability_identity():
    rows = curve({(1,'censored'):2,(2,'d3'):2,(3,'other_exit'):1,(4,'prepayment'):2,(6,'censored'):10},6)
    assert [r['cif_d3'] for r in rows]==sorted(r['cif_d3'] for r in rows)
    for r in rows:
        assert sum(r['cif_'+cause] for cause in ('d3','other_exit','prepayment'))+r['event_free_probability']==pytest.approx(1)


def test_bootstrap_deterministic_and_boundary_honest():
    counts = {(1,'d3'):10,(3,'prepayment'):20,(6,'censored'):70}
    a = bootstrap_intervals(counts,6,[6],resamples=100,seed=17)
    assert a==bootstrap_intervals(dict(reversed(list(counts.items()))),6,[6],resamples=100,seed=17)
    assert a[6]['ci_lower'] < .1 < a[6]['ci_upper']
    zero = bootstrap_intervals({(6,'censored'):100},6,[6],resamples=100,seed=17)[6]
    assert zero['ci_lower'] is None and zero['ci_status']=='boundary_event_support'


def test_complete_cohort_incidence_equals_direct_binary_count():
    counts = Counter({(1,'d3'):2,(2,'prepayment'):3,(3,'other_exit'):1,(6,'censored'):14})
    assert curve(counts,6)[-1]['cif_d3']==pytest.approx(2/20)


def test_file_run_and_source_verifier_reject_rehashed_metric_tamper(tmp_path):
    root=tmp_path/'project'
    shutil.copytree(ROOT/'sql',root/'sql')
    shutil.copytree(ROOT/'configs',root/'configs')
    canonical=root/'artifacts/private/canonical-synthetic'
    canonical.mkdir(parents=True)
    with database({'event':(25,{2:('D3PLUS',None)}),'healthy':(25,{}),
                   'prepaid':(4,{3:('CURRENT','PREPAID_OR_MATURED')})}) as db:
        for table in ('dim_loan','fact_loan_month'):
            db.table(table).write_parquet(str(canonical/(table+'.parquet')))
    receipt={'status':'CANONICAL_COMPLETE','outputs_sha256':{p.name:sha256(p) for p in canonical.glob('*.parquet')}}
    (canonical/'run-complete.json').write_text(json.dumps(receipt))
    result=run(root,canonical,resamples=100)
    assert verify(root,result)['status']=='PASS'
    summary=json.loads((result/'summary.json').read_text())
    summary['curves'][0]['cif_d3']=.91
    (result/'summary.json').write_text(json.dumps(summary))
    receipt=json.loads((result/'run-complete.json').read_text())
    receipt['outputs_sha256']['summary.json']=sha256(result/'summary.json')
    (result/'run-complete.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match='matrix-product'):
        verify(root,result)
