"""Bounded Arrow/GZIP census, source grains separate; no acceptance/PD inference."""
import csv,gzip,json,re,time,uuid
from collections import Counter
from pathlib import Path
import pyarrow as pa
import pyarrow.csv as pcsv
import pyarrow.compute as pc
from credit_atlas.workspace import read_json,sha256,write_new
root=Path.cwd();folder=root/'data/private/retail/lendingclub-full-source-3954d375d972'
receipt=read_json(folder/'acquisition-complete.json')
assert sha256(folder/'acquisition-complete.json')=='8c75b6f45be94ccc7e610f3be8aa1f51246b48bc69331dea8db518c69f657d55'
out=root/'artifacts/private'/('lendingclub-full-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
profiles=[];missing_tokens=pa.array(['','NA','N/A','null','NULL','NaN','nan','None'])
months={name:f'{i:02d}' for i,name in enumerate(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],1)}
for kind in ['accepted','rejected']:
    source=next(s for s in receipt['sources'] if s['file'].startswith(kind));path=folder/source['file']
    assert sha256(path)==source['sha256']
    with gzip.open(path,'rt',encoding='utf-8-sig',newline='') as f:header=next(csv.reader(f))
    if len(header)!=len(set(header)):raise ValueError('Duplicate source header')
    counts=Counter();groups=Counter();rows=0;malformed=[];last=time.monotonic()
    def invalid(row):
        malformed.append({'expected_columns':row.expected_columns,'actual_columns':row.actual_columns,'parser_line':row.number});return 'skip'
    with gzip.open(path,'rb') as stream:
        reader=pcsv.open_csv(stream,read_options=pcsv.ReadOptions(block_size=8*1024**2),
            parse_options=pcsv.ParseOptions(newlines_in_values=True,invalid_row_handler=invalid),
            convert_options=pcsv.ConvertOptions(column_types={n:pa.string() for n in header},null_values=[],strings_can_be_null=False))
        keys=['issue_d','loan_status'] if kind=='accepted' else ['Application Date','Policy Code']
        counter='loan_amnt' if kind=='accepted' else 'Amount Requested'
        for batch in reader:
            rows+=batch.num_rows;t=pa.Table.from_batches([batch])
            for name in header:
                values=pc.utf8_trim_whitespace(t[name]);blank=pc.is_in(values,value_set=missing_tokens)
                counts[name]+=pc.sum(pc.cast(blank,pa.int64())).as_py()
            grouped=t.group_by(keys).aggregate([(counter,'count')])
            for r in grouped.to_pylist():groups[tuple(r[k].strip() for k in keys)]+=r[counter+'_count']
            if time.monotonic()-last>12:print(kind,'profiled records',rows,flush=True);last=time.monotonic()
        # Python GzipFile verifies trailer CRC/ISIZE when Arrow reaches EOF.
        remainder=stream.read(1)
        if remainder:raise ValueError('CSV reader did not consume complete GZIP source')
        uncompressed_bytes=stream.tell()
    expected_name=kind+'_2007_to_2018q4.csv/'+kind+'_2007_to_2018Q4.csv'
    expected=next(f['totalBytes'] for f in receipt['publisher_file_inventory']['datasetFiles'] if f['name']==expected_name)
    if uncompressed_bytes!=expected:raise ValueError('Publisher uncompressed byte size mismatch')
    monthly=Counter();bad_dates=Counter();statuses=Counter()
    for (date,category),n in groups.items():
        if kind=='accepted':
            m=re.fullmatch(r'([A-Z][a-z]{2})-(20\d{2})',date);period=m[2]+'-'+months[m[1]] if m and m[1] in months else None
        else:
            from datetime import date as Date
            try:period=Date.fromisoformat(date).isoformat()[:7]
            except ValueError:period=None
        if period:monthly[(period,category)]+=n
        else:bad_dates[date]+=n
        statuses[category]+=n
    profiles.append({'kind':kind,'file':source['file'],'source_sha256':source['sha256'],'rows':rows,'columns':header,
        'raw_cell_positions':rows*len(header),'missing_counts':{n:counts[n] for n in header},
        'date_column':keys[0],'category_column':keys[1],'date_grain':'funded month' if kind=='accepted' else 'application day',
        'month_category_counts':[{'month':m,'source_category':c,'records':n} for (m,c),n in sorted(monthly.items())],
        'source_category_counts':dict(statuses),'invalid_or_missing_date_counts':dict(bad_dates),'malformed_rows':malformed,
        'uncompressed_bytes':uncompressed_bytes,'publisher_uncompressed_size_verified':True,'gzip_full_integrity_verified':True})
doc={'source_id':receipt['source_id'],'source_receipt_sha256':sha256(folder/'acquisition-complete.json'),'profiles':profiles,
    'ledger_unchanged':sha256(ledger)==before,'model_training_performed':False,'application_time_features_qualified':False,
    'fixed_horizon_target_qualified':False,'source_approval_rate_qualified':False,'original_issuer_fidelity_verified':False,
    'issuer_redistribution_rights_verified':False,'visibility':'private','public_release_approved':False,
    'limitations':['Accepted/funded issue-month grain differs from rejected application-day grain;counts do not define a comparable approval-rate denominator.',
        'Rejected records do not have counterfactual repayment outcomes;no default-label imputation or reject-inference qualification.',
        'Full source includes active/late statuses;current-status snapshot is not a fixed-horizon default event label.',
        'Payment/credit-pull/settlement dates are distinct from default event dates;do not substitute without a target contract.',
        'Publisher/helper code provenance does not certify original issuer bytes or historical feature availability.',
        'Publisher CC0 assertion does not certify issuer/bureau redistribution rights;private analysis only.']}
write_new(out/'profile.json',doc)
write_new(out/'receipt.json',{'status':'SOURCE_PROFILE_BUILT' if not any(p['malformed_rows'] for p in profiles) else 'SOURCE_PROFILE_WITH_ISSUES',
    'profile_sha256':sha256(out/'profile.json'),'rows':{p['kind']:p['rows'] for p in profiles},'gzip_integrity_verified':True,'ledger_unchanged':doc['ledger_unchanged']})
print(out);print(sha256(out/'profile.json'));print([(p['kind'],p['rows'],len(p['columns']),p['source_category_counts'],p['invalid_or_missing_date_counts']) for p in profiles])
