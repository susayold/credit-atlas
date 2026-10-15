"""Browser acceptance for the NSMO field-level wave coverage dictionary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8770/nsmo")
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    browser_errors: list[str] = []
    checks: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        response = page.goto(args.url, wait_until="networkidle", timeout=30_000)
        if response is None or response.status != 200:
            raise RuntimeError("NSMO page did not return HTTP 200")
        page.locator("#dictionary-count").get_by_text("319", exact=False).wait_for(timeout=15_000)
        checks.append("dictionary reports 319 survey-variable coverage rows")
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
            detail.get_by_text("Observed response waves", exact=True).wait_for()
            text = detail.inner_text()
            if observed not in text or not_asked not in text:
                raise AssertionError(f"Wave coverage mismatch in rendered detail for {field}")
            checks.append(f"{field} observed/not-asked wave ranges render correctly")
        if browser_errors:
            raise AssertionError(f"Browser JavaScript errors: {browser_errors}")
        browser.close()
    receipt = {
        "schema_version": "nsmo-wave-coverage-browser-qa-v1",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "url": args.url,
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
