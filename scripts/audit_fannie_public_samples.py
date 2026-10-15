"""Independent DuckDB CSV reader reconciles the Python/csv source profile."""
from collections import Counter
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.workspace import read_json,sha256,write_new
root=Path(__file__).resolve().parents[1]
profile=root/'artifacts/private/fannie-public-profile-fafc20762187/profile.json'
assert sha256(profile)=='e2575f225eeffc6d99beee07f5165c1b3a7c1a34e85d3c09f1f5d2c2ebed128e'
p=read_json(profile);source=root/'data/private/mortgage'/p['source_id']
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
con=duckdb.connect();con.execute("SET memory_limit='128MB'")
fields=0;cells=0;rows_checked=0
for item in p['profiles']:
    file=source/item['file'];record=next(x for x in p['sources'] if x['file']==item['file']);assert sha256(file)==record['sha256']
    rows=con.execute('SELECT * FROM read_csv(?,header=?,delim=?,all_varchar=true,nullstr=\'__NO_SOURCE_NULL__\')',[str(file),item['header_present'],item['delimiter']]).fetchall()
    assert len(rows)==item['rows'] and all(len(r)==item['columns'] and all(v is not None for v in r) for r in rows)
    for i,q in enumerate(item['quality']):
        assert sum(r[i]=='' for r in rows)==q['blank_cells']
        assert dict(sorted(Counter(r[i] for r in rows if r[i].strip().lower() in {'null','na','n/a'}).items()))==q['literal_null_tokens']
        fields+=1
    key=1 if item['family']=='single-family' else 0
    assert len(set(r[key] for r in rows))==item['loan_count']
    if item['family']=='single-family':
        assert dict(sorted(Counter(r[39] for r in rows).items()))==item['raw_delinquency_counts']
        assert dict(sorted(Counter(r[43] for r in rows).items()))==item['raw_zero_balance_counts']
        assert len(rows)-len(set((r[1],r[2]) for r in rows))==item['duplicate_loan_month_rows']
        expected=Counter((r[2],r[39]) for r in rows)
        assert {(r['reporting_month_raw'],r['raw_delinquency']):r['records'] for r in item['monthly_cells']}==expected
    elif item['columns']==3:
        ratios=[Decimal(r[2]) for r in rows]
        assert str(min(ratios))==item['reported_dscr']['min_exact'] and str(max(ratios))==item['reported_dscr']['max_exact']
        assert sum(x<1 for x in ratios)==item['reported_dscr']['below_one']
        assert dict(sorted(Counter(r[1] for r in rows).items()))==item['years']
    else:
        names=[q['source_field'] for q in item['quality']];idx=names.index('Loan Payment Status')
        assert dict(sorted(Counter(r[idx] for r in rows).items()))==item['payment_status_counts']
    cells+=len(rows)*item['columns'];rows_checked+=len(rows)
con.close()
assert sha256(ledger)==before
out=root/'artifacts/private'/('fannie-public-audit-'+uuid4().hex[:12]);out.mkdir()
write_new(out/'receipt.json',{'status':'PASS','reader':'DuckDB independent of Python csv profile','rows_checked':rows_checked,'source_positions_checked':cells,'field_missingness_checked':fields,'source_hashes_verified':True,'ledger_unchanged':True,'model_training_performed':False,'full_population_qualification':False})
print(out);print(rows_checked,cells,fields)
