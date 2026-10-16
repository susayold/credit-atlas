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
    view_id = next(row["view_id"] for row in catalog["views"] if row["status"] == "verified" and row.get("release_type") == "static snapshot")
    snapshot = service.hmda_national_views.view(view_id)
    dynamic_view_id = next(row["view_id"] for row in catalog["views"] if row["status"] == "verified" and row.get("release_type") == "dynamic weekly snapshot")
    dynamic_snapshot = service.hmda_national_views.view(dynamic_view_id)
    one_year_catalog = service.hmda_one_year_views.catalog()
    one_year_id = next(row["view_id"] for row in one_year_catalog["views"] if row["status"] == "verified")
    one_year_snapshot = service.hmda_one_year_views.view(one_year_id)
    one_year_2020_catalog = service.hmda_one_year_2020_views.catalog()
    one_year_2020_id = next(row["view_id"] for row in one_year_2020_catalog["views"] if row["status"] == "verified")
    one_year_2020_snapshot = service.hmda_one_year_2020_views.view(one_year_2020_id)
    one_year_2020_state_rows = service.hmda_one_year_2020_views.report(one_year_2020_id, {"dimension": "state_code"})["breakdown"]
    one_year_2020_reason_rows = service.hmda_one_year_2020_views.report(one_year_2020_id, {"dimension": "denial_reason_1"})["breakdown"]
    one_year_2021_catalog = service.hmda_one_year_2021_views.catalog()
    one_year_2021_id = next(row["view_id"] for row in one_year_2021_catalog["views"] if row["status"] == "verified")
    one_year_2021_snapshot = service.hmda_one_year_2021_views.view(one_year_2021_id)
    one_year_2021_state_rows = service.hmda_one_year_2021_views.report(one_year_2021_id, {"dimension": "state_code"})["breakdown"]
    one_year_2021_reason_rows = service.hmda_one_year_2021_views.report(one_year_2021_id, {"dimension": "denial_reason_1"})["breakdown"]
    one_year_2022_catalog = service.hmda_one_year_2022_views.catalog()
    one_year_2022_id = next(row["view_id"] for row in one_year_2022_catalog["views"] if row["status"] == "verified")
    one_year_2022_snapshot = service.hmda_one_year_2022_views.view(one_year_2022_id)
    one_year_2022_state_rows = service.hmda_one_year_2022_views.report(one_year_2022_id, {"dimension": "state_code"})["breakdown"]
    one_year_2022_reason_rows = service.hmda_one_year_2022_views.report(one_year_2022_id, {"dimension": "denial_reason_1"})["breakdown"]
    one_year_2023_catalog = service.hmda_one_year_2023_views.catalog()
    one_year_2023_id = next(row["view_id"] for row in one_year_2023_catalog["views"] if row["status"] == "verified")
    one_year_2023_snapshot = service.hmda_one_year_2023_views.view(one_year_2023_id)
    one_year_2023_state_rows = service.hmda_one_year_2023_views.report(one_year_2023_id, {"dimension": "state_code"})["breakdown"]
    one_year_2023_reason_rows = service.hmda_one_year_2023_views.report(one_year_2023_id, {"dimension": "denial_reason_1"})["breakdown"]
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
            page.goto(base + f"/?view=hmda&hmda_national_view_id={view_id}", wait_until="domcontentloaded")
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

            page.get_by_label("HMDA national release version").select_option(dynamic_view_id)
            page.get_by_role("button", name="Load release").click()
            expect(page.locator("#hmda-national-snapshot")).to_contain_text("dynamic weekly snapshot")
            expect(page.locator("#hmda-national-snapshot")).to_contain_text("2026-10-11")
            expect(page.locator("#hmda-national-summary .metric-value").nth(0)).to_have_text("13,558,306")
            expect(page.locator("#hmda-national-summary .metric-value").nth(1)).to_have_text("4,794")
            expect(page.locator("#hmda-national-summary .metric-value").nth(2)).to_have_text("9,373,448")
            expect(page.locator("#hmda-national-summary .metric-value").nth(3)).to_have_text("22.5718%")
            with page.expect_download() as info:
                page.get_by_role("link", name="Tải Excel · release compare + 99-field codebook + full breakdowns").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-National-2025-Dynamic-Review.xlsx"))
            expected_dynamic_book = root / "data/private/hmda/hmda-national-dynamic-2025-20261011/CreditAtlas-HMDA-National-2025-Dynamic-Review.xlsx"
            assert sha256(output / "CreditAtlas-HMDA-National-2025-Dynamic-Review.xlsx") == sha256(expected_dynamic_book)
            checks.append("Dynamic 2025 as-of release renders its own counts and rate; dated 5-sheet Excel review downloads byte-identically")

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

            one_year_2020_panel = page.locator("#hmda-one-year-2020")
            expect(one_year_2020_panel).to_contain_text("One-Year 2020")
            expect(one_year_2020_panel).to_contain_text("30/04/2022")
            expect(page.locator("#hmda-one-year-2020-summary .metric-value").nth(0)).to_have_text("25,666,745")
            expect(page.locator("#hmda-one-year-2020-summary .metric-value").nth(1)).to_have_text("4,512")
            expect(page.locator("#hmda-one-year-2020-summary .metric-value").nth(2)).to_have_text("18,134,264")
            expect(page.locator("#hmda-one-year-2020-summary .metric-value").nth(3)).to_have_text("15.8829%")
            expect(page.locator("#hmda-one-year-2020-actions tbody tr")).to_have_count(8)
            expect(page.locator("#hmda-one-year-2020-breakdown tbody tr")).to_have_count(len(one_year_2020_state_rows))
            expect(one_year_2020_panel).to_contain_text("Three-Year")
            checks.append("2020 One-Year static release renders audited row count, LEIs, denominator and current Three-Year API caveat")

            one_year_2020_panel.get_by_label("HMDA 2020 One-Year breakdown dimension").select_option("denial_reason_1")
            one_year_2020_panel.get_by_role("button", name="Đọc breakdown 2020").click()
            expect(page.locator("#hmda-one-year-2020-breakdown tbody tr")).to_have_count(len(one_year_2020_reason_rows))
            expect(page.locator("#hmda-one-year-2020-breakdown")).to_contain_text("denial_reason_1")
            with page.expect_download() as info:
                one_year_2020_panel.locator("button", has_text="Tải JSON").click()
            info.value.save_as(str(output / "hmda-one-year-2020-denial-reasons.json"))
            exported = json.loads((output / "hmda-one-year-2020-denial-reasons.json").read_text(encoding="utf-8"))
            expected = service.hmda_one_year_2020_views.report(one_year_2020_id, {"dimension": "denial_reason_1"})
            assert exported == expected
            checks.append("2020 denial-reason JSON matches the verified aggregate and source field mapping")

            with page.expect_download() as info:
                one_year_2020_panel.locator("#hmda-one-year-2020-scope a[href='/downloads/hmda-one-year-2020-audit.xlsx']").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-One-Year-2020-Audit.xlsx"))
            source_2020 = one_year_2020_snapshot["source_id"]
            expected_workbook = root / "data/private/hmda" / source_2020 / "CreditAtlas-HMDA-One-Year-2020-Audit.xlsx"
            assert sha256(output / "CreditAtlas-HMDA-One-Year-2020-Audit.xlsx") == sha256(expected_workbook)
            checks.append("2020 One-Year workbook downloads byte-identically from its verified private source")

            one_year_2021_panel = page.locator("#hmda-one-year-2021")
            expect(one_year_2021_panel).to_contain_text("One-Year 2021")
            expect(one_year_2021_panel).to_contain_text("01/05/2023")
            expect(page.locator("#hmda-one-year-2021-summary .metric-value").nth(0)).to_have_text("26,227,364")
            expect(page.locator("#hmda-one-year-2021-summary .metric-value").nth(1)).to_have_text("4,368")
            expect(page.locator("#hmda-one-year-2021-summary .metric-value").nth(2)).to_have_text("18,620,312")
            expect(page.locator("#hmda-one-year-2021-summary .metric-value").nth(3)).to_have_text("15.6948%")
            expect(page.locator("#hmda-one-year-2021-actions tbody tr")).to_have_count(8)
            expect(page.locator("#hmda-one-year-2021-breakdown tbody tr")).to_have_count(len(one_year_2021_state_rows))
            expect(one_year_2021_panel).to_contain_text("Three-Year")
            checks.append("2021 One-Year static release renders audited row count, LEIs, denominator, action profile and official Three-Year API caveat")

            one_year_2021_panel.get_by_label("HMDA 2021 One-Year breakdown dimension").select_option("denial_reason_1")
            one_year_2021_panel.get_by_role("button", name="Đọc breakdown 2021").click()
            expect(page.locator("#hmda-one-year-2021-breakdown tbody tr")).to_have_count(len(one_year_2021_reason_rows))
            expect(page.locator("#hmda-one-year-2021-breakdown")).to_contain_text("denial_reason_1")
            with page.expect_download() as info:
                one_year_2021_panel.locator("button", has_text="Tải JSON").click()
            info.value.save_as(str(output / "hmda-one-year-2021-denial-reasons.json"))
            exported = json.loads((output / "hmda-one-year-2021-denial-reasons.json").read_text(encoding="utf-8"))
            expected = service.hmda_one_year_2021_views.report(one_year_2021_id, {"dimension": "denial_reason_1"})
            assert exported == expected
            assert exported["visibility"] == "private" and exported["public_release_approved"] is False
            checks.append("2021 denial-reason JSON matches the verified aggregate and source-specific field mapping")

            with page.expect_download() as info:
                one_year_2021_panel.locator("#hmda-one-year-2021-scope a[href='/downloads/hmda-one-year-2021-audit.xlsx']").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-One-Year-2021-Audit.xlsx"))
            source_2021 = one_year_2021_snapshot["source_id"]
            expected_workbook = root / "data/private/hmda" / source_2021 / "CreditAtlas-HMDA-One-Year-2021-Audit.xlsx"
            assert sha256(output / "CreditAtlas-HMDA-One-Year-2021-Audit.xlsx") == sha256(expected_workbook)
            checks.append("2021 One-Year workbook downloads byte-identically from its verified private source")

            one_year_2022_panel = page.locator("#hmda-one-year-2022")
            expect(one_year_2022_panel).to_contain_text("One-Year 2022")
            expect(one_year_2022_panel).to_contain_text("01/05/2024")
            expect(page.locator("#hmda-one-year-2022-summary .metric-value").nth(0)).to_have_text("16,099,307")
            expect(page.locator("#hmda-one-year-2022-summary .metric-value").nth(1)).to_have_text("4,480")
            expect(page.locator("#hmda-one-year-2022-summary .metric-value").nth(2)).to_have_text("11,323,683")
            expect(page.locator("#hmda-one-year-2022-summary .metric-value").nth(3)).to_have_text("22.0795%")
            expect(page.locator("#hmda-one-year-2022-actions tbody tr")).to_have_count(8)
            expect(page.locator("#hmda-one-year-2022-breakdown tbody tr")).to_have_count(len(one_year_2022_state_rows))
            expect(one_year_2022_panel).to_contain_text("Three-Year")
            checks.append("2022 One-Year static release renders its audited records, institutions, denominator and actions with the current Three-Year API caveat")

            one_year_2022_panel.get_by_label("HMDA 2022 One-Year breakdown dimension").select_option("denial_reason_1")
            one_year_2022_panel.get_by_role("button", name="Đọc breakdown 2022").click()
            expect(page.locator("#hmda-one-year-2022-breakdown tbody tr")).to_have_count(len(one_year_2022_reason_rows))
            expect(page.locator("#hmda-one-year-2022-breakdown")).to_contain_text("denial_reason-1")
            with page.expect_download() as info:
                one_year_2022_panel.locator("button", has_text="Tải JSON").click()
            info.value.save_as(str(output / "hmda-one-year-2022-denial-reasons.json"))
            exported = json.loads((output / "hmda-one-year-2022-denial-reasons.json").read_text(encoding="utf-8"))
            expected = service.hmda_one_year_2022_views.report(one_year_2022_id, {"dimension": "denial_reason_1"})
            assert exported == expected
            checks.append("2022 action-3 denial-reason JSON matches the private source-specific aggregate")

            with page.expect_download() as info:
                one_year_2022_panel.locator("#hmda-one-year-2022-scope a[href='/downloads/hmda-one-year-2022-audit.xlsx']").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-One-Year-2022-Audit.xlsx"))
            source_2022 = one_year_2022_snapshot["source_id"]
            expected_workbook = root / "data/private/hmda" / source_2022 / "CreditAtlas-HMDA-One-Year-2022-Audit.xlsx"
            assert sha256(output / "CreditAtlas-HMDA-One-Year-2022-Audit.xlsx") == sha256(expected_workbook)
            checks.append("2022 One-Year workbook downloads byte-identically from the verified private source")

            one_year_2023_panel = page.locator("#hmda-one-year-2023")
            expect(one_year_2023_panel).to_contain_text("One-Year 2023")
            expect(one_year_2023_panel).to_contain_text("19/05/2025")
            expect(page.locator("#hmda-one-year-2023-summary .metric-value").nth(0)).to_have_text("11,564,178")
            expect(page.locator("#hmda-one-year-2023-summary .metric-value").nth(1)).to_have_text(f"{one_year_2023_snapshot['summary']['reporters']:,}")
            expect(page.locator("#hmda-one-year-2023-summary .metric-value").nth(2)).to_have_text("8,058,391")
            expect(page.locator("#hmda-one-year-2023-summary .metric-value").nth(3)).to_have_text("25.2792%")
            expect(page.locator("#hmda-one-year-2023-actions tbody tr")).to_have_count(8)
            expect(page.locator("#hmda-one-year-2023-breakdown tbody tr")).to_have_count(len(one_year_2023_state_rows))
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("695,021")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("-0.9948 pp")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("16,099,307")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("25,666,745")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("26,227,364")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("-0.1881 pp")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("2021")
            expect(page.locator("#hmda-one-year-2023-comparison")).to_contain_text("2,922,414")
            checks.append("2023 One-Year source and five-release 2020–2024 comparison render with matched denominator and verified 2021 release")

            one_year_2023_panel.get_by_label("HMDA 2023 One-Year breakdown dimension").select_option("denial_reason_1")
            one_year_2023_panel.get_by_role("button", name="Đọc breakdown 2023").click()
            expect(page.locator("#hmda-one-year-2023-breakdown tbody tr")).to_have_count(len(one_year_2023_reason_rows))
            expect(page.locator("#hmda-one-year-2023-breakdown")).to_contain_text("denial_reason-1")
            with page.expect_download() as info:
                one_year_2023_panel.locator("button", has_text="Tải JSON").click()
            info.value.save_as(str(output / "hmda-one-year-2023-denial-reasons.json"))
            exported = json.loads((output / "hmda-one-year-2023-denial-reasons.json").read_text(encoding="utf-8"))
            expected = service.hmda_one_year_2023_views.report(one_year_2023_id, {"dimension": "denial_reason_1"})
            assert exported == expected
            assert exported["visibility"] == "private" and exported["public_release_approved"] is False
            checks.append("2023 denial-reason JSON exactly matches the private aggregate; action-3-only source field mapping retained")

            with page.expect_download() as info:
                one_year_2023_panel.locator("#hmda-one-year-2023-scope a[href='/downloads/hmda-one-year-2023-audit.xlsx']").click()
            info.value.save_as(str(output / "CreditAtlas-HMDA-One-Year-2023-Audit.xlsx"))
            source_2023 = one_year_2023_snapshot["source_id"]
            expected_workbook = root / "data/private/hmda" / source_2023 / "CreditAtlas-HMDA-One-Year-2023-Audit.xlsx"
            assert sha256(output / "CreditAtlas-HMDA-One-Year-2023-Audit.xlsx") == sha256(expected_workbook)
            checks.append("2023 Excel codebook/KPI/source-audit workbook downloads byte-identically")

            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator("#hmda-national-summary")).to_be_visible()
            expect(page.locator("#hmda-one-year-2024-summary")).to_be_visible()
            expect(page.locator("#hmda-one-year-2020-summary")).to_be_visible()
            expect(page.locator("#hmda-one-year-2021-summary")).to_be_visible()
            expect(page.locator("#hmda-one-year-2022-summary")).to_be_visible()
            expect(page.locator("#hmda-one-year-2023-summary")).to_be_visible()
            page.screenshot(path=str(output / "hmda-national-mobile.png"), full_page=True)
            checks.append("National summary remains visible at 390px mobile width")
            assert not errors, errors
            browser.close()
        view_receipt = json.loads((root / "artifacts/private" / view_id / "view-complete.json").read_text(encoding="utf-8"))
        one_year_receipt = json.loads((root / "artifacts/private" / one_year_id / "view-complete.json").read_text(encoding="utf-8"))
        one_year_2020_receipt = json.loads((root / "artifacts/private" / one_year_2020_id / "view-complete.json").read_text(encoding="utf-8"))
        one_year_2021_receipt = json.loads((root / "artifacts/private" / one_year_2021_id / "view-complete.json").read_text(encoding="utf-8"))
        one_year_2022_receipt = json.loads((root / "artifacts/private" / one_year_2022_id / "view-complete.json").read_text(encoding="utf-8"))
        one_year_2023_receipt = json.loads((root / "artifacts/private" / one_year_2023_id / "view-complete.json").read_text(encoding="utf-8"))
        write_new(output / "receipt.json", {
            "status": "PASS", "checks": checks, "browser_errors": errors,
            "view_id": view_id, "snapshot_summary": snapshot["summary"],
            "dynamic_view_id": dynamic_view_id, "dynamic_summary": dynamic_snapshot["summary"],
            "one_year_view_id": one_year_id, "one_year_summary": one_year_snapshot["summary"],
            "one_year_2020_view_id": one_year_2020_id,
            "one_year_2020_summary": one_year_2020_snapshot["summary"],
            "one_year_2021_view_id": one_year_2021_id,
            "one_year_2021_summary": one_year_2021_snapshot["summary"],
            "one_year_2021_receipt_sha256": sha256(root / "artifacts/private" / one_year_2021_id / "view-complete.json"),
            "one_year_2021_aggregate_sha256": one_year_2021_receipt["aggregate_sha256"],
            "one_year_2022_view_id": one_year_2022_id,
            "one_year_2022_summary": one_year_2022_snapshot["summary"],
            "one_year_2023_view_id": one_year_2023_id,
            "one_year_2023_summary": one_year_2023_snapshot["summary"],
            "one_year_2024_receipt_sha256": sha256(root / "artifacts/private" / one_year_id / "view-complete.json"),
            "one_year_2024_aggregate_sha256": one_year_receipt["aggregate_sha256"],
            "one_year_2020_receipt_sha256": sha256(root / "artifacts/private" / one_year_2020_id / "view-complete.json"),
            "one_year_2020_aggregate_sha256": one_year_2020_receipt["aggregate_sha256"],
            "one_year_2022_receipt_sha256": sha256(root / "artifacts/private" / one_year_2022_id / "view-complete.json"),
            "one_year_2022_aggregate_sha256": one_year_2022_receipt["aggregate_sha256"],
            "one_year_2023_receipt_sha256": sha256(root / "artifacts/private" / one_year_2023_id / "view-complete.json"),
            "one_year_2023_aggregate_sha256": one_year_2023_receipt["aggregate_sha256"],
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
