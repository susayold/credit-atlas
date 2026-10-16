"""Browser acceptance for the private HMDA national snapshot workbench."""
from __future__ import annotations

import json
import argparse
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import sha256, timestamp, write_new

expect.set_options(timeout=120000)

def run(root):
    output = root / "artifacts/private" / ("hmda-national-browser-qa-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    catalog = service.hmda_national_views.catalog()
    view_id = next(row["view_id"] for row in catalog["views"] if row["status"] == "verified")
    snapshot = service.hmda_national_views.view(view_id)
    one_year_catalog = service.hmda_one_year_views.catalog()
    one_year_id = next(row["view_id"] for row in one_year_catalog["views"] if row["status"] == "verified")
    one_year_snapshot = service.hmda_one_year_views.view(one_year_id)
    web_root = ROOT / "apps/web"
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service, web_root=web_root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks, errors, diagnostic_text = [], [], None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.set_default_timeout(120000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.goto(base + "/?view=hmda", wait_until="domcontentloaded")
            diagnostic_text = page.locator("body").inner_text()[:5000]
            expect(page.locator("#hmda-national-snapshot")).to_contain_text("Toàn quốc")
            expect(page.locator("#hmda-national-summary .metric-value").nth(0)).to_have_text("13,543,606")
            expect(page.locator("#hmda-national-summary .metric-value").nth(1)).to_have_text("4,782")
            expect(page.locator("#hmda-national-summary .metric-value").nth(2)).to_have_text("9,360,942")
            expect(page.locator("#hmda-national-summary .metric-value").nth(3)).to_have_text("22.5948%")
            expect(page.locator("#hmda-national-actions tbody tr")).to_have_count(8)
            checks.append("National source verified; 13,543,606 records, 4,782 LEIs, exact action denominator and descriptive denied share")

            expect(page.locator("#hmda-national-breakdown tbody tr")).to_have_count(55)
            page.get_by_label("HMDA national breakdown dimension").select_option("denial_reason_1")
            page.get_by_role("button", name="Đọc national breakdown").click()
            expect(page.locator("#hmda-national-breakdown tbody tr")).to_have_count(10)
            expect(page.locator("#hmda-national-breakdown")).to_contain_text("Primary denial reason code")
            checks.append("State and primary denial-reason breakdowns render; denial reasons are restricted to action 3")

            with page.expect_download() as info:
                page.get_by_role("button", name="Tải breakdown JSON").click()
            info.value.save_as(str(output / "hmda-national-denial-reasons.json"))
            exported = json.loads((output / "hmda-national-denial-reasons.json").read_text(encoding="utf-8"))
            expected = service.hmda_national_views.report(view_id, {"dimension": "denial_reason_1"})
            assert exported == expected
            assert exported["visibility"] == "private" and exported["public_release_approved"] is False
            checks.append("Downloaded JSON exactly matches private server aggregate and release flags")

            with page.expect_download() as info:
                page.get_by_role("link", name="Tải Excel · codebook + KPI + source audit").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-National-2025-Audit.xlsx"))
            assert sha256(output / "CreditAtlas-HMDA-National-2025-Audit.xlsx") == sha256(
                root / "data/private/hmda/hmda-national-snapshot-2025-9a5e89600e3c/CreditAtlas-HMDA-National-2025-Audit.xlsx")
            checks.append("Excel codebook/KPI/source-audit workbook downloads byte-identically")

            one_year_panel = page.locator("#hmda-one-year-2024")
            expect(one_year_panel).to_contain_text("One-Year 2024")
            expect(page.locator("#hmda-one-year-2024-summary .metric-value").nth(0)).to_have_text("12,259,199")
            expect(page.locator("#hmda-one-year-2024-summary .metric-value").nth(1)).to_have_text("4,926")
            expect(page.locator("#hmda-one-year-2024-summary .metric-value").nth(2)).to_have_text("8,661,779")
            expect(page.locator("#hmda-one-year-2024-summary .metric-value").nth(3)).to_have_text("24.2844%")
            expect(page.locator("#hmda-one-year-2024-actions tbody tr")).to_have_count(8)
            expect(page.locator("#hmda-one-year-2024-breakdown tbody tr")).to_have_count(55)
            checks.append("2024 One-Year national source renders its reconciled row count, LEIs, denominator, share, actions and state profile separately from 2025 Snapshot")

            one_year_panel.get_by_label("HMDA 2024 One-Year breakdown dimension").select_option("denial_reason_1")
            one_year_panel.get_by_role("button", name="Đọc breakdown 2024").click()
            expect(page.locator("#hmda-one-year-2024-breakdown tbody tr")).to_have_count(10)
            expect(page.locator("#hmda-one-year-2024-breakdown")).to_contain_text("denial_reason-1")
            with page.expect_download() as info:
                one_year_panel.locator("button", has_text="Tải JSON").click()
            info.value.save_as(str(output / "hmda-one-year-2024-denial-reasons.json"))
            exported = json.loads((output / "hmda-one-year-2024-denial-reasons.json").read_text(encoding="utf-8"))
            expected = service.hmda_one_year_views.report(one_year_id, {"dimension": "denial_reason_1"})
            assert exported == expected
            assert exported["visibility"] == "private" and exported["public_release_approved"] is False
            checks.append("2024 denial-reason JSON exactly matches the private aggregate and source-specific field mapping")

            with page.expect_download() as info:
                one_year_panel.locator("#hmda-one-year-2024-scope a[href='/downloads/hmda-one-year-2024-audit.xlsx']").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-One-Year-2024-Audit.xlsx"))
            assert sha256(output / "CreditAtlas-HMDA-One-Year-2024-Audit.xlsx") == sha256(
                root / "data/private/hmda/hmda-national-one-year-2024-002bab12cd71/CreditAtlas-HMDA-One-Year-2024-Audit.xlsx")
            checks.append("2024 Excel workbook download matches the private seven-sheet audit workbook byte-for-byte")

            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("#hmda-national-summary")).to_be_visible()
            expect(page.locator("#hmda-one-year-2024-summary")).to_be_visible()
            page.screenshot(path=str(output / "hmda-national-mobile.png"), full_page=True)
            checks.append("National summary remains visible at 390px mobile width")
            assert not errors, errors
            browser.close()
        view_receipt = json.loads((root / "artifacts/private" / view_id / "view-complete.json").read_text(encoding="utf-8"))
        write_new(output / "receipt.json", {
            "status": "PASS", "checks": checks, "browser_errors": errors,
            "view_id": view_id, "snapshot_summary": snapshot["summary"],
            "one_year_view_id": one_year_id, "one_year_summary": one_year_snapshot["summary"],
            "source_receipt_sha256": view_receipt["source_receipt_sha256"],
            "aggregate_sha256": view_receipt["aggregate_sha256"],
            "app_js_sha256": sha256(ROOT / "apps/web/app.js"),
            "completed_at": timestamp(), "visibility": "private", "public_release_approved": False,
        })
        return {"status": "PASS", "checks": len(checks), "directory": str(output)}
    except Exception as error:
        write_new(output / "failed.json", {"status": "FAIL", "exception_type": type(error).__name__,
            "checks_completed": checks, "browser_errors": errors,
            "page_url": page.url if "page" in locals() else None,
            "page_text": diagnostic_text})
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Private CreditAtlas data root on D:")
    args = parser.parse_args()
    if args.root.resolve().drive.upper() != "D:":
        parser.error("Private browser QA artifacts must remain on D:")
    print(json.dumps(run(args.root.resolve()), indent=2))
