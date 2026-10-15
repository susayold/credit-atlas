"""Exact rational check using source JSON/Parquet and independently listed calendar."""
from pathlib import Path
from fractions import Fraction
from datetime import date,timedelta
import json,uuid
from urllib.request import urlopen
from urllib.parse import urlencode
import pyarrow.parquet as pq
from credit_atlas.workspace import sha256

root=Path.cwd();base='http://127.0.0.1:8770'
with urlopen(base+'/api/abs-views') as response:
    view=next(x['view_id'] for x in json.load(response)['views'] if x['status']=='verified')
with urlopen(base+'/api/abs-benchmark?'+urlencode({'view_id':view})) as response:report=json.load(response)
folder=root/'data/private/reference-rates'/report['source']['source_id']
raw=json.loads((folder/'sofrai.json').read_text(),parse_float=str)
rates={r['effectiveDate']:Fraction(str(r['average30day']))/100 for r in raw['refRates']}
# Reviewed US full-close dates in acquired SIFMA archive/current sections. Early closes excluded.
closed=set('2025-01-01 2025-01-20 2025-02-17 2025-04-18 2025-05-26 2025-06-19 2025-07-04 2025-09-01 2025-10-13 2025-11-11 2025-11-27 2025-12-25 2026-01-01 2026-01-19 2026-02-16 2026-05-25 2026-06-19 2026-07-03 2026-09-07 2026-10-12 2026-11-11 2026-11-26 2026-12-25'.split())
assert closed=={d for c in report['calendar'] for d in c['full_closes']}
case=root/'artifacts/private'/report['case_id'];periods=json.loads((case/'case-complete.json').read_text())['periods']
metrics=pq.read_table(case/'reported_metrics.parquet').to_pylist()
checks=[]
for p in periods:
    days=[];cursor=date.fromisoformat(p['accrual_start'])
    while len(days)<2:
        cursor-=timedelta(days=1)
        if cursor.weekday()<5 and str(cursor) not in closed:days.append(str(cursor))
    fixing=days[-1];rate=rates[fixing]
    coupon=max(Fraction(0),rate+Fraction(33,10000))
    def value(key):
        r=next(r for r in metrics if r['collection_end']==p['collection_end'] and r['section']=='note_slot' and r['slot']=='A-2b' and r['metric']==key)
        return Fraction(r['value'])
    actual_days=(date.fromisoformat(p['distribution_date'])-date.fromisoformat(p['accrual_start'])).days
    exact_interest=value('beginning_balance')*coupon*actual_days/360
    cents=exact_interest*100;rounded=(2*cents.numerator+cents.denominator)//(2*cents.denominator)
    row=next(r for r in report['rows'] if r['collection_end']==p['collection_end'])
    assert row['adjustment_date']==fixing and Fraction(row['administrator_fraction_exact'])==rate
    assert abs(value('sofr_rate')-rate)<=Fraction(1,10**15)
    assert abs(value('coupon')-coupon)<=Fraction(1,10**15)
    assert Fraction(row['reported_interest_due_exact'])==Fraction(rounded,100)
    assert Fraction(row['independent_base_interest_exact'])==Fraction(rounded,100)
    checks.append({'collection_end':p['collection_end'],'fixing':fixing,'rate_fraction':str(rate),
        'coupon_fraction':str(coupon),'interest_fraction_before_rounding':str(exact_interest),
        'rounded_interest_cents':rounded,'status':'PASS'})
out=root/'artifacts/private'/('abs-benchmark-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
receipt={'status':'PASS','checks':checks,'periods':len(checks),'source_receipt_sha256':report['source_receipt_sha256'],
    'api_module_not_imported':True,'calendar_source':'Manually reviewed SIFMA US full-close rows; independent date countdown',
    'rational_interest_no_decimal_helpers':True,'method_sha256':sha256(Path(__file__)),
    'historical_1500_vintage_verified':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(out);print('PASS',len(checks),'periods')
