"""Every annual filing/two explicit principal families vs raw companyfacts."""
import json
from collections import Counter
from decimal import Decimal,localcontext
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import uuid4
from credit_atlas.workspace import read_json,sha256,write_new

SUFFIXES=['InNextTwelveMonths','InYearTwo','InYearThree','InYearFour','InYearFive','AfterYearFive']
KEYS=['year_1','year_2','year_3','year_4','year_5','after_5']
def tags(family):
    if family=='debt_only':return ['LongTermDebtMaturitiesRepaymentsOfPrincipal'+s for s in SUFFIXES]
    return ['LongTermDebtAndCapitalLeaseObligationsRepaymentsOfPrincipalInNextTwelveMonths']+['LongTermDebtAndCapitalLeaseObligationsMaturitiesRepaymentsOfPrincipal'+s for s in SUFFIXES[1:]]

root=Path.cwd();case=root/'artifacts/private/sec-case-33077fe45722';statements=read_json(case/'annual-statements.json')
normalization=root/'artifacts/private/sec-normalization-acceptance-e466059ee35f/receipt.json';proof=read_json(normalization)
assert proof['status']=='PASS' and all(sha256(root/p)==digest for p,digest in proof['inputs_sha256'].items())
source=root/'data/private/sec/sec-source-13cf03606e0c';acquisition=read_json(source/'acquisition-complete.json')
raw={s['cik']:json.loads((source/s['file']).read_text(),parse_float=Decimal) for s in acquisition['files'] if s['kind']=='companyfacts'}
scopes=[];states=Counter();summaries=Counter();candidates=0
with localcontext() as ctx:
 ctx.prec=80
 for statement in statements:
  for family in ['debt_only','debt_and_capital_lease']:
   query={'view_id':'sec-view-b92d9914f1dc','cik':statement['cik'],'accession':statement['accession'],'asof':'2026-10-15','debt_scope':family}
   with urlopen('http://127.0.0.1:8770/api/sec-debt?'+urlencode(query),timeout=120) as response:r=json.load(response)
   assert r['filters']=={k:v for k,v in query.items() if k!='view_id'} and not any(r['qualification'].values())
   assert r['statement']=={k:statement[k] for k in ['cik','accession','report_date','filing_date','form','filing_url']}
   assert [b['bucket'] for b in r['buckets']]==KEYS
   values=[]
   for bucket,concept in zip(r['buckets'],tags(family)):
    definition=raw[statement['cik']]['facts'].get('us-gaap',{}).get(concept)
    observations=definition.get('units',{}).get('USD',[]) if definition else []
    selected=[(i,f) for i,f in enumerate(observations) if f['accn']==statement['accession'] and f['end']==statement['report_date'] and f['filed']==statement['filing_date'] and f['form']==statement['form'] and f.get('start') is None]
    signature={Decimal(f['val']) for _,f in selected};status='missing' if not selected else 'supported' if len(signature)==1 else 'ambiguous'
    expected_evidence=[{'taxonomy':'us-gaap','concept':concept,'unit':'USD','source_ordinal':i,'start_date':None,'end_date':f['end'],
       'value_exact':format(Decimal(f['val']),'f'),'filed_date':f['filed'],'form':f['form'],'accession':f['accn']} for i,f in selected]
    field=bucket['field'];assert field['concept']==concept and field['status']==status and field['evidence']==expected_evidence
    assert field['taxonomy']=='us-gaap' and field['unit']=='USD' and field['start_date'] is None and field['end_date']==statement['report_date']
    value=Decimal(selected[0][1]['val']) if status=='supported' else None
    assert (Decimal(field['value_exact']) if field['value_exact'] is not None else None)==value
    expected_definition={'label':definition.get('label'),'description':definition.get('description'),'units':list(definition['units'])} if definition else {'label':None,'description':None,'units':[]}
    assert bucket['definition']==expected_definition
    values.append(value);states[status]+=1;candidates+=len(selected)
   supported=[v for v in values if v is not None];negative=any(v<0 for v in supported);complete=len(supported)==6 and not negative
   subtotal=sum(supported,Decimal(0)) if supported else None
   expected_status='INVALID_NEGATIVE_BUCKET' if negative else 'COMPLETE_ZERO_SCHEDULE' if complete and subtotal==0 else 'COMPLETE_DISCLOSED_SCHEDULE' if complete else 'PARTIAL_DISCLOSED_SCHEDULE'
   summary=r['summary'];assert summary['status']==expected_status and summary['supported_buckets']==len(supported) and summary['requested_buckets']==6
   for key,expected in [('supported_subtotal_exact',subtotal),('disclosed_schedule_total_exact',subtotal if complete else None)]:
    assert (Decimal(summary[key]) if summary[key] is not None else None)==expected
   positive=complete and subtotal>0
   assert (Decimal(summary['first_three_years_share_exact']) if summary['first_three_years_share_exact'] is not None else None)==(sum(values[:3])/subtotal if positive else None)
   for bucket,value in zip(r['buckets'],values):
    assert (Decimal(bucket['share_of_disclosed_schedule_exact']) if bucket['share_of_disclosed_schedule_exact'] is not None else None)==(value/subtotal if positive else None)
   assert summary['largest_buckets']==([k for k,v in zip(KEYS,values) if v==max(values)] if positive else [])
   summaries[expected_status]+=1;scopes.append({'cik':statement['cik'],'accession':statement['accession'],'family':family,'status':expected_status,'supported':len(supported)})
  if len(scopes)%20==0:print({'scopes_passed':len(scopes)},flush=True)
assert len(scopes)==134 and all(sha256(root/p)==digest for p,digest in proof['inputs_sha256'].items())
out=root/'artifacts/private'/('sec-maturity-acceptance-audit-'+uuid4().hex[:12])
write_new(out/'receipt.json',{'status':'PASS','scopes':scopes,'bucket_cells_checked':804,'bucket_statuses':dict(states),
 'candidate_evidence_entries':candidates,'summary_statuses':dict(summaries),'normalization_audit_sha256':sha256(normalization),
 'method_sha256':sha256(Path(__file__)),'debt_method_sha256':sha256(root/'src/credit_atlas/sec_debt.py'),
 'full_completion_proven':False,'remaining':'Current maturity Excel/native/app evidence and memo capture;facility cashflow qualification remains separate'})
print(out)
