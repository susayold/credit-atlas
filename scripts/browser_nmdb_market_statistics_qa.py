"""Browser acceptance for FHFA NMDB New/Outstanding market statistics."""

from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

from credit_atlas.nmdb_mortgage_statistics import catalog, report
from credit_atlas.server import handler_for


def _segments(rows: list[dict]) -> int:
    count = 0
    open_segment = False
    for row in rows:
        if row["selected_value"] is None:
            open_segment = False
        elif not open_segment:
            count += 1
            open_segment = True
    return count


def _service(root: Path):
    # Keep this QA server focused on the read-only NMDB endpoints. Other routes
    # are wired by handler_for but are not called by this acceptance run.
    return SimpleNamespace(
        root=root,
        nmdb_mortgage_statistics_catalog=lambda: catalog(root),
        nmdb_mortgage_statistics=lambda query: report(root, query),
    )


def _wait_for_points(page, expected: int) -> None:
    page.wait_for_function(
        "expected => { const chart = document.querySelector('#content .nmdb-chart'); "
        "return !!chart && chart.querySelectorAll('.nmdb-point').length === expected; }",
        arg=expected,
        timeout=30_000,
    )


def _select(page, locator, value: str) -> None:
    locator.focus()
    locator.select_option(value)
    page.wait_for_load_state("networkidle", timeout=30_000)


def _download_and_check(page, path: Path, expected: dict) -> None:
    link = page.get_by_role("link", name="Tải Excel theo filter đang chọn")
    with page.expect_download() as info:
        link.click()
    download = info.value
    download.save_as(path)
    if path.read_bytes()[:2] != b"PK":
        raise AssertionError("Query-scoped Excel endpoint did not return an XLSX package")

    book = load_workbook(path, data_only=True)
    try:
        required_sheets = ["Start Here", "Selected data", "Definitions", "Quality & lineage"]
        if book.sheetnames != required_sheets:
            raise AssertionError(f"Unexpected workbook sheets: {book.sheetnames}")
        start = book["Start Here"]
        if start["B2"].value != expected["product_label"]:
            raise AssertionError("Workbook product does not match the selected query")
        geography = str(start["B4"].value)
        for token in (expected["filters"]["geo_level"], expected["filters"]["geo_name"], expected["filters"]["geo_id"]):
            if token not in geography:
                raise AssertionError("Workbook geography does not match the selected query")
        if start["B5"].value != expected["filters"]["market"]:
            raise AssertionError("Workbook mortgage market does not match the selected query")
        if expected["series"]["series_id"] not in str(start["B6"].value):
            raise AssertionError("Workbook series does not match the selected query")
        if expected["measure"] not in str(start["B10"].value):
            raise AssertionError("Workbook weighting does not match the selected query")
        coverage = str(start["B11"].value)
        if str(expected["filters"]["from_year"]) not in coverage or str(expected["filters"]["to_year"]) not in coverage:
            raise AssertionError("Workbook coverage range does not match the selected query")
        data = book["Selected data"]
        rows = list(data.iter_rows(min_row=2, values_only=True))
        if len(rows) != len(expected["rows"]):
            raise AssertionError("Workbook row count does not match the API query")
        if rows[-1][0] != expected["rows"][-1]["period"]:
            raise AssertionError("Workbook latest period does not match the API query")
        if rows[-1][12] != expected["rows"][-1]["selected_value"]:
            raise AssertionError("Workbook selected value does not match the API query")
        unavailable = sum(row[12] is None for row in rows)
        if unavailable != expected["quality"]["selected_value_unavailable_rows"]:
            raise AssertionError("Workbook does not preserve selected-value missingness")
        flagged = sum(str(row[15]).startswith("Yes") for row in rows)
        if flagged != expected["quality"]["suppressed_rows"]:
            raise AssertionError("Workbook does not preserve suppression flags")
        if len(data._charts) != 1:
            raise AssertionError("Workbook should include one selected-series chart")
    finally:
        book.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Private workspace containing the receipt-bound NMDB mart")
    parser.add_argument("--web-root", type=Path, help="Public checkout UI directory when data and code use separate roots")
    parser.add_argument("--receipt", required=True, type=Path, help="Private QA JSON output; downloaded workbooks stay beside it")
    args = parser.parse_args()
    root = args.root.resolve()
    web_root = args.web_root.resolve() if args.web_root else None
    catalog_data = catalog(root)
    products = {row["product"]: row for row in catalog_data["products"]}

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(_service(root), web_root=web_root))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    checks: list[str] = []
    errors: list[str] = []
    downloads = args.receipt.parent
    downloads.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            response = page.goto(f"http://127.0.0.1:{server.server_port}/?view=nmdb", wait_until="networkidle", timeout=60_000)
            if response is None or response.status != 200:
                raise RuntimeError("NMDB workbench did not return HTTP 200")

            product = page.get_by_label("Sản phẩm", exact=True)
            geo_level = page.get_by_label("Geography level", exact=True)
            geography = page.get_by_label("Geography", exact=True)
            market = page.get_by_label("Mortgage market", exact=True)
            series = page.get_by_label("Chỉ số FHFA", exact=True)
            measure = page.get_by_label("Weight / measure", exact=True)
            from_year = page.get_by_label("Từ năm", exact=True)
            to_year = page.get_by_label("Đến năm", exact=True)
            _wait_for_points(page, 28)
            new_query = {
                "product": "new_annual", "geo_level": "National", "geo_id": "USA",
                "market": "All Mortgages", "series_id": "AVE_INTRATE", "measure": "VALUE1",
                "from_year": "1998", "to_year": "2025",
            }
            new_report = report(root, new_query)
            if new_report["quality"]["observations"] != 28 or new_report["rows"][-1]["selected_value"] != 6.3:
                raise AssertionError("National New annual source checkpoint changed")
            if not page.locator("#content .metric-value").nth(0).inner_text().startswith("6.3"):
                raise AssertionError("New annual latest KPI does not match 6.3% source observation")
            checks.append("New annual default filter and latest KPI match the receipt-bound 1998–2025 source series")

            _select(page, product, "outstanding_quarterly")
            _wait_for_points(page, 54)
            _select(page, series, "AVE_MTMLTV")
            measure.locator('option[value="VALUE2"]').wait_for(state="attached", timeout=20_000)
            _select(page, measure, "VALUE2")
            _wait_for_points(page, 54)
            outstanding_query = {
                "product": "outstanding_quarterly", "geo_level": "National", "geo_id": "USA",
                "market": "All Mortgages", "series_id": "AVE_MTMLTV", "measure": "VALUE2",
                "from_year": "2013", "to_year": "2026",
            }
            outstanding = report(root, outstanding_query)
            if outstanding["quality"]["observations"] != 54 or outstanding["rows"][-1]["period"] != "2026Q2" or outstanding["rows"][-1]["selected_value"] != 54.2:
                raise AssertionError("Outstanding quarterly VALUE2 source checkpoint changed")
            if not page.locator("#content .metric-value").nth(0).inner_text().startswith("54.2"):
                raise AssertionError("Outstanding latest KPI does not match 54.2% source observation")
            if "nmdb_measure=VALUE2" not in page.url or "nmdb_product=outstanding_quarterly" not in page.url:
                raise AssertionError("Selected NMDB product and weight are not persisted in the URL")
            checks.append("Outstanding stock, VALUE2 UPB weighting, 54 quarterly points and URL filters match the source")

            _select(page, series, "TOT_UPB")
            if measure.locator("option").count() != 1 or measure.input_value() != "VALUE1":
                raise AssertionError("VALUE1-only outstanding series exposes an unsupported VALUE2 selector")
            rejected = page.request.get(
                f"http://127.0.0.1:{server.server_port}/api/nmdb-mortgage-statistics?"
                + urlencode({**outstanding_query, "series_id": "TOT_UPB", "measure": "VALUE2"})
            )
            if rejected.status != 400:
                raise AssertionError("API accepted VALUE2 for VALUE1-only TOT_UPB")
            checks.append("VALUE1-only series is enforced in the selector and rejected by the API")

            _select(page, product, "new_annual")
            _select(page, geo_level, "State")
            geography.locator('option[value="AK"]').wait_for(state="attached", timeout=20_000)
            _select(page, geography, "AK")
            _select(page, market, "Jumbo Market")
            _select(page, series, "AVE_INTRATE")
            _select(page, measure, "VALUE1")
            alaska_query = {
                "product": "new_annual", "geo_level": "State", "geo_id": "AK",
                "market": "Jumbo Market", "series_id": "AVE_INTRATE", "measure": "VALUE1",
                "from_year": str(products["new_annual"]["first_year"]), "to_year": str(products["new_annual"]["last_year"]),
            }
            alaska = report(root, alaska_query)
            segments = _segments(alaska["rows"])
            _wait_for_points(page, sum(row["selected_value"] is not None for row in alaska["rows"]))
            path = page.locator("#content .nmdb-chart path.line-primary").get_attribute("d") or ""
            if path.count("M") != segments or segments < 2:
                raise AssertionError("Chart connects across NMDB suppression gaps instead of drawing separate segments")
            metrics = [item.inner_text() for item in page.locator("#content .metric-value").all()]
            if metrics[3] != f"{alaska['quality']['suppressed_rows']} / {alaska['quality']['selected_value_unavailable_rows']}":
                raise AssertionError("Suppressed and unavailable counts do not match the source query")
            if "2025" not in page.locator("#content").inner_text() or "Suppressed / unavailable" not in page.locator("#content").inner_text():
                raise AssertionError("Missing latest Alaska observation is not clearly shown as unavailable")
            checks.append(f"Alaska Jumbo series retains {alaska['quality']['suppressed_rows']} suppressed cells and breaks the chart into {segments} observed segments")

            _download_and_check(page, downloads / "CreditAtlas-NMDB-New-Alaska-Jumbo-browser-qa.xlsx", alaska)
            checks.append("New annual filtered workbook preserves 27 source periods, suppression flags and unavailable selected values")

            _select(page, product, "outstanding_quarterly")
            _select(page, series, "AVE_MTMLTV")
            measure.locator('option[value="VALUE2"]').wait_for(state="attached", timeout=20_000)
            _select(page, measure, "VALUE2")
            _wait_for_points(page, 54)
            outstanding = report(root, outstanding_query)
            _download_and_check(page, downloads / "CreditAtlas-NMDB-Outstanding-VALUE2-browser-qa.xlsx", outstanding)
            checks.append("Outstanding VALUE2 filtered workbook matches the 54-quarter API series and latest 2026Q2 value")

            page.reload(wait_until="networkidle", timeout=60_000)
            page.get_by_label("Sản phẩm").wait_for()
            _wait_for_points(page, 54)
            if page.get_by_label("Sản phẩm", exact=True).input_value() != "outstanding_quarterly" or page.get_by_label("Weight / measure", exact=True).input_value() != "VALUE2":
                raise AssertionError("Reload does not restore the selected NMDB query")
            checks.append("Reload restores the selected NMDB product, series and weighting from URL state")

            page.set_viewport_size({"width": 390, "height": 844})
            dimensions = page.evaluate(
                "() => { const node=document.querySelector('.nmdb-filters'); "
                "return {width:node.clientWidth,scroll:node.scrollWidth,chart:document.querySelector('.nmdb-chart').getBoundingClientRect().width}; }"
            )
            if dimensions["scroll"] > dimensions["width"] or dimensions["chart"] > dimensions["width"] + 1:
                raise AssertionError(f"NMDB filters or chart overflow a mobile viewport: {dimensions}")
            checks.append("Filters and chart fit a 390px mobile viewport")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    if errors:
        raise AssertionError(f"Browser page or console errors: {errors}")

    receipt = {
        "schema_version": "nmdb-market-browser-qa-v1",
        "status": "PASS",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "page_errors": errors,
        "data": {
            "mart_sha256": catalog_data["mart_sha256"],
            "new_annual_rows": products["new_annual"]["row_count"],
            "outstanding_quarterly_rows": products["outstanding_quarterly"]["row_count"],
            "new_alaska_jumbo_suppressed": alaska["quality"]["suppressed_rows"],
            "outstanding_latest_period": outstanding["rows"][-1]["period"],
            "outstanding_latest_value2": outstanding["rows"][-1]["selected_value"],
        },
        "limitations": [
            "Workbook content was checked with openpyxl; Microsoft Excel desktop open/recalculate is not asserted.",
            "Only the documented NMDB New/Outstanding query paths were browser-tested.",
            "No raw loan-level identifiers or source rows are written to this receipt.",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
