"""Real-source suite/retail browser acceptance with aggregate export checks."""
import json
import threading
import uuid
from http.server import ThreadingHTTPServer

from playwright.sync_api import sync_playwright, expect
from browser_navigation import navigate_workspace, select_task

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new

expect.set_options(timeout=60000)


def run(root):
    output = root / "artifacts/private" / ("suite-browser-qa-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    catalog = service.suite_views.catalog()
    verified = [v for v in catalog["views"] if v["status"] == "verified"]
    if not verified:
        raise ValueError("Real verified suite view required")
    identifier = verified[0]["view_id"]
    expected = service.suite_views.view(identifier)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    errors, checks = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.goto(base + "/?view=suite&view_id=" + identifier, wait_until="networkidle")
            page.locator('.atlas-evidence-details summary').click()
            expect(page.locator("#content")).to_contain_text("Catalog nguồn thật")
            assert page.locator("#content tbody tr").count() == 25  # five modules plus twenty source files
            checks.append("real five-workspace/source catalog: 5 modules, 20 files")
            page.get_by_label("Lọc source theo workspace").select_option("P3")
            assert page.locator("#content tbody tr").count() == 14  # nine P3 files plus five module rows
            checks.append("P3 source filter retains nine source/reference files")
            page.screenshot(path=str(output / "suite-desktop.png"), full_page=True)
            navigate_workspace(page, 'retail')
            expect(page.locator('#retail-model-summary')).to_contain_text('3,001')
            expect(page.locator("#content")).to_contain_text("3,001")
            expect(page.locator("#content")).to_contain_text("0.7779")
            expect(page.locator("#content")).to_contain_text("0.136377")
            select_task(page, 'Validation')
            expect(page.locator("#content")).to_contain_text("Holdout reliability")
            checks.append("real frozen boosting/raw holdout counts and metrics")
            assert page.locator("#run-select").is_disabled() and page.locator("#segment-select").is_disabled()
            assert page.locator("#basis-select").is_disabled()
            checks.append("mortgage filters disabled in retail")
            assert not page.locator("#content").get_by_text("Lưu finding từ view này").count()
            checks.append("retail does not save findings under a mortgage case")
            with page.expect_download() as download_info:
                page.locator("#export-report").click()
            download = download_info.value
            download.save_as(str(output / "aggregate-export.json"))
            exported = json.loads((output / "aggregate-export.json").read_text(encoding="utf-8"))
            assert exported == expected
            encoded = json.dumps(exported)
            for forbidden in ("source_client_id", "raw_probability", "calibrated_probability", "inputs_sha256", "coefficients", "trees"):
                assert forbidden not in encoded, forbidden
            assert exported["public_release_approved"] is False
            checks.append("private export matches verified aggregate snapshot; no individual IDs/scores/model parameters")
            page.screenshot(path=str(output / "retail-desktop.png"), full_page=True)
            page.reload(wait_until="networkidle")
            expect(page.get_by_role('tab',name='Validation',exact=True)).to_have_attribute('aria-selected','true')
            checks.append("retail URL/snapshot survives reload")
            navigate_workspace(page, 'business')
            expect(page.locator('#business-summary')).to_contain_text('2,190,504')
            expect(page.locator("#content")).to_contain_text("2,190,504")
            expect(page.locator("#active-module")).to_have_text("P3")
            checks.append("real SBA business case and source-record grain")
            select_task(page, 'Cohorts & outcomes')
            page.get_by_label("SBA program", exact=True).select_option("504")
            expect(page.locator("#content")).to_contain_text("229,049 selected source records")
            page.get_by_label("SBA dimension", exact=True).select_option("approval_fiscal_year")
            page.get_by_label("SBA bucket", exact=True).select_option("2020")
            selected = [r for r in expected["business"]["aggregates"]["dimensions"]["approval_fiscal_year"] if r["program"] == "504" and r["bucket"] == "2020"]
            selected_count = sum(r["records"] for r in selected)
            expect(page.locator("#content")).to_contain_text(f"{selected_count:,} selected source records")
            select_task(page, 'Chất lượng')
            expect(page.locator("#content")).to_contain_text("Quality findings · toàn nguồn")
            checks.append("504/FY2020 filter uses actual aggregate support; quality retains whole-source scope")
            with page.expect_download() as info:
                page.locator("#export-report").click()
            info.value.save_as(str(output / "business-export.json"))
            report = json.loads((output / "business-export.json").read_text(encoding="utf-8"))
            assert report["rows"] == selected and report["selected_record_count"] == selected_count
            assert report["filters"] == {"program": "504", "dimension": "approval_fiscal_year", "bucket": "2020"}
            assert report["quality"] == expected["business"]["quality"]
            assert report["quality_scope"].startswith("whole_source")
            assert report["fixed_horizon_default_target_qualified"] is False
            assert '"source_record_key":' not in json.dumps(report) and '"BorrName":' not in json.dumps(report)
            checks.append("scoped business export retains decimal strings, source quality, no borrower/record identifiers")
            page.screenshot(path=str(output / "business-desktop.png"), full_page=True)
            select_task(page, 'Cohorts & outcomes')
            page.reload(wait_until="networkidle")
            expect(page.get_by_label("SBA program", exact=True)).to_have_value("504")
            expect(page.get_by_label("SBA bucket", exact=True)).to_have_value("2020")
            checks.append("business URL/reload restores program, dimension and bucket")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "business-mobile.png"), full_page=True)
            checks.append("390px business mobile without page horizontal overflow")
            page.set_viewport_size({"width": 1440, "height": 1000})
            navigate_workspace(page, 'overview')
            expect(page.locator(".metric-value").first).to_have_text("50,000")
            assert not page.locator("#segment-select").is_disabled()
            checks.append("navigation back to actual mortgage loads correct independent case")
            page.set_viewport_size({"width": 390, "height": 844})
            navigate_workspace(page, 'retail')
            select_task(page, 'Tổng quan')
            expect(page.locator('#retail-model-summary')).to_contain_text('3,001')
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "retail-mobile.png"), full_page=True)
            checks.append("390px mobile retail without page horizontal overflow")
            # Retail is usable even when no mortgage run is available.
            page.route("**/api/runs", lambda route: route.fulfill(json={"runs": []}))
            page.reload(wait_until="networkidle")
            expect(page.locator('#retail-model-summary')).to_contain_text('3,001')
            checks.append("retail available without mortgage runs")
            assert not errors, errors
            checks.append("no JavaScript/console errors")
            browser.close()
        write_new(output / "receipt.json", {"status": "PASS", "completed_at": timestamp(), "view_id": identifier,
                  "checks": checks, "browser_errors": errors, "visibility": "private", "public_release_approved": False})
        return {"status": "PASS", "checks": len(checks), "directory": str(output)}
    except Exception as error:
        write_new(output / "failed.json", {"status": "FAIL", "exception_type": type(error).__name__,
                  "checks_completed": checks, "browser_errors": errors})
        raise
    finally:
        server.shutdown(); server.server_close(); worker.join(timeout=5)


if __name__ == "__main__":
    print(json.dumps(run(app_root()), indent=2))
