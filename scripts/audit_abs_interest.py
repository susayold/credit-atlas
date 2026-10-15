"""Independent exact-rational benchmark for reported WOART base interest."""
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import json
import sys
import uuid

import pyarrow.parquet as pq

from credit_atlas.abs_contract import verify
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def audit(identifier):
    root=app_root();terms_report=verify(root,identifier)
    case_id=terms_report['case_id'];folder=root/'artifacts/private'/case_id
    case=json.loads((folder/'case-complete.json').read_text())
    rows=pq.read_table(folder/'reported_metrics.parquet').to_pylist()
    values={(r['collection_end'],r['section'],r['slot'],r['metric']):r['value'] for r in rows}
    # Separately transcribed cover constants; no call to interest(), coupon() or cents().
    fixed_rates={'A-1':'0.04411','A-2a':'0.0449','A-3':'0.0473','A-4':'0.0486','B':'0.0508','C':'0.0517'}
    previous=date(2025,1,29);checks=[]
    for period in case['periods']:
        end=period['collection_end'];payment=date.fromisoformat(period['distribution_date'])
        for slot in ('A-1','A-2a','A-2b','A-3','A-4','B','C'):
            balance=Fraction(values[(end,'note_slot',slot,'beginning_balance')])
            rate=(max(Fraction(0),Fraction(values[(end,'note_slot',slot,'sofr_rate')])+Fraction(33,10000))
                  if slot=='A-2b' else Fraction(fixed_rates[slot]))
            days=(payment-previous).days if slot in ('A-1','A-2b') else (16 if end=='2025-01-31' else 30)
            exact=balance*rate*Fraction(days,360)
            cent_fraction=exact*100
            rounded=(2*cent_fraction.numerator+cent_fraction.denominator)//(2*cent_fraction.denominator)
            expected=Decimal(rounded)/Decimal(100)
            observed=Decimal(values[(end,'note_slot',slot,'interest_paid')])
            implementation=next(c for c in terms_report['checks'] if c['collection_end']==end and c['check']=='base_interest_'+slot)
            delta=observed-expected
            checks.append({'collection_end':end,'slot':slot,'days':days,'rate_fraction':str(rate),
                'unrounded_interest_numerator':str(exact.numerator),'unrounded_interest_denominator':str(exact.denominator),
                'rational_expected_usd':str(expected),'reported_paid_usd':str(observed),'delta_usd':str(delta),
                'implementation_expected_usd':implementation['expected'],
                'pass':abs(delta)<=Decimal('.01') and Decimal(implementation['expected'])==expected})
        previous=payment
    output=root/'artifacts/private'/('abs-interest-audit-'+uuid.uuid4().hex[:12]);output.mkdir(parents=True)
    report={'audit_id':output.name,'terms_id':identifier,'case_id':case_id,'created_at':timestamp(),
        'status':'PASS' if all(c['pass'] for c in checks) else 'FAIL','checks':checks,
        'failed_checks':sum(not c['pass'] for c in checks),
        'maximum_source_difference_usd':str(max(abs(Decimal(c['delta_usd'])) for c in checks)),
        'terms_receipt_sha256':sha256(root/'artifacts/private'/identifier/'terms-complete.json'),
        'method_sha256':sha256(Path(__file__)),'visibility':'private','public_release_approved':False,
        'limits':['Base interest benchmark only; no carryover/acceleration or independent benchmark-fixing validation',
                  'Rate input for floating tranche is reported SOFR; interpreted under original prospectus spread/floor',
                  'Exact rational arithmetic versus Decimal implementation; source cash flows remain reported values']}
    write_new(output/'audit.json',report)
    print(json.dumps({k:report[k] for k in ('audit_id','status','failed_checks','maximum_source_difference_usd')}))
    print('Exact-rational checks:',len(checks))


if __name__=='__main__':audit(sys.argv[1])
