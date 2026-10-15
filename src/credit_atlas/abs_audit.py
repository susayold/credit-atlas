"""Independent raw-XLS versus canonical-cell audit and source arithmetic in SQL."""
import uuid
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import xlrd

from .abs_servicer import verify_case, verify_source
from .workspace import contained, sha256, timestamp, write_new


def audit(root, identifier):
    case=verify_case(root,identifier)
    source,_=verify_source(root,case['source_id'])
    rows=[]
    for filename in ('WOART_2025-A_2025.xls','WOART_2025-A_2026.xls'):
        book=xlrd.open_workbook(source/filename,formatting_info=True)
        for sheet in book.sheets():
            for r in range(sheet.nrows):
                for c in range(sheet.ncols):
                    cell=sheet.cell(r,c)
                    if cell.ctype == xlrd.XL_CELL_EMPTY:
                        continue
                    rows.append({'file':filename,'sheet':sheet.name,'row':r+1,'column':c+1,
                        'cell_type':cell.ctype,'raw_value':str(cell.value),
                        'number_format':book.format_map[book.xf_list[cell.xf_index].format_key].format_str})
    canonical=pq.read_table(root/'artifacts/private'/identifier/'source_cells.parquet')
    connection=duckdb.connect()
    connection.register('original',pa.Table.from_pylist(rows))
    connection.register('canonical',canonical)
    mismatch=connection.execute('''SELECT count(*) FROM (
        (SELECT * FROM original EXCEPT ALL SELECT * FROM canonical)
        UNION ALL (SELECT * FROM canonical EXCEPT ALL SELECT * FROM original))''').fetchone()[0]
    # Bind explicit source cells, not the adapter's semantic keys or its saved checks.
    connection.execute('''CREATE TEMP TABLE cells AS
        SELECT file,sheet,row,cast(round(cast(raw_value AS DECIMAL(38,10)),2) AS DECIMAL(38,2)) amount
        FROM original WHERE "column"=2 AND cell_type=2''')
    expressions=[('pool', 'r15-r16-r17-r18-r19-r20'),('beginning_pool','r15-r13-r14'),
        ('net_loss','r17-r39-r40'),('delinquency','r29+r30+r31+r32-r33'),
        ('available_funds','r58+r59+r60+r61-r62'),('cash','r62-r82'),
        ('distribution', '+'.join('r'+str(r) for r in range(65,81))+'-r82'),
        ('note_balance','r94-r95-r96'),('note_payment','r154+r155-r156'),
        ('principal_distribution','r67+r69+r71+r73+r75+r77-r155'),
        ('interest_distribution','r66+r68+r70+r72+r74-r154'),
        ('reserve','r275+r276+r277+r278-r279'),('reserve_change','r279-r275-r280')]
    for slot,bal,pay in zip(('A1','A2a','A2b','A3','A4','B','C','D','E'),range(98,147,6),(158,164,170,177,183,189,195,201,207)):
        offset=1 if slot=='A2b' else 0
        expressions += [(slot+'_balance',f'r{bal+1}-r{bal+2}-r{bal+3}'),
                        (slot+'_payment',f'r{pay+2+offset}+r{pay+3+offset}-r{pay+4+offset}'),
                        (slot+'_principal_sections',f'r{bal+2}-r{pay+3+offset}')]
    for label,bal_offset,pay_offset,total in [('beginning',1,None,94),('ending',3,None,96),('principal',2,None,95),
        ('interest',None,2,154),('payment_principal',None,3,155),('total_paid',None,4,156)]:
        positions=([bal+bal_offset for bal in range(98,147,6)] if bal_offset is not None else
                   [pay+pay_offset+(1 if pay==170 else 0) for pay in (158,164,170,177,183,189,195,201,207)])
        expressions.append(('slots_'+label,'+'.join('r'+str(r) for r in positions)+'-r'+str(total)))
    positions=sorted(set(int(n) for _,expression in expressions for n in __import__('re').findall(r'r(\d+)',expression)))
    select=','.join(f'max(CASE WHEN row={r} THEN amount END) AS r{r}' for r in positions)
    connection.execute('CREATE TEMP TABLE source_amounts AS SELECT file,sheet,'+select+' FROM cells GROUP BY file,sheet')
    arithmetic=[]
    for name,expression in expressions:
        results=connection.execute('SELECT file,sheet,('+expression+') delta FROM source_amounts ORDER BY file,sheet').fetchall()
        for filename,sheet,delta in results:
            arithmetic.append({'file':filename,'sheet':sheet,'check':name,'delta_usd':None if delta is None else str(delta),
                'pass':delta is not None and abs(delta)<=__import__('decimal').Decimal('.01')})
    # Accounts never use currency rounding or decimal tolerances.
    accounts=connection.execute('''SELECT file,sheet,
        sum(CASE WHEN row=15 THEN cast(raw_value AS DECIMAL(38,10))
                 WHEN row IN (16,17,18,20) THEN -cast(raw_value AS DECIMAL(38,10)) ELSE 0 END) delta
        FROM original WHERE "column"=3 AND cell_type=2 AND row IN (15,16,17,18,20)
        GROUP BY file,sheet ORDER BY file,sheet''').fetchall()
    for filename,sheet,delta in accounts:
        arithmetic.append({'file':filename,'sheet':sheet,'check':'accounts','delta_accounts':str(delta),'pass':delta==0})
    identifier='abs-audit-'+uuid.uuid4().hex[:12]
    output=contained(root,'artifacts/private/'+identifier);output.mkdir(parents=True)
    report={'audit_id':identifier,'case_id':case['case_id'],'status':'PASS' if mismatch==0 and all(x['pass'] for x in arithmetic) else 'FAIL',
        'created_at':timestamp(),'source_cells':len(rows),'source_numeric_cells':sum(r['cell_type']==2 for r in rows),
        'source_date_cells':sum(r['cell_type']==3 for r in rows),'source_text_cells':sum(r['cell_type']==1 for r in rows),
        'styled_blank_cells':sum(r['cell_type']==6 for r in rows),'different_cell_rows':mismatch,
        'arithmetic':arithmetic,'failed_checks':sum(not x['pass'] for x in arithmetic),
        'case_receipt_sha256':sha256(root/'artifacts/private'/case['case_id']/'case-complete.json'),
        'audit_method_sha256':sha256(Path(__file__)),'visibility':'private','public_release_approved':False,
        'limits':['Independent source-cell multiset and source accounting checks, not contractual waterfall replay',
                  'Publisher formula caches read as source evidence; formula calculation not certified',
                  'USD rounded to cents in independent SQL; NULL inputs fail checks']}
    write_new(output/'audit.json',report)
    connection.close()
    return report
