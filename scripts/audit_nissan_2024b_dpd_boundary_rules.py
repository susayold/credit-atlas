"""Compare literal and one-day-shifted Nissan certificate DPD bucket rules."""
from __future__ import annotations
import json,uuid
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import pyarrow.parquet as pq
from credit_atlas.workspace import contained,read_json,sha256,timestamp,write_new
from audit_nissan_2024b_certificate_tieout import profile_certificate,decimal
ROOT=Path(__file__).resolve().parents[1]
HISTORY="nissan-2024b-validation-panel-7cd3605b4e07"
PANEL="nissan-2024b-validation-panel-9534e22c34fc"
BUCKETS=("31-60 Days Delinquent","61-90 Days Delinquent","91-120 Days Delinquent","More than 120 Days")
ZERO=Decimal(0)
def D(v): return decimal(v) or ZERO
def literal(d): return BUCKETS[0] if d is not None and 31<=d<=60 else BUCKETS[1] if d is not None and 61<=d<=90 else BUCKETS[2] if d is not None and 91<=d<=120 else BUCKETS[3] if d is not None and d>120 else None
def shifted(d): return BUCKETS[0] if d is not None and 31<=d<60 else BUCKETS[1] if d is not None and 60<=d<90 else BUCKETS[2] if d is not None and 90<=d<=120 else BUCKETS[3] if d is not None and d>120 else None
def main():
 source=contained(ROOT,f"data/private/structured/{HISTORY}");panel=contained(ROOT,f"data/private/derived/{PANEL}")
 sr=read_json(source/"acquisition-complete.json");pm=read_json(panel/"dataset-complete.json")
 sm={x["report_date"][:7]:x for x in sr["reports"]};files={x["report_date"][:7]:x for x in pm["parquet_files"]}
 if set(sm)!=set(files) or len(files)!=23:raise ValueError("Nissan source/panel scope mismatch")
 results=[];counts=Counter()
 for month in sorted(files):
  x=files[month];path=contained(panel,x["file"])
  if path.stat().st_size!=x["bytes"] or sha256(path)!=x["sha256"]:raise ValueError(f"Panel hash mismatch: {month}")
  src=sm[month];meta=src["10d"]["ex99_1"];certpath=contained(source,meta["file"])
  if sha256(certpath)!=meta["sha256"]:raise ValueError(f"Certificate hash mismatch: {month}")
  cert=profile_certificate(certpath);calcs={rule:{b:{"count":0,"balance":ZERO} for b in BUCKETS} for rule in ("literal","shifted")}
  for batch in pq.ParquetFile(path).iter_batches(batch_size=8192,columns=["reportingPeriodActualEndBalanceAmount","currentDelinquencyStatus_days_past_due"]):
   for row in batch.to_pylist():
    bal=D(row.get("reportingPeriodActualEndBalanceAmount")); d=row.get("currentDelinquencyStatus_days_past_due")
    if bal<=ZERO or d is None:continue
    for rule,fn in (("literal",literal),("shifted",shifted)):
     name=fn(d)
     if name:calcs[rule][name]["count"]+=1;calcs[rule][name]["balance"]+=bal
  tieouts={}
  for rule in calcs:
   checks=[];deltas={}
   for name in BUCKETS:
    actual=calcs[rule][name];expected=cert["delinquency_buckets"][name]
    count_delta=actual["count"]-expected["contract_count"];bal_delta=actual["balance"]-Decimal(expected["balance"])
    checks.extend([count_delta==0,bal_delta==ZERO]);deltas[name]={"count_delta":count_delta,"balance_delta":str(bal_delta)}
   tieouts[rule]={"exact_field_checks":sum(checks),"total_checks":8,"buckets":deltas}
   counts[rule]+=sum(checks)
  results.append({"report_date":src["report_date"],"abs_ee_accession":src["abs_ee"]["accession"],"10d_accession":src["10d"]["accession"],"tieouts":tieouts,"source_day_60_count":calcs["literal"][BUCKETS[0]]["count"]-calcs["shifted"][BUCKETS[0]]["count"],"source_day_60_balance":str(calcs["literal"][BUCKETS[0]]["balance"]-calcs["shifted"][BUCKETS[0]]["balance"]),"source_day_90_count":(calcs["literal"][BUCKETS[1]]["count"]-calcs["shifted"][BUCKETS[1]]["count"])+(calcs["literal"][BUCKETS[0]]["count"]-calcs["shifted"][BUCKETS[0]]["count"]),"source_day_90_balance":str((calcs["literal"][BUCKETS[1]]["balance"]-calcs["shifted"][BUCKETS[1]]["balance"])+(calcs["literal"][BUCKETS[0]]["balance"]-calcs["shifted"][BUCKETS[0]]["balance"]))})
 output={"status":"NISSAN_2024B_DPD_BOUNDARY_RULES_COMPARED","issuer":sr["issuer"],"period_count":23,"source_receipt_sha256":sha256(source/"acquisition-complete.json"),"panel_manifest_sha256":sha256(panel/"dataset-complete.json"),"aggregate_exact_checks":dict(counts),"periods":results,"candidate_rule":"Shift certificate boundaries one day earlier: bucket 31-60 receives source DPD 31-59; 61-90 receives 60-89; 91-120 receives 90-120. This was motivated by the exact June 2025 balance/count residuals and is diagnostic only until issuer semantics are confirmed.","limitations":["The SEC certificate provides aggregate counts and balances, not loan-level bucket assignments.","Exact tie-out under an alternate boundary convention is evidence for a mapping hypothesis; it does not prove the servicer used that calculation.","Do not silently replace the literal field-based mapping in production without EX-103/servicer confirmation."],"created_at":timestamp(),"visibility":"private","public_release_approved":False}
 out=contained(ROOT,"artifacts/private/nissan-2024b-dpd-boundary-audit-"+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
 write_new(out/"audit.json",output);write_new(out/"receipt.json",{"status":output["status"],"audit_sha256":sha256(out/"audit.json"),"aggregate_exact_checks":dict(counts),"visibility":"private","public_release_approved":False})
 print(out);print(json.dumps({"aggregate_exact_checks":dict(counts),"june":next(r for r in results if r["report_date"]=="2025-06-30"),"months_with_shifted_improvement":sum(r["tieouts"]["shifted"]["exact_field_checks"]>r["tieouts"]["literal"]["exact_field_checks"] for r in results)},indent=2))
if __name__=="__main__":main()
