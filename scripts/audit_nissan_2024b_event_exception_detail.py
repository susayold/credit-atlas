"""Drill into Nissan 2024-B monthly event-count/principal exceptions.

Stores only hashed asset identifiers; official values and source file hashes remain traceable.
"""
from __future__ import annotations
import hashlib, json, sys, uuid
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import pyarrow.parquet as pq
from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new
from audit_nissan_2024b_certificate_tieout import profile_certificate, decimal

ROOT=Path(__file__).resolve().parents[1]
HISTORY_ID="nissan-2024b-validation-panel-7cd3605b4e07"
PANEL_ID="nissan-2024b-validation-panel-9534e22c34fc"
TARGETS={"2025-01","2025-02","2025-07","2025-08"}
COLUMNS=["assetTypeNumber","assetNumber","chargedoffPrincipalAmount","zeroBalanceCode","reportingPeriodActualEndBalanceAmount","recoveredAmount"]
ZERO=Decimal("0")

def key(row): return (row.get("assetTypeNumber"),row.get("assetNumber"))
def amount(row,field): return decimal(row.get(field)) or ZERO
def codes(row):
    value=row.get("zeroBalanceCode")
    if value in (None,""): return set()
    return {str(x).strip() for x in (value if isinstance(value,(list,tuple,set)) else [value]) if x not in (None,"")}
def key_hash(k): return hashlib.sha256((str(k[0])+"|"+str(k[1])).encode()).hexdigest()[:16]

def audit():
    source=contained(ROOT,f"data/private/structured/{HISTORY_ID}")
    panel=contained(ROOT,f"data/private/derived/{PANEL_ID}")
    sr=read_json(source/"acquisition-complete.json"); pm=read_json(panel/"dataset-complete.json")
    source_month={x["report_date"][:7]:x for x in sr["reports"]}
    panel_month={x["report_date"][:7]:x for x in pm["parquet_files"]}
    if set(source_month)!=set(panel_month) or len(panel_month)!=23: raise ValueError("Paired 23-period panel changed")
    panel_dir=panel
    # Keep only selected exception windows in memory for adjacent-row context.
    windows={m for target in TARGETS for m in (target,)}
    rows_by_month={m:{} for m in windows}
    seen_code4=set(); event_results={}
    for month in sorted(panel_month):
        part=panel_month[month]; path=contained(panel_dir,part["file"])
        if path.stat().st_size!=part["bytes"] or sha256(path)!=part["sha256"]: raise ValueError(f"Panel hash mismatch: {month}")
        capture=month in TARGETS
        first=[]; repeated=[]; positive=[]; zero_first=[]; no_code4=[]; chargeoff_sum=ZERO
        for batch in pq.ParquetFile(path).iter_batches(batch_size=8192,columns=COLUMNS):
            for row in batch.to_pylist():
                k=key(row); c=codes(row); co=amount(row,"chargedoffPrincipalAmount")
                if capture: rows_by_month[month][k]=row
                if co>ZERO:
                    positive.append((k,row)); chargeoff_sum+=co
                    if "4" not in c: no_code4.append((k,row))
                if "4" in c:
                    (first if k not in seen_code4 else repeated).append((k,row))
                    if k not in seen_code4 and co==ZERO: zero_first.append((k,row))
                    seen_code4.add(k)
        if capture:
            src=source_month[month]; cert_meta=src["10d"]["ex99_1"]
            cert_path=contained(source,cert_meta["file"])
            if sha256(cert_path)!=cert_meta["sha256"]: raise ValueError(f"Certificate hash mismatch: {month}")
            cert=profile_certificate(cert_path)
            event_results[month]={
                "report_date":src["report_date"],"abs_ee_accession":src["abs_ee"]["accession"],"abs_ee_source_sha256":src["abs_ee"]["ex102"]["compressed_sha256"],
                "10d_accession":src["10d"]["accession"],"certificate_sha256":cert_meta["sha256"],"panel_sha256":part["sha256"],
                "certificate_defaulted_receivables":cert["defaulted_count"],"certificate_principal_on_defaulted_receivables":cert["gross_defaulted_principal"],
                "certificate_recoveries":cert["principal_recoveries_of_defaulted_receivables"],"certificate_monthly_net_losses":cert["performance_kpis"]["monthly_net_losses"],"certificate_current_net_loss_ratio_pct":cert["performance_kpis"]["current_net_loss_ratio_pct"],
                "asset_positive_chargeoff_count":len(positive),"asset_positive_chargeoff_amount":str(chargeoff_sum),
                "first_code4_count":len(first),"first_code4_chargeoff_amount":str(sum((amount(r,"chargedoffPrincipalAmount") for k,r in first),ZERO)),
                "repeated_code4_count":len(repeated),"repeated_code4_chargeoff_amount":str(sum((amount(r,"chargedoffPrincipalAmount") for k,r in repeated),ZERO)),
                "first_code4_zero_chargeoff_count":len(zero_first),"positive_chargeoff_without_code4_count":len(no_code4),
                "asset_event_rows":[]}
            selected={k:r for k,r in positive}
            selected.update({k:r for k,r in zero_first})
            for k,row in selected.items():
                event_results[month]["asset_event_rows"].append({"asset_key_sha256_prefix":key_hash(k),"chargedoffPrincipalAmount":str(amount(row,"chargedoffPrincipalAmount")),"zeroBalanceCode":sorted(codes(row)),"ending_balance":str(amount(row,"reportingPeriodActualEndBalanceAmount")),"recoveredAmount":str(amount(row,"recoveredAmount"))})
    # Add previous/current/next monthly source observations for anonymized event keys.
    for month,result in event_results.items():
        ym=month.split("-"); idx=int(ym[0])*12+int(ym[1])-1
        adjacent=[f"{(n-1)//12:04d}-{(n-1)%12+1:02d}" for n in (idx,idx+2)]
        current=rows_by_month[month]
        # Load adjacent months only when a report window needs them.
        adjacent_maps={}
        for adj in adjacent:
            if adj in panel_month:
                pp=contained(panel_dir,panel_month[adj]["file"]); m={}
                for batch in pq.ParquetFile(pp).iter_batches(batch_size=8192,columns=COLUMNS):
                    for row in batch.to_pylist(): m[key(row)]=row
                adjacent_maps[adj]=m
        details={r["asset_key_sha256_prefix"]:r for r in result["asset_event_rows"]}
        raw_by_hash={key_hash(k):k for k in current if key_hash(k) in details}
        for h,item in details.items():
            k=raw_by_hash[h]; item["adjacent_observations"]={}
            for adj,m in adjacent_maps.items():
                r=m.get(k)
                item["adjacent_observations"][adj]=None if r is None else {"chargedoffPrincipalAmount":str(amount(r,"chargedoffPrincipalAmount")),"zeroBalanceCode":sorted(codes(r)),"ending_balance":str(amount(r,"reportingPeriodActualEndBalanceAmount"))}
    result={"status":"NISSAN_2024B_EVENT_EXCEPTIONS_DRILLED","issuer":sr["issuer"],"panel_manifest_sha256":sha256(panel/"dataset-complete.json"),"source_receipt_sha256":sha256(source/"acquisition-complete.json"),"periods":event_results,"limitations":["Asset IDs are SHA-256 prefixes for private linkage only; no borrower identity is disclosed.","ABS-EE monthly snapshots and 10-D certificate line items are reconciled observations; discrepancy cause is not established by this audit.","First code-4 uses first occurrence across the observed 23-month panel and does not resolve left truncation before 2024-10."],"created_at":timestamp(),"visibility":"private","public_release_approved":False}
    out=contained(ROOT,"artifacts/private/nissan-2024b-event-exceptions-"+uuid.uuid4().hex[:12]); out.mkdir(parents=True)
    write_new(out/"audit.json",result); write_new(out/"receipt.json",{"status":result["status"],"periods":len(event_results),"audit_sha256":sha256(out/"audit.json"),"visibility":"private","public_release_approved":False})
    print(out); print(json.dumps({m:{k:v for k,v in p.items() if k not in ("asset_event_rows",)} for m,p in event_results.items()},indent=2))
    return out
if __name__=="__main__": audit()

