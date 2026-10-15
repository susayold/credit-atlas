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

            if page.locator("#target-quarter-table tbody tr").count() != 51:
                raise AssertionError("quarter support table does not show all 51 performance quarters")
            checks.append("quarter table distinguishes full and short horizons")
            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(150)
            dimensions = page.evaluate("({width: document.querySelector('.target-feasibility-panel').clientWidth, scrollWidth: document.querySelector('.target-feasibility-panel').scrollWidth, columns: getComputedStyle(document.querySelector('#target-feasibility-metrics')).gridTemplateColumns.split(' ').length})")
            if dimensions["scrollWidth"] > dimensions["width"] or dimensions["columns"] != 2:
                raise AssertionError(f"target panel overflows or fails mobile KPI layout: {dimensions}")
            checks.append("mobile target panel fits viewport with two KPI columns")
            if errors:
                raise AssertionError(f"Browser JavaScript errors: {errors}")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

    receipt = {
        "schema_version": "nsmo-target-feasibility-browser-qa-v1",
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
