"""Audit event-occurrence, unique-loan and follow-up denominators for D01."""
import json
import uuid
from collections import defaultdict
from pathlib import Path

import duckdb

from credit_atlas.workspace import sha256, timestamp, write_new

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "artifacts/private/d01-a24484b21a21"
FOLLOWUP_PATH = ROOT / "artifacts/private/episode-followup-20261008.json"


def run():
    case = json.loads((CASE / "case-complete.json").read_text(encoding="utf-8"))
    snapshot_path = CASE / "snapshot.json"
    if sha256(snapshot_path) != case["outputs_sha256"]["snapshot.json"]:
        raise ValueError("Frozen D01 snapshot failed case receipt verification")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    episode_input = next(item for item in case["verified_inputs"]
                         if Path(item["path"]).name == "episodes.parquet")
    episode_path = ROOT / Path(episode_input["path"])
    canonical_path = ROOT / case["canonical_run"] / "dim_loan.parquet"
    if sha256(episode_path) != episode_input["sha256"]:
        raise ValueError("Episode source hash changed")
    followup = json.loads(FOLLOWUP_PATH.read_text(encoding="utf-8"))
    if (followup.get("case_id") != case["case_id"]
            or followup.get("pipeline_run") != case["pipeline_run"]):
        raise ValueError("Follow-up projection belongs to a different case/run")
    con = duckdb.connect()
    try:
        summary_rows = con.execute("""
          WITH by_loan AS (
            SELECT event_type, loan_id, COUNT(*) AS occurrences
            FROM read_parquet(?) GROUP BY event_type, loan_id
          )
          SELECT event_type, SUM(occurrences)::BIGINT AS event_rows,
                 COUNT(*)::BIGINT AS distinct_loans,
                 MAX(occurrences)::BIGINT AS max_events_per_loan,
                 COUNT(*) FILTER (WHERE occurrences > 1)::BIGINT AS loans_with_repeat,
                 SUM(occurrences - 1)::BIGINT AS repeat_event_rows
          FROM by_loan GROUP BY event_type ORDER BY event_type
        """, [str(episode_path)]).fetchall()
        segment_rows = con.execute("""
          WITH by_loan AS (
            SELECT CASE WHEN d.is_relief_refinance THEN 'relief' ELSE 'non_relief' END AS segment,
                   e.event_type, e.loan_id, COUNT(*) AS occurrences
            FROM read_parquet(?) e JOIN read_parquet(?) d USING (loan_id)
            GROUP BY 1, 2, 3
          )
          SELECT segment, event_type, SUM(occurrences)::BIGINT AS event_rows,
                 COUNT(*)::BIGINT AS distinct_loans,
                 MAX(occurrences)::BIGINT AS max_events_per_loan,
                 SUM(occurrences - 1)::BIGINT AS repeat_event_rows
          FROM by_loan GROUP BY segment, event_type ORDER BY segment, event_type
        """, [str(episode_path), str(canonical_path)]).fetchall()
    finally:
        con.close()
    all_summary = {row[0]: dict(zip(("event_type", "event_rows", "distinct_loans",
                                   "max_events_per_loan", "loans_with_repeat", "repeat_event_rows"), row))
                   for row in summary_rows}
    segment_summary = {(row[0], row[1]): dict(zip(("segment", "event_type", "event_rows",
                                                  "distinct_loans", "max_events_per_loan",
                                                  "repeat_event_rows"), row)) for row in segment_rows}
    notes = snapshot["episode_notes"]["episode_events"]
    if sum(row["event_rows"] for row in all_summary.values()) != 4902:
        raise ValueError("Unexpected event-occurrence total")
    for event_type, summary in all_summary.items():
        if summary["event_rows"] != notes[event_type]:
            raise ValueError(f"Snapshot event count does not reconcile: {event_type}")
        segment_count = sum(segment_summary[(segment, event_type)]["event_rows"]
                            for segment in ("relief", "non_relief"))
        segment_loans = sum(segment_summary[(segment, event_type)]["distinct_loans"]
                            for segment in ("relief", "non_relief"))
        if segment_count != summary["event_rows"] or segment_loans != summary["distinct_loans"]:
            raise ValueError(f"Exclusive segments do not reconcile: {event_type}")
    followup_checks = []
    for segment in ("all", "relief", "non_relief"):
        for event_type, total in sorted(all_summary.items()):
            segment_total = total["event_rows"] if segment == "all" else segment_summary[(segment, event_type)]["event_rows"]
            for horizon in (6, 12):
                rows = [row for row in followup["rows"] if row["segment"] == segment
                        and row["event_type"] == event_type and row["horizon_months"] == horizon]
                status_events = sum(row["events"] for row in rows)
                if status_events != segment_total:
                    raise ValueError(f"Follow-up statuses fail event denominator: {segment}/{event_type}/{horizon}")
                followup_checks.append({"segment": segment, "event_type": event_type,
                                        "horizon_months": horizon, "denominator_event_rows": segment_total,
                                        "status_event_rows_sum": status_events,
                                        "status_groups": len(rows),
                                        "distinct_loans_summed_across_statuses": sum(row["distinct_loans"] for row in rows)})
    audit = {
        "created_at": timestamp(), "case_id": case["case_id"], "pipeline_run": case["pipeline_run"],
        "method_version": followup["method_version"],
        "sources": {"case_receipt_sha256": sha256(CASE / "case-complete.json"),
                    "snapshot_sha256": sha256(snapshot_path),
                    "episode_parquet_sha256": sha256(episode_path),
                    "followup_projection_sha256": sha256(FOLLOWUP_PATH)},
        "grain_contract": {
            "event_rows": "confirmed episode occurrences; repeated cure/redefault events are retained",
            "distinct_loans": "unique loans within exactly one event_type/segment; not additive across event types",
            "followup_denominator": "all confirmed event rows for the same event_type/segment/horizon, partitioned once by observed support status",
            "probability_status": "no event rate or probability is calculated; follow-up completeness is support, not a no-redefault outcome",
        },
        "event_counts": list(all_summary.values()),
        "segment_counts": list(segment_summary.values()),
        "followup_denominator_checks": followup_checks,
        "totals": {"event_rows": sum(row["event_rows"] for row in all_summary.values()),
                   "unique_loans_with_any_event": conclusive_unique_loans(episode_path),
                   "followup_denominator_checks": len(followup_checks),
                   "all_status_partitions_exact": True},
        "limitations": ["Single origination vintage 2012.",
                        "No cure or redefault probabilities are estimated.",
                        "Repeated events from the same loan are dependent and event/loan denominators differ."],
    }
    output = ROOT / "artifacts/private" / ("d01-episode-denominators-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output / "audit.json", audit)
    write_new(output / "receipt.json", {"status": "PASS", "audit": str((output / "audit.json").relative_to(ROOT)),
              "audit_sha256": sha256(output / "audit.json"), "event_rows": audit["totals"]["event_rows"],
              "unique_loans_with_any_event": audit["totals"]["unique_loans_with_any_event"],
              "followup_denominator_checks": len(followup_checks), "source_loan_ids_exposed": False})
    return {"output": str(output), "totals": audit["totals"],
            "event_counts": [{"type": row["event_type"], "events": row["event_rows"],
                              "loans": row["distinct_loans"], "repeat_rows": row["repeat_event_rows"]}
                             for row in all_summary.values()]}


def conclusive_unique_loans(episode_path):
    con = duckdb.connect()
    try:
        return con.execute("SELECT COUNT(DISTINCT loan_id) FROM read_parquet(?)",
                           [str(episode_path)]).fetchone()[0]
    finally:
        con.close()


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
