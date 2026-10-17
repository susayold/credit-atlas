"""Focused browser smoke test for the 2025 HMDA state × loan-type intersection."""
from __future__ import annotations

import argparse
import json
import sys
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from openpyxl import load_workbook
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.server import handler_for  # noqa: E402
from credit_atlas.service import ResearchService  # noqa: E402
from credit_atlas.workspace import read_json, sha256, timestamp, write_new  # noqa: E402

expect.set_options(timeout=90000)


def run(root: Path, release: str) -> dict:
    output = root / "artifacts/private" / ("hmda-intersection-browser-smoke-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / "smoke-reviews.sqlite3")
    source_prefix = f"hmda-national-{release}-2025-"
    candidates = []
    for receipt_path in sorted((root / "artifacts/private").glob("hmda-national-view-*/view-complete.json")):
        try:
            candidate = read_json(receipt_path)
            if (str(candidate.get("source_id", "")).startswith(source_prefix)
                    and candidate.get("status") == "VERIFIED_HMDA_NATIONAL_AGGREGATE_VIEW"
                    and candidate.get("methods") == service.hmda_national_views._methods):
                candidates.append((candidate.get("completed_at", ""), receipt_path.parent.name,
                                   candidate.get("source_id")))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if not candidates:
        raise ValueError(f"No current receipt-bound 2025 {release} aggregate view was found")
    _, current_view, source_id = max(candidates)
    view_id = current_view
    # Verify only the selected release's receipt. This focused test omits the
    # unrelated release catalog and older annual-panel checks.
    service.hmda_national_views._view(view_id)
    selected_view = service.hmda_national_views.view(view_id)
    service.hmda_national_views.catalog = lambda: {"views": [{
        "view_id": view_id,
        "source_id": selected_view["source_id"],
        "status": "verified",
        "records": selected_view["summary"]["records"],
        "snapshot_date": selected_view["snapshot_date"],
        "release_type": selected_view["release_type"],
    }]}
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service, web_root=ROOT / "apps/web"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors: list[str] = []
    checks: list[str] = []
    excel_responses: list[dict] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.set_default_timeout(90000)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("response", lambda response: excel_responses.append({
                "status": response.status, "url_path": urlsplit(response.url).path,
            }) if urlsplit(response.url).path == "/api/hmda-national-excel" else None)
            page.goto(f"http://127.0.0.1:{server.server_port}/?view=hmda&hmda_national_view_id={view_id}",
                      wait_until="domcontentloaded")
            expected = service.hmda_national_views.report(view_id, {
                "dimension": "state_code", "filter_state_code": "CA", "filter_loan_type": "1"})
            summary = expected["filtered_summary"]
            expect(page.locator("#hmda-national-summary .metric-value").nth(0)).to_have_text(
                f"{selected_view['summary']['records']:,}")
            page.get_by_label("HMDA national state filter").select_option("CA")
            page.get_by_label("HMDA national loan type filter").select_option("1")
            page.get_by_role("button", name="Áp dụng giao cắt").click()
            expect(page.locator("#hmda-national-intersection-summary .metric-value").nth(0)).to_have_text(
                f"{summary['records']:,}")
            expect(page.locator("#hmda-national-intersection-summary .metric-value").nth(1)).to_have_text(
                f"{summary['decision_denominator']:,}")
            expect(page.locator("#hmda-national-intersection-summary .metric-value").nth(2)).to_have_text(
                f"{summary['denied_numerator']:,}")
            expect(page.locator("#hmda-national-intersection-summary .metric-value").nth(3)).to_have_text(
                f"{float(summary['descriptive_denial_rate']) * 100:.4f}%")
            checks.append("Selected-release UI shows receipt-verified California × conventional summary with scoped denominator")
            assert "hmda_national_filter_state=CA" in page.url and "hmda_national_filter_loan_type=1" in page.url
            checks.append("Applied filters persist in the page URL")

            with page.expect_download() as info:
                page.get_by_role("button", name="Tải JSON giao cắt").click()
            download_path = output / f"hmda-national-{source_id}-california-conventional.json"
            info.value.save_as(str(download_path))
            exported = json.loads(download_path.read_text(encoding="utf-8"))
            assert exported == expected
            checks.append("Filtered JSON download exactly matches the receipt-verified selected-release API result")

            with page.expect_download() as info:
                page.get_by_role("button", name="Tải Excel giao cắt").click()
            workbook_path = output / "CreditAtlas-HMDA-2025-Filtered.xlsx"
            info.value.save_as(str(workbook_path))
            workbook = load_workbook(workbook_path, data_only=False, read_only=False)
            assert workbook.sheetnames == ["Summary", "Actions", "Method & sources"]
            assert workbook["Summary"]["B6"].value == "CA"
            assert workbook["Summary"]["B7"].value == "Conventional · 1"
            assert workbook["Summary"]["B12"].value == summary["records"]
            assert workbook["Summary"]["B13"].value == summary["decision_denominator"]
            assert workbook["Summary"]["B14"].value == summary["denied_numerator"]
            assert abs(workbook["Summary"]["B15"].value
                       - float(summary["descriptive_denial_rate"])) < 1e-15
            assert [workbook["Actions"].cell(row, 3).value for row in range(2, 10)] == [
                row["records"] for row in summary["actions"]]
            formula_count = sum(1 for sheet in workbook.worksheets for cells in sheet.iter_rows()
                                for cell in cells if isinstance(cell.value, str) and cell.value.startswith("="))
            assert formula_count == 12
            assert not workbook._external_links
            workbook.close()
            checks.append("Filtered Excel download contains the selected filters, five KPIs and all eight action counts")
            checks.append("Excel workbook read-back finds 12 reconciliation/share formulas and no external links")
            assert not errors, errors
            browser.close()

        receipt_path = root / "artifacts/private" / view_id / "view-complete.json"
        receipt = read_json(receipt_path)
        write_new(output / "receipt.json", {
            "status": "PASS",
            "checks": checks,
            "browser_errors": errors,
            "view_id": view_id,
            "source_id": selected_view["source_id"],
            "source_receipt_sha256": receipt["source_receipt_sha256"],
            "aggregate_sha256": receipt["aggregate_sha256"],
            "filtered_summary": exported["filtered_summary"],
            "filtered_excel_sha256": sha256(workbook_path),
            "filtered_excel_formula_count": formula_count,
            "app_js_sha256": sha256(ROOT / "apps/web/app.js"),
            "completed_at": timestamp(),
            "visibility": "private",
            "public_release_approved": False,
            "scope_note": f"Focused {selected_view['release_type']} intersection smoke only; other releases and older annual panels were not part of this run.",
        })
        return {"status": "PASS", "checks": len(checks), "directory": str(output)}
    except Exception as error:
        write_new(output / "failed.json", {
            "status": "FAIL", "exception_type": type(error).__name__,
            "checks_completed": checks, "browser_errors": errors,
            "excel_responses": excel_responses,
            "page_url": page.url if "page" in locals() else None,
            "page_text": _page_text(page) if "page" in locals() else None,
        })
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _page_text(page):
    try:
        return page.locator("body").inner_text(timeout=5000)[:5000]
    except Exception:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Private CreditAtlas data root on D:")
    parser.add_argument("--release", choices=("snapshot", "dynamic"), default="snapshot",
                        help="Receipt-bound 2025 HMDA release to exercise.")
    args = parser.parse_args()
    if args.root.resolve().drive.upper() != "D:":
        parser.error("HMDA private browser evidence must remain on D:")
    print(json.dumps(run(args.root.resolve(), args.release), indent=2))
