"""Reconcile Toyota 2022-B loan-level ABS-EE snapshots to monthly SEC 10-D certificates."""
from __future__ import annotations

import json
import re
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

import pyarrow.parquet as pq

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
HISTORY_ID = "toyota-2022b-absee-history-435918e7209a"
PANEL_ID = "toyota-2022b-absee-panel-1d111a2e0a47"
PANEL_AUDIT_ID = "toyota-2022b-absee-panel-audit-c9fbf983fa4e"
CERTIFICATE_ID = "toyota-2022b-10d-certificates-941fa44791c8"
ZERO = Decimal("0")


class TableParser(HTMLParser):
    """Extract table rows/cells from SEC's archived submission envelope and HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.table_depth = 0
        self.tables = []
        self.rows = None
        self.row = None
        self.in_cell = False
        self.cell_parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table_depth += 1
            if self.table_depth == 1:
                self.rows = []
        elif self.table_depth == 1 and tag == "tr":
            self.row = []
        elif self.table_depth == 1 and tag in ("td", "th"):
            self.in_cell, self.cell_parts = True, []
        elif self.table_depth == 1 and tag in ("br", "p", "div") and self.in_cell:
            self.cell_parts.append(" ")

    def handle_endtag(self, tag):
        if self.table_depth == 1 and tag in ("td", "th") and self.in_cell:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell, self.cell_parts = False, []
        elif self.table_depth == 1 and tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.table_depth:
            if self.table_depth == 1:
                self.tables.append(self.rows or [])
                self.rows = None
            self.table_depth -= 1

    def handle_data(self, data):
        if self.table_depth == 1 and self.in_cell:
            self.cell_parts.append(data)


def decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip().replace("\u00a0", " ")
    if not text:
        return None
    negative = "(" in text or text.startswith("$(")
    cleaned = re.sub(r"[^0-9.]", "", text)
    if not cleaned:
        return None
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -number if negative else number


def find_row(rows: list[list[str]], label: str) -> list[str] | None:
    for row in rows:
        if row and row[0].strip().casefold() == label.casefold():
            return row
    return None


def values(row: list[str] | None) -> list[tuple[int, str, Decimal]]:
    if row is None:
        return []
    parsed = []
    for index, value in enumerate(row[1:], 1):
        number = decimal(value)
        if number is not None:
            parsed.append((index, value, number))
    return parsed


def current_first(rows, label):
    found = values(find_row(rows, label))
    return found[0][2] if found else None


def current_last(rows, label):
    found = values(find_row(rows, label))
    return found[-1][2] if found else None


def delinquency_cells(rows, label):
    row = find_row(rows, label)
    parsed = values(row)
    # Certificate row order: percent of contracts, contract count, percent of pool, balance.
    if len(parsed) < 4:
        return None
    return {"contract_count": int(parsed[1][2]), "balance": parsed[-1][2],
            "reported_rate": parsed[0][2], "reported_balance_rate": parsed[2][2]}


def profile_certificate(path: Path) -> dict:
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    rows = [row for table in parser.tables for row in table]
    required = ["Number of Liquidated Receivables", "Gross Principal of Liquidated Receivables",
                "Net Liquidation Proceeds Received During the Collection Period",
                "Recoveries on Previously Liquidated Contracts", "Net Credit Losses"]
    fields = {}
    for label in required:
        value = current_first(rows, label)
        if value is None:
            raise ValueError(f"Certificate field missing: {label} in {path.name}")
        fields[label] = str(value)
    proceeds = current_last(rows, "Aggregate Net Liquidation Proceeds")
    pool = current_last(rows, "Receivables Pool Balance")
    contracts = current_last(rows, "Number of Contracts")
    if proceeds is None or pool is None or contracts is None:
        raise ValueError(f"Certificate collection/pool summary missing: {path.name}")
    fields["Aggregate Net Liquidation Proceeds"] = str(proceeds)
    fields["Receivables Pool Balance"] = str(pool)
    fields["Number of Contracts"] = int(contracts)
    bucket_names = ["30-59 Days Delinquent", "60-89 Days Delinquent",
                    "90-119 Days Delinquent", "120 or more Days Delinquent"]
    fields["delinquency_buckets"] = {}
    for label in bucket_names:
        bucket = delinquency_cells(rows, label)
        if bucket is None:
            raise ValueError(f"Delinquency bucket missing or ambiguous: {label} in {path.name}")
        fields["delinquency_buckets"][label] = {k: str(v) for k, v in bucket.items()}
    fields["table_count"] = len(parser.tables)
    return fields


def audit() -> Path:
    history = contained(ROOT, f"data/private/structured/{HISTORY_ID}")
    panel = contained(ROOT, f"data/private/derived/{PANEL_ID}")
    certificates = contained(ROOT, f"data/private/structured/{CERTIFICATE_ID}")
    panel_manifest = read_json(panel / "dataset-complete.json")
    panel_audit = read_json(contained(ROOT, f"artifacts/private/{PANEL_AUDIT_ID}/audit.json"))
    cert_receipt = read_json(certificates / "acquisition-complete.json")
    if (cert_receipt.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_10D_CERTIFICATES_ACQUIRED"
            or cert_receipt.get("period_count") != 51 or panel_manifest.get("report_count") != 51
            or panel_audit.get("row_month_observations") != 2508991):
        raise ValueError("Toyota source receipts do not meet expected 51-period panel scope")
    source_by_month = {row["report_date"][:7]: row for row in cert_receipt["reports"]}
    panel_by_month = {row["report_date"][:7]: row for row in panel_manifest["parquet_files"]}
    if set(source_by_month) != set(panel_by_month) or len(source_by_month) != 51:
        raise ValueError("Toyota 10-D certificates and ABS-EE periods do not align")

    period_results = []
    checks = Counter()
    delta_sums = Counter()
    for month in sorted(source_by_month):
        source = source_by_month[month]
        cert_path = contained(certificates, source["certificate"]["file"])
        if sha256(cert_path) != source["certificate"]["sha256"]:
            raise ValueError(f"Certificate source hash mismatch: {month}")
        certificate = profile_certificate(cert_path)
        part = panel_by_month[month]
        panel_path = contained(panel, part["file"])
        if panel_path.stat().st_size != part["bytes"] or sha256(panel_path) != part["sha256"]:
            raise ValueError(f"ABS-EE panel source hash mismatch: {month}")
        agg = {
            "row_count": 0, "positive_balance_count": 0, "nonzero_balance_count": 0,
            "pool_balance": ZERO, "chargeoff_amount": ZERO, "chargeoff_events": 0,
            "recovered_amount": ZERO,
            "dpd": {name: {"count": 0, "balance": ZERO} for name in
                    ("30-59 Days Delinquent", "60-89 Days Delinquent", "90-119 Days Delinquent", "120 or more Days Delinquent")},
        }
        columns = ["assetTypeNumber", "assetNumber", "reportingPeriodActualEndBalanceAmount",
                   "chargedoffPrincipalAmount", "recoveredAmount", "currentDelinquencyStatus_days_past_due"]
        for batch in pq.ParquetFile(panel_path).iter_batches(batch_size=8192, columns=columns):
            for row in batch.to_pylist():
                agg["row_count"] += 1
                balance = decimal(row.get("reportingPeriodActualEndBalanceAmount")) or ZERO
                chargeoff = decimal(row.get("chargedoffPrincipalAmount")) or ZERO
                recovery = decimal(row.get("recoveredAmount")) or ZERO
                if balance > ZERO:
                    agg["positive_balance_count"] += 1
                if balance != ZERO:
                    agg["nonzero_balance_count"] += 1
                    agg["pool_balance"] += balance
                if chargeoff > ZERO:
                    agg["chargeoff_events"] += 1
                    agg["chargeoff_amount"] += chargeoff
                agg["recovered_amount"] += recovery
                dpd = row.get("currentDelinquencyStatus_days_past_due")
                if balance > ZERO and dpd is not None:
                    if 30 <= dpd < 60:
                        name = "30-59 Days Delinquent"
                    elif 60 <= dpd < 90:
                        name = "60-89 Days Delinquent"
                    elif 90 <= dpd < 120:
                        name = "90-119 Days Delinquent"
                    elif dpd >= 120:
                        name = "120 or more Days Delinquent"
                    else:
                        name = None
                    if name:
                        agg["dpd"][name]["count"] += 1
                        agg["dpd"][name]["balance"] += balance

        cert_chargeoff = Decimal(certificate["Gross Principal of Liquidated Receivables"])
        cert_events = int(Decimal(certificate["Number of Liquidated Receivables"]))
        cert_recovery = Decimal(certificate["Aggregate Net Liquidation Proceeds"])
        cert_pool = Decimal(certificate["Receivables Pool Balance"])
        ties = {
            "pool_balance_exact": agg["pool_balance"] == cert_pool,
            "positive_balance_count_matches": agg["positive_balance_count"] == certificate["Number of Contracts"],
            "chargeoff_event_count_matches": agg["chargeoff_events"] == cert_events,
            "chargeoff_amount_matches_gross_liquidations": agg["chargeoff_amount"] == cert_chargeoff,
            "recovered_amount_matches_aggregate_net_liquidation_proceeds": agg["recovered_amount"] == cert_recovery,
        }
        checks.update({key: 1 if passed else 0 for key, passed in ties.items()})
        delta_sums["chargeoff_amount"] += agg["chargeoff_amount"] - cert_chargeoff
        delta_sums["recovered_amount"] += agg["recovered_amount"] - cert_recovery
        delta_sums["pool_balance"] += agg["pool_balance"] - cert_pool
        bucket_results = {}
        for name, obs in agg["dpd"].items():
            cert = certificate["delinquency_buckets"][name]
            count_delta = obs["count"] - int(Decimal(cert["contract_count"]))
            amount_delta = obs["balance"] - Decimal(cert["balance"])
            bucket_results[name] = {"loan_count": obs["count"], "certificate_count": int(Decimal(cert["contract_count"])),
                                    "count_delta": count_delta, "loan_balance": str(obs["balance"]),
                                    "certificate_balance": cert["balance"], "balance_delta": str(amount_delta),
                                    "count_exact": count_delta == 0, "balance_exact": amount_delta == ZERO}
            checks[f"bucket_{name}_count_exact"] += int(count_delta == 0)
            checks[f"bucket_{name}_balance_exact"] += int(amount_delta == ZERO)
        period_results.append({
            "report_date": source["report_date"], "filing_date": source["filing_date"],
            "10d_accession": source["accession"], "abs_ee_accession": source["abs_ee_accession"],
            "asset_rows": agg["row_count"], "positive_balance_count": agg["positive_balance_count"],
            "certificate_contract_count": certificate["Number of Contracts"],
            "asset_pool_balance": str(agg["pool_balance"]), "certificate_pool_balance": str(cert_pool),
            "asset_chargeoff_events": agg["chargeoff_events"], "certificate_liquidated_receivables": cert_events,
            "asset_chargeoff_amount": str(agg["chargeoff_amount"]), "certificate_gross_liquidated_principal": str(cert_chargeoff),
            "asset_recovered_amount_signed": str(agg["recovered_amount"]),
            "certificate_aggregate_net_liquidation_proceeds": str(cert_recovery),
            "source_certificate": certificate, "ties": ties, "delinquency_buckets": bucket_results,
        })

    result = {
        "status": "TOYOTA_2022B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED",
        "issuer": cert_receipt["issuer"], "period_count": len(period_results),
        "report_start": period_results[0]["report_date"], "report_end": period_results[-1]["report_date"],
        "source_ids": {"history": HISTORY_ID, "panel": PANEL_ID, "panel_audit": PANEL_AUDIT_ID,
                       "certificates": CERTIFICATE_ID},
        "source_sha256": {"history_receipt": sha256(history / "acquisition-complete.json"),
                          "panel_manifest": sha256(panel / "dataset-complete.json"),
                          "panel_audit": sha256(contained(ROOT, f"artifacts/private/{PANEL_AUDIT_ID}/audit.json")),
                          "certificate_receipt": sha256(certificates / "acquisition-complete.json")},
        "check_counts": dict(sorted(checks.items())),
        "aggregate_delta_sums": {k: str(v) for k, v in sorted(delta_sums.items())},
        "periods": period_results,
        "limitations": [
            "Certificate tie-outs validate aggregate sources and do not turn servicing history into origination PD labels.",
            "ABS-EE recoveredAmount and certificate liquidation proceeds may represent related but differently signed/classified amounts; retain period deltas and definitions.",
            "Day-bucket tie-out uses positive-ending-balance rows and certificate's displayed 30-59/60-89/90-119/120+ group definitions; it is an observed reconciliation, not a legal default test.",
            "No lifetime recovery/LGD is calculated; flow, prior-liquidation recoveries and repossession proceeds remain separately defined in the certificate and EX-103.",
        ],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/toyota-2022b-certificate-tieout-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "audit_sha256": sha256(out / "audit.json"),
                                     "periods": len(period_results), "check_counts": result["check_counts"],
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "checks": result["check_counts"],
                      "aggregate_delta_sums": result["aggregate_delta_sums"]}))
    return out


if __name__ == "__main__":
    audit()
