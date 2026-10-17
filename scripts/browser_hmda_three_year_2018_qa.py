"""Targeted browser acceptance for the private HMDA 2018 Three-Year panel."""
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
        parser.error("Private HMDA evidence must remain on D:")
    output = root / "artifacts/private" / ("hmda-three-year-2018-browser-qa-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    catalog = service.hmda_three_year_2018_views.catalog()
    view_id = next(row["view_id"] for row in catalog["views"] if row["status"] == "verified")
    snapshot = service.hmda_three_year_2018_views.view(view_id)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service, web_root=ROOT / "apps/web"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks, errors = [], []
    screenshot = output / "hmda-2018-three-year.png"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.set_default_timeout(60_000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.goto(base + "/?view=hmda&hmda_panel=three_year_2018", wait_until="domcontentloaded", timeout=60_000)
            panel = page.locator("#hmda-three-year-2018")
            try:
                expect(panel).to_contain_text("Three-Year 2018")
            except Exception:
                page.screenshot(path=str(screenshot), full_page=False)
                (output / "browser-failure.json").write_text(json.dumps({
                    "url": page.url, "title": page.title(), "content": page.locator("#content").inner_text(),
                    "page_errors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
                raise
            expect(panel).to_contain_text("1.961 dòng action -1")
            expect(panel.locator("#hmda-three-year-2018-summary .metric-value").nth(0)).to_have_text("15,138,510")
            expect(panel.locator("#hmda-three-year-2018-summary .metric-value").nth(1)).to_have_text("1,961")
            expect(panel.locator("#hmda-three-year-2018-summary .metric-value").nth(2)).to_have_text("10,623,751")
            expect(panel.locator("#hmda-three-year-2018-actions tbody tr")).to_have_count(8)
            state_rows = panel.locator("#hmda-three-year-2018-breakdown tbody tr")
            expect(state_rows).to_have_count(57)
            checks.append("Verified source, exact totals, quarantine, eight actions, and 57 state categories")

            dimension = page.get_by_label("HMDA 2018 Three-Year breakdown dimension")
            dimension.select_option("ltv_band")
            page.get_by_role("button", name="Đọc breakdown 2018").click()
            expect(panel.locator("#hmda-three-year-2018-breakdown")).to_contain_text("LTV band")
            expect(panel.locator("#hmda-three-year-2018-breakdown tbody tr").first).to_be_visible()
            checks.append("LTV band filter updates the source-bound breakdown")

            with page.expect_download() as download_event:
                panel.get_by_role("link", name="Tải Excel").click()
            xlsx = download_event.value
            assert xlsx.suggested_filename == "CreditAtlas-HMDA-2018-Three-Year-Analysis.xlsx"
            download_path = output / xlsx.suggested_filename
            xlsx.save_as(download_path)
            assert download_path.stat().st_size > 100_000
            checks.append("Private Excel workbook downloads with the expected filename")

            page.set_viewport_size({"width": 390, "height": 844})
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            assert overflow is False, "Mobile viewport has horizontal overflow"
            checks.append("390px mobile viewport has no horizontal overflow")
            page.screenshot(path=str(screenshot), full_page=False)
            browser.close()
        if errors:
            raise AssertionError("Browser errors: " + "; ".join(errors))
        receipt = {"status": "PASS", "completed_at": timestamp(), "view_id": view_id,
            "source_id": snapshot["source_id"], "checks": checks, "browser_errors": errors,
            "app_js_sha256": sha256(ROOT / "apps/web/app.js"),
            "style_css_sha256": sha256(ROOT / "apps/web/style.css"),
            "qa_script_sha256": sha256(Path(__file__)),
            "screenshot": screenshot.name, "visibility": "private", "public_release_approved": False}
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
