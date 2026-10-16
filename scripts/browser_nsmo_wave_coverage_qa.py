"""Browser acceptance for the NSMO field-level wave coverage dictionary."""

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
    browser_errors: list[str] = []
    checks: list[str] = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=args.root.resolve())))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/nsmo"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.on("pageerror", lambda error: browser_errors.append(str(error)))
            response = page.goto(url, wait_until="networkidle", timeout=30_000)
            if response is None or response.status != 200:
                raise RuntimeError("NSMO page did not return HTTP 200")
            download = page.locator('a.excel-download[href="/downloads/nsmo-reference.xlsx"]')
            if download.get_attribute("href") != "/downloads/nsmo-reference.xlsx":
                raise AssertionError("NSMO Excel reference download is not linked from the dictionary")
            checks.append("codebook/category Excel workbook is linked from the dictionary")
            page.locator("#dictionary-count").get_by_text("319", exact=False).wait_for(timeout=15_000)
            page.locator("#dictionary-count").get_by_text("9", exact=False).wait_for(timeout=15_000)
            checks.append("dictionary reports 319 survey-variable coverage rows and 9 item notes")
            dictionary_intro = page.locator(".dictionary-panel").inner_text()
            for phrase in ("giá trị không thiếu trong PUF", "impute", "không phải response rate", "Biến Z"):
                if phrase.lower() not in dictionary_intro.lower():
                    raise AssertionError(f"Imputation caveat is missing: {phrase}")
            checks.append("dictionary explains imputation, Z-variable limits and non-response-rate scope")
            for field, observed, not_asked in (
                ("x20j", "13-24", "1-12;25-46"),
                ("x14a", "7-46", "1-6"),
                ("x14a_1", "1-6", "7-46"),
            ):
                search = page.locator("#field-search")
                search.fill(field)
                option = page.locator(f'.field-option[data-field="{field}"]')
                option.wait_for(timeout=10_000)
                option.click()
                detail = page.locator("#field-detail")
                detail.get_by_text("PUF waves with nonmissing values (may be imputed)", exact=True).wait_for()
                text = detail.inner_text()
                if observed not in text or not_asked not in text:
                    raise AssertionError(f"Wave coverage mismatch in rendered detail for {field}")
                checks.append(f"{field} observed/not-asked wave ranges render correctly")
            page.locator("#field-search").fill("x94a")
            page.locator('.field-option[data-field="x94a"]').click()
            detail = page.locator("#field-detail")
            detail.get_by_text("Cross-wave comparability", exact=True).wait_for()
            text = detail.inner_text()
            if "borrow enough money" not in text or "borrow a significant amount" not in text:
                raise AssertionError("X94A wording-version break is not visible in the field detail")
            checks.append("X94A wording-version break and trend sensitivity render in the dictionary")

            legacy_payload = page.evaluate("async () => await (await fetch('/api/nsmo-dictionary')).json()")
            legacy_payload.pop("item_comparability", None)
            legacy_payload.pop("item_comparability_count", None)
            page.route("**/api/nsmo-dictionary", lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps(legacy_payload)))
            page.reload(wait_until="networkidle")
            page.locator("#field-search").fill("x94a")
            page.locator('.field-option[data-field="x94a"]').click()
            detail = page.locator("#field-detail")
            detail.get_by_text("Cross-wave review unavailable", exact=True).wait_for()
            if "codebook field details remain available" not in detail.inner_text():
                raise AssertionError("Legacy dictionary response does not explain its missing item notes")
            if "ghi chú version chưa được server nạp" not in page.locator("#dictionary-count").inner_text():
                raise AssertionError("Dictionary header does not show that the legacy server lacks review notes")
            checks.append("legacy server dictionary stays usable and explains missing review notes")
            if browser_errors:
                raise AssertionError(f"Browser JavaScript errors: {browser_errors}")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    receipt = {
        "schema_version": "nsmo-wave-coverage-browser-qa-v1",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "url": "/nsmo on isolated local test server",
        "browser": "Microsoft Edge headless via Playwright",
        "checks": checks,
        "page_errors": browser_errors,
        "privacy": "No identifiers, screenshots or source rows captured.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "page_errors": 0}))


if __name__ == "__main__":
    main()
