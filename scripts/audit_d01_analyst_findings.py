"""Recompute analyst findings from the frozen D01 report and fail on drift."""
import json
import uuid
from pathlib import Path

from credit_atlas.workspace import sha256, timestamp, write_new

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "artifacts/private/d01-a24484b21a21"


def run():
    case = json.loads((CASE / "case-complete.json").read_text(encoding="utf-8"))
    report_path = CASE / "report.json"
    foundation_path = CASE / "foundation-complete.json"
    report_hash = sha256(report_path)
    foundation_hash = sha256(foundation_path)
    if (case["status"] != "D01_DESCRIPTIVE_COMPLETE"
            or case["outputs_sha256"]["report.json"] != report_hash
            or case["outputs_sha256"]["foundation-complete.json"] != foundation_hash):
        raise ValueError("Frozen D01 report failed case receipt hash verification")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    foundation = json.loads(foundation_path.read_text(encoding="utf-8"))
    tables = {table["table_id"]: table["rows"] for table in report["tables"]}
    monthly = tables["portfolio_monthly"]
    vintage = {(row["segment"], row["observation_age"]): row
               for row in tables["vintage_competing_risk"]}
    outcomes = {row["outcome"]: row["loans"] for row in tables["label_outcomes"]}
    loss = tables["observed_loss_summary"][0]
    by_month = {row["period"][:7]: row for row in monthly}
    selected_months = {month: by_month[month] for month in ("2020-03", "2020-05", "2020-06", "2020-07")}
    peak = max(monthly, key=lambda row: row["d3_count_share"])
    rel12, nonrel12, all12 = vintage["relief", 12], vintage["non_relief", 12], vintage["all", 12]
    if (len(monthly) != 171 or len(outcomes) != 5 or sum(outcomes.values()) != 50000
            or peak["period"][:7] != "2020-07" or peak["d3_active_loans"] != 505
            or all12["observed_d3_count"] != 102 or loss["terminal_loans"] != 381
            or loss["unresolved_terminal_loans"] != 7):
        raise ValueError("D01 aggregate finding invariants changed; review before publishing")
    audit = {
        "created_at": timestamp(),
        "case_id": case["case_id"],
        "pipeline_run": case["pipeline_run"],
        "source_years": case["source_years"],
        "target_version": case["target_version"],
        "source_report": "artifacts/private/d01-a24484b21a21/report.json",
        "source_report_sha256": report_hash,
        "case_receipt_sha256": sha256(CASE / "case-complete.json"),
        "population": {"source_loans": foundation["source_summary"]["origination_loans"],
                       "loan_month_rows": foundation["source_summary"]["performance_rows"],
                       "reporting_months": len(monthly), "range": [monthly[0]["period"], monthly[-1]["period"]]},
        "finding_1_d3_stock": {
            "baseline_2020_03": {"d3_loans": selected_months["2020-03"]["d3_active_loans"],
                                  "active_loans": selected_months["2020-03"]["state_usable_active_loans"],
                                  "count_share": selected_months["2020-03"]["d3_count_share"]},
            "2020_05": {"d3_loans": selected_months["2020-05"]["d3_active_loans"],
                        "active_loans": selected_months["2020-05"]["state_usable_active_loans"],
                        "count_share": selected_months["2020-05"]["d3_count_share"]},
            "2020_06": {"d3_loans": selected_months["2020-06"]["d3_active_loans"],
                        "active_loans": selected_months["2020-06"]["state_usable_active_loans"],
                        "count_share": selected_months["2020-06"]["d3_count_share"],
                        "balance_share": selected_months["2020-06"]["d3_balance_share"]},
            "peak": {"period": peak["period"], "d3_loans": peak["d3_active_loans"],
                     "active_loans": peak["state_usable_active_loans"], "count_share": peak["d3_count_share"],
                     "d3_upb": peak["d3_active_upb"], "active_upb": peak["state_usable_active_upb"],
                     "balance_share": peak["d3_balance_share"]},
        },
        "finding_2_12m_competing_incidence": {
            "all": {key: all12[key] for key in ("eligible_loans", "at_risk", "observed_d3_count",
                     "observed_prepayment_count", "observed_other_exit_count", "cif_d3", "ci_lower", "ci_upper")},
            "relief": {key: rel12[key] for key in ("eligible_loans", "at_risk", "observed_d3_count",
                        "observed_prepayment_count", "observed_other_exit_count", "cif_d3", "ci_lower", "ci_upper")},
            "non_relief": {key: nonrel12[key] for key in ("eligible_loans", "at_risk", "observed_d3_count",
                            "observed_prepayment_count", "observed_other_exit_count", "cif_d3", "ci_lower", "ci_upper")},
            "binary_target_counts": outcomes,
        },
        "finding_3_observed_loss_coverage": {key: loss[key] for key in (
            "terminal_loans", "reported_loss_loans", "unresolved_terminal_loans", "availability",
            "reported_loss_sum_usd", "reported_loss_mean_usd", "reported_loss_min_usd",
            "reported_loss_max_usd", "severity_mean_uncapped", "severity_max_uncapped",
            "component_bridge_complete_rows", "partial_component_rows", "gate_status", "gate_reasons",
            "expected_loss_dollars", "research_ready")},
        "limitations": [
            "One origination vintage only; latest-revised retrospective performance, not strict point-in-time releases.",
            "D3 is the source numeric delinquency state 03-99; this stock series is not a new-default rate or causal event study.",
            "Relief/non-Relief comparison is observational; differing program selection and only 13 non-Relief 12-month events prohibit causal claims.",
            "Reported loss and uncapped severity are conditional on observed terminal records; not a qualified LGD or expected-loss estimate.",
            "No model was fitted; no annual vintage was added by this audit.",
        ],
    }
    output = ROOT / "artifacts/private" / ("d01-analyst-findings-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output / "audit.json", audit)
    receipt = {"status": "PASS", "audit": str((output / "audit.json").relative_to(ROOT)),
               "audit_sha256": sha256(output / "audit.json"), "source_report_sha256": report_hash,
               "case_receipt_sha256": audit["case_receipt_sha256"], "finding_count": 3,
               "source_loan_ids_exposed": False, "model_fit": False}
    write_new(output / "receipt.json", receipt)
    return {"output": str(output), "receipt": receipt, "finding_1_peak_month": peak["period"],
            "finding_1_peak_d3": peak["d3_active_loans"], "finding_2_events": all12["observed_d3_count"],
            "finding_3_resolved_loss_rows": loss["reported_loss_loans"]}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
