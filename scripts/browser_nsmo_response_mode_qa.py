"""Browser acceptance for FHFA's aggregate NSMO survey-return table."""

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
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=args.root.resolve())))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = page.goto(f"http://127.0.0.1:{server.server_port}/nsmo", wait_until="networkidle", timeout=30_000)
            if response is None or response.status != 200:
                raise RuntimeError("NSMO page did not return HTTP 200")
            status = page.locator("#survey-returns-state")
            status.get_by_text("48 waves reconciled", exact=False).wait_for(timeout=20_000)
            checks.append("API reports reconciled 48-wave table")
            metrics = page.locator("#survey-returns-metrics .metric")
            if metrics.count() != 4:
                raise AssertionError("Expected four response-mode summary metrics")
            metric_text = metrics.all_inner_texts()
            if not any("45.55%" in text for text in metric_text):
                raise AssertionError("PUF-wide online share is not displayed")
            if not any("23.87% → 64.93%" in text for text in metric_text):
                raise AssertionError("Wave 1 to 46 online-share drift is not displayed")
            checks.append("PUF KPIs show response share and wave 1–46 change")
            table = page.locator("#survey-returns-table table")
            if table.locator("tbody tr").count() != 48:
                raise AssertionError("Expected all 48 FHFA report waves")
            if "Outside PUF" not in table.locator("tbody tr").nth(46).inner_text():
                raise AssertionError("Wave 47 is not labeled outside PUF v7.0")
            if "Outside PUF" not in table.locator("tbody tr").nth(47).inner_text():
                raise AssertionError("Wave 48 is not labeled outside PUF v7.0")
            checks.append("All report waves render, with waves 47–48 separated from PUF")
            usable_metrics = page.locator("#usable-responses-metrics .metric").all_inner_texts()
            if len(usable_metrics) != 4 or not any("63,151" in text for text in usable_metrics):
                raise AssertionError("Usable returned surveys are not summarized")
            if not any("62,359" in text for text in usable_metrics) or not any("792" in text for text in usable_metrics):
                raise AssertionError("PUF inclusion and aggregate scope gap are not summarized")
            usable_table = page.locator("#usable-responses-table table")
            if usable_table.locator("tbody tr").count() != 46:
                raise AssertionError("Expected 46 usable-response disposition rows")
            if "295" not in usable_table.locator("tbody tr").nth(6).inner_text():
                raise AssertionError("Wave 7 remote-rural scope gap is not visible")
            if "497" not in usable_metrics[-1]:
                raise AssertionError("Wave 45–46 origination-scope gap is not visible")
            checks.append("Tables 4–6 reconcile returned, usable and PUF release counts")
            limitation = " ".join(page.locator(".response-mode-panel .footnote").all_inner_texts())
            if "không có trường response-mode ở cấp mortgage" not in limitation:
                raise AssertionError("Mode-to-mortgage linkage limitation is not visible")
            checks.append("UI explains no respondent-level mode linkage and no causal interpretation")
            dictionary_count = page.locator("#dictionary-count").inner_text()
            if "587 feature gates" not in dictionary_count or "0 feature đã duyệt" not in dictionary_count:
                raise AssertionError("Dictionary does not disclose the full gate inventory and zero approved features")
            page.locator("#field-search").fill("sex_o1")
            page.locator("#field-results button").first.click()
            detail = page.locator("#field-detail").inner_text()
            if "SENSITIVE_OR_PROXY_POLICY_REVIEW" not in detail or "NOT_APPROVED_GOVERNANCE_REVIEW_REQUIRED" not in detail:
                raise AssertionError("Sensitive-field governance gate is not shown in the field detail")
            checks.append("587 model gates are searchable; sensitive fields show an explicit governance hold")
            if errors:
                raise AssertionError(f"Browser JavaScript errors: {errors}")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    receipt = {
        "schema_version": "nsmo-dictionary-gates-browser-qa-v2",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "page_errors": errors,
        "privacy": "Aggregate wave counts only; no respondent rows, IDs, or screenshots captured.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
