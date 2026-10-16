"""Build a receipt-bound parquet mart from the two acquired FHFA NMDB products."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.nmdb_mortgage_statistics import MART_RELATIVE, RECEIPT_RELATIVE  # noqa: E402
from credit_atlas.workspace import sha256  # noqa: E402

SOURCE_FILES = {
    "new_annual": "nmdb-new-mortgage-statistics-all-annual.zip",
    "outstanding_quarterly": "nmdb-outstanding-mortgage-statistics-all-quarterly.zip",
}
PROFILE_FILES = {
    "new_annual": "new_annual-profile.json",
    "outstanding_quarterly": "outstanding_quarterly-profile.json",
}
HEADERS = [
    "SOURCE", "FREQUENCY", "GEOLEVEL", "GEOID", "GEONAME", "MARKET", "PERIOD",
    "YEAR", "QUARTER", "MONTH", "SUPPRESSED", "SERIESID", "VALUE1", "VALUE2",
]


def _hash_stream(stream, destination: Path) -> str:
    digest = hashlib.sha256()
    with destination.open("wb") as output:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def _latest_source_dir(root: Path) -> Path:
    candidates = []
    for folder in (root / "data/private/public-context").glob("fhfa-nmdb-composition-*"):
        receipt_path = folder / "receipt.json"
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if receipt.get("status") == "PASS" and set(receipt.get("datasets", {})) >= set(SOURCE_FILES):
            candidates.append((receipt.get("retrieved_at", ""), folder))
    if not candidates:
        raise FileNotFoundError("No PASS FHFA NMDB New/Outstanding acquisition receipt found")
    return sorted(candidates, reverse=True)[0][1]


def build(root: Path, source_dir: Path) -> dict:
    root = root.resolve()
    source_dir = source_dir.resolve()
    if root.drive.upper() != "D:" or source_dir.drive.upper() != "D:":
        raise ValueError("FHFA NMDB mart inputs and outputs must remain on D:")
    raw_receipt = json.loads((source_dir / "receipt.json").read_text(encoding="utf-8"))
    if raw_receipt.get("status") != "PASS" or raw_receipt.get("loan_level_rows_emitted") is not False:
        raise ValueError("Source acquisition receipt is not a passed public aggregate package")
    if raw_receipt.get("forecast_or_imputation_used") is not False:
        raise ValueError("Source receipt indicates forecast/imputation; refusing to build mart")

    out_dir = (root / MART_RELATIVE).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = root / MART_RELATIVE
    staged_path = out_dir / "market-statistics.staged.parquet"
    extracts: dict[str, Path] = {}
    source_evidence = {}

    with tempfile.TemporaryDirectory(prefix="fhfa-nmdb-mart-", dir=out_dir) as temp_name:
        temp_dir = Path(temp_name)
        for product, archive_name in SOURCE_FILES.items():
            archive_path = source_dir / archive_name
            profile_path = source_dir / PROFILE_FILES[product]
            if not archive_path.is_file() or not profile_path.is_file():
                raise FileNotFoundError(f"Missing {product} source archive or profile")
            dataset_receipt = raw_receipt["datasets"][product]
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            if dataset_receipt.get("profile") != profile:
                raise ValueError(f"{product} profile file differs from the acquisition receipt")
            archive_sha = sha256(archive_path)
            if archive_sha != dataset_receipt["download"].get("sha256"):
                raise ValueError(f"{product} ZIP hash differs from its PASS receipt")
            if profile.get("rows") != profile.get("unique_aggregate_keys"):
                raise ValueError(f"{product} source profile does not certify unique aggregate keys")
            expected_member = profile.get("member")
            if not expected_member or not expected_member.endswith(".csv"):
                raise ValueError(f"{product} profile has no expected CSV member")
            csv_path = temp_dir / f"{product}.csv"
            with zipfile.ZipFile(archive_path) as archive:
                members = [item for item in archive.infolist() if not item.is_dir()]
                if len(members) != 1 or members[0].filename != expected_member:
                    raise ValueError(f"{product} ZIP member differs from its acquired profile")
                if archive.testzip() is not None:
                    raise ValueError(f"{product} ZIP CRC is invalid")
                with archive.open(members[0]) as source:
                    csv_sha = _hash_stream(source, csv_path)
            if csv_sha != profile.get("csv_sha256"):
                raise ValueError(f"{product} CSV content hash differs from its acquired profile")
            extracts[product] = csv_path
            source_evidence[product] = {
                "archive": archive_name,
                "archive_sha256": archive_sha,
                "csv_member": expected_member,
                "csv_sha256": csv_sha,
                "profile": PROFILE_FILES[product],
                "profile_sha256": sha256(profile_path),
                "source_rows": profile["rows"],
                "unique_aggregate_keys": profile["unique_aggregate_keys"],
                "suppressed_rows": profile.get("suppression_row_counts", {}).get("1", 0),
                "missing_value1_rows": profile.get("missing_value1_rows", 0),
                "missing_value2_rows": profile.get("missing_value2_rows", 0),
            }

        con = duckdb.connect(database=":memory:")
        try:
            union = []
            for product, csv_path in extracts.items():
                path_sql = str(csv_path).replace("'", "''")
                union.append(
                    "SELECT "
                    f"'{product}' AS product, "
                    "SOURCE AS source, FREQUENCY AS frequency, GEOLEVEL AS geography_level, "
                    "GEOID AS geography_id, GEONAME AS geography_name, MARKET AS market, "
                    "PERIOD AS period, TRY_CAST(YEAR AS INTEGER) AS year, "
                    "TRY_CAST(NULLIF(QUARTER, '') AS INTEGER) AS quarter, "
                    "TRY_CAST(NULLIF(MONTH, '') AS INTEGER) AS month, "
                    "TRY_CAST(SUPPRESSED AS INTEGER) = 1 AS suppressed, SERIESID AS series_id, "
                    "COALESCE(VALUE1, '') AS value1_raw, COALESCE(VALUE2, '') AS value2_raw, "
                    "TRY_CAST(NULLIF(NULLIF(VALUE1, '.'), '') AS DOUBLE) AS value1, "
                    "TRY_CAST(NULLIF(NULLIF(VALUE2, '.'), '') AS DOUBLE) AS value2 "
                    f"FROM read_csv('{path_sql}', header=true, all_varchar=true, strict_mode=true, null_padding=false)"
                )
            sql = "COPY (" + " UNION ALL ".join(union) + ") TO '" + str(staged_path).replace("'", "''") + "' (FORMAT PARQUET, COMPRESSION ZSTD)"
            con.execute(sql)
            validation = con.execute(
                "SELECT product, count(*), sum(CASE WHEN suppressed THEN 1 ELSE 0 END), "
                "sum(CASE WHEN value1_raw IN ('', '.') THEN 1 ELSE 0 END), "
                "sum(CASE WHEN value2_raw IN ('', '.') THEN 1 ELSE 0 END), "
                "sum(CASE WHEN value1_raw NOT IN ('', '.') AND value1 IS NULL THEN 1 ELSE 0 END), "
                "sum(CASE WHEN value2_raw NOT IN ('', '.') AND value2 IS NULL THEN 1 ELSE 0 END) "
                "FROM read_parquet(?) GROUP BY product ORDER BY product",
                [str(staged_path)],
            ).fetchall()
        finally:
            con.close()

    expected = {}
    for product, evidence in source_evidence.items():
        expected[product] = (
            evidence["source_rows"], evidence["suppressed_rows"],
            evidence["missing_value1_rows"], evidence["missing_value2_rows"],
        )
    actual = {row[0]: tuple(int(value or 0) for value in row[1:5]) for row in validation}
    invalid_numeric = {row[0]: (int(row[5] or 0), int(row[6] or 0)) for row in validation}
    if actual != expected or any(v1 or v2 for v1, v2 in invalid_numeric.values()):
        staged_path.unlink(missing_ok=True)
        raise ValueError(f"Canonical mart profile does not reconcile to acquisition receipt: {actual!r}")

    staged_path.replace(final_path)
    mart_sha = sha256(final_path)
    receipt = {
        "status": "PASS", "dataset": "FHFA NMDB New Residential Mortgage and Outstanding Mortgage aggregate statistics",
        "source_page": raw_receipt["source_page"], "source_release_date": raw_receipt["source_release_date"],
        "retrieved_at": raw_receipt["retrieved_at"], "built_at": datetime.now(timezone.utc).isoformat(),
        "source_receipt": str((source_dir / "receipt.json").resolve()),
        "source_receipt_sha256": sha256(source_dir / "receipt.json"),
        "mart_path": str(final_path.resolve()), "mart_sha256": mart_sha,
        "row_count": sum(row[1] for row in validation), "source_evidence": source_evidence,
        "quality": {
            "rows_by_product": {row[0]: row[1] for row in validation},
            "suppressed_rows_by_product": {row[0]: int(row[2] or 0) for row in validation},
            "missing_value1_rows_by_product": {row[0]: int(row[3] or 0) for row in validation},
            "missing_value2_rows_by_product": {row[0]: int(row[4] or 0) for row in validation},
            "invalid_numeric_value_rows_by_product": {key: {"VALUE1": value[0], "VALUE2": value[1]} for key, value in invalid_numeric.items()},
            "source_key": ["product", "source", "frequency", "series_id", "geography_level", "geography_id", "market", "period"],
            "source_keys_unique": True,
            "source_suppression_and_missing_preserved": True,
            "loan_level_rows_emitted": False,
            "forecast_or_imputation_used": False,
        },
    }
    receipt_path = root / RECEIPT_RELATIVE
    receipt_tmp = receipt_path.with_suffix(".staged.json")
    receipt_tmp.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    receipt_tmp.replace(receipt_path)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas workspace root on D:")
    parser.add_argument("--source-dir", type=Path, help="PASS FHFA acquisition directory; defaults to newest PASS package")
    args = parser.parse_args()
    source_dir = args.source_dir.resolve() if args.source_dir else _latest_source_dir(args.root.resolve())
    result = build(args.root, source_dir)
    print(json.dumps({"status": result["status"], "rows": result["row_count"], "mart": result["mart_path"], "sha256": result["mart_sha256"], "quality": result["quality"]}, indent=2))


if __name__ == "__main__":
    main()
