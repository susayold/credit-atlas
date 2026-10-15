"""Audit the data and denominators supplied to D01 descriptive charts."""
from __future__ import annotations

import json
import math
from pathlib import Path
from uuid import uuid4

from credit_atlas.service import ResearchService
from credit_atlas.workspace import timestamp, write_new

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "d01-a24484b21a21"


def close(a, b, *, rel=1e-10, abs_tol=1e-6):
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_tol)


def audit(root: Path = ROOT):
    service = ResearchService(root, review_path=root / "artifacts/private/d01-chart-support-qa.sqlite3")
    case = service.case(CASE_ID)
    data = case["snapshot"]
    snapshot = data["snapshot"]
    checks = []

    # These are the exact fields consumed by the count and UPB stock-share charts.
    monthly_rows = snapshot["monthly"] + [row for rows in data["monthly_by_segment"].values() for row in rows]
    for row in monthly_rows:
        if row["state_usable_active_loans"]:
            expected = row["d3_active_loans"] / row["state_usable_active_loans"]
            if not close(row["d3_count_share"], expected):
                raise AssertionError(f"D3 count-share denominator mismatch at {row['period']}")
        elif row["d3_count_share"] is not None:
            raise AssertionError("Empty count denominator must remain unavailable")
        if row["state_usable_active_upb"]:
            if row["d3_active_upb"] is None:
                if row["d3_active_loans"] == 0 and row["d3_balance_share"] != 0:
                    raise AssertionError("No D3 loans must yield a known zero balance share")
                if row["d3_active_loans"] > 0 and row["d3_balance_share"] is not None:
                    raise AssertionError("Missing D3 UPB must remain unavailable")
            elif not close(row["d3_balance_share"], row["d3_active_upb"] / row["state_usable_active_upb"]):
                raise AssertionError(f"D3 UPB-share denominator mismatch at {row['period']}")
        elif row["d3_balance_share"] is not None:
            raise AssertionError("Empty UPB denominator must remain unavailable")
    checks.append({"name": "monthly_stock_chart", "status": "PASS", "points": len(monthly_rows),
                   "series": ["active_loans", "observed_active_upb", "d3_count_share", "d3_balance_share"],
                   "denominator": "state_usable_active_loans / state_usable_active_upb"})

    # Vintage charts and their support cards must share segment/horizon rows.
    vintage_rows = snapshot["vintage_evidence"]["rows"]
    for row in vintage_rows:
        if row["eligible_loans"] <= 0 or row["source_loans"] != row["eligible_loans"] + row["excluded_loans"]:
            raise AssertionError("Vintage source/eligible/excluded support does not reconcile")
        if not 0 <= row["cif_d3"] <= 1 or not 0 <= row["cif_prepayment"] <= 1 or not 0 <= row["cif_other_exit"] <= 1:
            raise AssertionError("Vintage chart contains an invalid incidence")
        if row["cif_d3"] + row["cif_prepayment"] + row["cif_other_exit"] > 1 + 1e-9:
            raise AssertionError("Competing-event incidence exceeds one")
        if row["observed_d3_count"] + row["observed_prepayment_count"] + row["observed_other_exit_count"] > row["eligible_loans"]:
            raise AssertionError("Vintage event counts exceed eligible support")
        if row["at_risk"] > row["eligible_loans"]:
            raise AssertionError("Vintage risk set exceeds eligible loans")
    checks.append({"name": "vintage_incidence_and_support", "status": "PASS", "rows": len(vintage_rows),
                   "segments": sorted({row["segment"] for row in vintage_rows}),
                   "horizons_months": sorted({row["observation_age"] for row in vintage_rows})})

    # Origination-profile bars are shares within their segment and selected dimension.
    profile = snapshot["portfolio_profile"]["rows"]
    grouped = {}
    for row in profile:
        grouped.setdefault((row["segment"], row["dimension"]), []).append(row)
    for key, rows in grouped.items():
        if not close(sum(row["count_share"] for row in rows), 1, abs_tol=1e-8):
            raise AssertionError(f"Portfolio count shares do not sum to one: {key}")
        if not close(sum(row["balance_share"] for row in rows), 1, abs_tol=1e-8):
            raise AssertionError(f"Portfolio balance shares do not sum to one: {key}")
        if len({row["segment_loans"] for row in rows}) != 1:
            raise AssertionError(f"Portfolio segment loan denominator changes within buckets: {key}")
        if len({row["segment_opening_upb"] for row in rows}) != 1:
            raise AssertionError(f"Portfolio opening-UPB denominator changes within buckets: {key}")
    checks.append({"name": "portfolio_profile_bars", "status": "PASS", "groups": len(grouped),
                   "denominators": ["segment_loans", "segment_opening_upb"]})

    # Transition matrices use common origin denominators. Count probabilities reconcile;
    # balance probabilities may sum below one only where an opening balance is missing.
    transitions = service.period_transitions(CASE_ID)
    for name in ("rows", "lifetime_rows"):
        rows = transitions[name]
        groups = {}
        for row in rows:
            key = (row["reporting_year"], row["segment"], row["origin"])
            groups.setdefault(key, []).append(row)
        for key, cells in groups.items():
            if len({cell["origin_pairs"] for cell in cells}) != 1:
                raise AssertionError(f"Transition origin-pair denominator differs across cells: {key}")
            if sum(cell["pairs"] for cell in cells) != cells[0]["origin_pairs"]:
                raise AssertionError(f"Transition cell counts fail to reconcile to origin: {key}")
            if not close(sum(cell["count_probability"] for cell in cells), 1, abs_tol=1e-8):
                raise AssertionError(f"Count transition probabilities do not sum to one: {key}")
            if len({cell["origin_opening_upb"] for cell in cells}) != 1:
                raise AssertionError(f"Transition origin-UPB denominator differs across cells: {key}")
            upb_total = cells[0]["origin_opening_upb"]
            probability = sum(cell["balance_probability"] for cell in cells)
            if probability > 1 + 1e-8 or (upb_total and not close(probability,
                    sum(cell["opening_upb"] for cell in cells) / upb_total, abs_tol=1e-8)):
                raise AssertionError(f"Balance transition probabilities fail denominator reconciliation: {key}")
        checks.append({"name": "transition_matrix_" + name, "status": "PASS", "rows": len(rows),
                       "origin_groups": len(groups), "count_probability_total": "1 per origin",
                       "balance_missingness": "retained in probability coverage"})
    if set(transitions["reconciliation"].values()) != {"PASS"}:
        raise AssertionError("Transition frozen-engine reconciliation failed")

    # Loss bridge must add to resolved reported loss; unresolved remains outside the bridge.
    loss = snapshot["loss_summary"]
    bridge = loss["component_bridge"]
    if not close(sum(bridge.values()), loss["reported_loss_sum_usd"], abs_tol=1e-5):
        raise AssertionError("Signed loss bridge does not reconcile to resolved reported loss")
    if loss["component_bridge_complete_rows"] != loss["reported_loss_loans"]:
        raise AssertionError("Loss bridge support differs from resolved loss-loan support")
    if loss["unresolved_terminal_loans"] <= 0 or loss["expected_loss_dollars"] is not None:
        raise AssertionError("Loss display must preserve unresolved support and unavailable expected loss")
    checks.append({"name": "observed_loss_bridge", "status": "PASS",
                   "resolved_loans": loss["reported_loss_loans"],
                   "unresolved_terminal_loans": loss["unresolved_terminal_loans"],
                   "bridge_total_usd": round(sum(bridge.values()), 2),
                   "expected_loss_dollars": None})

    output = root / "artifacts/private" / ("d01-chart-support-" + uuid4().hex[:12])
    output.mkdir(parents=True)
    receipt = {"status": "PASS", "created_at": timestamp(), "case_id": CASE_ID,
               "pipeline_run": snapshot["pipeline_run"], "checks": checks,
               "limitations": ["Data/API contract audit; paired with browser QA for rendered view presence and filter behavior.",
                               "Descriptive chart integrity does not imply model qualification or population representativeness."],
               "visibility": "private", "public_release_approved": False}
    write_new(output / "receipt.json", receipt)
    return {"status": "PASS", "check_count": len(checks), "receipt": str(output / "receipt.json")}


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
