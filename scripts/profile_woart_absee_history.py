"""Profile official World Omni ABS-EE XML and reconcile monthly totals to issuer certificates."""
from __future__ import annotations

import gzip
import json
import re
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

import pyarrow.parquet as pq

from credit_atlas.abs_servicer import verify_case
from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


SOURCE_PATTERN = re.compile(r"woart-absee-history-[0-9a-f]{12}")
MIRROR_ID = "absee-mirror-f97dcd09916d"
KEY_FIELDS = ("assetTypeNumber", "assetNumber")
COMPARE_FIELDS = (
    "assetTypeNumber", "assetNumber", "reportingPeriodBeginningDate",
    "reportingPeriodEndingDate", "currentDelinquencyStatus",
    "reportingPeriodActualEndBalanceAmount", "chargedoffPrincipalAmount",
    "recoveredAmount", "repossessedProceedsAmount",
)
MONEY_FIELDS = (
    "originalLoanAmount", "reportingPeriodBeginningLoanBalanceAmount",
    "reportingPeriodActualEndBalanceAmount", "scheduledPrincipalAmount",
    "scheduledInterestAmount", "actualPrincipalCollectedAmount",
    "actualInterestCollectedAmount", "recoveredAmount", "chargedoffPrincipalAmount",
    "repossessedProceedsAmount",
)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def decimal(value: str | None) -> Decimal | None:
    if value is None or not value.strip():
        return None
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric XML value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError("Nonfinite XML value")
    return result


def normalize(left, right) -> bool:
    if left is None or right is None or str(left).strip() == "" or str(right).strip() == "":
        return left in (None, "") and right in (None, "")
    if str(left) == str(right):
        return True
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except InvalidOperation:
        return False


def mirror_rows(path: Path) -> dict[tuple[str, str], dict]:
    table = pq.read_table(path)
    rows = {}
    for batch in table.to_batches(max_chunksize=4096):
        for row in batch.to_pylist():
            key = (str(row.get("assetTypeNumber")), str(row.get("assetNumber")))
            rows[key] = row
    return rows


def profile_xml(folder: Path, report: dict, mirror_path: Path | None) -> dict:
    xml_record = report["xml"]
    path = folder / xml_record["file"]
    names = set()
    missing = Counter()
    value_counts = {k: Counter() for k in
                    ("currentDelinquencyStatus", "assetTypeNumber", "obligorGeographicLocation",
                     "vehicleNewUsedCode", "zeroBalanceCode", "repossessedIndicator")}
    scores = Counter()
    pti = Counter()
    sums = Counter()
    ids = set()
    duplicate_ids = 0
    records = 0
    positive = 0
    zero_balance = 0
    mirror = mirror_rows(mirror_path) if mirror_path else None
    mirror_matches = 0
    compared_values = Counter()
    mirror_mismatches = Counter()
    mirror_rows_seen = set()
    balance_by_delinquency: dict[str, Decimal] = Counter()
    count_by_delinquency = Counter()

    with gzip.open(path, "rb") as source:
        for _, element in ET.iterparse(source, events=("end",)):
            if local(element.tag) != "assets" or any(local(c.tag) == "assets" for c in element):
                continue
            row = {local(child.tag): child.text for child in element}
            element.clear()
            records += 1
            names.update(row)
            for field in names:
                if row.get(field) is None or not row.get(field, "").strip():
                    missing[field] += 1
            for field, counts in value_counts.items():
                counts[row.get(field) if row.get(field) else "<BLANK>"] += 1
            key_values = tuple(row.get(k) for k in KEY_FIELDS)
            if any(not x for x in key_values):
                raise ValueError("Missing ABS-EE asset key")
            if key_values in ids:
                duplicate_ids += 1
            ids.add(key_values)
            balance = decimal(row.get("reportingPeriodActualEndBalanceAmount")) or Decimal(0)
            if balance > 0:
                positive += 1
            else:
                zero_balance += 1
            status = row.get("currentDelinquencyStatus") or "<BLANK>"
            count_by_delinquency[status] += 1
            balance_by_delinquency[status] += balance
            for field in MONEY_FIELDS:
                value = decimal(row.get(field))
                if value is not None:
                    sums[field] += value
            score = decimal(row.get("obligorCreditScore"))
            if score is not None:
                lower = (int(score) // 50) * 50
                scores[f"{lower}-{lower + 49}"] += 1
            payment_to_income = decimal(row.get("paymentToIncomePercentage"))
            if payment_to_income is not None:
                pti[f"{(payment_to_income * 100):.2f}%"] += 1
            if mirror is not None:
                mirror_row = mirror.get(key_values)
                if mirror_row is None:
                    mirror_mismatches["missing_asset_key"] += 1
                else:
                    mirror_rows_seen.add(key_values)
                    fields = [f for f in COMPARE_FIELDS if f in mirror_row]
                    for field in fields:
                        compared_values[field] += 1
                        if field in mirror_row and not normalize(row.get(field), mirror_row.get(field)):
                            mirror_mismatches[field] += 1
                    mirror_matches += 1

    if mirror is not None:
        mirror_mismatches["mirror_only_asset_keys"] = len(set(mirror) - mirror_rows_seen)
    return {
        "report_date": report["report_date"],
        "filing_date": report["filing_date"],
        "accession": report["xml"]["accession"],
        "xml_sha256": report["xml"]["uncompressed_sha256"],
        "rows": records,
        "field_count": len(names),
        "fields": sorted(names),
        "missing_by_field": {k: missing[k] for k in sorted(names)},
        "duplicate_asset_keys": duplicate_ids,
        "unique_asset_keys": len(ids),
        "positive_ending_balance_assets": positive,
        "zero_or_negative_ending_balance_assets": zero_balance,
        "balance_by_delinquency_status_raw": {
            k: {"accounts": count_by_delinquency[k], "ending_balance": str(balance_by_delinquency[k])}
            for k in sorted(count_by_delinquency)
        },
        "raw_category_counts": {k: dict(sorted(v.items())) for k, v in value_counts.items()},
        "score_bucket_counts_50pt": dict(sorted(scores.items())),
        "pti_exact_value_counts": dict(sorted(pti.items())),
        "money_sums_unqualified_units": {k: str(sums[k]) for k in sorted(MONEY_FIELDS)},
        "mirror_comparison": None if mirror is None else {
            "mirror_rows": len(mirror),
            "matched_asset_keys": mirror_matches,
            "compared_fields": sorted(compared_values),
            "compared_values_by_field": dict(sorted(compared_values.items())),
            "mismatch_counts_by_field": {k: v for k, v in mirror_mismatches.items() if v},
            "full_row_fidelity_verified": False,
        },
    }


def run(source_id: str) -> Path:
    if not SOURCE_PATTERN.fullmatch(source_id):
        raise ValueError("Invalid official ABS-EE source ID")
    root = Path(__file__).resolve().parents[1]
    folder = contained(root, "data/private/structured/" + source_id)
    source_receipt = read_json(folder / "acquisition-complete.json")
    if (source_receipt.get("status") != "SEC_OFFICIAL_ABSEE_HISTORY_ACQUIRED"
            or source_receipt.get("issuer") != "World Omni Auto Receivables Trust 2025-A"
            or source_receipt.get("visibility") != "private"
            or source_receipt.get("public_release_approved") is not False
            or len(source_receipt.get("reports", [])) != 20):
        raise ValueError("Official ABS-EE history acquisition contract mismatch")
    for report in source_receipt["reports"]:
        path = contained(folder, report["xml"]["file"])
        if path.stat().st_size != report["xml"]["compressed_bytes"] or sha256(path) != report["xml"]["compressed_sha256"]:
            raise ValueError("Compressed official XML changed")
    case_id = "abs-case-fcbaa9573ac3"
    case = verify_case(root, case_id)
    metric_path = contained(root, f"artifacts/private/{case_id}/reported_metrics.parquet")
    metrics = pq.read_table(metric_path).to_pylist()
    metric_index = {(m["collection_end"], m["section"], m["metric"], m["slot"]): m for m in metrics}
    by_date = {date: metric_index[(date, "pool", "ending_pool", "")] for date in
               {m["collection_end"] for m in metrics if m["section"] == "pool" and m["metric"] == "ending_pool"}}
    mirror_root = contained(root, "data/private/structured/" + MIRROR_ID)
    mirror_receipt = read_json(mirror_root / "acquisition-complete.json")
    mirror_by_date = {x["reportDate"]: mirror_root / x["file"] for x in mirror_receipt["selected_filings"]}
    periods, reconciliations = [], []
    for report in source_receipt["reports"]:
        period = profile_xml(folder, report, mirror_by_date.get(report["report_date"]))
        periods.append(period)
        certified = by_date.get(report["report_date"])
        if certified is None:
            raise ValueError("No corresponding monthly servicing certificate")
        xml_sum = Decimal(period["money_sums_unqualified_units"]["reportingPeriodActualEndBalanceAmount"])
        ysoa = Decimal(metric_index[(report["report_date"], "pool", "ending_ysoa", "")]["value"])
        cert_pool = Decimal(certified["value"])
        cert_sum = cert_pool + ysoa
        delta = xml_sum - cert_sum
        reconciliations.append({
            "report_date": report["report_date"],
            "xml_positive_balance_assets": period["positive_ending_balance_assets"],
            "certificate_ending_pool_accounts": int(metric_index[(report["report_date"], "pool", "ending_pool_accounts", "")]["value"]),
            "asset_xml_ending_balance_reconciles_to": "certificate ending pool balance plus reported YSOA",
            "xml_ending_balance_sum": str(xml_sum),
            "certificate_ending_pool": str(cert_pool),
            "certificate_ending_ysoa": str(ysoa),
            "certificate_ending_receivables_including_ysoa": str(cert_sum),
            "delta": str(delta),
            "balance_matches_to_cent": abs(delta) <= Decimal("0.01"),
            "positive_asset_count_delta": period["positive_ending_balance_assets"] - int(metric_index[(report["report_date"], "pool", "ending_pool_accounts", "")]["value"]),
        })
    output = contained(root, "artifacts/private/woart-absee-official-profile-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    profile = {
        "status": "OFFICIAL_XML_PROFILED_AND_CERTIFICATE_RECONCILIATION_COMPLETE",
        "source_id": source_id,
        "source_receipt_sha256": sha256(folder / "acquisition-complete.json"),
        "source_case_id": case_id,
        "source_case_receipt_sha256": sha256(root / f"artifacts/private/{case_id}/case-complete.json"),
        "mirror_source_id": MIRROR_ID,
        "periods": periods,
        "certificate_reconciliations": reconciliations,
        "all_monthly_balances_match_to_cent": all(x["balance_matches_to_cent"] for x in reconciliations),
        "mirror_comparison_scope": "Matched public mirror key rows and selected source fields only; not full-row fidelity certification.",
        "model_ready": False,
        "visibility": "private",
        "public_release_approved": False,
        "limitations": [
            "Raw delinquency codes remain unqualified; no day-bucket mapping is inferred from code values.",
            "Monetary fields retain source strings/sums and require official XSD/semantics confirmation before modeling.",
            "Asset-key continuity does not establish borrower identity or a causal exit/default label.",
            "Schedule AL/CFR definitions describe meaning but do not alone verify technical XML enumerations.",
            "Asset XML balances reconcile to certificate pool plus reported YSOA; reported positive-asset counts differ from certificate account counts by a small amount that remains unexplained.",
            "A monthly balance tie-out is an aggregate reconciliation, not a complete filing audit or legal sign-off.",
        ],
        "created_at": timestamp(),
    }
    write_new(output / "profile.json", profile)
    write_new(output / "receipt.json", {
        "status": profile["status"], "profile_sha256": sha256(output / "profile.json"),
        "source_receipt_sha256": profile["source_receipt_sha256"],
        "periods": len(periods), "rows": sum(p["rows"] for p in periods),
        "all_monthly_balances_match_to_cent": profile["all_monthly_balances_match_to_cent"],
        "mirror_compared_periods": sum(p["mirror_comparison"] is not None for p in periods),
        "mirror_field_mismatch_periods": sum(bool(p["mirror_comparison"]["mismatch_counts_by_field"])
                                             for p in periods if p["mirror_comparison"] is not None),
        "raw_identifiers_exported": False,
        "model_ready": False,
        "visibility": "private",
        "public_release_approved": False,
    })
    print(output)
    print(json.dumps(read_json(output / "receipt.json")))
    return output


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: profile_woart_absee_history.py woart-absee-history-<12 hex>")
    run(sys.argv[1])
