"""Real-data browser acceptance, using a separate private QA review database."""
from __future__ import annotations

import json
import threading
import uuid
import zipfile
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
    hmda_views = [row for row in service.hmda_views.catalog()["views"] if row["status"] == "verified"]
    bank_views = [row for row in service.bank_views.catalog()["views"] if row["status"] == "verified"]
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
            page.goto(base + "/?view=market", wait_until="networkidle")
            expect(page.locator("#page-title")).to_have_text("Market Context & Bond Scenario Lab")
            expect(page.locator("#content")).to_contain_text("Series coverage & units")
            market_from = page.get_by_label("Market from date").input_value()
            market_to = page.get_by_label("Market to date").input_value()
            with page.expect_download() as captured:
                page.locator("#export-report").click()
            market_download = captured.value
            market_path = output / "market-series-report.json"
            market_download.save_as(str(market_path))
            market_report = json.loads(market_path.read_text(encoding="utf-8"))
            assert market_report["visibility"] == "private"
            assert market_report["public_release_approved"] is False
            assert market_report["filters"]["from"] == market_from
            assert market_report["filters"]["to"] == market_to
            assert market_report["native_rows"] == len(market_report["rows"])
            checks.append("market export downloads valid private JSON matching the displayed date filters")
            select_task(page, "Bond scenarios")
            with page.expect_download() as captured:
                page.get_by_role("button", name="Xuất bond scenario riêng tư", exact=True).click()
            bond_download = captured.value
            bond_path = output / "market-bond-scenario.json"
            bond_download.save_as(str(bond_path))
            bond_report = json.loads(bond_path.read_text(encoding="utf-8"))
            assert bond_report["visibility"] == "private"
            assert bond_report["public_release_approved"] is False
            assert bond_report["source_market_series_used_for_pricing"] is False
            checks.append("bond scenario export preserves private scope and assumption-only pricing caveat")
            page.goto(base + "/?run=" + case_id + "&view=overview", wait_until="networkidle")
            for view in ["sources", "portfolio", "vintage", "transitions", "models", "loss", "evidence"]:
                navigate_workspace(page, view)
                page.wait_for_timeout(180)
                expect(page.locator("#content")).not_to_contain_text("Invalid request")
                expect(page.locator("#content")).not_to_contain_text("Research evidence unavailable")
                if view == "sources":
                    expect(page.locator("#content")).to_contain_text("Quality monitoring & investigation", timeout=15000)
                    checks.append("source monitoring and investigation view")
                    nmdb = page.locator("#fhfa-nmdb-performance")
                    expect(nmdb).to_contain_text("2026Q2", timeout=15000)
                    assert nmdb.locator('svg[role="img"]').count() == 2
                    expect(nmdb).to_contain_text("not a loan-level panel")
                    checks.append("public FHFA NMDB aggregate history renders with source-population caveats")
                    with page.expect_download() as captured:
                        page.get_by_role("button", name="Xuất FHFA NMDB aggregate JSON", exact=True).click()
                    download = captured.value
                    download.save_as(str(output / "fhfa-nmdb-context.json"))
                    context_export = json.loads((output / "fhfa-nmdb-context.json").read_text(encoding="utf-8"))
                    assert context_export["status"] == "AVAILABLE"
                    assert len(context_export["rows"]) == 98
                    assert context_export["quality"]["archive_sha256"] == "f13c2b3a09b3c4318d43bcf2ba1fcc1e79f9b9c5a1c5ac2f49553dc377787dca"
                    checks.append("FHFA NMDB standalone source export includes all quarters and the verified archive hash")
                    cfpb = page.locator("#cfpb-mortgage-trends")
                    expect(cfpb).to_contain_text("2008-01 → 2025-12", timeout=15000)
                    expect(cfpb).to_contain_text("507", timeout=15000)
                    assert cfpb.locator('svg[aria-label="CFPB monthly mortgage delinquency rates by selected geography"]').is_visible()
                    checks.append("CFPB monthly aggregate context renders 2008–2025 coverage and geography options")
                    cfpb.get_by_label("CFPB mortgage performance geography").select_option("County|01003")
                    expect(cfpb).to_contain_text("Baldwin County, AL · 01003", timeout=15000)
                    with page.expect_download() as captured:
                        cfpb.get_by_role("button", name="Xuất CFPB geography JSON", exact=True).click()
                    cfpb_download = captured.value
                    cfpb_path = output / "cfpb-mortgage-trends-county-01003.json"
                    cfpb_download.save_as(str(cfpb_path))
                    cfpb_export = json.loads(cfpb_path.read_text(encoding="utf-8"))
                    assert cfpb_export["visibility"] == "private"
                    assert cfpb_export["public_release_approved"] is False
                    assert cfpb_export["selected_geography"]["geoid"] == "01003"
                    assert cfpb_export["selected_geography"]["name"] == "Baldwin County"
                    assert len(cfpb_export["rows"]) == 216
                    assert cfpb_export["rows"][-1]["period"] == "2025-12"
                    assert set(cfpb_export["quality"]["selected_source_hashes"]) == {"30_89", "90_plus"}
                    checks.append("CFPB county selection and JSON export preserve normalized FIPS, 216 months and source hashes")
                    cfpb_error_page = context.new_page()
                    cfpb_error_page.goto(base + "?run=" + case_id + "&view=overview", wait_until="networkidle")
                    navigate_workspace(cfpb_error_page, "sources")
                    cfpb_error_page.locator("#cfpb-mortgage-trends").get_by_label(
                        "CFPB mortgage performance geography").select_option("County|01003")
                    cfpb_error_page.route("**/api/cfpb-mortgage-trends-report*", lambda route: route.fulfill(
                        status=503, content_type="application/json",
                        body=json.dumps({"error": "Synthetic CFPB aggregate export outage"})))
                    cfpb_error_page.locator("#cfpb-mortgage-trends").get_by_role(
                        "button", name="Xuất CFPB geography JSON", exact=True).click()
                    expect(cfpb_error_page.locator("#notice.error")).to_contain_text("Synthetic CFPB aggregate export outage")
                    checks.append("CFPB aggregate export outage is reported without a fake download")
                    cfpb_error_page.unroute("**/api/cfpb-mortgage-trends-report*")
                    cfpb_error_page.close()
                    pudb = page.locator("#fhfa-pudb-acquisition")
                    expect(pudb).to_contain_text("2,093,767", timeout=15000)
                    expect(pudb).to_contain_text("no monthly payment performance")
                    expect(pudb).to_contain_text("not all applications/denials")
                    checks.append("FHFA PUDB acquisition profile renders with explicit no-performance/no-denial limits")
                    with page.expect_download() as captured:
                        page.get_by_role("button", name="Xuất FHFA PUDB aggregate profile", exact=True).click()
                    download = captured.value
                    pudb_path = output / "fhfa-pudb-aggregate-profile.json"
                    download.save_as(str(pudb_path))
                    pudb_export = json.loads(pudb_path.read_text(encoding="utf-8"))
                    assert pudb_export["status"] == "AVAILABLE"
                    assert pudb_export["visibility"] == "private"
                    assert pudb_export["public_release_approved"] is False
                    assert pudb_export["rows"] == 2_093_767 and pudb_export["columns"] == 66
                    assert pudb_export["unique_record_keys"] == pudb_export["rows"]
                    assert "record_num_sf_ctf" not in pudb_export
                    checks.append("FHFA PUDB export contains verified aggregates and no record-level keys")
                    hud = page.locator("#hud-fha-iif-tract")
                    expect(hud).to_contain_text("85,154", timeout=15000)
                    expect(hud).to_contain_text("timing as unresolved")
                    expect(hud).to_contain_text("−4 value is excluded")
                    checks.append("HUD FHA tract exposure profile renders with its vintage and special-code caveats")
                    with page.expect_download() as captured:
                        page.get_by_role("button", name="Xuất HUD FHA aggregate profile", exact=True).click()
                    download = captured.value
                    hud_path = output / "hud-fha-iif-aggregate-profile.json"
                    download.save_as(str(hud_path))
                    hud_export = json.loads(hud_path.read_text(encoding="utf-8"))
                    assert hud_export["status"] == "AVAILABLE" and hud_export["visibility"] == "private"
                    assert hud_export["unique_tracts"] == 85_154 and hud_export["states_or_territories"] == 52
                    assert "GEOID" not in hud_export and "GEOID" not in json.dumps(hud_export)
                    assert hud_export["uninterpreted_source_codes"]["unpaid_balance_usd"] == {"-4": 9_598}
                    checks.append("HUD FHA export keeps tract keys private and quarantines the undocumented -4 value")
                    with page.expect_download() as captured:
                        page.get_by_role("link", name="Xuất Fannie sample JSON", exact=True).click()
                    download = captured.value
                    fannie_path = output / "fannie-public-samples-report.json"
                    download.save_as(str(fannie_path))
                    fannie_export = json.loads(fannie_path.read_text(encoding="utf-8"))
                    assert fannie_export["visibility"] == "private"
                    assert fannie_export["public_release_approved"] is False
                    assert fannie_export["source_id"] == "fannie-public-samples-4d84128d3cb6"
                    checks.append("shared attachment handler exports the cross-workspace Fannie format audit with its private filename")
                    fed_bank = page.locator("#fed-bank-mortgage-context")
                    expect(fed_bank).to_contain_text("five products × three bank-size groups")
                    expect(fed_bank).to_contain_text("All commercial banks")
                    expect(fed_bank).to_contain_text("Top 100 banks")
                    expect(fed_bank).to_contain_text("Other banks")
                    checks.append("Federal Reserve bank-quality panel exposes all three size groups across five domains")
                    with page.expect_download(timeout=30000) as captured:
                        page.get_by_role("link", name="Federal Reserve · bank asset quality", exact=True).click()
                    fed_download = captured.value
                    assert fed_download.suggested_filename == "CreditAtlas-Fed-Bank-Asset-Quality.xlsx"
                    fed_workbook_path = output / fed_download.suggested_filename
                    fed_download.save_as(str(fed_workbook_path))
                    official_local_workbook = root / "apps" / "excel" / "templates" / "CreditAtlas-Fed-Bank-Asset-Quality.xlsx"
                    assert fed_workbook_path.read_bytes() == official_local_workbook.read_bytes()
                    with zipfile.ZipFile(fed_workbook_path) as workbook_zip:
                        assert workbook_zip.testzip() is None
                        workbook_xml = workbook_zip.read("xl/workbook.xml").decode("utf-8")
                        assert all(sheet in workbook_xml for sheet in ("Overview", "Quarterly History", "Series Dictionary", "Sources &amp; QA"))
                        assert len([name for name in workbook_zip.namelist() if name.startswith("xl/charts/chart")]) == 10
                    checks.append("Federal Reserve Excel download preserves source workbook bytes, four sheets and ten charts")
                    fed_error_page = context.new_page()
                    fed_failed_downloads = []
                    fed_error_page.on("download", lambda download: fed_failed_downloads.append(download.suggested_filename))
                    fed_error_page.goto(base + "/?view=sources", wait_until="networkidle")
                    fed_error_page.route("**/downloads/fed-bank-mortgage-context.xlsx", lambda route: route.fulfill(
                        status=503, content_type="application/json",
                        body=json.dumps({"error": "Synthetic Federal Reserve workbook outage"})))
                    fed_error_page.get_by_role("link", name="Federal Reserve · bank asset quality", exact=True).click()
                    expect(fed_error_page.locator("#notice.error")).to_contain_text("Synthetic Federal Reserve workbook outage")
                    assert fed_failed_downloads == []
                    checks.append("Federal Reserve workbook HTTP 503 is shown without creating a fake Excel download")
                    fed_error_page.unroute("**/downloads/fed-bank-mortgage-context.xlsx")
                    fed_error_page.route("**/downloads/fed-bank-mortgage-context.xlsx", lambda route: route.fulfill(
                        status=200, content_type="text/html", body="<html>not a workbook</html>"))
                    fed_error_page.get_by_role("link", name="Federal Reserve · bank asset quality", exact=True).click()
                    expect(fed_error_page.locator("#notice.error")).to_contain_text(
                        "HTML page instead of a downloadable report"
                    )
                    assert fed_failed_downloads == []
                    checks.append("Federal Reserve workbook rejects HTTP 200 HTML and creates no fake Excel download")
                    fed_error_page.close()
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
            failed_market_downloads = []
            error_page.on("download", lambda download: failed_market_downloads.append(download.suggested_filename))
            error_page.goto(base + "/?view=market", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Series coverage & units")
            error_page.route("**/api/market-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic market-series export outage"})))
            error_page.locator("#export-report").click()
            expect(error_page.locator("#notice.error")).to_contain_text("Synthetic market-series export outage")
            assert failed_market_downloads == []
            checks.append("HTTP 503 market-series export shows an error without creating a fake download")
            error_page.unroute("**/api/market-report*")
            select_task(error_page, "Bond scenarios")
            error_page.route("**/api/bond-report*", lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html>bond export unavailable</html>"))
            error_page.get_by_role("button", name="Xuất bond scenario riêng tư", exact=True).click()
            expect(error_page.locator("#notice.error")).to_contain_text("Research API HTTP 502 returned a non-JSON error")
            assert failed_market_downloads == []
            checks.append("HTTP 502 bond-scenario export exposes failure without a fake download")
            error_page.unroute("**/api/bond-report*")
            download_page = context.new_page()
            download_page.goto(base + "/?view=overview", wait_until="networkidle")
            attachment_downloads = []
            download_page.on("download", lambda download: attachment_downloads.append(download.suggested_filename))
            download_page.evaluate("""() => { const a=document.createElement('a'); a.id='qa-attachment-download';
                a.href='/api/exposure-excel-template'; a.setAttribute('download',''); a.textContent='QA attachment';
                a.style.position='fixed'; a.style.zIndex='99999'; a.style.top='4px'; document.body.append(a); }""")
            with download_page.expect_download(timeout=15000) as download_info:
                download_page.locator("#qa-attachment-download").click(force=True)
            downloaded = download_info.value
            assert downloaded.suggested_filename == "CreditAtlas-Portfolio-Input.xlsx", downloaded.suggested_filename
            checks.append("shared attachment download validates and preserves server filename for a real Excel template")
            download_page.route("**/api/exposure-excel-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic portfolio Excel export outage"})))
            download_page.evaluate("""() => { const a=document.createElement('a'); a.id='qa-failed-attachment-download';
                a.href='/api/exposure-excel-report?import_id=qa'; a.setAttribute('download','private.xlsx');
                a.textContent='QA failed attachment'; a.style.position='fixed'; a.style.zIndex='99999';
                a.style.top='40px'; document.body.append(a); }""")
            download_page.locator("#qa-failed-attachment-download").click(force=True)
            expect(download_page.locator("#notice.error")).to_contain_text("Synthetic portfolio Excel export outage")
            assert attachment_downloads == ["CreditAtlas-Portfolio-Input.xlsx"], attachment_downloads
            checks.append("HTTP 503 attachment export reports failure and never creates a fake Excel download")
            download_page.unroute("**/api/exposure-excel-report*")
            download_page.close()

            kpi_page = context.new_page()
            kpi_downloads = []
            kpi_page.on("download", lambda download: kpi_downloads.append(download.suggested_filename))
            kpi_page.goto(base + "/?view=monitor", wait_until="networkidle")
            kpi_button = kpi_page.get_by_role("button", name="Xuất KPI Excel", exact=True)
            expect(kpi_button).to_be_enabled(timeout=120000)
            with kpi_page.expect_download(timeout=240000) as workbook_info:
                kpi_button.click()
            workbook_download = workbook_info.value
            workbook_path = output / "monitor-kpi-workbook.xlsx"
            workbook_download.save_as(str(workbook_path))
            assert workbook_download.suggested_filename == "CreditAtlas-KPI-all.xlsx"
            with zipfile.ZipFile(workbook_path) as workbook:
                assert workbook.testzip() is None
                assert "xl/workbook.xml" in workbook.namelist()
            assert kpi_downloads == ["CreditAtlas-KPI-all.xlsx"]
            checks.append("real monitor POST export passes XLSX content validation and downloads a readable workbook")
            kpi_page.route("**/api/kpi-workbook", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic KPI workbook outage"})) if route.request.method == "POST" else route.continue_())
            kpi_button.click()
            expect(kpi_page.locator("#credit-monitor .monitor-source-ribbon .callout")).to_contain_text("Synthetic KPI workbook outage")
            assert kpi_downloads == ["CreditAtlas-KPI-all.xlsx"]
            checks.append("HTTP 503 KPI workbook POST shows the server error and creates no fake Excel file")
            kpi_page.unroute("**/api/kpi-workbook")
            kpi_page.locator("#credit-monitor .monitor-source-ribbon .callout").last.evaluate("e=>e.remove()")
            kpi_page.route("**/api/kpi-workbook", lambda route: route.fulfill(
                status=200, content_type="text/html", body="<html>upstream login page</html>")
                if route.request.method == "POST" else route.continue_())
            kpi_button.click()
            expect(kpi_page.locator("#credit-monitor .monitor-source-ribbon .callout")).to_contain_text(
                "Research API returned an HTML page instead of a downloadable report")
            assert kpi_downloads == ["CreditAtlas-KPI-all.xlsx"]
            checks.append("HTTP 200 HTML masquerading as KPI Excel is rejected without creating a file")
            kpi_page.unroute("**/api/kpi-workbook")
            kpi_page.close()

            sec_page = context.new_page()
            sec_downloads = []
            sec_page.on("download", lambda download: sec_downloads.append(download.suggested_filename))
            sec_page.goto(base + "/?view=sec&workspace_tab=debt", wait_until="networkidle")
            sec_button = sec_page.get_by_role("button", name="Xuất maturity Excel", exact=True)
            expect(sec_button).to_be_visible(timeout=60000)
            with sec_page.expect_download(timeout=120000) as sec_info:
                sec_button.click()
            sec_download = sec_info.value
            sec_path = output / "sec-maturity-workbook.xlsx"
            sec_download.save_as(str(sec_path))
            assert sec_download.suggested_filename == "CreditAtlas-Maturities-0000320193.xlsx"
            with zipfile.ZipFile(sec_path) as workbook:
                assert workbook.testzip() is None
                assert "xl/workbook.xml" in workbook.namelist()
            assert sec_downloads == ["CreditAtlas-Maturities-0000320193.xlsx"]
            checks.append("real SEC maturity POST export downloads a readable XLSX workbook")
            sec_page.route("**/api/sec-debt-workbook", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic SEC workbook outage"})) if route.request.method == "POST" else route.continue_())
            sec_button.click()
            expect(sec_page.locator("#sec-debt .callout")).to_contain_text("Synthetic SEC workbook outage")
            assert sec_downloads == ["CreditAtlas-Maturities-0000320193.xlsx"]
            checks.append("HTTP 503 SEC workbook POST reports the source error without creating a fake file")
            sec_page.unroute("**/api/sec-debt-workbook")
            sec_page.locator("#sec-debt .callout").last.evaluate("e=>e.remove()")
            sec_page.route("**/api/sec-debt-workbook", lambda route: route.fulfill(
                status=200, content_type="text/html", body="<html>upstream login page</html>")
                if route.request.method == "POST" else route.continue_())
            sec_button.click()
            expect(sec_page.locator("#sec-debt .callout")).to_contain_text(
                "Research API returned an HTML page instead of a downloadable report")
            assert sec_downloads == ["CreditAtlas-Maturities-0000320193.xlsx"]
            checks.append("HTTP 200 HTML masquerading as SEC Excel is rejected without creating a file")
            sec_page.unroute("**/api/sec-debt-workbook")
            sec_page.close()

            sec_standard_page = context.new_page()
            sec_standard_downloads = []
            sec_standard_page.on("download", lambda download: sec_standard_downloads.append(download.suggested_filename))
            sec_standard_page.goto(base + "/?view=sec&workspace_tab=coverage", wait_until="networkidle")
            sec_standard_button = sec_standard_page.get_by_role("button", name="Xuất SEC Excel", exact=True)
            expect(sec_standard_button).to_be_visible(timeout=60000)
            with sec_standard_page.expect_download(timeout=120000) as sec_standard_info:
                sec_standard_button.click()
            sec_standard_download = sec_standard_info.value
            sec_standard_path = output / "sec-standard-workbook.xlsx"
            sec_standard_download.save_as(str(sec_standard_path))
            assert sec_standard_download.suggested_filename == "CreditAtlas-SEC-0000320193.xlsx"
            with zipfile.ZipFile(sec_standard_path) as workbook:
                assert workbook.testzip() is None
                assert "xl/workbook.xml" in workbook.namelist()
            assert sec_standard_downloads == ["CreditAtlas-SEC-0000320193.xlsx"]
            checks.append("real SEC interest-coverage POST export downloads a readable XLSX workbook")
            sec_standard_page.route("**/api/sec-workbook", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic SEC standard workbook outage"}))
                if route.request.method == "POST" else route.continue_())
            sec_standard_button.click()
            expect(sec_standard_page.locator("#content .callout")).to_contain_text(
                "Synthetic SEC standard workbook outage")
            assert sec_standard_downloads == ["CreditAtlas-SEC-0000320193.xlsx"]
            checks.append("HTTP 503 SEC standard workbook POST reports failure without creating a fake file")
            sec_standard_page.unroute("**/api/sec-workbook")
            sec_standard_page.locator("#content .callout").last.evaluate("e=>e.remove()")
            sec_standard_page.route("**/api/sec-workbook", lambda route: route.fulfill(
                status=200, content_type="text/html", body="<html>upstream login page</html>")
                if route.request.method == "POST" else route.continue_())
            sec_standard_button.click()
            expect(sec_standard_page.locator("#content .callout")).to_contain_text(
                "Research API returned an HTML page instead of a downloadable report")
            assert sec_standard_downloads == ["CreditAtlas-SEC-0000320193.xlsx"]
            checks.append("HTTP 200 HTML masquerading as SEC standard Excel is rejected without a fake file")
            sec_standard_page.unroute("**/api/sec-workbook")
            sec_standard_page.close()

            sec_get_page = context.new_page()
            sec_get_page.goto(base + "/?view=sec&workspace_tab=note-rules", wait_until="networkidle")
            sec_get_cases = [
                ("Payment rules", "Xuất note rules JSON", "CreditAtlas-private-note-rules.json",
                 "sec-note-rules-report", "rules", 5),
                ("Note cashflows", "Xuất note schedule JSON", "CreditAtlas-private-note-schedule.json",
                 "sec-note-schedule-report", "rows", 42),
                ("Debt maturities", "Xuất maturity JSON", "CreditAtlas-private-SEC-maturities.json",
                 "sec-debt-report", "buckets", 6),
                ("Interest coverage", "Xuất SEC coverage JSON", "CreditAtlas-private-SEC-coverage.json",
                 "sec-coverage-report", "periods", 5),
                ("Annual trends", "Xuất SEC trend JSON", "CreditAtlas-private-SEC-trend.json",
                 "sec-trend-report", "periods", 5),
            ]
            for task_label, export_label, filename, _, rows_key, expected_rows in sec_get_cases:
                if task_label != "Payment rules":
                    sec_get_page.get_by_role("tab", name=task_label, exact=True).click()
                export_link = sec_get_page.get_by_role("link", name=export_label, exact=True)
                expect(export_link).to_be_visible(timeout=60000)
                with sec_get_page.expect_download(timeout=60000) as sec_json_info:
                    export_link.click()
                sec_json_download = sec_json_info.value
                assert sec_json_download.suggested_filename == filename
                sec_json_path = output / filename
                sec_json_download.save_as(str(sec_json_path))
                sec_json = json.loads(sec_json_path.read_text(encoding="utf-8"))
                assert len(sec_json[rows_key]) == expected_rows
                checks.append("SEC " + task_label.lower() + " GET export returns valid JSON with the server filename")
            sec_get_downloads = []
            sec_get_page.on("download", lambda download: sec_get_downloads.append(download.suggested_filename))
            sec_get_page.get_by_role("tab", name="Interest coverage", exact=True).click()
            coverage_link = sec_get_page.get_by_role("link", name="Xuất SEC coverage JSON", exact=True)
            expect(coverage_link).to_be_visible(timeout=60000)
            sec_get_page.route("**/api/sec-coverage-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic SEC coverage export outage"})))
            coverage_link.click()
            expect(sec_get_page.locator("#notice.error")).to_contain_text("Synthetic SEC coverage export outage")
            assert sec_get_downloads == []
            checks.append("HTTP 503 SEC GET attachment reports failure without creating a fake JSON download")
            sec_get_page.unroute("**/api/sec-coverage-report*")
            sec_get_page.close()

            affordability_page = context.new_page()
            affordability_downloads = []
            affordability_page.on("download", lambda download: affordability_downloads.append(download.suggested_filename))
            affordability_page.goto(base + "/?view=retail&workspace_tab=affordability", wait_until="networkidle")
            affordability_page.get_by_label("Affordability case reference").fill("qa-post-export")
            affordability_page.get_by_label("Affordability scope reference").fill("qa-scope")
            affordability_page.get_by_label("Affordability currency").fill("USD")
            affordability_page.get_by_role("button", name="Tính affordability", exact=True).click()
            export_affordability = affordability_page.get_by_role("button", name="Xuất affordability JSON", exact=True)
            expect(export_affordability).to_be_enabled(timeout=60000)
            with affordability_page.expect_download(timeout=60000) as affordability_info:
                export_affordability.click()
            affordability_download = affordability_info.value
            affordability_path = output / "affordability-report.json"
            affordability_download.save_as(str(affordability_path))
            affordability_report = json.loads(affordability_path.read_text(encoding="utf-8"))
            assert affordability_download.suggested_filename == "CreditAtlas-private-affordability.json"
            assert affordability_report["visibility"] == "private"
            assert affordability_report["credit_decision"] is None
            assert affordability_downloads == ["CreditAtlas-private-affordability.json"]
            checks.append("real affordability POST export downloads valid private JSON with no credit decision")
            affordability_page.route("**/api/affordability-report", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic affordability report outage"}))
                if route.request.method == "POST" else route.continue_())
            export_affordability.click()
            expect(affordability_page.locator("#affordability .callout")).to_contain_text(
                "Synthetic affordability report outage")
            assert affordability_downloads == ["CreditAtlas-private-affordability.json"]
            checks.append("HTTP 503 affordability POST reports the server error without creating a fake JSON file")
            affordability_page.unroute("**/api/affordability-report")
            affordability_page.locator("#affordability .callout").last.evaluate("e=>e.remove()")
            affordability_page.route("**/api/affordability-report", lambda route: route.fulfill(
                status=200, content_type="text/html", body="<html>upstream login page</html>")
                if route.request.method == "POST" else route.continue_())
            export_affordability.click()
            expect(affordability_page.locator("#affordability .callout")).to_contain_text(
                "Research API returned an HTML page instead of a downloadable report")
            assert affordability_downloads == ["CreditAtlas-private-affordability.json"]
            checks.append("HTTP 200 HTML masquerading as affordability JSON is rejected without creating a file")
            affordability_page.unroute("**/api/affordability-report")
            affordability_page.close()
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
            error_page.unroute("**/api/runs*")

            error_page.route("**/api/period-transitions*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic transition-service outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=transitions", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Synthetic transition-service outage")
            assert error_page.locator(".matrix-cell button").count() == 0
            checks.append("HTTP 503 transition mart outage shows unavailable evidence without a transition matrix")
            error_page.unroute("**/api/period-transitions*")

            error_page.route("**/api/episode-followup*", lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html>upstream unavailable</html>"))
            error_page.goto(base + "/?run=" + case_id + "&view=transitions", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Forward-only episode events")
            expect(error_page.locator("#content")).to_contain_text("Research API HTTP 502 returned a non-JSON error")
            checks.append("HTTP 502 episode-follow-up failure keeps local events and marks supplemental evidence unavailable")
            error_page.unroute("**/api/episode-followup*")

            error_page.route("**/api/monitoring*", lambda route: route.fulfill(
                status=500, content_type="application/json",
                body=json.dumps({"error": "Synthetic source-monitoring failure"})))
            error_page.goto(base + "/?run=" + case_id + "&view=sources", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Synthetic source-monitoring failure")
            expect(error_page.locator("#content")).to_contain_text("Origination rows")
            checks.append("HTTP 500 monitoring failure is surfaced beside source profile, not rendered as zero")
            error_page.unroute("**/api/monitoring*")

            error_page.route("**/api/loans*", lambda route: route.fulfill(
                status=500, content_type="application/json",
                body=json.dumps({"error": "Synthetic private-loan query failure"})))
            error_page.goto(base + "/?run=" + case_id + "&view=lifecycle", wait_until="networkidle")
            expect(error_page.locator(".loan-selection-list")).to_contain_text("Synthetic private-loan query failure")
            assert error_page.locator(".loan-row").count() == 0
            checks.append("HTTP 500 private-loan query failure clears rows and displays the query error")
            error_page.unroute("**/api/loans*")

            error_page.route("**/api/timeline*", lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html>timeline upstream unavailable</html>"))
            error_page.goto(base + "/?run=" + case_id + "&view=lifecycle", wait_until="networkidle")
            expect(error_page.locator(".loan-row").first).to_be_visible()
            expect(error_page.locator(".loan-layout .card").nth(1)).to_contain_text("Research API HTTP 502 returned a non-JSON error")
            checks.append("HTTP 502 private timeline failure keeps selectable loans and marks timeline unavailable")
            error_page.unroute("**/api/timeline*")

            failed_downloads = []
            error_page.on("download", lambda download: failed_downloads.append(download.suggested_filename))
            error_page.route("**/api/report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic private-report export outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=portfolio", wait_until="networkidle")
            error_page.locator("#export-report").click()
            expect(error_page.locator("#notice.error")).to_contain_text("Synthetic private-report export outage")
            assert failed_downloads == []
            checks.append("HTTP 503 private-report export shows an error and does not trigger a fake download")
            error_page.unroute("**/api/report*")

            context_downloads = []
            error_page.on("download", lambda download: context_downloads.append(download.suggested_filename))
            error_page.route("**/api/fhfa-nmdb-performance-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic NMDB export outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=sources", wait_until="networkidle")
            error_page.get_by_role("button", name="Xuất FHFA NMDB aggregate JSON", exact=True).click()
            expect(error_page.locator("#notice.error")).to_contain_text("Synthetic NMDB export outage")
            assert context_downloads == []
            checks.append("NMDB source export failure is surfaced and does not produce a file")
            error_page.unroute("**/api/fhfa-nmdb-performance-report*")

            error_page.route("**/api/fhfa-pudb-profile-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic FHFA PUDB export outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=sources", wait_until="networkidle")
            error_page.get_by_role("button", name="Xuất FHFA PUDB aggregate profile", exact=True).click()
            expect(error_page.locator("#notice.error")).to_contain_text("Synthetic FHFA PUDB export outage")
            assert context_downloads == []
            checks.append("FHFA PUDB export failure is visible and does not create a fake file")
            error_page.unroute("**/api/fhfa-pudb-profile-report*")

            error_page.route("**/api/hud-fha-iif-profile-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic HUD FHA export outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=sources", wait_until="networkidle")
            error_page.get_by_role("button", name="Xuất HUD FHA aggregate profile", exact=True).click()
            expect(error_page.locator("#notice.error")).to_contain_text("Synthetic HUD FHA export outage")
            assert context_downloads == []
            checks.append("HUD FHA source export failure is surfaced and does not produce a file")
            error_page.unroute("**/api/hud-fha-iif-profile-report*")

            error_page.route("**/api/fannie-samples-report*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic Fannie source export outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=sources", wait_until="networkidle")
            error_page.get_by_role("link", name="Xuất Fannie sample JSON", exact=True).click()
            expect(error_page.locator("#notice.error")).to_contain_text("Synthetic Fannie source export outage")
            assert context_downloads == []
            checks.append("Fannie cross-workspace source export outage is visible without a fake JSON file")
            error_page.unroute("**/api/fannie-samples-report*")

            error_page.route("**/api/mortgage-provenance*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic provenance-service outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=sources", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Synthetic provenance-service outage")
            assert error_page.locator("#mortgage-provenance").count() == 0
            checks.append("HTTP 503 source-provenance failure is visible without presenting a partial provenance card")
            error_page.unroute("**/api/mortgage-provenance*")

            error_page.route("**/api/studies*", lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html>study store unavailable</html>"))
            error_page.goto(base + "/?run=" + case_id + "&view=models", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Actual research model: chưa qualified")
            expect(error_page.locator("#content")).to_contain_text("Thiếu annual vintages bắt buộc")
            expect(error_page.locator("#content")).to_contain_text("Research API HTTP 502 returned a non-JSON error")
            checks.append("HTTP 502 prepared-study failure preserves the before-fit gate and marks study evidence unavailable")
            error_page.unroute("**/api/studies*")

            error_page.route("**/api/observed-loss-details*", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic loss-diagnostics outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=loss", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Synthetic loss-diagnostics outage")
            expect(error_page.locator("#content")).to_contain_text("Signed observed loss bridge")
            assert error_page.locator("#observed-loss-details").count() == 0
            checks.append("HTTP 503 loss-diagnostics failure retains frozen bridge but omits unavailable diagnostic metrics")
            error_page.unroute("**/api/observed-loss-details*")

            error_page.route("**/api/findings*", lambda route: route.fulfill(
                status=500, content_type="application/json",
                body=json.dumps({"error": "Synthetic findings-service outage"})))
            error_page.goto(base + "/?run=" + case_id + "&view=evidence", wait_until="networkidle")
            expect(error_page.locator("#content")).to_contain_text("Synthetic findings-service outage")
            expect(error_page.locator("#content")).to_contain_text("Frozen run lineage")
            checks.append("HTTP 500 findings failure is surfaced while frozen run lineage remains visible")
            error_page.unroute("**/api/findings*")

            error_page.route("**/api/finding-history*", lambda route: route.fulfill(
                status=502, content_type="text/html", body="<html>history service unavailable</html>"))
            error_page.goto(base + "/?run=" + case_id + "&view=evidence", wait_until="networkidle")
            error_page.get_by_role("button", name="Xem history", exact=True).first.click()
            expect(error_page.locator("#notice.error")).to_contain_text("Research API HTTP 502 returned a non-JSON error")
            checks.append("HTTP 502 finding-history failure is surfaced without fabricating review history")
            error_page.unroute("**/api/finding-history*")

            error_page.route("**/api/findings", lambda route: route.fulfill(
                status=503, content_type="application/json",
                body=json.dumps({"error": "Synthetic finding-save outage"}))
                if route.request.method == "POST" else route.continue_())
            error_page.get_by_role("button", name="+ Lưu finding", exact=True).click()
            error_page.locator("#finding-title").fill("QA ONLY — failed save")
            error_page.locator("#finding-body").fill("Synthetic failure test; must remain unsaved.")
            error_page.locator("#save-finding").click()
            expect(error_page.locator("#finding-dialog")).to_be_visible()
            expect(error_page.locator("#finding-error")).to_contain_text("Synthetic finding-save outage")
            checks.append("HTTP 503 finding-save failure keeps the dialog open and exposes the error")
            error_page.unroute("**/api/findings")
            error_page.locator("#cancel-finding").click()

            error_page.close()
            # HMDA and FDIC exports are delivered through the same attachment
            # handler as D01. Exercise their actual route shapes so a failed
            # direct GET cannot silently save an error response as a report.
            failed_workspace_downloads = []
            error_page = context.new_page()
            error_page.on("download", lambda download: failed_workspace_downloads.append(download.suggested_filename))
            if hmda_views:
                error_page.route("**/api/hmda-report*", lambda route: route.fulfill(
                    status=503, content_type="application/json",
                    body=json.dumps({"error": "Synthetic HMDA export outage"})))
                error_page.route("**/api/hmda-labeled-report*", lambda route: route.fulfill(
                    status=503, content_type="application/json",
                    body=json.dumps({"error": "Synthetic HMDA export outage"})))
                error_page.goto(base + "/?view=hmda&hmda_view_id=" + hmda_views[0]["view_id"], wait_until="networkidle")
                error_page.locator("#export-report").click()
                expect(error_page.locator("#notice.error")).to_contain_text("Synthetic HMDA export outage")
                assert failed_workspace_downloads == []
                checks.append("HMDA GET export outage is visible and creates no error-file download")
                error_page.unroute("**/api/hmda-report*")
                error_page.unroute("**/api/hmda-labeled-report*")
            if bank_views:
                error_page.route("**/api/bank-report*", lambda route: route.fulfill(
                    status=503, content_type="application/json",
                    body=json.dumps({"error": "Synthetic FDIC bank export outage"})))
                error_page.goto(base + "/?view=bank&bank_view_id=" + bank_views[0]["view_id"], wait_until="networkidle")
                error_page.locator("#export-report").click()
                expect(error_page.locator("#notice.error")).to_contain_text("Synthetic FDIC bank export outage")
                assert failed_workspace_downloads == []
                checks.append("FDIC bank GET export outage is visible and creates no error-file download")
                error_page.unroute("**/api/bank-report*")
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
