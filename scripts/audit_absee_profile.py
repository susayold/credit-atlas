"""Arrow columnar audit independent of the row-wise structural profiler."""
from pathlib import Path
import json,sys,uuid
from datetime import datetime
from decimal import Decimal
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from credit_atlas.workspace import sha256

root=Path.cwd();profile_path=Path(sys.argv[1]).resolve()
profile=json.loads(profile_path.read_text());folder=root/'data/private/structured'/profile['source_id']
count=0;field_checks=0;sums=0
for p in profile['periods']:
    t=pq.read_table(folder/p['file']);assert t.num_rows==p['rows']
    assert t.column_names==p['columns'];count+=t.num_rows
    for field in t.column_names:
        a=t[field]
        empty=pc.sum(pc.cast(pc.fill_null(pc.equal(pc.utf8_trim_whitespace(a),''),False),pa.int64())).as_py()
        assert a.null_count+(empty or 0)==p['missing_by_field'][field];field_checks+=1
    for field,total in p['money_sums_exact'].items():
        actual=pc.sum(pc.cast(t[field],pa.decimal128(38,10))).as_py()
        assert actual==Decimal(total);sums+=1
    for ending in pc.unique(t['reportingPeriodEndingDate']).to_pylist():
        assert datetime.strptime(ending,'%m-%d-%Y').date().isoformat()==p['report_date']
    combined=pc.binary_join_element_wise(t['assetTypeNumber'],t['assetNumber'],pa.scalar('|',type=pa.large_string()))
    assert pc.count_distinct(combined).as_py()==p['unique_keys']
    assert t.num_rows-pc.count_distinct(combined).as_py()==p['duplicate_key_rows']
out=root/'artifacts/private'/('absee-profile-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
(out/'receipt.json').write_text(json.dumps({'status':'PASS','profile_sha256':sha256(profile_path),
    'source_rows_compared':count,'field_missingness_checks':field_checks,'exact_money_sum_checks':sums,
    'source_value_fidelity_verified':False,'raw_xml_acquired':False,'scope':'Checks local Parquet projection only; not original SEC XML.'},indent=2),encoding='utf8')
print(out)
