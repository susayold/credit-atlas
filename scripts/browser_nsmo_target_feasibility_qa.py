"""Browser acceptance for the aggregate-only NSMO target-feasibility panel."""

from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

from playwright.sync_api import sync_playwright

from credit_atlas.server import handler_for


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    checks: list[str] = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(SimpleNamespace(root=args.root)))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/nsmo"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            response = page.goto(url, wait_until="networkidle", timeout=45_000)
            if response is None or response.status != 200:
                raise RuntimeError("NSMO page did not return HTTP 200")
            state = page.locator("#target-feasibility-state")
            state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            checks.append("hash-bound feasibility receipt loads in UI")

            metrics = page.locator("#target-feasibility-metrics").inner_text()
            if "59,703" not in metrics or "156" not in metrics:
                raise AssertionError("one-landmark baseline/90+ support metrics do not match verified aggregates")
            checks.append("one-landmark distinct-loan support renders")

            mode = page.locator("#target-anchor-choice")
            mode.select_option("repeated")
            metrics = page.locator("#target-feasibility-metrics").inner_text()
            if "872,888" not in metrics or "2,174" not in metrics:
                raise AssertionError("repeated-landmark snapshot/event metrics do not match verified aggregates")
            note = page.locator("#target-feasibility-note").inner_text()
            if "not independent" not in note:
                raise AssertionError("repeated-landmark dependence caveat is not visible")
            checks.append("repeated landmarks show snapshot and dependence caveat")

            same_month_metrics = page.locator("#same-month-ambiguity-metrics").inner_text()
            if not all(value in same_month_metrics for value in ("42,236", "126", "21")):
                raise AssertionError(f"same-month snapshot-status totals do not match receipt: {same_month_metrics}")
            same_month_rows = page.locator("#same-month-ambiguity-table tbody tr").all_inner_texts()
            if len(same_month_rows) != 3 or not all("A · history ended" in row for row in same_month_rows):
                raise AssertionError("same-month ambiguity table does not preserve the A-status breakdown")
            checks.append("same-month close/snapshot status counts and interpretation render")

            page.locator("#target-vintage-band").select_option("2017-2019")
            rows = page.locator("#target-vintage-table tbody tr").all_inner_texts()
            if len(rows) != 3 or not all(year in " ".join(rows) for year in ("2017", "2018", "2019")):
                raise AssertionError("vintage band filter does not return 2017–2019 rows")
            same_month_rows = page.locator("#same-month-ambiguity-table tbody tr").all_inner_texts()
            if len(same_month_rows) != 3 or not all("A · history ended" in row for row in same_month_rows):
                raise AssertionError("vintage filter does not update same-month status breakdown")
            checks.append("vintage filter narrows repeated-landmark table")

            page.locator("#target-vintage-band").select_option("all")

            if page.locator("#target-quarter-table tbody tr").count() != 51:
                raise AssertionError("quarter support table does not show all 51 performance quarters")
            checks.append("quarter table distinguishes full and short horizons")

            origin_state = page.locator("#origination-feasibility-state")
            origin_state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            origin_metrics = page.locator("#origination-feasibility-metrics").inner_text()
            if "65" not in origin_metrics or "53,184" not in origin_metrics:
                raise AssertionError("origination-aligned feasibility metrics do not match the verified receipt")
            if page.locator("#origination-feasibility-table tbody tr").count() != 12:
                raise AssertionError("origination-aligned table does not show all 12 vintages")
            origin_note = page.locator("#origination-feasibility-note").inner_text()
            if "cannot establish event dates" not in origin_note or "PD" not in origin_note:
                raise AssertionError("origination-aligned support caveat is not visible")
            checks.append("origination-aligned support shows sparse outcomes and no-PD caveat")

            page.locator("#target-vintage-band").select_option("2017-2019")
            origin_rows = page.locator("#origination-feasibility-table tbody tr").all_inner_texts()
            if len(origin_rows) != 3 or not all(year in " ".join(origin_rows) for year in ("2017", "2018", "2019")):
                raise AssertionError("origination vintage filter does not narrow to 2017–2019")
            checks.append("shared vintage filter applies to origination support table")
            page.locator("#target-vintage-band").select_option("all")

            transition_state = page.locator("#transition-support-state")
            transition_state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            transition_metrics = page.locator("#transition-support-metrics").inner_text()
            if not all(value in transition_metrics for value in ("322 / 296", "363 / 322", "393 / 330")):
                raise AssertionError(f"distinct/repeated transition support does not match the verified receipt: {transition_metrics}")
            if page.locator("#transition-support-table tbody tr").count() != 36:
                raise AssertionError("transition support table does not show all vintage/state groups")
            transition_note = page.locator("#transition-support-note").inner_text()
            if not all(value in transition_note for value in ("859", "805", "50", "4")):
                raise AssertionError("first-observed event partition is not fully visible")
            checks.append("first-observed 90+ support reconciles by state and vintage")

            page.locator("#target-vintage-band").select_option("2017-2019")
            transition_rows = page.locator("#transition-support-table tbody tr").all_inner_texts()
            if len(transition_rows) != 9 or not all(year in " ".join(transition_rows) for year in ("2017", "2018", "2019")):
                raise AssertionError("transition support vintage filter does not return 2017–2019 groups")
            checks.append("shared vintage filter applies to transition support table")
            page.locator("#target-vintage-band").select_option("all")

            risk_state = page.locator("#first-entry-risk-set-state")
            risk_state.get_by_text("Receipt verified", exact=False).wait_for(timeout=15_000)
            risk_metrics = page.locator("#first-entry-risk-set-metrics").inner_text()
            if not all(value in risk_metrics for value in ("57,311", "695", "887,861", "31,202")):
                raise AssertionError(f"first-entry risk-set metrics do not match the verified receipt: {risk_metrics}")
            if page.locator("#first-entry-risk-set-table tbody tr").count() != 31:
                raise AssertionError("first-entry risk-set table does not show all vintage/state groups")
            selection_rows = page.locator("#first-entry-population-table tbody tr").all_inner_texts()
            if len(selection_rows) != 12 or "2013" not in selection_rows[0] or "83.64%" not in selection_rows[0]:
                raise AssertionError(f"vintage entry-selection reconciliation is incorrect: {selection_rows[:1]}")
            if "2024" not in selection_rows[-1] or "96.39%" not in selection_rows[-1]:
                raise AssertionError(f"latest-vintage entry-selection support is incorrect: {selection_rows[-1:]}")
            missing_rows = page.locator("#first-entry-missing-table tbody tr").all_inner_texts()
            if len(missing_rows) != 12 or not all(value in missing_rows[0] for value in ("2013", "951", "6", "8")):
                raise AssertionError(f"pre-entry missing-status classes do not reconcile for 2013: {missing_rows[:1]}")
            if not all(value in missing_rows[-1] for value in ("2024", "65", "6", "4")):
                raise AssertionError(f"pre-entry missing-status classes do not reconcile for 2024: {missing_rows[-1:]}")
            risk_note = page.locator("#first-entry-risk-set-note").inner_text()
            if "administrative end: 23,802" not in risk_note or "population entry partition is 57,311" not in risk_note:
                raise AssertionError("first-entry risk-set censoring/support note is incomplete")
            checks.append("first-entry dynamic risk-set support and exits render")

            page.locator("#risk-entry-state").select_option("C")
            risk_metrics = page.locator("#first-entry-risk-set-metrics").inner_text()
            if "57,233" not in risk_metrics or page.locator("#first-entry-risk-set-table tbody tr").count() != 12:
                raise AssertionError("entry-state filter does not isolate current-at-entry mortgages")
            page.locator("#target-vintage-band").select_option("2017-2019")
            if page.locator("#first-entry-risk-set-table tbody tr").count() != 3:
                raise AssertionError("shared vintage filter does not narrow first-entry risk-set rows")
            if page.locator("#first-entry-population-table tbody tr").count() != 3:
                raise AssertionError("shared vintage filter does not narrow entry-selection rows")
            if page.locator("#first-entry-missing-table tbody tr").count() != 3:
                raise AssertionError("shared vintage filter does not narrow pre-entry status rows")
            checks.append("entry-state and shared vintage filters update risk-set and selection tables")
            page.locator("#risk-entry-state").select_option("all")
            page.locator("#target-vintage-band").select_option("all")

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(150)
            dimensions = page.evaluate("({width: document.querySelector('.target-feasibility-panel').clientWidth, scrollWidth: document.querySelector('.target-feasibility-panel').scrollWidth, columns: getComputedStyle(document.querySelector('#target-feasibility-metrics')).gridTemplateColumns.split(' ').length, origColumns: getComputedStyle(document.querySelector('#origination-feasibility-metrics')).gridTemplateColumns.split(' ').length, origTableWidth: document.querySelector('#origination-feasibility-table').clientWidth, origTableScroll: document.querySelector('#origination-feasibility-table').scrollWidth, transitionColumns: getComputedStyle(document.querySelector('#transition-support-metrics')).gridTemplateColumns.split(' ').length, transitionTableWidth: document.querySelector('#transition-support-table').clientWidth, transitionTableScroll: document.querySelector('#transition-support-table').scrollWidth, sameMonthColumns: getComputedStyle(document.querySelector('#same-month-ambiguity-metrics')).gridTemplateColumns.split(' ').length, sameMonthTableWidth: document.querySelector('#same-month-ambiguity-table').clientWidth, sameMonthTableScroll: document.querySelector('#same-month-ambiguity-table').scrollWidth})")
            if dimensions["scrollWidth"] > dimensions["width"] or dimensions["columns"] != 2:
                raise AssertionError(f"target panel overflows or fails mobile KPI layout: {dimensions}")
            if dimensions["origColumns"] != 2 or dimensions["origTableScroll"] <= dimensions["origTableWidth"]:
                raise AssertionError(f"origination panel mobile layout or table scroller is incorrect: {dimensions}")
            if dimensions["transitionColumns"] != 2 or dimensions["transitionTableScroll"] <= dimensions["transitionTableWidth"]:
                raise AssertionError(f"transition support mobile layout or table scroller is incorrect: {dimensions}")
            if dimensions["sameMonthColumns"] != 2 or dimensions["sameMonthTableScroll"] <= dimensions["sameMonthTableWidth"]:
                raise AssertionError(f"same-month status mobile layout or table scroller is incorrect: {dimensions}")
            checks.append("mobile feasibility panels fit viewport and tables scroll horizontally")
            if errors:
                raise AssertionError(f"Browser JavaScript errors: {errors}")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

    receipt = {
        "schema_version": "nsmo-target-feasibility-browser-qa-v2",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "browser": "Microsoft Edge headless via Playwright",
        "checks": checks,
        "page_errors": errors,
        "privacy": "No identifiers, screenshots or source rows captured.",
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "page_errors": len(errors)}))


if __name__ == "__main__":
    main()
