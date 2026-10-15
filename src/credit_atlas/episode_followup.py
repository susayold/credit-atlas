"""Observation support after confirmed episode events; never a cure-rate estimator."""
from __future__ import annotations

from collections import defaultdict
from itertools import groupby

import duckdb

from .workspace import contained

VERSION = "d01-confirmed-episode-followup-v1"


def month_number(date):
    return date.year * 12 + date.month


def audit_followup(anchor, months, horizon):
    """Months are (date, state, terminal), with unique increasing monthly grain."""
    if type(horizon) is not int or horizon not in (6, 12):
        raise ValueError("Supported follow-up horizons are 6 and 12 months")
    ordinals = [month_number(row[0]) for row in months]
    if any(b <= a for a, b in zip(ordinals, ordinals[1:])):
        raise ValueError("Monthly grain must be unique and sorted")
    at = month_number(anchor)
    positions = {number: index for index, number in enumerate(ordinals)}
    if at not in positions:
        raise ValueError("Confirmed event must exist in the canonical loan timeline")
    start = positions[at]
    if months[start][2] is not None:
        return "terminal_at_confirmation", 0
    observed = 0
    for row in months[start + 1:]:
        number = month_number(row[0])
        if number != at + observed + 1:
            return "interrupted_gap", observed
        if row[1] == "UNKNOWN":
            return "interrupted_unknown", observed
        if row[2] is not None:
            return "terminal_exit", observed
        observed += 1
        if observed == horizon:
            return "complete_nonterminal_followup", observed
    return "end_of_source", observed


def build(root, case):
    manifest = case["manifest"]
    aggregated = defaultdict(lambda: {"events": 0, "loans": set(), "observed_months": 0})
    with duckdb.connect() as db:
        db.execute("SET memory_limit='1GB'")
        db.execute("SET threads=2")
        db.read_parquet(str(contained(root, manifest["canonical_run"]) / "dim_loan.parquet")).create_view("dim_loan")
        db.read_parquet(str(contained(root, manifest["canonical_run"]) / "fact_loan_month.parquet")).create_view("fact")
        db.read_parquet(str(contained(root, manifest["portfolio_run"]) / "episodes.parquet")).create_view("episodes")
        events = defaultdict(list)
        query = """SELECT e.loan_id,e.confirmation_month,e.event_type,
                   CASE WHEN d.is_relief_refinance THEN 'relief'
                   WHEN d.is_relief_refinance IS FALSE THEN 'non_relief' ELSE 'unknown' END
                   FROM episodes e JOIN dim_loan d USING(loan_id)
                   ORDER BY e.loan_id,e.confirmation_month,e.event_type"""
        for loan, date, event, segment in db.execute(query).fetchall():
            events[loan].append((date, event, segment))
        cursor = db.execute("""SELECT f.loan_id,f.period,f.delinquency_state,f.terminal_type
                               FROM fact f JOIN (SELECT DISTINCT loan_id FROM episodes) e USING(loan_id)
                               ORDER BY f.loan_id,f.period""")

        def stream():
            while batch := cursor.fetchmany(10000):
                yield from batch

        audited = 0
        for loan, observations in groupby(stream(), lambda row: row[0]):
            months = [row[1:] for row in observations]
            for anchor, event, segment in events[loan]:
                audited += 1
                for horizon in (6, 12):
                    status, observed = audit_followup(anchor, months, horizon)
                    for selected in (segment, "all"):
                        group = aggregated[selected, event, horizon, status]
                        group["events"] += 1
                        group["loans"].add(loan)
                        group["observed_months"] += observed
        if audited != sum(len(group) for group in events.values()):
            raise ValueError("Episode events must reconcile to canonical observation support")
    result = [{"segment": key[0], "event_type": key[1], "horizon_months": key[2], "followup_status": key[3],
               "events": value["events"], "distinct_loans": len(value["loans"]),
               "observed_nonterminal_months_sum": value["observed_months"]}
              for key, value in sorted(aggregated.items())]
    return {"schema_version": 1, "method_version": VERSION, "case_id": manifest["case_id"],
            "pipeline_run": manifest["pipeline_run"], "rows": result, "audited_events": audited,
            "anchor": "actual_confirmation_month_never_backdated",
            "limitations": ["Episode counts are repeated events, not independent loans or cure/redefault probabilities.",
                           "Complete means contiguous known nonterminal observations after confirmation.",
                           "Terminal exits are reported separately; no missing follow-up is filled.",
                           "Distinct loan counts cannot be added across event/status groups."],
            "visibility": "private", "public_release_approved": False}
