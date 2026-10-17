"""Private browser acceptance for the direct Treasury P5 source path."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import uuid
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.server import handler_for  # noqa: E402
from credit_atlas.service import ResearchService  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(workspace: Path) -> dict:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise ValueError("Private market data and browser receipts must remain on D:")
    output = workspace / "artifacts/private" / ("treasury-browser-qa-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(workspace, review_path=output / "qa-reviews.sqlite3")
    catalog = service.market_views.catalog()
    views = [row for row in catalog["views"] if row["status"] == "verified"]
    target = None
    snapshot = None
    for row in views:
        candidate = service.market_views.view(row["view_id"])
        has_direct_treasury = any(
            leg["source_id"] == "treasury-daily-par-yield"
            for profile in candidate["profiles"]
            for leg in profile.get("source_legs", [])
        )
        if has_direct_treasury:
            target, snapshot = row, candidate
            break
    if target is None or snapshot is None:
        raise ValueError("Receipt-verified direct Treasury P5 view is not available")

    identifier = target["view_id"]
    profile = next(row for row in snapshot["profiles"] if row["series"] == "DGS10")
    direct_leg = next((leg for leg in profile.get("source_legs", [])
                       if leg["source_id"] == "treasury-daily-par-yield"), None)
    if not direct_leg or direct_leg["role"] != "direct_publisher_from_1990-01-02":
        raise AssertionError("DGS10 is not bound to the direct Treasury source leg")

    query = {"view_id": identifier, "series": "DGS10", "from": "2026-10-14", "to": "2026-10-16"}
    expected = service.market_views.report(identifier, query)
    if not expected["rows"] or any(
        row["source_id"] != "treasury-daily-par-yield"
        or not row["source_sha256"]
        for row in expected["rows"]
    ):
        raise AssertionError("Selected direct-source report rows lack Treasury provenance")

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), handler_for(service, web_root=ROOT / "apps" / "web")
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    errors: list[str] = []
    checks: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text)
                    if message.type == "error" else None)
            page.goto(
                f"http://127.0.0.1:{server.server_port}/?view=market&market_view_id={identifier}",
                wait_until="networkidle",
            )
            expect(page.locator("#active-module")).to_have_text("P5")
            expect(page.locator("#context-note")).to_contain_text("45,517 native observations")
            expect(page.locator("#content")).to_contain_text("2026-10-16")
            expect(page.locator("#content")).to_contain_text("treasury-daily-par-yield")
            expect(page.locator("#content")).to_contain_text("direct publisher from 1990-01-02")
            checks.append("P5 renders the receipt-bound Treasury direct-source role and latest observation")

            page.get_by_label("Market series", exact=True).select_option("DGS10")
            page.get_by_label("Market from date", exact=True).fill(query["from"])
            page.get_by_label("Market to date", exact=True).fill(query["to"])
            page.get_by_role("button", name="Đọc market observations", exact=True).click()
            expect(page.locator("#content")).to_contain_text("selected native rows")
            expect(page.locator("#content")).to_contain_text("treasury-daily-par-yield")
            checks.append("date-filtered series explorer labels the direct Treasury source leg")

            with page.expect_download() as download_info:
                page.locator("#export-report").click()
            download = download_info.value
            export_path = output / download.suggested_filename
            download.save_as(str(export_path))
            actual = json.loads(export_path.read_text(encoding="utf-8"))
            if actual != expected:
                raise AssertionError("Downloaded report differs from the verified API payload")
            if actual["public_release_approved"] is not False or any(
                row["source_id"] != "treasury-daily-par-yield" or not row["source_sha256"]
                for row in actual["rows"]
            ):
                raise AssertionError("Export lost private-release boundary or row-level source lineage")
            checks.append("downloaded JSON equals API report and retains per-row source/hash and private flag")

            page.set_viewport_size({"width": 390, "height": 844})
            if page.evaluate("document.documentElement.scrollWidth <= innerWidth") is not True:
                raise AssertionError("P5 page overflows at a 390px viewport")
            page.screenshot(path=str(output / "treasury-mobile.png"), full_page=True)
            checks.append("P5 market page has no horizontal overflow at 390px")
            if errors:
                raise AssertionError(f"Browser errors: {errors}")
            checks.append("no browser JavaScript/page errors")
            browser.close()
    except Exception as error:
        receipt = {
            "status": "FAIL",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "view_id": identifier,
            "case_id": snapshot["case_id"],
            "checks": checks,
            "browser_errors": errors,
            "exception_type": type(error).__name__,
            "visibility": "private",
            "public_release_approved": False,
        }
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        raise
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

    receipt = {
        "status": "PASS",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "view_id": identifier,
        "case_id": snapshot["case_id"],
        "source_id": direct_leg["source_id"],
        "source_sha256_prefix": direct_leg["sha256"][:12],
        "checks": checks,
        "browser_errors": errors,
        "export_sha256": sha256(export_path),
        "visibility": "private",
        "public_release_approved": False,
    }
    receipt_path = output / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {"status": "PASS", "checks": len(checks), "receipt": str(receipt_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True,
                        help="Private CreditAtlas D: workspace holding market source data")
    args = parser.parse_args()
    print(json.dumps(run(args.workspace), indent=2))
