"""Verify the cross-issuer Nissan 2024-B card in the local ABS-EE app."""
import json
import re
import uuid
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

from credit_atlas.workspace import contained

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8785"


def main():
    out = contained(ROOT, "artifacts/private/nissan-2024b-external-ui-qa-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    errors, checks = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(BASE + "/?view=abs&workspace_tab=absee-profile", wait_until="networkidle")
        nissan = page.locator("#absee-nissan-2024b-external")
        expect(nissan).to_contain_text("1,154,259", timeout=180000)
        expect(nissan).to_contain_text("20 / 23")
        expect(nissan).to_contain_text("178 / 184")
        expect(nissan).to_contain_text("17 / 23 exact")
        expect(nissan).to_contain_text("First code-4 count / principal")
        expect(nissan).to_contain_text("21 / 23; amount 20 / 23")
        expect(nissan).to_contain_text("Do not reuse Toyota")
        expect(nissan).to_contain_text("Current net-loss ratio · first → latest")
        expect(nissan).to_contain_text("0.08% → 0.56%")
        ratio_chart = nissan.locator('svg[aria-label*="Nissan 10-D current and four-month average net-loss ratios"]')
        expect(ratio_chart).to_be_visible()
        ratio_path = ratio_chart.locator("path.line-primary").get_attribute("d") or ""
        ratio_y = [float(y) for _, _, y in re.findall(r"([ML])([0-9.]+),([0-9.]+)", ratio_path)]
        if not ratio_y or min(ratio_y) < 15 or max(ratio_y) > 200:
            raise AssertionError("Negative net-loss ratio was clipped by the chart scale")
        expect(nissan).to_contain_text("4-month average")
        expect(nissan).to_contain_text("23 / 23 No · threshold 4.90%")
        expect(nissan).to_contain_text("10-D KPI arithmetic is internally conserved")
        expect(nissan).to_contain_text("Live SEC submissions census")
        expect(nissan).to_contain_text("No 10-D/A or ABS-EE/A found")
        expect(nissan).to_contain_text("degrades the full 23-period tie-out from 178/184 to 86/184")
        expect(nissan).to_contain_text("all six months with an asset/certificate amount gap")
        checks.append("External issuer card shows KPI conservation, live SEC census, recovery timing, and local DPD boundary caveat")
        kpis = nissan.locator("details").filter(has=page.locator("summary", has_text="all 23 reported 10-D KPI observations"))
        kpis.locator("summary").click()
        expect(kpis).to_contain_text("Monthly net loss · USD")
        expect(kpis).to_contain_text("Ending reserve · USD")
        expect(kpis).to_contain_text("-$316,637.01")
        expect(kpis).to_contain_text("-0.39%")
        checks.append("All 23 reported certificate KPI observations expand with negative monthly loss preserved")
        rows = nissan.locator("details").first
        rows.locator("summary").click()
        expect(rows).to_contain_text("2025-07-31")
        expect(rows).to_contain_text("714186.05")
        expect(rows).to_contain_text("First code-4 count Δ")
        page.screenshot(path=str(out / "desktop.png"), full_page=True)
        checks.append("23-period monthly exceptions expand")
        page.set_viewport_size({"width": 390, "height": 844})
        if page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
            raise AssertionError("Mobile view has horizontal overflow")
        page.screenshot(path=str(out / "mobile.png"), full_page=True)
        checks.append("Mobile layout has no horizontal overflow")
        with urlopen(BASE + "/api/absee-profile") as response:
            result = json.load(response)
            if response.status != 200 or response.headers.get("Cache-Control") != "no-store":
                raise AssertionError("API status or cache policy changed")
        validation = result["official_nissan_2024b_external_validation"]
        if validation["different_issuer_servicer_family_from_toyota"] is not True:
            raise AssertionError("External issuer lineage marker missing")
        if validation["model_external_validation_completed"] is not False:
            raise AssertionError("Model qualification disclaimer missing")
        checks.append("API pins audit and keeps model validation unqualified")
        tieout = validation["certificate_tieout"]
        if tieout["check_counts"]["monthly_net_loss_equals_defaulted_principal_less_recoveries"] != 23:
            raise AssertionError("Monthly net loss conservation check failed")
        if tieout["check_counts"]["cumulative_net_loss_equals_sum_of_monthly_net_loss"] != 23:
            raise AssertionError("Cumulative net loss conservation check failed")
        checks.append("API publishes both 23/23 net-loss arithmetic checks")
        if validation["submission_history"]["july_report_date_amendments"] != []:
            raise AssertionError("July amendment census changed")
        if validation["dpd_boundary_diagnostic"]["aggregate_exact_checks"] != {"literal": 178, "shifted": 86}:
            raise AssertionError("DPD boundary diagnostic changed")
        if len(validation["recovery_dpd_exception_audit"]["recovery_periods"]) != 6:
            raise AssertionError("Recovery exception audit scope changed")
        checks.append("API pins current submissions census, six recovery periods and boundary diagnostic")
        if errors:
            raise AssertionError(errors)
        checks.append("No browser JavaScript errors")
        browser.close()
    (out / "receipt.json").write_text(json.dumps({"status": "PASS", "checks": checks,
        "periods": 23, "rows": 1154259,
        "monthly_net_loss_conservation": "23/23",
        "recovery_exact_periods": 17,
        "negative_current_net_loss_ratio_preserved": True,
        "cumulative_net_loss_conservation": "23/23"}, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()

