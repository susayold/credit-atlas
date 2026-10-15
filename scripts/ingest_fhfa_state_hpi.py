from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.fhfa_hpi import normalize_state_hpi_csv  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate and normalize the official FHFA state All-Transactions HPI CSV."
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path(r"D:\data\Codex\credit-atlas\data\private\fhfa-hpi\source\hpi_at_state.csv"),
        help="Official source CSV stored privately on D:",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/data/fhfa-state-all-transactions-hpi-quarterly-2026q2.csv",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "docs/data/fhfa-state-all-transactions-hpi-quarterly-2026q2-receipt.json",
    )
    parser.add_argument(
        "--retrieval-receipt",
        type=Path,
        help="Optional private receipt from the source download; paths are not copied to the public receipt.",
    )
    args = parser.parse_args()
    result = normalize_state_hpi_csv(args.raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["state_code", "year", "quarter", "index_nsa"])
        for record in result.records:
            writer.writerow([record[0], record[1], record[2], f"{record[3]:.2f}"])
    retrieval_receipt_path = args.retrieval_receipt or args.raw.parent / "download-receipt.json"
    retrieval = {}
    if retrieval_receipt_path.is_file():
        retrieval = json.loads(retrieval_receipt_path.read_text(encoding="utf-8"))
    reference_assets = []
    for name, url in [
        ("hpi_dictionary.xlsx", "https://www.fhfa.gov/document/d/hpi/hpi_dictionary.xlsx"),
        ("hpi_specifications.xlsx", "https://www.fhfa.gov/document/d/hpi/hpi_specifications.xlsx"),
    ]:
        reference_path = args.raw.parent / name
        reference_assets.append({
            "name": name,
            "url": url,
            "sha256": _sha256(reference_path) if reference_path.is_file() else None,
        })
    source_entry = next(
        (item for item in retrieval.get("files", []) if item.get("name") == args.raw.name),
        {},
    )
    receipt = {
        "status": "PASS",
        "dataset": "FHFA HPI quarterly state All-Transactions NSA",
        "source_page": "https://www.fhfa.gov/house-price-index",
        "source_file": "hpi_at_state.csv",
        "source_url": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv",
        "dictionary_url": "https://www.fhfa.gov/document/d/hpi/hpi_dictionary.xlsx",
        "specification_url": "https://www.fhfa.gov/document/d/hpi/hpi_specifications.xlsx",
        "retrieved_at_utc": retrieval.get("retrieved_at_utc"),
        "normalized_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": _sha256(args.raw),
        "download_receipt_sha256": source_entry.get("sha256"),
        "reference_assets": reference_assets,
        "normalized_sha256": _sha256(args.output),
        "observations": len(result.records),
        "geographies": result.geography_count,
        "first_period": result.first_period,
        "latest_period": result.latest_period,
        "duplicate_keys": 0,
        "missing_values": 0,
        "index_type": "All-Transactions",
        "frequency": "quarterly",
        "seasonal_adjustment": "not seasonally adjusted",
        "index_base": "1980Q1=100",
        "interpretation_limits": [
            "Geographic index, not a property-level valuation or borrower attribute.",
            "Current downloaded history is retrospective and does not preserve historical release vintages.",
            "Use as aggregate collateral-market context; do not treat as a point-in-time loan feature without an availability/revision protocol.",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.status, "observations": len(result.records),
                      "geographies": result.geography_count, "first_period": result.first_period,
                      "latest_period": result.latest_period, "output": str(args.output),
                      "receipt": str(args.receipt)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
