"""Independent DuckDB accounting audit of saved conditional waterfall state."""
from pathlib import Path
import json
import sys
import uuid

import duckdb
import pyarrow as pa

from credit_atlas.abs_waterfall import verify_replay
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def audit(identifier):
    root=app_root();report=verify_replay(root,identifier)
    ledger=[];balances=[];totals=[]
    for p in report['periods']:
        end=p['collection_end'];inputs=p['inputs'];result=p['result']
        for row in result['ledger']:ledger.append({'collection_end':end,**row})
        for slot,begin in inputs['beginning_balances'].items():
            balances.append({'collection_end':end,'slot':slot,'beginning':begin,
                'paid':result['principal_paid'][slot],'ending':result['ending_balances'][slot]})
        totals.append({'collection_end':end,'available_funds':inputs['available_funds'],
            'reserve_beginning':inputs['reserve_beginning'],'reserve_ending':result['reserve_ending'],
            'certificate_paid':result['certificate_paid'],'redeposit':result['collection_account_redeposit']})
    # Do not read the implementation's claimed conservation deltas/pass flags.
    con=duckdb.connect()
    fields=('collection_end','priority','name','due','paid','shortfall','from_available_funds','reserve_draw',
            'reserve_credit','cash_before','cash_after','reserve_before','reserve_after','external_distribution')
    con.register('saved_ledger',pa.Table.from_pylist([{k:r[k] for k in fields} for r in ledger]))
    con.register('saved_balances',pa.Table.from_pylist(balances));con.register('saved_totals',pa.Table.from_pylist(totals))
    money_fields=fields[3:-1]
    projection='collection_end,priority,name,external_distribution,'+','.join(
        f'cast({field} AS DECIMAL(38,2)) {field}' for field in money_fields)
    con.execute('CREATE TEMP TABLE money_ledger AS SELECT '+projection+' FROM saved_ledger')
    stage_sql='''SELECT collection_end,priority,
        cash_before-from_available_funds-cash_after cash_delta,
        reserve_before-reserve_draw+reserve_credit-reserve_after reserve_delta,
        paid-from_available_funds-reserve_draw paid_delta,
        due-paid-shortfall due_delta,
        CASE WHEN cash_after>=0 AND reserve_after>=0 AND due>=paid AND paid>=0
            AND from_available_funds>=0 AND reserve_draw>=0 AND reserve_credit>=0 THEN 0 ELSE 1 END negative_state
        FROM money_ledger ORDER BY collection_end,priority'''
    stage_rows=con.execute(stage_sql).fetchall()
    stage_checks=[{'collection_end':end,'priority':priority,
        'cash_delta':str(cash),'reserve_delta':str(reserve),'paid_delta':str(paid),
        'due_delta':str(due),'negative_state':negative,'pass':cash==reserve==paid==due==negative==0}
        for end,priority,cash,reserve,paid,due,negative in stage_rows]
    continuity_sql='''SELECT collection_end,priority,
        cash_before-lag(cash_after) OVER(PARTITION BY collection_end ORDER BY priority) cash_link_delta,
        reserve_before-lag(reserve_after) OVER(PARTITION BY collection_end ORDER BY priority) reserve_link_delta
        FROM money_ledger ORDER BY collection_end,priority'''
    links=con.execute(continuity_sql).fetchall()
    links=[{'collection_end':end,'priority':priority,'cash_delta':str(cash),'reserve_delta':str(reserve),
        'pass':cash==reserve==0} for end,priority,cash,reserve in links if priority!=1]
    balance_sql='''SELECT collection_end,slot,cast(beginning AS DECIMAL(38,2))-cast(paid AS DECIMAL(38,2))-
        cast(ending AS DECIMAL(38,2)) delta FROM saved_balances ORDER BY collection_end,slot'''
    balance_checks=[{'collection_end':end,'slot':slot,'delta':str(delta),'pass':delta==0}
        for end,slot,delta in con.execute(balance_sql).fetchall()]
    total_sql='''SELECT t.collection_end,
        cast(t.available_funds AS DECIMAL(38,2))+cast(t.reserve_beginning AS DECIMAL(38,2))-
        sum(CASE WHEN l.priority NOT IN (8,11) THEN l.paid ELSE 0 END)-
        cast(t.certificate_paid AS DECIMAL(38,2))-cast(t.redeposit AS DECIMAL(38,2))-
        cast(t.reserve_ending AS DECIMAL(38,2)) delta,
        max(CASE WHEN l.priority=1 THEN l.cash_before END)-cast(t.available_funds AS DECIMAL(38,2)) initial_cash_delta,
        max(CASE WHEN l.priority=1 THEN l.reserve_before END)-cast(t.reserve_beginning AS DECIMAL(38,2)) initial_reserve_delta,
        max(CASE WHEN l.priority=11 THEN l.reserve_after END)-cast(t.reserve_ending AS DECIMAL(38,2)) ending_reserve_delta,
        max(CASE WHEN l.priority=11 THEN l.cash_after END) ending_cash,
        max(CASE WHEN l.priority=11 THEN l.paid END)-cast(t.certificate_paid AS DECIMAL(38,2))-
            cast(t.redeposit AS DECIMAL(38,2)) residual_delta
        FROM saved_totals t JOIN money_ledger l USING(collection_end)
        GROUP BY t.collection_end,t.available_funds,t.reserve_beginning,t.reserve_ending,t.certificate_paid,t.redeposit
        ORDER BY t.collection_end'''
    total_checks=[{'collection_end':row[0],'cash_delta':str(row[1]),'initial_cash_delta':str(row[2]),
        'initial_reserve_delta':str(row[3]),'ending_reserve_delta':str(row[4]),'ending_cash':str(row[5]),
        'residual_delta':str(row[6]),'pass':all(v==0 for v in row[1:])} for row in con.execute(total_sql).fetchall()]
    checks=stage_checks+links+balance_checks+total_checks
    output=root/'artifacts/private'/('abs-waterfall-audit-'+uuid.uuid4().hex[:12]);output.mkdir(parents=True)
    result={'audit_id':output.name,'waterfall_id':identifier,'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL',
        'created_at':timestamp(),'ledger_stage_rows':len(ledger),'tranche_balance_rows':len(balances),
        'stage_checks':stage_checks,'continuity_checks':links,'balance_checks':balance_checks,'period_checks':total_checks,
        'failed_checks':sum(not c['pass'] for c in checks),'sql':{'stage':stage_sql,'continuity':continuity_sql,'balance':balance_sql,'period':total_sql},
        'waterfall_receipt_sha256':sha256(root/'artifacts/private'/identifier/'waterfall-complete.json'),
        'method_sha256':sha256(Path(__file__)),'visibility':'private','public_release_approved':False,
        'limits':['Independent state/money accounting SQL, not independent certification of legal priorities or due-input completeness',
            'Reserve deposit is internal transfer: excluded from external cash sum and retained in ending reserve',
            'Conditional replay assumptions and unsupported branches remain those of the verified waterfall receipt']}
    write_new(output/'audit.json',result);con.close()
    print(json.dumps({k:result[k] for k in ('audit_id','status','ledger_stage_rows','tranche_balance_rows','failed_checks')}))
    print('Independent SQL check rows:',len(checks))


if __name__=='__main__':audit(sys.argv[1])
