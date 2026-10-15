"""Reconcile Toyota Auto Receivables 2024-B ABS-EE snapshots to 10-D certificates."""
from __future__ import annotations

import json
import uuid
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq

from audit_toyota_2022b_certificate_tieout import ZERO, decimal, profile_certificate
from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new

ROOT = Path(__file__).resolve().parents[1]
HISTORY_ID = "toyota-2024b-validation-panel-5286fb3cae94"
PANEL_ID = "toyota-2024b-validation-panel-35e5183b1c22"
CERT_FIELDS = ("30-59 Days Delinquent", "60-89 Days Delinquent",
               "90-119 Days Delinquent", "120 or more Days Delinquent")


def audit() -> Path:
    source = contained(ROOT, f"data/private/structured/{HISTORY_ID}")
    panel = contained(ROOT, f"data/private/derived/{PANEL_ID}")
    source_receipt = read_json(source / "acquisition-complete.json")
    panel_manifest = read_json(panel / "dataset-complete.json")
    if (source_receipt.get("status") != "SEC_OFFICIAL_TOYOTA_2024B_PAIRED_HISTORY_ACQUIRED"
            or source_receipt.get("period_count") != 29 or panel_manifest.get("report_count") != 29):
        raise ValueError("Toyota 2024-B source receipts do not meet expected 29-period scope")
    source_by_month = {row["report_date"][:7]: row for row in source_receipt["reports"]}
    panel_by_month = {row["report_date"][:7]: row for row in panel_manifest["parquet_files"]}
    if set(source_by_month) != set(panel_by_month) or len(source_by_month) != 29:
        raise ValueError("Toyota 2024-B ABS-EE and 10-D periods do not align")

    results, checks, delta_sums = [], Counter(), Counter()
    for month in sorted(source_by_month):
        src, part = source_by_month[month], panel_by_month[month]
        cert_meta = src["10d"]["ex99_1"]
        cert_path, panel_path = contained(source, cert_meta["file"]), contained(panel, part["file"])
        if sha256(cert_path) != cert_meta["sha256"]:
            raise ValueError(f"Certificate source hash mismatch: {month}")
        if panel_path.stat().st_size != part["bytes"] or sha256(panel_path) != part["sha256"]:
            raise ValueError(f"ABS-EE panel hash/size mismatch: {month}")
        cert = profile_certificate(cert_path)
        agg = {"rows": 0, "positive_count": 0, "pool": ZERO, "chargeoff": ZERO,
               "chargeoff_events": 0, "recovered": ZERO,
               "dpd": {name: {"count": 0, "balance": ZERO} for name in CERT_FIELDS}}
        columns = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                   "chargedoffPrincipalAmount", "recoveredAmount", "currentDelinquencyStatus_days_past_due"]
        for batch in pq.ParquetFile(panel_path).iter_batches(batch_size=8192, columns=columns):
            for row in batch.to_pylist():
                agg["rows"] += 1
                balance = decimal(row.get("reportingPeriodActualEndBalanceAmount")) or ZERO
                chargeoff = decimal(row.get("chargedoffPrincipalAmount")) or ZERO
                recovered = decimal(row.get("recoveredAmount")) or ZERO
                if balance > ZERO:
                    agg["positive_count"] += 1
                    agg["pool"] += balance
                if chargeoff > ZERO:
                    agg["chargeoff_events"] += 1
                    agg["chargeoff"] += chargeoff
                agg["recovered"] += recovered
                dpd = row.get("currentDelinquencyStatus_days_past_due")
                if balance > ZERO and dpd is not None:
                    bucket = (CERT_FIELDS[0] if 30 <= dpd < 60 else CERT_FIELDS[1] if 60 <= dpd < 90
                              else CERT_FIELDS[2] if 90 <= dpd < 120 else CERT_FIELDS[3] if dpd >= 120 else None)
                    if bucket:
                        agg["dpd"][bucket]["count"] += 1
                        agg["dpd"][bucket]["balance"] += balance
        if agg["rows"] != part["rows"] or agg["rows"] != part["unique_asset_keys"]:
            raise ValueError(f"ABS-EE row/key count mismatch: {month}")

        cert_chargeoff = Decimal(cert["Gross Principal of Liquidated Receivables"])
        cert_events = int(Decimal(cert["Number of Liquidated Receivables"]))
        cert_pool = Decimal(cert["Receivables Pool Balance"])
        ties = {"pool_balance_exact": agg["pool"] == cert_pool,
                "positive_balance_count_matches": agg["positive_count"] == cert["Number of Contracts"],
                "chargeoff_event_count_matches": agg["chargeoff_events"] == cert_events,
                "chargeoff_amount_matches_gross_liquidations": agg["chargeoff"] == cert_chargeoff,
                "recovered_amount_matches_aggregate_net_liquidation_proceeds":
                    agg["recovered"] == Decimal(cert["Aggregate Net Liquidation Proceeds"])}
        checks.update({k: int(v) for k, v in ties.items()})
        delta_sums["pool_balance"] += agg["pool"] - cert_pool
        delta_sums["chargeoff_amount"] += agg["chargeoff"] - cert_chargeoff
        delta_sums["recovered_amount"] += agg["recovered"] - Decimal(cert["Aggregate Net Liquidation Proceeds"])
        buckets = {}
        for name in CERT_FIELDS:
            reported = cert["delinquency_buckets"][name]
            count_delta = agg["dpd"][name]["count"] - int(Decimal(reported["contract_count"]))
            balance_delta = agg["dpd"][name]["balance"] - Decimal(reported["balance"])
            buckets[name] = {"asset_count": agg["dpd"][name]["count"],
                             "certificate_count": int(Decimal(reported["contract_count"])),
                             "count_delta": count_delta, "asset_balance": str(agg["dpd"][name]["balance"]),
                             "certificate_balance": reported["balance"], "balance_delta": str(balance_delta),
                             "count_exact": count_delta == 0, "balance_exact": balance_delta == ZERO}
            checks[f"bucket_{name}_count_exact"] += int(count_delta == 0)
            checks[f"bucket_{name}_balance_exact"] += int(balance_delta == ZERO)
        results.append({"report_date": src["report_date"], "abs_ee_accession": src["abs_ee"]["accession"],
                        "10d_accession": src["10d"]["accession"], "asset_rows": agg["rows"],
                        "positive_balance_count": agg["positive_count"], "certificate_contract_count": cert["Number of Contracts"],
                        "asset_pool_balance": str(agg["pool"]), "certificate_pool_balance": str(cert_pool),
                        "asset_chargeoff_events": agg["chargeoff_events"], "certificate_liquidated_receivables": cert_events,
                        "asset_chargeoff_amount": str(agg["chargeoff"]),
                        "certificate_gross_liquidated_principal": str(cert_chargeoff),
                        "asset_recovered_amount_signed": str(agg["recovered"]),
                        "certificate_aggregate_net_liquidation_proceeds": cert["Aggregate Net Liquidation Proceeds"],
                        "ties": ties, "delinquency_buckets": buckets})

    result = {"status": "TOYOTA_2024B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED",
              "issuer": source_receipt["issuer"], "period_count": len(results),
              "report_start": results[0]["report_date"], "report_end": results[-1]["report_date"],
              "source_ids": {"history": HISTORY_ID, "panel": PANEL_ID},
              "source_sha256": {"history_receipt": sha256(source / "acquisition-complete.json"),
                                "panel_manifest": sha256(panel / "dataset-complete.json")},
              "check_counts": dict(sorted(checks.items())),
              "aggregate_delta_sums": {k: str(v) for k, v in sorted(delta_sums.items())},
              "periods": results,
              "limitations": ["Same servicer/issuer family as Toyota 2022-B; this tests deal-period transfer, not issuer-independent generalization.",
                              "Certificate ties reconcile aggregate reporting and do not create origination PD labels.",
                              "ABS-EE recoveredAmount and certificate proceeds can have different definitions; retain observed deltas.",
                              "No lifetime recovery/LGD is calculated."],
              "created_at": timestamp(), "visibility": "private", "public_release_approved": False}
    out = contained(ROOT, "artifacts/private/toyota-2024b-certificate-tieout-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": len(results), "check_counts": result["check_counts"],
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "checks": result["check_counts"],
                      "aggregate_delta_sums": result["aggregate_delta_sums"]}))
    return out


if __name__ == "__main__":
    audit()
