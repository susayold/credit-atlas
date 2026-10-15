"""Check all expense choices/cutoffs/windows against raw SEC observations."""
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4
from browser_sec_coverage_qa import audit as audit_raw_candidates
from audit_sec_ratio_trend_acceptance import dec_ratio
from credit_atlas.workspace import read_json,sha256,write_new

root=Path.cwd();scopes=[];states=Counter();candidates=0;fields=0
normalized=root/'artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json'
proof=read_json(normalized);assert proof['status']=='PASS'
assert all(sha256(root/p)==digest for p,digest in proof['inputs_sha256'].items())
for cik in ['0000320193','0000789019','0000037996','0001467858']:
    for concept in ['InterestExpenseNonoperating','InterestExpense','InterestExpenseDebt']:
        plans=[('2026-10-15',y) for y in ['3','5','10']]+[('2018-01-01','10'),('2000-01-01','10')]
        for cutoff,years in plans:
            query={'view_id':'sec-view-b92d9914f1dc','cik':cik,'asof':cutoff,'years':years,'interest_concept':concept}
            with urlopen('http://127.0.0.1:8770/api/sec-coverage?'+urlencode(query),timeout=120) as response:r=json.load(response)
            assert r['filters']=={k:v for k,v in query.items() if k!='view_id'}
            assert not any(r['qualification'].values())
            supported=audit_raw_candidates(root,r)
            for p in r['periods']:
                if not p['fields']:continue
                assert p['fields']['interest_expense']['concept']==concept
                assert p['fields']['interest_paid']['concept']=='InterestPaid'
                assert p['fields']['interest_paid_net']['concept']=='InterestPaidNet'
                for f in p['fields'].values():fields+=1;candidates+=len(f['evidence'])
                for name,n in [('operating_income_coverage','operating_income'),('reported_ocf_coverage','operating_cashflow')]:
                    numerator=p['fields'][n];denominator=p['fields']['interest_expense'];value=p['ratios'][name]
                    status='supported'
                    if numerator['status']!='supported' or denominator['status']!='supported':status='missing_or_ambiguous_input'
                    elif (numerator['start_date'],numerator['end_date'])!=(denominator['start_date'],denominator['end_date']):status='period_mismatch'
                    elif Decimal(denominator['value_exact'])<=0:status='nonpositive_interest_expense'
                    assert value['status']==status
                    if status=='supported':assert Decimal(value['value_exact'])==dec_ratio(numerator['value_exact'],denominator['value_exact'])
                    else:assert value['value_exact'] is None
                    assert value['formula']==numerator['concept']+' / '+concept
                    states[status]+=1
            scopes.append({'cik':cik,'concept':concept,'cutoff':cutoff,'years':years,'periods':len(r['periods']),'supported_ratios':supported})
    print({'cik':cik,'scopes':len(scopes)},flush=True)
assert all(sha256(root/p)==digest for p,digest in proof['inputs_sha256'].items())
out=root/'artifacts/private'/('sec-coverage-scope-audit-'+uuid4().hex[:12])
write_new(out/'receipt.json',{'status':'PASS','scopes':scopes,'field_cells_checked':fields,
    'candidate_evidence_checked':candidates,'ratio_status_counts':dict(states),
    'normalization_audit_sha256':sha256(normalized),'method_sha256':sha256(Path(__file__)),
    'helper_sha256':{'browser_sec_coverage_qa':sha256(root/'scripts/browser_sec_coverage_qa.py'),
                     'audit_sec_ratio_trend_acceptance':sha256(root/'scripts/audit_sec_ratio_trend_acceptance.py')},
    'coverage_method_sha256':sha256(root/'src/credit_atlas/sec_coverage.py'),
    'full_completion_proven':False,'remaining':'Current complete Analysis/Facts Excel qualification and requirement-level acceptance'})
print(out)
