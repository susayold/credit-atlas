"""Prepare a small FHFA NMDB national/all-mortgages Excel reference payload."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.nmdb_mortgage_statistics import PRODUCTS, SERIES, VALUE1_ONLY, MART_RELATIVE, catalog  # noqa: E402


def prepare(root: Path) -> dict:
    root = root.resolve()
    mart = root / MART_RELATIVE
    metadata = catalog(root)
    con = duckdb.connect(database=":memory:")
    try:
        rows = con.execute(
            "SELECT product, source, frequency, period, year, quarter, month, series_id, "
            "value1_raw, value2_raw, value1, value2, suppressed "
            "FROM read_parquet(?) WHERE geography_level='National' AND geography_id='USA' "
            "AND market='All Mortgages' ORDER BY product, year, quarter NULLS FIRST, series_id",
            [str(mart)],
        ).fetchall()
    finally:
        con.close()
    products = {}
    for product, source, frequency, period, year, quarter, month, series_id, v1_raw, v2_raw, v1, v2, suppressed in rows:
        label, unit, definition = SERIES[product].get(
            series_id, (series_id.replace("_", " ").title(), "source units", "See FHFA Appendix B or C.")
        )
        products.setdefault(product, []).append({
            "source": source, "frequency": frequency, "period": period, "year": year,
            "quarter": quarter, "month": month, "series_id": series_id, "label": label,
            "unit": unit, "definition": definition,
            "supported_weights": ["VALUE1"] + (["VALUE2"] if series_id not in VALUE1_ONLY[product] else []),
            "value1_raw": v1_raw, "value2_raw": v2_raw,
            "value1": float(v1) if v1 is not None else None,
            "value2": float(v2) if v2 is not None else None, "suppressed": bool(suppressed),
        })
    series_metadata = {}
    for key, mapping in SERIES.items():
        series_metadata[key] = {
            series_id: {
                "label": values[0], "unit": values[1], "definition": values[2],
                "supported_weights": ["VALUE1"] + (["VALUE2"] if series_id not in VALUE1_ONLY[key] else []),
                "weight_note": "FHFA Appendix specifies VALUE1 only for this series." if series_id in VALUE1_ONLY[key] else "Select VALUE1 or VALUE2 where published; the weighting estimand differs.",
            }
            for series_id, values in mapping.items()
        }
    return {
        "source_release_date": metadata["source_release_date"], "retrieved_at": metadata["retrieved_at"],
        "mart_sha256": metadata["mart_sha256"], "source_page": metadata["source_page"],
        "dictionary_url": metadata["dictionary_url"], "quality": metadata["quality"],
        "products": PRODUCTS, "data": products,
        "series": series_metadata,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"Prepared {sum(len(v) for v in result['data'].values()):,} national/all-mortgage rows for artifact-tool workbook")


if __name__ == "__main__":
    main()
