"""Analyze Nissan 2024-B recovery and June 2025 delinquency reconciliation exceptions."""
from __future__ import annotations
import hashlib,json,uuid
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import pyarrow.parquet as pq
from credit_atlas.workspace import contained,read_json,sha256,timestamp,write_new
from audit_nissan_2024b_certificate_tieout import profile_certificate,decimal
ROOT=Path(__file__).resolve().parents[1]
HISTORY="nissan-2024b-validation-panel-7cd3605b4e07"
PANEL="nissan-2024b-validation-panel-9534e22c34fc"
RECOVERY_MONTHS=["2024-12","2025-01","2025-02","2025-03","2025-04","2025-05"]
BUCKETS=("31-60 Days Delinquent","61-90 Days Delinquent","91-120 Days Delinquent","More than 120 Days")
ZERO=Decimal(0)
def as_decimal(v): return decimal(v) or ZERO
def codes(v):
 if v in (None,""): return set()
 return {str(x).strip() for x in (v if isinstance(v,(list,tuple,set)) else [v]) if x not in (None,"")}
def digest_key(row): return hashlib.sha256((str(row.get("assetTypeNumber"))+"|"+str(row.get("assetNumber"))).encode()).hexdigest()[:16]
def bucket(d): return BUCKETS[0] if d is not None and 31<=d<=60 else BUCKETS[1] if d is not None and 61<=d<=90 else BUCKETS[2] if d is not None and 91<=d<=120 else BUCKETS[3] if d is not None and d>120 else None
def batches(path,columns):
 for batch in pq.ParquetFile(path).iter_batches(batch_size=8192,columns=columns):
  yield from batch.to_pylist()
def audit():
 src=contained(ROOT,f"data/private/structured/{HISTORY}"); panel=contained(ROOT,f"data/private/derived/{PANEL}")
 receipt=read_json(src/"acquisition-complete.json"); manifest=read_json(panel/"dataset-complete.json")
 source_by_month={r["report_date"][:7]:r for r in receipt["reports"]}; panel_by_month={r["report_date"][:7]:r for r in manifest["parquet_files"]}
 if len(panel_by_month)!=23 or set(panel_by_month)!=set(source_by_month):raise ValueError("Source/panel monthly scope changed")
 # Observed code-4 history, so recovery timing is not inferred from only same-row status.
 first_code4_month={}
 for month in sorted(panel_by_month):
  x=panel_by_month[month]; path=contained(panel,x["file"])
  if sha256(path)!=x["sha256"]:raise ValueError("Panel parquet hash mismatch")
  for r in batches(path,["assetTypeNumber","assetNumber","zeroBalanceCode"]):
   if "4" in codes(r.get("zeroBalanceCode")):
    k=(r.get("assetTypeNumber"),r.get("assetNumber"))
    first_code4_month.setdefault(k,month)
 recovery=[]
 for month in RECOVERY_MONTHS:
  x=panel_by_month[month]; path=contained(panel,x["file"]); srcrow=source_by_month[month]; cert_meta=srcrow["10d"]["ex99_1"]
  cert=profile_certificate(contained(src,cert_meta["file"]))
  total=ZERO; positives=Counter(); positive_amounts=defaultdict(Decimal); negative=ZERO; negative_count=0; positive_with_chargeoff=0
  for r in batches(path,["assetTypeNumber","assetNumber","recoveredAmount","chargedoffPrincipalAmount","zeroBalanceCode"]):
   recovery_amount=as_decimal(r.get("recoveredAmount")); chargeoff=as_decimal(r.get("chargedoffPrincipalAmount")); total+=recovery_amount
   if recovery_amount>ZERO:
    k=(r.get("assetTypeNumber"),r.get("assetNumber")); current="4" in codes(r.get("zeroBalanceCode")); first=first_code4_month.get(k)
    group="code4_same_row" if current else "code4_previously_observed" if first and first<month else "code4_first_observed_later" if first and first>month else "no_code4_observed_in_panel"
    positives[group]+=1; positive_amounts[group]+=recovery_amount
    if chargeoff>ZERO:positive_with_chargeoff+=1

   elif recovery_amount<ZERO:negative+=recovery_amount;negative_count+=1
  recovery.append({"report_date":srcrow["report_date"],"asset_recovered_signed":str(total),"certificate_recoveries":cert["recoveries_of_defaulted_receivables"],"asset_minus_certificate":str(total-Decimal(cert["recoveries_of_defaulted_receivables"])),"positive_recovery_row_months":dict(positives),"positive_recovery_amount_by_code4_timing":{k:str(v) for k,v in positive_amounts.items()},"negative_recovery_rows":negative_count,"negative_recovery_sum":str(negative),"positive_recovery_rows_also_positive_chargeoff":positive_with_chargeoff,"certificate_sha256":cert_meta["sha256"],"panel_sha256":x["sha256"]})
 # Reconcile and list near-boundary June rows; candidate identity is exploratory, not asserted.
 month="2025-06"; x=panel_by_month[month]; path=contained(panel,x["file"]); srcrow=source_by_month[month]; cert_meta=srcrow["10d"]["ex99_1"]; cert=profile_certificate(contained(src,cert_meta["file"]))
 asset=defaultdict(lambda:{"count":0,"balance":ZERO}); day_stats=defaultdict(lambda:{"count":0,"balance":ZERO}); edge=[]
 cols=["assetTypeNumber","assetNumber","reportingPeriodActualEndBalanceAmount","currentDelinquencyStatus_days_past_due","currentDelinquencyStatus_raw","interestPaidThroughDate","nextReportingPeriodPaymentAmountDue"]
 for r in batches(path,cols):
  bal=as_decimal(r.get("reportingPeriodActualEndBalanceAmount")); d=r.get("currentDelinquencyStatus_days_past_due")
  if bal<=ZERO or d is None:continue
  b=bucket(d)
  if b:
   asset[b]["count"]+=1;asset[b]["balance"]+=bal
   day_stats[d]["count"]+=1;day_stats[d]["balance"]+=bal
  if 55<=d<=95 and b:
   edge.append({"asset_key_sha256_prefix":digest_key(r),"dpd_days":d,"source_status":r.get("currentDelinquencyStatus_raw"),"ending_balance":str(bal),"interest_paid_through_date":r.get("interestPaidThroughDate"),"next_payment_due":str(r.get("nextReportingPeriodPaymentAmountDue")) if r.get("nextReportingPeriodPaymentAmountDue") is not None else None,"asset_bucket":b})
 buckets={}
 for name in BUCKETS:
  actual=asset[name]; expected=cert["delinquency_buckets"][name]
  buckets[name]={"asset_count":actual["count"],"certificate_count":expected["contract_count"],"count_delta":actual["count"]-expected["contract_count"],"asset_balance":str(actual["balance"]),"certificate_balance":expected["balance"],"balance_delta":str(actual["balance"]-Decimal(expected["balance"]))}
     
 output={"status":"NISSAN_2024B_RECOVERY_AND_DPD_EXCEPTIONS_ANALYZED","source_receipt_sha256":sha256(src/"acquisition-complete.json"),"panel_manifest_sha256":sha256(panel/"dataset-complete.json"),"keys_with_code4_first_observation_in_panel":len(first_code4_month),"recovery_periods":recovery,"june_2025_delinquency":{"report_date":srcrow["report_date"],"bucket_tieout":buckets,"near_boundary_rows":sorted(edge,key=lambda r:(r["dpd_days"],r["ending_balance"])),"near_boundary_day_counts_and_balances":{str(d):{"count":v["count"],"balance":str(v["balance"])} for d,v in sorted(day_stats.items()) if 55<=d<=95},"exact_day_60_count_and_balance":{"count":day_stats[60]["count"],"balance":str(day_stats[60]["balance"])},"exact_day_90_count_and_balance":{"count":day_stats[90]["count"],"balance":str(day_stats[90]["balance"])},"certificate_sha256":cert_meta["sha256"],"panel_sha256":x["sha256"]},"interpretation_limitations":["A recoveredAmount row may refer to a receivable charged off in a different reporting month; code-4 observed anywhere in this finite panel is not lifetime event proof.","Certificate delinquency buckets are aggregate-only; candidate ABS-EE rows near bucket boundaries do not establish which receivables the servicer counted.","This audit does not convert asset-level recoveries or DPD observations into PD/LGD labels."],"created_at":timestamp(),"visibility":"private","public_release_approved":False}
 out=contained(ROOT,"artifacts/private/nissan-2024b-recovery-dpd-exceptions-"+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
 write_new(out/"audit.json",output);write_new(out/"receipt.json",{"status":output["status"],"audit_sha256":sha256(out/"audit.json"),"recovery_months":len(recovery),"june_dpd_near_boundary_rows":len(edge),"visibility":"private","public_release_approved":False})
 print(out);print(json.dumps({"recovery_periods":recovery,"june_buckets":buckets,"near_boundary_rows":len(edge),"days":output["june_2025_delinquency"]["near_boundary_day_counts_and_balances"]},ensure_ascii=False,indent=2))
if __name__=="__main__": audit()
