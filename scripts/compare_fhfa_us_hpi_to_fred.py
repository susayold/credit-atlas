from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.fhfa_hpi import normalize_us_census_hpi_csv  # noqa: E402
from credit_atlas.workspace import sha256  # noqa: E402


def _retrieval_receipt(path: Path) -> dict:
    candidates = [path.with_name(path.stem + "-receipt.json"), path.parent / "download-receipt.json"]
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {}


def compare(fhfa_path: Path, fred_path: Path, output_path: Path) -> dict:
    fhfa = normalize_us_census_hpi_csv(fhfa_path)
    direct = {
        (year, quarter): Decimal(f"{value:.2f}")
        for geography, year, quarter, value in fhfa.records
        if geography == "USA"
    }

    fred: dict[tuple[int, int], Decimal | None] = {}
    with fred_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["observation_date", "USSTHPI"]:
            raise ValueError("FRED HPI snapshot schema is not observation_date,USSTHPI")
        for row in reader:
            observed = date.fromisoformat(row["observation_date"])
            if observed.day != 1 or observed.month not in (1, 4, 7, 10):
                raise ValueError("FRED HPI snapshot contains a non-quarter-start date")
            key = (observed.year, (observed.month - 1) // 3 + 1)
            if key in fred:
                raise ValueError("FRED HPI snapshot has duplicate quarters")
            raw = row["USSTHPI"]
            try:
                fred[key] = None if raw in ("", ".") else Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("FRED HPI snapshot contains an invalid index value") from exc

    overlap = set(direct) & set(fred)
    direct_only = set(direct) - set(fred)
    fred_only = set(fred) - set(direct)
    missing_disagreements = [key for key in overlap if fred[key] is None]
    mismatches = [key for key in overlap if fred[key] is not None and direct[key] != fred[key]]
    fhfa_receipt, fred_receipt = _retrieval_receipt(fhfa_path), _retrieval_receipt(fred_path)
    result = {
        "status": "PASS" if not (direct_only or fred_only or missing_disagreements or mismatches) else "FAIL",
        "comparison_method": "Exact Decimal equality on U.S. national quarterly All-Transactions HPI values; no rounding or interpolation.",
        "direct_source": {
            "publisher": "Federal Housing Finance Agency",
            "url": "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_us_and_census.csv",
            "sha256": sha256(fhfa_path),
            "bytes": fhfa_path.stat().st_size,
            "retrieved_at": fhfa_receipt.get("retrieved_at_utc"),
            "national_rows": len(direct),
            "first_period": f"{min(direct)[0]}Q{min(direct)[1]}",
            "latest_period": f"{max(direct)[0]}Q{max(direct)[1]}",
        },
        "fred_comparator": {
            "source_id": "fred-ussthpi",
            "sha256": sha256(fred_path),
            "bytes": fred_path.stat().st_size,
            "rows": len(fred),
            "retrieved_at": fred_receipt.get("retrieved_at"),
        },
        "overlap_rows": len(overlap),
        "direct_only_periods": len(direct_only),
        "fred_only_periods": len(fred_only),
        "missing_value_disagreements": len(missing_disagreements),
        "value_mismatches": len(mismatches),
        "compared_at_utc": datetime.now(timezone.utc).isoformat(),
        "receipt_file": output_path.name,
        "interpretation_limit": "Snapshot overlap parity does not establish same retrieval vintage, historical publication availability, model qualification, or redistribution rights.",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare direct FHFA U.S. HPI with a local FRED USSTHPI snapshot.")
    parser.add_argument("--fhfa", type=Path, required=True, help="Private direct FHFA U.S./Census quarterly CSV")
    parser.add_argument("--fred", type=Path, required=True, help="Private FRED USSTHPI quarterly CSV")
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "data/private/fhfa-national-hpi-research/parity-receipt.json",
        help="Private parity receipt path",
    )
    args = parser.parse_args()
    result = compare(args.fhfa, args.fred, args.output)
    print(json.dumps({key: result[key] for key in (
        "status", "overlap_rows", "direct_only_periods", "fred_only_periods",
        "missing_value_disagreements", "value_mismatches", "receipt_file",
    )}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
