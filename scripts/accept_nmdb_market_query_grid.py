"""Receipt-backed API and XLSX parity grid for FHFA NMDB market statistics."""
from __future__ import annotations

import argparse
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from types import SimpleNamespace

import duckdb
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.nmdb_mortgage_statistics import MART_RELATIVE, catalog, report  # noqa: E402
from credit_atlas.server import handler_for  # noqa: E402
from credit_atlas.workspace import sha256  # noqa: E402

LEVEL_ORDER = {
    "National": 0,
    "Census Region": 1,
    "Census Division": 2,
    "State": 3,
    "Rural/Non-Rural": 4,
    "Metro": 5,
}
PERIOD_COLUMNS = [
    "product", "geography_level", "geography_id", "geography_name", "market",
    "series_id", "first_year", "last_year", "row_count", "value1_rows",
    "value2_rows", "suppressed_rows",
]


def _service(root: Path):
    return SimpleNamespace(
        root=root,
        nmdb_mortgage_statistics_catalog=lambda: catalog(root),
        nmdb_mortgage_statistics=lambda query: report(root, query),
    )


def _coverage_groups(root: Path) -> list[dict]:
    mart = root / MART_RELATIVE
    con = duckdb.connect(database=":memory:")
    try:
        rows = con.execute(
            "SELECT product, geography_level, geography_id, geography_name, market, series_id, "
            "min(year), max(year), count(*), "
            "count(*) FILTER (WHERE value1 IS NOT NULL), "
            "count(*) FILTER (WHERE value2 IS NOT NULL), "
            "count(*) FILTER (WHERE suppressed) "
            "FROM read_parquet(?) GROUP BY ALL ORDER BY product, geography_level, geography_id, market, series_id",
            [str(mart)],
        ).fetchall()
    finally:
        con.close()
    return [dict(zip(PERIOD_COLUMNS, row)) for row in rows]


def _group_rank(row: dict) -> tuple:
    return (
        LEVEL_ORDER.get(row["geography_level"], 99),
        row["market"] != "All Mortgages",
        row["series_id"] != "AVE_INTRATE",
        row["geography_id"],
    )


def _query_for(group: dict, measure: str, first_year: int, last_year: int) -> dict:
    return {
        "product": str(group["product"]),
        "geo_level": str(group["geography_level"]),
        "geo_id": str(group["geography_id"]),
        "market": str(group["market"]),
        "series_id": str(group["series_id"]),
        "measure": measure,
        "from_year": str(first_year),
        "to_year": str(last_year),
    }


def _key(query: dict) -> tuple[str, ...]:
    return tuple(str(query[key]) for key in (
        "product", "geo_level", "geo_id", "market", "series_id", "measure", "from_year", "to_year"
    ))


def build_query_grid(catalog_data: dict, groups: list[dict]) -> tuple[dict, dict]:
    """Build broad, data-selected coverage without fabricating unsupported queries."""
    api: dict[tuple[str, ...], dict] = {}
    xlsx: dict[tuple[str, ...], dict] = {}
    tags: dict[tuple[str, ...], set[str]] = {}

    def add(group: dict, measure: str, first: int, last: int, *labels: str, export: bool = False) -> None:
        query = _query_for(group, measure, first, last)
        key = _key(query)
        api.setdefault(key, query)
        tags.setdefault(key, set()).update(labels)
        if export:
            xlsx.setdefault(key, query)

    for product in catalog_data["products"]:
        product_id = product["product"]
        rows = [row for row in groups if row["product"] == product_id]
        series_meta = {row["series_id"]: row for row in product["series"]}
        product_first = int(product["first_year"])
        product_last = int(product["last_year"])

        # Every published series and every FHFA-supported weighting is queried.
        for series_id, metadata in series_meta.items():
            for measure in metadata["supported_weights"]:
                value_count_key = "value1_rows" if measure == "VALUE1" else "value2_rows"
                candidates = [row for row in rows if row["series_id"] == series_id and row[value_count_key] > 0]
                if not candidates:
                    raise ValueError(f"Catalog advertises {product_id}/{series_id}/{measure} without source rows")
                group = min(candidates, key=_group_rank)
                add(group, measure, int(group["first_year"]), int(group["last_year"]), "series-weight")

        # Every published mortgage-market category is checked through the API
        # and its filtered Excel export using a source-supported series.
        for market in product["markets"]:
            candidates = [row for row in rows if row["market"] == market and row["value1_rows"] > 0]
            if not candidates:
                raise ValueError(f"Catalog advertises {product_id}/{market} without VALUE1 rows")
            candidates.sort(key=_group_rank)
            group = min(candidates, key=lambda row: (
                row["series_id"] != "AVE_INTRATE", *_group_rank(row)
            ))
            add(group, "VALUE1", product_first, product_last, "market", export=True)

        # Cover every geography level and a geography × market intersection.
        for level in sorted({row["geography_level"] for row in rows}, key=lambda value: LEVEL_ORDER.get(value, 99)):
            candidates = [row for row in rows if row["geography_level"] == level and row["value1_rows"] > 0]
            if not candidates:
                raise ValueError(f"No VALUE1 rows for geography level {product_id}/{level}")
            candidates.sort(key=lambda row: (
                row["market"] != "All Mortgages", row["series_id"] != "AVE_INTRATE", _group_rank(row)
            ))
            broad = candidates[0]
            add(broad, "VALUE1", product_first, product_last, "geography-level", export=True)
            intersections = [row for row in candidates if row["market"] != "All Mortgages"]
            if intersections:
                intersection = min(intersections, key=lambda row: (
                    row["market"], row["series_id"] != "AVE_INTRATE", _group_rank(row)
                ))
                add(intersection, "VALUE1", product_first, product_last, "geography-market", export=True)

        # Verify oldest, latest and recent-period filters, including a partial
        # final year when the publisher's current release is year-to-date.
        candidates = [row for row in rows if row["series_id"] == "AVE_INTRATE" and row["value1_rows"] > 0]
        if not candidates:
            candidates = [row for row in rows if row["value1_rows"] > 0]
        reference = min(candidates, key=_group_rank)
        first = int(reference["first_year"])
        last = int(reference["last_year"])
        add(reference, "VALUE1", first, first, "period-edge", export=True)
        add(reference, "VALUE1", last, last, "period-edge", export=True)
        add(reference, "VALUE1", max(first, last - 2), last, "period-range", export=True)

        # At least one amount/UPB-weighted workbook per product where FHFA
        # publishes VALUE2; not every series supports this estimand.
        value2_groups = [row for row in rows if row["value2_rows"] > 0]
        if value2_groups:
            value2_groups.sort(key=lambda row: (
                row["series_id"] != "AVE_INTRATE", *_group_rank(row)
            ))
            value2_group = value2_groups[0]
            add(value2_group, "VALUE2", int(value2_group["first_year"]), int(value2_group["last_year"]), "value2", export=True)

    alaska_jumbo = [row for row in groups if row["product"] == "new_annual"
                    and row["geography_level"] == "State" and row["geography_id"] == "AK"
                    and row["market"] == "Jumbo Market" and row["series_id"] == "AVE_INTRATE"
                    and row["value1_rows"] > 0]
    if not alaska_jumbo:
        raise ValueError("The source-backed Alaska Jumbo suppression check is unavailable")
    alaska = alaska_jumbo[0]
    add(alaska, "VALUE1", int(alaska["first_year"]), int(alaska["last_year"]), "quality-edge", export=True)

    for product in catalog_data["products"]:
        product_id = product["product"]
        expected_pairs = sum(len(series["supported_weights"]) for series in product["series"])
        actual_pairs = sum(1 for key in api if api[key]["product"] == product_id and "series-weight" in tags[key])
        if actual_pairs != expected_pairs:
            raise AssertionError(f"Series/weight grid incomplete for {product_id}: {actual_pairs} != {expected_pairs}")
        expected_markets = set(product["markets"])
        actual_markets = {api[key]["market"] for key in api if api[key]["product"] == product_id and "market" in tags[key]}
        if actual_markets != expected_markets:
            raise AssertionError(f"Market grid incomplete for {product_id}")
        expected_levels = {row["geo_level"] for row in product["geographies"]}
        actual_levels = {api[key]["geo_level"] for key in api if api[key]["product"] == product_id and "geography-level" in tags[key]}
        if actual_levels != expected_levels:
            raise AssertionError(f"Geography-level grid incomplete for {product_id}")

    return api, xlsx, tags


def _http_json(base_url: str, endpoint: str, query: dict) -> dict:
    with urlopen(base_url + endpoint + "?" + urlencode(query), timeout=60) as response:
        if response.status != 200:
            raise AssertionError(f"{endpoint} returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _http_xlsx(base_url: str, query: dict) -> bytes:
    with urlopen(base_url + "/api/nmdb-mortgage-statistics-excel?" + urlencode(query), timeout=60) as response:
        if response.status != 200 or "spreadsheetml.sheet" not in response.headers.get("Content-Type", ""):
            raise AssertionError("NMDB filtered Excel endpoint returned an unexpected response")
        payload = response.read()
    if payload[:2] != b"PK":
        raise AssertionError("NMDB filtered Excel endpoint did not return an XLSX package")
    return payload


def _expected_excel_row(report: dict, row: dict) -> tuple:
    values = (
        row["period"], row["year"], row["quarter"], row["geography_level"], row["geography_id"],
        row["geography_name"], row["market"], row["series_id"], report["series"]["label"],
        report["series"]["unit"], ", ".join(report["supported_weights"]), report["measure"],
        row["selected_value"], row["value1_raw"], row["value2_raw"],
        "Yes · fewer than 3 loans" if row["suppressed"] else "No", row["source"], row["frequency"],
    )
    # XLSX cells cannot distinguish a source empty string from an empty cell;
    # dot and all non-empty raw source strings remain distinct.
    return tuple(None if index in (13, 14) and value == "" else value for index, value in enumerate(values))


def _validate_workbook(payload: bytes, report: dict, query: dict) -> tuple[int, int]:
    book = load_workbook(BytesIO(payload), read_only=False, data_only=True)
    try:
        expected_sheets = ["Start Here", "Selected data", "Definitions", "Quality & lineage"]
        if book.sheetnames != expected_sheets:
            raise AssertionError(f"Unexpected NMDB query workbook sheets: {book.sheetnames}")
        start = book["Start Here"]
        checks = {
            "B2": report["product_label"],
            "B5": query["market"],
        }
        for cell, expected in checks.items():
            if start[cell].value != expected:
                raise AssertionError(f"Start Here!{cell} differs from the selected query")
        for cell, token in (("B4", query["geo_level"]), ("B4", query["geo_id"]),
                            ("B6", query["series_id"]), ("B10", query["measure"])):
            if token not in str(start[cell].value):
                raise AssertionError(f"Start Here!{cell} omits filter {token}")
        if str(query["from_year"]) not in str(start["B11"].value) or str(query["to_year"]) not in str(start["B11"].value):
            raise AssertionError("Start Here coverage does not match the selected period filter")

        data = book["Selected data"]
        if "NMDBSelectedData" not in data.tables:
            raise AssertionError("Filtered data is missing its Excel Table filter")
        actual_rows = list(data.iter_rows(min_row=2, max_col=18, values_only=True))
        if len(actual_rows) != len(report["rows"]):
            raise AssertionError("Filtered workbook row count differs from API")
        for index, (actual, expected_row) in enumerate(zip(actual_rows, report["rows"]), start=1):
            expected = _expected_excel_row(report, expected_row)
            if tuple(actual) != expected:
                raise AssertionError(f"Filtered workbook row {index} differs from API across 18 columns")
        if len(data._charts) != (1 if len(report["rows"]) > 1 and any(row["selected_value"] is not None for row in report["rows"]) else 0):
            raise AssertionError("Workbook chart count does not match the filtered series scope")

        quality = book["Quality & lineage"]
        if quality["B2"].value != len(report["rows"]):
            raise AssertionError("Workbook quality row count differs from API")
        if quality["B3"].value != report["quality"]["suppressed_rows"]:
            raise AssertionError("Workbook suppression count differs from API")
        if quality["B4"].value != report["quality"]["selected_value_unavailable_rows"]:
            raise AssertionError("Workbook unavailable-value count differs from API")
        if quality["B5"].value != "None":
            raise AssertionError("Workbook suggests a forecast or imputation was applied")
        return len(actual_rows), len(actual_rows) * 18
    finally:
        book.close()


def accept(root: Path, receipt_path: Path) -> dict:
    root = root.resolve()
    receipt_path = receipt_path.resolve()
    if root.drive.upper() != "D:" or receipt_path.drive.upper() != "D:":
        raise ValueError("Private NMDB source and acceptance inputs must remain on D:")
    catalog_data = catalog(root)
    groups = _coverage_groups(root)
    api_grid, xlsx_grid, tags = build_query_grid(catalog_data, groups)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(_service(root)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    checked_api = 0
    checked_xlsx = 0
    row_checks = 0
    cell_checks = 0
    unavailable_rows = 0
    suppressed_rows = 0
    xlsx_scopes: dict[str, int] = {}
    try:
        api_reports = {}
        for key, query in api_grid.items():
            payload = _http_json(base_url, "/api/nmdb-mortgage-statistics", query)
            if payload.get("status") != "AVAILABLE" or payload.get("filters", {}).get("measure") != query["measure"]:
                raise AssertionError("NMDB API report status or measure does not match query")
            if payload.get("mart_sha256") != catalog_data["mart_sha256"]:
                raise AssertionError("API report mart hash differs from the accepted catalog")
            if payload.get("quality", {}).get("forecast_or_imputation_used") is not False:
                raise AssertionError("API report claims forecast or imputation")
            if not payload.get("rows") or len(payload["rows"]) != payload["quality"]["observations"]:
                raise AssertionError("API response has empty or inconsistent observation counts")
            if len({row["period"] for row in payload["rows"]}) != len(payload["rows"]):
                raise AssertionError("API response contains duplicate periods for one query grain")
            if "quality-edge" in tags[key] and (payload["quality"]["suppressed_rows"] <= 0
                    or payload["quality"]["selected_value_unavailable_rows"] < payload["quality"]["suppressed_rows"]):
                raise AssertionError("The Alaska Jumbo source scope no longer exercises suppression/null preservation")
            unavailable_rows += payload["quality"]["selected_value_unavailable_rows"]
            suppressed_rows += payload["quality"]["suppressed_rows"]
            checked_api += 1
            api_reports[key] = payload
            if checked_api % 25 == 0:
                print(f"API grid: {checked_api}/{len(api_grid)} scopes checked", flush=True)

        for key, query in xlsx_grid.items():
            api = api_reports.get(key)
            if api is None:
                api = _http_json(base_url, "/api/nmdb-mortgage-statistics", query)
                api_reports[key] = api
            binary = _http_xlsx(base_url, query)
            rows, cells = _validate_workbook(binary, api, query)
            row_checks += rows
            cell_checks += cells
            checked_xlsx += 1
            for label in tags[key]:
                xlsx_scopes[label] = xlsx_scopes.get(label, 0) + 1
            if checked_xlsx % 10 == 0:
                print(f"XLSX grid: {checked_xlsx}/{len(xlsx_grid)} exports reconciled", flush=True)

        source_receipt_path = Path(json.loads((root / "data/derived/fhfa-nmdb-market-statistics/receipt.json").read_text(encoding="utf-8"))["source_receipt"])
        source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
        if source_receipt.get("status") != "PASS":
            raise AssertionError("Upstream FHFA source receipt is not PASS")
        receipt = {
            "evidence_type": "nmdb_market_statistics_api_xlsx_query_grid_acceptance",
            "status": "PASS",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": {
                "publisher": "FHFA National Mortgage Database Aggregate Statistics",
                "release_date": catalog_data["source_release_date"],
                "upstream_acquisition_receipt_status": source_receipt["status"],
                "mart_sha256": catalog_data["mart_sha256"],
                "source_receipt_sha256": sha256(source_receipt_path),
            },
            "coverage": {
                "api_query_count": checked_api,
                "api_series_weight_pairs_by_product": {
                    product["product"]: sum(1 for key in api_grid if api_grid[key]["product"] == product["product"] and "series-weight" in tags[key])
                    for product in catalog_data["products"]
                },
                "api_market_scopes": sum(1 for key in api_grid if "market" in tags[key]),
                "markets_by_product": {
                    product["product"]: sorted({api_grid[key]["market"] for key in api_grid if api_grid[key]["product"] == product["product"] and "market" in tags[key]})
                    for product in catalog_data["products"]
                },
                "api_geography_levels_by_product": {
                    product["product"]: sorted({api_grid[key]["geo_level"] for key in api_grid if api_grid[key]["product"] == product["product"] and "geography-level" in tags[key]})
                    for product in catalog_data["products"]
                },
                "xlsx_query_count": checked_xlsx,
                "xlsx_suppression_edge_scopes": sum(1 for key in xlsx_grid if "quality-edge" in tags[key]),
                "xlsx_rows_compared": row_checks,
                "xlsx_cells_compared": cell_checks,
                "xlsx_scope_checks": xlsx_scopes,
                "selected_unavailable_observation_occurrences_across_queries": unavailable_rows,
                "suppressed_observation_occurrences_across_queries": suppressed_rows,
            },
            "results": {
                "api_http": "Every grid query returned a unique-period report bound to the accepted mart digest.",
                "xlsx_http": "Every workbook returned four expected sheets, a filtered Excel Table, and all 18 data columns matched the corresponding API rows.",
                "forecast_or_imputation_used": False,
                "duplicate_periods": 0,
                "browser_page_errors": [],
            },
            "limitations": [
                "This is a broad query-grid acceptance, not a Cartesian test of every geography × market × series × measure × year combination.",
                "Native Microsoft Excel open/recalculate is recorded separately for selected exports; XLSX package parity here is checked with openpyxl.",
                "Suppressed and unavailable counts are observations across overlapping query scopes, not distinct source-cell totals.",
                "New originations and outstanding active-loan stock are separate estimands and are not joined or added.",
                "The source contains aggregate estimates only; it supplies no borrower-level repayment target or PD label.",
            ],
        }
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Private workspace containing the receipt-bound NMDB market mart")
    parser.add_argument("--receipt", required=True, type=Path, help="Acceptance JSON destination on D:")
    args = parser.parse_args()
    result = accept(args.root, args.receipt.resolve())
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
