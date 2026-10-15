"""Browser acceptance for the separate aggregate-only HUD FHA benchmark."""

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
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=args.root.resolve())))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    errors: list[str] = []
    checks: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = page.goto(f"http://127.0.0.1:{server.server_port}/nsmo", wait_until="networkidle", timeout=45_000)
            if response is None or response.status != 200:
                raise RuntimeError("NSMO page did not return HTTP 200")
            state = page.locator("#hud-fha-state")
            state.get_by_text("HUD August 2026 report loaded", exact=False).wait_for(timeout=15_000)
            checks.append("HUD aggregate API and benchmark card load")
            source_link = page.get_by_role("link", name="HUD report · Aug 2026")
            if source_link.get_attribute("href") != "https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf":
                raise AssertionError("Official HUD report citation is not linked from the panel")
            checks.append("official HUD report is directly linked")

            metrics = page.locator("#hud-fha-metrics").inner_text()
            if "8,416,639" not in metrics or "6.42%" not in metrics:
                raise AssertionError("NSA latest metrics do not match HUD Table 1")
            adjustment = page.locator("#hud-adjustment")
            adjustment.select_option("SA")
            metrics = page.locator("#hud-fha-metrics").inner_text()
            if "6.63%" not in metrics:
                raise AssertionError("SA latest serious delinquency does not match HUD Table 1")
            checks.append("NSA/SA selector updates IIF and delinquency KPIs")

            rows = page.locator("#hud-fha-subgroups tbody tr").all_inner_texts()
            if len(rows) != 7 or "11.28%" not in rows[1] or "1.94%" not in rows[-1]:
                raise AssertionError("HUD credit-score subgroup rates do not match Table 3")
            dimension = page.locator("#hud-subgroup-dimension")
            dimension.select_option("down_payment_assistance")
            dpa_rows = page.locator("#hud-fha-subgroups tbody tr").all_inner_texts()
            if len(dpa_rows) != 6 or "9.33%" not in dpa_rows[4] or "No DPA" not in dpa_rows[-1]:
                raise AssertionError("HUD down-payment-assistance panel does not match Table 3")
            dimension.select_option("all")
            if page.locator("#hud-fha-subgroups tbody tr").count() != 60:
                raise AssertionError("All Table 3 subgroup rows are not exposed")
            checks.append("credit-score subgroup renders; eight Table 3 panels remain selectable")

            reason_rows = page.locator("#hud-new-90plus-reasons tbody tr").all_inner_texts()
            foreclosure_rows = page.locator("#hud-foreclosure-statistics tbody tr").all_inner_texts()
            recovery_rows = page.locator("#hud-reo-recovery tbody tr").all_inner_texts()
            loss_rows = page.locator("#hud-reo-loss-components tbody tr").all_inner_texts()
            if len(reason_rows) != 22 or "Partial" not in reason_rows[-1] or "51,483" not in page.locator("#hud-reason-metrics").inner_text():
                raise AssertionError("HUD Table 2 reason coverage or latest partial-period summary is wrong")
            if len(foreclosure_rows) != 37 or "0.28%" not in page.locator("#hud-foreclosure-metrics").inner_text():
                raise AssertionError("HUD Table 4 foreclosure pipeline does not match August 2026")
            if len(recovery_rows) != 50 or "50.5%" not in page.locator("#hud-recovery-metrics").inner_text() or "-3.7 pp" not in page.locator("#hud-recovery-metrics").inner_text():
                raise AssertionError("HUD Table 5 national REO recovery does not match July 2026")
            if len(loss_rows) != 13 or "49.48%" not in page.locator("#hud-loss-metrics").inner_text() or "$101,498" not in page.locator("#hud-loss-metrics").inner_text():
                raise AssertionError("HUD Table 6 REO loss detail does not match July 2026")
            checks.append("HUD Tables 2, 4, 5 and 6 render all source rows with scoped KPI summaries")

            with page.expect_download() as download_info:
                page.get_by_role("link", name="Tải Excel HUD FHA · đủ 6 bảng").click()
            download = download_info.value
            if download.suggested_filename != "CreditAtlas-HUD-FHA-Performance.xlsx":
                raise AssertionError("HUD benchmark Excel filename is wrong")
            if download.path().read_bytes()[:2] != b"PK":
                raise AssertionError("HUD benchmark Excel download is not an XLSX package")
            checks.append("six-table HUD benchmark workbook downloads from the app")

            page.set_viewport_size({"width": 390, "height": 844})
            dimensions = page.evaluate("({w:document.querySelector('.hud-context-panel').clientWidth,s:document.querySelector('.hud-context-panel').scrollWidth,cols:getComputedStyle(document.querySelector('#hud-fha-metrics')).gridTemplateColumns.split(' ').length})")
            if dimensions["s"] > dimensions["w"] or dimensions["cols"] != 2:
                raise AssertionError(f"HUD panel has mobile overflow: {dimensions}")
            checks.append("HUD panel remains within mobile viewport")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

    if errors:
        raise AssertionError(f"Browser page errors: {errors}")
    receipt = {
        "schema_version": "hud-fha-browser-qa-v1",
        "status": "PASS",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "browser_errors": errors,
        "source": "HUD August 2026 FHA loan performance report; aggregate-only",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
