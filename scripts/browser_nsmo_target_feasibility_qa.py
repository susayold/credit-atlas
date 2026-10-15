"""Browser acceptance for the aggregate-only NSMO target-feasibility panel."""

from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from playwright.sync_api import sync_playwright

from credit_atlas.server import handler_for


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    checks: list[str] = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=args.root)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/nsmo"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = page.goto(url, wait_until="networkidle", timeout=45_000)
            if response is None or response.status != 200:
                raise RuntimeError("NSMO page did not return HTTP 200")
            state = page.locator("#target-feasibility-state")
            state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            checks.append("hash-bound feasibility receipt loads in UI")

            metrics = page.locator("#target-feasibility-metrics").inner_text()
            if "59,703" not in metrics or "156" not in metrics:
                raise AssertionError("one-landmark baseline/90+ support metrics do not match verified aggregates")
            checks.append("one-landmark distinct-loan support renders")

            mode = page.locator("#target-anchor-choice")
            mode.select_option("repeated")
            metrics = page.locator("#target-feasibility-metrics").inner_text()
            if "872,888" not in metrics or "2,174" not in metrics:
                raise AssertionError("repeated-landmark snapshot/event metrics do not match verified aggregates")
            note = page.locator("#target-feasibility-note").inner_text()
            if "not independent" not in note:
                raise AssertionError("repeated-landmark dependence caveat is not visible")
            checks.append("repeated landmarks show snapshot and dependence caveat")

            page.locator("#target-vintage-band").select_option("2017-2019")
            rows = page.locator("#target-vintage-table tbody tr").all_inner_texts()
            if len(rows) != 3 or not all(year in " ".join(rows) for year in ("2017", "2018", "2019")):
                raise AssertionError("vintage band filter does not return 2017–2019 rows")
            checks.append("vintage filter narrows repeated-landmark table")

            page.locator("#target-vintage-band").select_option("all")

            if page.locator("#target-quarter-table tbody tr").count() != 51:
                raise AssertionError("quarter support table does not show all 51 performance quarters")
            checks.append("quarter table distinguishes full and short horizons")

            origin_state = page.locator("#origination-feasibility-state")
            origin_state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            origin_metrics = page.locator("#origination-feasibility-metrics").inner_text()
            if "65" not in origin_metrics or "53,184" not in origin_metrics:
                raise AssertionError("origination-aligned feasibility metrics do not match the verified receipt")
            if page.locator("#origination-feasibility-table tbody tr").count() != 12:
                raise AssertionError("origination-aligned table does not show all 12 vintages")
            origin_note = page.locator("#origination-feasibility-note").inner_text()
            if "cannot establish event dates" not in origin_note or "PD" not in origin_note:
                raise AssertionError("origination-aligned support caveat is not visible")
            checks.append("origination-aligned support shows sparse outcomes and no-PD caveat")

            page.locator("#target-vintage-band").select_option("2017-2019")
            origin_rows = page.locator("#origination-feasibility-table tbody tr").all_inner_texts()
            if len(origin_rows) != 3 or not all(year in " ".join(origin_rows) for year in ("2017", "2018", "2019")):
                raise AssertionError("origination vintage filter does not narrow to 2017–2019")
            checks.append("shared vintage filter applies to origination support table")
            page.locator("#target-vintage-band").select_option("all")

            transition_state = page.locator("#transition-support-state")
            transition_state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            transition_metrics = page.locator("#transition-support-metrics").inner_text()
            if not all(value in transition_metrics for value in ("322 / 296", "363 / 322", "393 / 330")):
                raise AssertionError(f"distinct/repeated transition support does not match the verified receipt: {transition_metrics}")
            if page.locator("#transition-support-table tbody tr").count() != 36:
                raise AssertionError("transition support table does not show all vintage/state groups")
            transition_note = page.locator("#transition-support-note").inner_text()
            if not all(value in transition_note for value in ("859", "805", "50", "4")):
                raise AssertionError("first-observed event partition is not fully visible")
            checks.append("first-observed 90+ support reconciles by state and vintage")

            page.locator("#target-vintage-band").select_option("2017-2019")
            transition_rows = page.locator("#transition-support-table tbody tr").all_inner_texts()
            if len(transition_rows) != 9 or not all(year in " ".join(transition_rows) for year in ("2017", "2018", "2019")):
                raise AssertionError("transition support vintage filter does not return 2017–2019 groups")
            checks.append("shared vintage filter applies to transition support table")
            page.locator("#target-vintage-band").select_option("all")

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(150)
            dimensions = page.evaluate("({width: document.querySelector('.target-feasibility-panel').clientWidth, scrollWidth: document.querySelector('.target-feasibility-panel').scrollWidth, columns: getComputedStyle(document.querySelector('#target-feasibility-metrics')).gridTemplateColumns.split(' ').length, origColumns: getComputedStyle(document.querySelector('#origination-feasibility-metrics')).gridTemplateColumns.split(' ').length, origTableWidth: document.querySelector('#origination-feasibility-table').clientWidth, origTableScroll: document.querySelector('#origination-feasibility-table').scrollWidth, transitionColumns: getComputedStyle(document.querySelector('#transition-support-metrics')).gridTemplateColumns.split(' ').length, transitionTableWidth: document.querySelector('#transition-support-table').clientWidth, transitionTableScroll: document.querySelector('#transition-support-table').scrollWidth})")
            if dimensions["scrollWidth"] > dimensions["width"] or dimensions["columns"] != 2:
                raise AssertionError(f"target panel overflows or fails mobile KPI layout: {dimensions}")
            if dimensions["origColumns"] != 2 or dimensions["origTableScroll"] <= dimensions["origTableWidth"]:
                raise AssertionError(f"origination panel mobile layout or table scroller is incorrect: {dimensions}")
            if dimensions["transitionColumns"] != 2 or dimensions["transitionTableScroll"] <= dimensions["transitionTableWidth"]:
                raise AssertionError(f"transition support mobile layout or table scroller is incorrect: {dimensions}")
            checks.append("mobile feasibility panels fit viewport and tables scroll horizontally")
            if errors:
                raise AssertionError(f"Browser JavaScript errors: {errors}")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

    receipt = {
        "schema_version": "nsmo-target-feasibility-browser-qa-v2",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "browser": "Microsoft Edge headless via Playwright",
        "checks": checks,
        "page_errors": errors,
        "privacy": "No identifiers, screenshots or source rows captured.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "page_errors": len(errors)}))


if __name__ == "__main__":
    main()
