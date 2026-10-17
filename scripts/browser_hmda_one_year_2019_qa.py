"""Targeted browser acceptance for the private HMDA 2019 One-Year release."""
from __future__ import annotations

import argparse
import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

from playwright.sync_api import expect, sync_playwright

expect.set_options(timeout=120_000)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import sha256, timestamp, write_new


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    args = parser.parse_args()
    root = args.root.resolve()
    if root.drive.upper() != "D:":
        parser.error("Private HMDA evidence and downloads must remain on D:")

    output = root / "artifacts/private" / ("hmda-one-year-2019-browser-qa-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    catalog = service.hmda_one_year_2019_views.catalog()
    view_id = next(row["view_id"] for row in catalog["views"] if row["status"] == "verified")
    snapshot = service.hmda_one_year_2019_views.view(view_id)
    state_report = service.hmda_one_year_2019_views.report(view_id, {"dimension": "state_code"})
    reason_report = service.hmda_one_year_2019_views.report(view_id, {"dimension": "denial_reason_1"})
    source_folder = root / "data/private/hmda" / snapshot["source_id"]
    source_workbook = source_folder / "CreditAtlas-HMDA-One-Year-2019-Audit.xlsx"
    if not source_workbook.is_file():
        raise FileNotFoundError(source_workbook)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service, web_root=ROOT / "apps/web"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks: list[str] = []
    errors: list[str] = []
    screenshot = output / "hmda-2019-one-year.png"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(120_000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.goto(base + "/?view=hmda&hmda_panel=one_year_2019", wait_until="domcontentloaded", timeout=60_000)

            panel = page.locator("#hmda-one-year-2019")
            expect(page.get_by_label("HMDA release or analysis")).to_have_value("one_year_2019")
            expect(panel).to_contain_text("One-Year 2019")
            expect(panel).to_contain_text("more than 12 months")
            expect(panel.locator("#hmda-one-year-2019-summary .metric-value").nth(0)).to_have_text("17,563,200")
            expect(panel.locator("#hmda-one-year-2019-summary .metric-value").nth(1)).to_have_text("5,565")
            expect(panel.locator("#hmda-one-year-2019-summary .metric-value").nth(2)).to_have_text("12,280,699")
            expect(panel.locator("#hmda-one-year-2019-summary .metric-value").nth(3)).to_have_text("20.6479%")
            expect(panel.locator("#hmda-one-year-2019-actions tbody tr")).to_have_count(8)
            expect(panel.locator("#hmda-one-year-2019-breakdown tbody tr")).to_have_count(len(state_report["breakdown"]))
            expect(panel).to_contain_text("not default PD")
            checks.append("2019 frozen One-Year source renders its verified row, reporter, action-denominator and descriptive denial-share totals with the publisher's extended-update caveat")

            panel.get_by_label("HMDA 2019 One-Year breakdown dimension").select_option("denial_reason_1")
            panel.get_by_role("button", name="Đọc breakdown 2019").click()
            expect(panel.locator("#hmda-one-year-2019-breakdown tbody tr")).to_have_count(len(reason_report["breakdown"]))
            expect(panel.locator("#hmda-one-year-2019-breakdown")).to_contain_text("Primary denial reason")
            with page.expect_download() as download_event:
                panel.get_by_role("button", name="Tải JSON").click()
            json_download = download_event.value
            json_path = output / json_download.suggested_filename
            json_download.save_as(json_path)
            downloaded_report = json.loads(json_path.read_text(encoding="utf-8"))
            assert downloaded_report == reason_report
            assert downloaded_report["visibility"] == "private" and downloaded_report["public_release_approved"] is False
            checks.append("Action-3-only denial-reason filter and downloaded JSON match the private server aggregate exactly")

            with page.expect_download() as download_event:
                panel.locator("#hmda-one-year-2019-scope a[href='/downloads/hmda-one-year-2019-audit.xlsx']").click()
            workbook_download = download_event.value
            assert workbook_download.suggested_filename == source_workbook.name
            workbook_path = output / workbook_download.suggested_filename
            workbook_download.save_as(workbook_path)
            assert sha256(workbook_path) == sha256(source_workbook)
            checks.append("KPI/codebook/source-audit workbook downloads byte-for-byte equal to the receipt-bound private workbook")

            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "390px mobile viewport has horizontal overflow"
            expect(page.get_by_label("HMDA release or analysis")).to_have_value("one_year_2019")
            page.screenshot(path=str(screenshot), full_page=True)
            checks.append("One-Year 2019 module selector and analysis fit the 390px viewport without horizontal overflow")
            browser.close()

        if errors:
            raise AssertionError("Browser errors: " + "; ".join(errors))
        view_receipt = root / "artifacts/private" / view_id / "view-complete.json"
        receipt = {
            "status": "PASS",
            "completed_at": timestamp(),
            "view_id": view_id,
            "source_id": snapshot["source_id"],
            "summary": snapshot["summary"],
            "denominator_contract": snapshot["denominator_contract"],
            "checks": checks,
            "browser_errors": errors,
            "view_receipt_sha256": sha256(view_receipt),
            "source_workbook_sha256": sha256(source_workbook),
            "app_js_sha256": sha256(ROOT / "apps/web/app.js"),
            "screenshot": screenshot.name,
            "visibility": "private",
            "public_release_approved": False,
        }
        write_new(output / "receipt.json", receipt)
        print(json.dumps({"status": "PASS", "receipt": str(output / "receipt.json"), "checks": checks,
            "browser_errors": errors}, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
