"""Real-data browser acceptance, using a separate private QA review database."""
from __future__ import annotations

import json
import threading
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

from browser_navigation import navigate_workspace, select_task
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new

expect.set_options(timeout=60000)


def run(root: Path):
    output = root / "artifacts/private" / ("browser-qa-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    runs = service.runs()["runs"]
    actual = [r for r in runs if r["descriptive_status"] == "verified_rebuild"]
    if not actual:
        raise ValueError("Real verified case required for browser acceptance")
    case_id = actual[0]["case_id"]
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    errors, checks, mobile_results = [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("response", lambda response: errors.append(
                "HTTP " + str(response.status) + " " + response.url.split("?", 1)[0])
                if response.status >= 400 else None)
            page.goto(base + "/?view=overview", wait_until="networkidle")
            expect(page.locator("#page-title")).to_have_text("Mortgage Lifecycle & Loss Lab")
            expect(page.locator(".metric-value").first).to_have_text("50,000")
            page.screenshot(path=str(output / "overview-desktop.png"), full_page=True)
            checks.append("real overview source counts")
            for view in ["sources", "portfolio", "vintage", "transitions", "models", "loss", "evidence"]:
                navigate_workspace(page, view)
                page.wait_for_timeout(180)
                expect(page.locator("#content")).not_to_contain_text("Invalid request")
                expect(page.locator("#content")).not_to_contain_text("Research evidence unavailable")
                if view == "sources":
                    expect(page.locator("#content")).to_contain_text("Quality monitoring & investigation", timeout=15000)
                    checks.append("source monitoring and investigation view")
                if view == "transitions":
                    expect(page.locator("#content")).to_contain_text("Episode follow-up support", timeout=15000)
                    checks.append("real episode follow-up support view")
                if view == "portfolio":
                    count_chart = page.locator('svg[aria-label="Observed active monthly stock"]')
                    share_chart = page.locator('svg[aria-label="Observed D3 share"]')
                    expect(count_chart).to_be_visible()
                    expect(share_chart).to_be_visible()
                    assert count_chart.locator("path").get_attribute("d").count("M") >= 1
                    assert share_chart.locator("path").get_attribute("d").count("M") >= 1
                    expect(page.locator("#content")).to_contain_text("State usable")
                    checks.append("monthly portfolio charts render observed series with denominator notes")
                if view == "vintage":
                    chart = page.locator('svg[aria-label="Competing incidence at 6, 12 and 24 months"]')
                    expect(chart).to_be_visible()
                    assert chart.locator("path").count() == 3
                    expect(page.locator("#content")).to_contain_text("Eligible loans")
                    expect(page.locator("#content")).to_contain_text("At risk cuối horizon")
                    checks.append("competing-incidence chart renders three series with risk-set support")
                if view == "loss":
                    chart = page.locator('svg[aria-label="Signed observed loss component bridge in USD"]')
                    expect(chart).to_be_visible()
                    assert chart.locator("rect").count() >= 5
                    expect(page.locator("#content")).to_contain_text("Unresolved terminal loans")
                    checks.append("signed loss chart renders components beside unresolved support")
                if view == "models":
                    expect(page.locator("#content")).to_contain_text("Prepared studies & feature audit", timeout=15000)
                    expect(page.locator("#content")).to_contain_text("BLOCKED_BEFORE_FIT")
                    expect(page.locator("#content")).to_contain_text("Chưa đạt gate huấn luyện")
                    checks.append("actual assessment blocked-before-fit state and reasons")
                    expect(page.locator("#content")).to_contain_text("FEATURE_AUDIT_NOT_MODEL_READY")
                    expect(page.locator("#content")).to_contain_text("43,327 loans")
                    checks.append("actual train-only feature audit and unqualified model study view")
                page.screenshot(path=str(output / (view + "-desktop.png")), full_page=True)
                checks.append("view " + view)
            navigate_workspace(page, 'vintage')
            page.locator("#segment-select").select_option("relief")
            expect(page.locator(".metric-value").nth(1)).to_have_text("89")
            page.locator("#segment-select").select_option("non_relief")
            expect(page.locator(".metric-value").nth(1)).to_have_text("13")
            page.get_by_role("button", name="24 tháng", exact=True).click()
            expect(page.locator("#content")).to_contain_text("24m")
            checks.append("vintage segment and horizon filters")
            navigate_workspace(page, 'transitions')
            page.locator("#segment-select").select_option("all")
            episode_card = page.locator("#content .card").filter(has_text="Forward-only episode events")
            first_d3 = episode_card.locator("tbody tr").filter(has_text="First observed D3")
            expect(first_d3.locator("td").nth(1)).to_have_text("1,713")
            expect(first_d3.locator("td").nth(2)).to_have_text("1,713")
            expect(episode_card).to_contain_text("Event rows đếm occurrences")
            followup_card = page.locator("#content .card").filter(has_text="Episode follow-up support")
            expect(followup_card).to_contain_text("follow-up status chia toàn bộ event rows")
            page.locator("#segment-select").select_option("relief")
            expect(page.locator("#content .card").filter(has_text="Forward-only episode events").locator("tbody tr").filter(has_text="First observed D3")).to_contain_text("1,094")
            page.locator("#segment-select").select_option("non_relief")
            expect(page.locator("#content .card").filter(has_text="Forward-only episode events").locator("tbody tr").filter(has_text="First observed D3")).to_contain_text("619")
            page.locator("#segment-select").select_option("all")
            checks.append("episode event and unique-loan denominators reconcile overall and by mutually exclusive segment")
            page.locator("#basis-select").select_option("balance")
            page.locator(".matrix-cell button").first.click()
            expect(page.locator(".matrix-detail")).to_contain_text("Distinct loans")
            expect(page.locator(".matrix-detail")).to_contain_text("Origin denominator")
            checks.append("transition basis and cell support")
            page.locator('.matrix-cell button[title="CURRENT → CREDIT_TERMINATION"]').click()
            expect(page.locator(".matrix-detail")).to_contain_text("Sparse: <30 distinct loans")
            checks.append("sparse transition cell exposes distinct-loan support warning")
            page.goto(base + "/?run=" + case_id + "&view=transitions&segment=non_relief&transition_year=2011", wait_until="networkidle")
            expect(page.locator("#transition-year")).to_have_value("2011")
            expect(page.locator("#content")).to_contain_text("Không có adjacent pairs")
            expect(page.locator("#content")).to_contain_text("Episode follow-up support")
            page.locator("#basis-select").select_option("balance")
            checks.append("unavailable year stays empty while lifetime episodes remain visible")
            page.locator("#transition-year").select_option("2020")
            expect(page.locator("#content")).to_contain_text("reporting 2020")
            expect(page.locator("#content")).to_contain_text("Episode follow-up support")
            page.reload(wait_until="networkidle")
            expect(page.locator("#transition-year")).to_have_value("2020")
            expect(page.locator("#content")).to_contain_text("reporting 2020")
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(output / "transitions-2020-mobile.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.screenshot(path=str(output / "transitions-2020-desktop.png"), full_page=True)
            checks.append("reporting-year matrix filter, URL reload and mobile layout")
            navigate_workspace(page, 'lifecycle')
            expect(page.locator(".loan-row").first).to_be_visible(timeout=15000)
            expect(page.locator("#content")).to_contain_text("Confirmed episode events", timeout=15000)
            expect(page.locator("#content")).not_to_contain_text("loan_id")
            page.screenshot(path=str(output / "lifecycle-desktop.png"), full_page=True)
            checks.append("private loan list and real timeline")
            page.goto(base + "/?run=" + case_id + "&view=portfolio&segment=non_relief&transition_year=2020", wait_until="networkidle")
            page.locator("#month-from").wait_for(state="visible", timeout=15000)
            page.locator("#month-from").fill("2020-01")
            page.locator("#month-from").dispatch_event("change")
            page.locator("#month-to").fill("2020-12")
            page.locator("#month-to").dispatch_event("change")
            expect(page.locator(".metric-label").first).to_contain_text("2020-12")
            page.reload(wait_until="networkidle")
            expect(page.locator("#month-from")).to_have_value("2020-01")
            expect(page.locator("#month-to")).to_have_value("2020-12")
            checks.append("monthly filters and URL reload persistence")
            with page.expect_download() as captured:
                page.locator("#export-report").click()
            download = captured.value
            download.save_as(str(output / "private-filtered-report.json"))
            report = json.loads((output / "private-filtered-report.json").read_text(encoding="utf-8"))
            assert report["case_id"] == case_id and report["public_release_approved"] is False
            assert report["filter_context"]["segment"] == "non_relief"
            monthly = next(t for t in report["report"]["tables"] if t["table_id"] == "portfolio_monthly")
            assert len(monthly["rows"]) == 12
            assert all("2020-01" <= r["period"][:7] <= "2020-12" for r in monthly["rows"])
            assert report["schema_version"] == 2
            supplement = report["supplemental_evidence"]
            assert supplement["quality_monitoring"]["filters_applied"] == []
            followup = supplement["episode_followup"]
            assert all(r["segment"] == "non_relief" for r in followup["rows"])
            assert {r["horizon_months"] for r in followup["rows"]} == {6, 12}
            periods = supplement["period_transitions"]
            assert report["filter_context"]["transition_year"] == "2020"
            assert periods["rows"] and periods["lifetime_rows"]
            assert all(r["reporting_year"] == 2020 and r["segment"] == "non_relief"
                       for r in periods["rows"])
            assert all(r["reporting_year"] is None and r["segment"] == "non_relief"
                       for r in periods["lifetime_rows"])
            assert set(periods["reconciliation"].values()) == {"PASS"}
            checks.append("year-filtered export retains reconciled lifetime comparator")
            assert "not" in report["scope_notes"]["transitions"].lower()
            checks.append("private export includes lineage-bound quality and episode support")
            checks.append("private export matches selected run and monthly/segment filters")
            page.get_by_role("button", name="+ Lưu finding từ view này", exact=True).click()
            page.locator("#finding-title").fill("QA ONLY — synthetic review text")
            page.locator("#finding-body").fill("Browser acceptance record; not a research conclusion. Tests save/reopen/revision history.")
            page.locator("#save-finding").click()
            expect(page.locator("#finding-dialog")).not_to_be_visible()
            navigate_workspace(page, 'evidence')
            expect(page.locator(".finding-card")).to_contain_text("QA ONLY")
            page.get_by_role("button", name="Sửa / review", exact=True).click()
            page.locator("#finding-status").select_option("reviewed")
            page.locator("#save-finding").click()
            expect(page.locator(".finding-card")).to_contain_text("revision 2")
            page.get_by_role("button", name="Xem history", exact=True).click()
            expect(page.locator(".history-block")).to_contain_text("r2")
            page.reload(wait_until="networkidle")
            expect(page.locator(".finding-card")).to_contain_text("revision 2")
            checks.append("isolated QA finding save/reopen/review/history persistence")
            page.set_viewport_size({"width": 390, "height": 844})
            navigate_workspace(page, 'overview')
            page.screenshot(path=str(output / "overview-mobile.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            checks.append("390px mobile layout without horizontal page overflow")
            for view in ["portfolio", "vintage", "transitions", "loss", "models"]:
                navigate_workspace(page, view)
                ready = {"portfolio": 'svg[aria-label="Observed active monthly stock"]',
                         "vintage": 'svg[aria-label="Competing incidence at 6, 12 and 24 months"]',
                         "transitions": ".matrix-cell button", "loss": 'svg[aria-label="Signed observed loss component bridge in USD"]',
                         "models": ".gate-card"}[view]
                page.locator(ready).first.wait_for(state="visible", timeout=15000)
                dimensions = page.evaluate("""() => ({viewport: innerWidth, document: document.documentElement.scrollWidth,
                    body: document.body.scrollWidth, offending: [...document.querySelectorAll('body *')]
                    .filter(e => e.getBoundingClientRect().right > innerWidth + 1)
                    .slice(0, 8).map(e => ({tag:e.tagName, id:e.id, className:typeof e.className==='string'?e.className:'',
                        right:Math.round(e.getBoundingClientRect().right), width:Math.round(e.getBoundingClientRect().width)}))})""")
                mobile_results.append({"view": view, **dimensions})
                page.screenshot(path=str(output / (view + "-mobile.png")), full_page=True)
                assert dimensions["document"] <= dimensions["viewport"], json.dumps(dimensions)
                checks.append("390px mobile layout without page overflow: " + view)
            error_page = context.new_page()
            error_page.set_viewport_size({"width": 1280, "height": 900})
            error_page.route("**/api/snapshot*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Frozen evidence or serving code changed; verify artifacts and restart with reviewed code"})))
            error_page.goto(base + "/?run=" + case_id + "&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Evidence chưa khả dụng")
            expect(error_page.locator(".error-panel")).to_contain_text("Frozen evidence or serving code changed")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("stale-evidence 503 fails closed without displaying prior metrics")
            error_page.unroute("**/api/snapshot*")
            missing_catalog = service.runs()
            missing_entry = dict(next(row for row in missing_catalog["runs"] if row["case_id"] == case_id))
            missing_entry["case_id"] = "d01-000000000000"
            missing_catalog["runs"].append(missing_entry)
            error_page.route("**/api/runs*", lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps(missing_catalog)))
            error_page.goto(base + "/?run=d01-000000000000&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Case or research record not found")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("missing-run 404 fails closed without replacing missing values with zero")
            error_page.unroute("**/api/runs*")
            error_page.goto(base + "/?run=unlisted-run&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Requested frozen run is not present")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("unknown URL run remains selected as unavailable instead of silently switching runs")
            error_page.route("**/api/snapshot*", lambda route: route.abort("failed"))
            error_page.goto(base + "/?run=" + case_id + "&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Evidence chưa khả dụng")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("snapshot connection failure fails closed without displaying metrics")
            error_page.unroute("**/api/snapshot*")
            error_page.route("**/api/snapshot*", lambda route: route.fulfill(
                status=200, content_type="application/json", body="not-json"))
            error_page.goto(base + "/?run=" + case_id + "&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Evidence chưa khả dụng")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("malformed snapshot response fails closed without displaying metrics")
            error_page.unroute("**/api/snapshot*")
            error_page.route("**/api/snapshot*", lambda route: route.fulfill(
                status=500, content_type="application/json",
                body=json.dumps({"error": "Synthetic internal server failure"})))
            error_page.goto(base + "/?run=" + case_id + "&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Synthetic internal server failure")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("HTTP 500 JSON error fails closed without displaying prior metrics")
            error_page.unroute("**/api/snapshot*")
            error_page.route("**/api/snapshot*", lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html><body>upstream unavailable</body></html>"))
            error_page.goto(base + "/?run=" + case_id + "&view=overview", wait_until="networkidle")
            expect(error_page.locator(".error-panel")).to_contain_text("Evidence chưa khả dụng")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("HTTP 502 non-JSON error fails closed without displaying prior metrics")
            error_page.unroute("**/api/snapshot*")
            error_page.route("**/api/runs*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic run-catalog outage"})))
            error_page.goto(base + "/?view=overview", wait_until="networkidle")
            expect(error_page.locator("#notice.error")).to_contain_text("Không đọc được private research API")
            assert error_page.locator(".metric-value").count() == 0
            checks.append("HTTP 503 run-catalog failure shows unavailable notice without metrics")
            error_page.close()
            assert not errors, errors
            checks.append("no browser JavaScript or console errors")
            context.close()
            browser.close()
        result = {"status": "PASS", "completed_at": timestamp(), "case_id": case_id,
                  "checks": checks, "browser_errors": errors, "review_database": "isolated_QA_only",
                  "source_kind": "actual_authorized_annual_sample", "screenshots_visibility": "private"}
        write_new(output / "receipt.json", result)
        return {"status": "PASS", "checks": len(checks), "output": str(output)}
    except Exception as error:
        write_new(output / "failed.json", {"status": "FAIL", "exception_type": type(error).__name__,
                  "checks_completed": checks, "browser_errors": errors, "mobile_results": mobile_results})
        raise
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    print(json.dumps(run(app_root()), indent=2))
