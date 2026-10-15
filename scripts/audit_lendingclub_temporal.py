"""Independent Arrow temporal census; no source cutoff or label substitution."""
import gzip,json,uuid
from collections import Counter
from pathlib import Path
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.compute as pc
from credit_atlas.workspace import sha256
root=Path.cwd();path=root/'artifacts/private/lendingclub-temporal-profile-1333a9b4a286/profile.json'
assert sha256(path)=='8b4b6cbee90ef9b9ff09f29f62a183c28a000cf0cb9725e23582ecc7ec529425'
doc=json.loads(path.read_text(encoding='utf8'));file=root/'data/private/retail'/doc['source_id']/doc['source_file']['file'];assert sha256(file)==doc['source_file']['sha256']
out=root/'artifacts/private'/('lendingclub-temporal-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
columns=['issue_d','loan_status','term','last_pymnt_d','last_credit_pull_d','next_pymnt_d','member_id']
date_fields=['issue_d','last_pymnt_d','last_credit_pull_d','next_pymnt_d']
stats={k:{'valid':0,'min':None,'max':None,'nonblank_unparsed':0} for k in date_fields};groups=Counter();rows=0;missing_member=0;unsupported_terms=0
def ordinal(d):return pc.add(pc.multiply(pc.year(d),12),pc.month(d))
def flags(x):return pc.cast(pc.fill_null(x,False),pa.int64())
with gzip.open(file,'rb') as stream:
    reader=csv.open_csv(stream,read_options=csv.ReadOptions(block_size=8*1024**2),parse_options=csv.ParseOptions(newlines_in_values=True),
        convert_options=csv.ConvertOptions(include_columns=columns,column_types={n:pa.string() for n in columns},null_values=[],strings_can_be_null=False))
    for batch in reader:
        t=pa.Table.from_batches([batch]);rows+=batch.num_rows;dates={}
        for name in date_fields:
            text=t[name]
            # Windows Arrow does not parse abbreviated English months here.
            # Translate the literal source month before numeric date parsing;
            # day1 is only a month-arithmetic anchor,not an observed source day.
            parts=pc.extract_regex(text,pattern=r'^(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(?P<year>[0-9]{4})$')
            month_index=pc.index_in(pc.struct_field(parts,'month'),value_set=pa.array(['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']))
            month_number=pc.utf8_lpad(pc.cast(pc.add(month_index,1),pa.string()),width=2,padding='0')
            canonical=pc.binary_join_element_wise(pc.struct_field(parts,'year'),month_number,pa.scalar('01'),'-')
            d=pc.strptime(canonical,format='%Y-%m-%d',unit='s',error_is_null=True);dates[name]=d
            s=stats[name];s['valid']+=pc.sum(pc.cast(pc.is_valid(d),pa.int64())).as_py()
            s['nonblank_unparsed']+=pc.sum(flags(pc.and_(pc.is_null(d),pc.not_equal(pc.utf8_trim_whitespace(text),'')))).as_py()
            mm=pc.min_max(d).as_py()
            if mm['min'] is not None:s['min']=min(s['min'],mm['min']) if s['min'] else mm['min'];s['max']=max(s['max'],mm['max']) if s['max'] else mm['max']
        term=pc.utf8_trim_whitespace(pc.replace_substring(t['term'],'months',''))
        term=pc.cast(pc.if_else(pc.equal(term,''),pa.scalar(None,type=pa.string()),term),pa.int32())
        unsupported_terms+=pc.sum(flags(pc.or_(pc.is_null(term),pc.invert(pc.is_in(term,value_set=pa.array([36,60],type=pa.int32())))))).as_py()
        missing_member+=pc.sum(flags(pc.equal(t['member_id'],''))).as_py()
        booked=dates['issue_d'];payment=dates['last_pymnt_d'];pull=dates['last_credit_pull_d']
        # Calendar month labels do not need a timezone database on Windows.
        month_label=pc.binary_join_element_wise(pc.cast(pc.year(booked),pa.string()),pc.utf8_lpad(pc.cast(pc.month(booked),pa.string()),width=2,padding='0'),'-')
        values=pa.table({'issue_month':month_label,'source_loan_status':t['loan_status'],'contract_term_months':term,
            'records':pa.array([1]*batch.num_rows,type=pa.int64()),'last_payment_month_available':flags(pc.is_valid(payment)),
            'last_payment_span_at_least_12m':flags(pc.greater_equal(pc.subtract(ordinal(payment),ordinal(booked)),12)),
            'last_payment_before_booking':flags(pc.less(payment,booked)),'last_credit_pull_before_booking':flags(pc.less(pull,booked))})
        keys=['issue_month','source_loan_status','contract_term_months'];metrics=[n for n in values.column_names if n not in keys]
        result=values.group_by(keys).aggregate([(n,'sum') for n in metrics])
        for r in result.to_pylist():
            key=tuple(r[k] for k in keys)
            for metric in metrics:groups[(key,metric)]+=r[metric+'_sum']
    assert not stream.read(1)
issues=[]
for expected in doc['date_profiles']:
    s=stats[expected['field']];actual=[s['valid'],s['min'].strftime('%Y-%m'),s['max'].strftime('%Y-%m'),s['nonblank_unparsed']]
    if actual!=[expected['valid_months'],expected['min_observed_month'],expected['max_observed_month'],expected['nonblank_unparsed']]:issues.append(expected['field'])
expected_groups=Counter()
for r in doc['cohort_term_payment_span']:
    key=(r['issue_month'],r['source_loan_status'],r['contract_term_months'])
    for metric in ['records','last_payment_month_available','last_payment_span_at_least_12m','last_payment_before_booking','last_credit_pull_before_booking']:expected_groups[(key,metric)]=r[metric]
if groups!=expected_groups:issues.append('cohort/term/span/chronology counts')
if (rows,missing_member,unsupported_terms)!=(doc['source_rows'],doc['missing_member_id'],doc['unsupported_or_missing_contract_term']):issues.append('source support counts')
unchanged=sha256(ledger)==before
result={'status':'PASS' if not issues and unchanged else 'ISSUES_FOUND','issues':issues,'date_profiles_checked':4,'cohort_groups_checked':len(doc['cohort_term_payment_span']),
    'cohort_metrics_checked':len(expected_groups),'rows':rows,'ledger_unchanged':unchanged,'scope':'Independent Arrow date parsing/month ordinals/chronology;not observation cutoff,continuous follow-up or PD12 maturity proof'}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(out);print(result)
if result['status']!='PASS':raise SystemExit(1)
