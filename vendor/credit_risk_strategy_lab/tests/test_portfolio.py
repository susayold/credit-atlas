from datetime import date
from pathlib import Path
import duckdb
from crsl.episodes import episode_events
from crsl.portfolio import create_marts

def test_cure_confirmation_not_backdated():
    states=['D3PLUS','CURRENT','CURRENT','CURRENT','D3PLUS']
    events=list(episode_events(('fixture',date(2012,i+1,1),s,None) for i,s in enumerate(states)))
    assert [e[2] for e in events]==['FIRST_OBSERVED_D3','ONE_MONTH_CURE','SUSTAINED_CURE_CONFIRMED','REDEFAULT_AFTER_SUSTAINED_CURE']
    assert events[2][1]==date(2012,4,1)

def test_unsustained_cure_not_redefault():
    events=list(episode_events(('fixture',date(2012,i+1,1),s,None) for i,s in enumerate(['D3PLUS','CURRENT','D3PLUS'])))
    assert sum(e[2]=='FIRST_OBSERVED_D3' for e in events)==1
    assert not any(e[2]=='REDEFAULT_AFTER_SUSTAINED_CURE' for e in events)

def test_gap_interrupts_cure():
    events=list(episode_events([('fixture',date(2012,1,1),'D3PLUS',None),
      ('fixture',date(2012,3,1),'CURRENT',None),('fixture',date(2012,4,1),'CURRENT',None),('fixture',date(2012,5,1),'CURRENT',None)]))
    assert len(events)==1

def test_unknown_interrupts_cure():
    events=list(episode_events(('fixture',date(2012,i+1,1),s,None) for i,s in enumerate(['D3PLUS','UNKNOWN','CURRENT','CURRENT','CURRENT'])))
    assert len(events)==1

def test_exit_current_is_not_sustained_cure():
    rows=[('fixture',date(2012,1,1),'D3PLUS',None),
          ('fixture',date(2012,2,1),'CURRENT',None),
          ('fixture',date(2012,3,1),'CURRENT',None),
          ('fixture',date(2012,4,1),'CURRENT','PREPAID_OR_MATURED')]
    assert not any(e[2]=='SUSTAINED_CURE_CONFIRMED' for e in episode_events(rows))

def test_transition_gap_opening_weight_and_stock():
    with duckdb.connect() as db:
        db.execute('CREATE TABLE fact_loan_month(loan_id VARCHAR,period DATE,current_upb DECIMAL(18,2),delinquency_state VARCHAR,terminal_type VARCHAR)')
        db.execute("""INSERT INTO fact_loan_month VALUES
          ('a','2012-01-01',100,'CURRENT',NULL),('a','2012-02-01',10,'D3PLUS',NULL),
          ('b','2012-01-01',300,'CURRENT',NULL),('b','2012-02-01',0,'CURRENT','PREPAID_OR_MATURED'),
          ('c','2012-01-01',500,'CURRENT',NULL),('c','2012-03-01',400,'CURRENT',NULL)""")
        create_marts(db,Path(__file__).resolve().parents[1]/'sql')
        row=db.execute("SELECT pairs,count_probability,opening_balance_probability FROM transition_matrix WHERE origin='CURRENT' AND destination='D3PLUS'").fetchone()
        assert row==(1,0.5,0.25)
        assert db.execute("SELECT COUNT(*) FROM pairs WHERE destination='GAP'").fetchone()[0]==1
        assert db.execute("SELECT active_loans,terminal_loans FROM monthly WHERE period='2012-02-01'").fetchone()==(1,1)
