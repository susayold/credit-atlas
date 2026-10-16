"""Read verified frozen cases and expose bounded private application views."""
from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from pathlib import Path

import duckdb

from .reviews import Reviews
from .snapshot import TARGET, json_ready, rows
from .workspace import completed_cases, contained, engine_root, load_engine, read_json, sha256

CASE_PATTERN = re.compile(r"d01-[0-9a-f]{12}\Z")
TOKEN_PATTERN = re.compile(r"[0-9a-f]{24}\Z")
MONTH_PATTERN = re.compile(r"\d{4}-(?:0[1-9]|1[0-2])\Z")
_SERVING_SOURCES = {
    name: {"path": Path(__file__).parent / (name + ".py"),
           "sha256": sha256(Path(__file__).parent / (name + ".py"))}
    for name in ["service", "monitoring", "episode_followup", "period_transitions", "study_registry", "study_features", "assessment", "snapshot", "workspace", "reviews", "server", "suite_snapshot"]}


def filters_from(query: dict) -> dict:
    filters = {"segment": query.get("segment", "all"), "basis": query.get("basis", "count"),
               "horizon": query.get("horizon", "12"), "from": query.get("from", ""), "to": query.get("to", ""),
               "transition_year": query.get("transition_year", "all")}
    if not isinstance(filters["transition_year"], str) or not re.fullmatch(r"all|(?:19|20)\d{2}", filters["transition_year"]):
        raise ValueError("Transition year must be all or a reporting year")
    if filters["segment"] not in {"all", "relief", "non_relief", "unknown"}:
        raise ValueError("Unsupported segment")
    if filters["basis"] not in {"count", "balance"} or filters["horizon"] not in {"6", "12", "24"}:
        raise ValueError("Unsupported metric basis or horizon")
    if any(value and not MONTH_PATTERN.fullmatch(value) for value in [filters["from"], filters["to"]]):
        raise ValueError("Reporting range must use YYYY-MM")
    if filters["from"] and filters["to"] and filters["from"] > filters["to"]:
        raise ValueError("Reporting range is reversed")
    return filters


class EvidenceChanged(ValueError):
    pass


class ResearchService:
    def __init__(self, root: Path, *, review_path: Path | None = None):
        self.root = root.resolve()
        self.upstream = load_engine(self.root)
        selected_review_path = review_path or self.root / "artifacts/private/reviews.sqlite3"
        if not selected_review_path.resolve().is_relative_to(self.root / "artifacts/private"):
            raise ValueError("Review storage must remain in the private workspace")
        self.reviews = Reviews(selected_review_path)
        self.cache = {}
        self._supplement_locks = {
            "episode_followup": threading.RLock(),
            "period_transitions": threading.RLock(),
        }
        self.method_sources = copy.deepcopy(_SERVING_SOURCES)
        from .suite_snapshot import SuiteViews
        self.suite_views = SuiteViews(self.root)
        from .bank_views import BankViews
        self.bank_views = BankViews(self.root)
        from .market_views import MarketViews
        self.market_views = MarketViews(self.root)
        from .bankruptcy_views import BankruptcyViews
        self.bankruptcy_views = BankruptcyViews(self.root)
        from .bankruptcy_model_views import BankruptcyModelViews
        self.bankruptcy_model_views = BankruptcyModelViews(self.root)
        from .country_views import CountryViews
        self.country_views = CountryViews(self.root)
        from .sec_views import SecViews
        self.sec_views = SecViews(self.root)
        from .abs_views import AbsViews
        self.abs_views = AbsViews(self.root)
        from .hmda_views import HmdaViews
        self.hmda_views = HmdaViews(self.root)
        from .hmda_national_views import HmdaNationalViews
        self.hmda_national_views = HmdaNationalViews(self.root)
        from .hmda_reference_views import HmdaReferenceViews
        self.hmda_reference_views = HmdaReferenceViews(self.root, self.hmda_views)
        from .hmda_cohort_views import HmdaCohortViews
        self.hmda_cohort_views = HmdaCohortViews(self.root, self.hmda_views)
        from .exposure_views import ExposureViews
        self.exposure_views = ExposureViews(self.root)
        from .exposure_movement_views import ExposureMovementViews
        self.exposure_movement_views = ExposureMovementViews(self.root)
        from .exposure_scenario_views import ExposureScenarioViews
        self.exposure_scenario_views = ExposureScenarioViews(self.root)
        from .exposure_ecl_views import ExposureEclViews
        self.exposure_ecl_views = ExposureEclViews(self.root)
        from .exposure_tail_views import ExposureTailViews
        self.exposure_tail_views = ExposureTailViews(self.root)
        from .exposure_convergence_views import ExposureConvergenceViews
        self.exposure_convergence_views = ExposureConvergenceViews(self.root)
        from .portfolio_reviews import PortfolioReviews
        self.portfolio_reviews = PortfolioReviews(self, selected_review_path.with_name(selected_review_path.stem+'-portfolio.sqlite3'))
        from .excel_workbench import ExcelWorkbench
        self.excel_workbench = ExcelWorkbench(self)
        from .retail_policy_views import RetailPolicyViews
        self.retail_policy_views = RetailPolicyViews(self.root)
        from .retail_subgroup_views import RetailSubgroupViews
        self.retail_subgroup_views = RetailSubgroupViews(self.root)
        from .retail_explanation_views import RetailExplanationViews
        self.retail_explanation_views = RetailExplanationViews(self.root)
        from .retail_cohort_explanation_views import RetailCohortExplanationViews
        self.retail_cohort_explanation_views = RetailCohortExplanationViews(self.root)

    def case(self, case_id: str):
        if not isinstance(case_id, str) or not CASE_PATTERN.fullmatch(case_id):
            raise ValueError("Invalid case ID")
        for method in self.method_sources.values():
            if sha256(method["path"]) != method["sha256"]:
                raise EvidenceChanged("Serving method changed; restart with reviewed code")
        path = self.root / "artifacts/private" / case_id
        complete_path = path / "case-complete.json"
        if not complete_path.is_file():
            raise KeyError("Completed case not found")
        complete_hash = sha256(complete_path)
        if case_id in self.cache:
            cached = self.cache[case_id]
            if complete_hash != cached["complete_hash"]:
                raise EvidenceChanged("Frozen case receipt changed")
            for relative, expected_stat in cached["stats"].items():
                file = contained(self.root, relative)
                stat = file.stat()
                if (stat.st_size, stat.st_mtime_ns) != expected_stat:
                    raise EvidenceChanged("Frozen case evidence changed")
            # Hash the small serving contracts even if timestamps were preserved.
            for name in ["snapshot.json", "report.json"]:
                if sha256(path / name) != cached["manifest"]["outputs_sha256"][name]:
                    raise EvidenceChanged("Serving contract changed")
            return cached
        manifest = read_json(complete_path)
        if (manifest.get("status") != "D01_DESCRIPTIVE_COMPLETE" or
                manifest.get("case_id") != case_id or
                manifest.get("target_version") != TARGET["version"] or
                manifest.get("visibility") != "private" or
                manifest.get("public_release_approved") is not False or
                manifest.get("engine_commit") != self.upstream["commit"]):
            raise ValueError("Private verified case from the pinned engine is required")
        if not {"snapshot.json", "report.json", "loan-index.parquet", "foundation-complete.json"}.issubset(manifest["outputs_sha256"]):
            raise ValueError("Complete private serving artifact digests are required")
        tracked = {}
        expected = manifest["verified_inputs"] + [
            {"path": str((path / name).relative_to(self.root)), "sha256": digest}
            for name, digest in manifest["outputs_sha256"].items()]
        for item in expected:
            file = contained(self.root, item["path"])
            if sha256(file) != item["sha256"]:
                raise EvidenceChanged("Frozen evidence hash mismatch")
            stat = file.stat()
            tracked[item["path"]] = (stat.st_size, stat.st_mtime_ns)
        snapshot = read_json(path / "snapshot.json")
        report = read_json(path / "report.json")
        if (snapshot["case_id"] != case_id or snapshot["pipeline_run"] != manifest["pipeline_run"] or
                snapshot["target"] != TARGET or snapshot["visibility"] != "private" or
                report["pipeline_run"] != manifest["pipeline_run"]):
            raise ValueError("Case, target and report lineage must match")
        cached = {"path": path, "manifest": manifest, "snapshot": snapshot,
                  "report": report, "stats": tracked, "complete_hash": complete_hash}
        self.cache[case_id] = cached
        return cached

    def runs(self):
        result = []
        for path, manifest in completed_cases(self.root):
            try:
                snapshot = self.case(path.name)["snapshot"]
                result.append({"case_id": path.name, "completed_at": manifest["completed_at"],
                              "source_years": snapshot["source_years"], "source_release": snapshot["source_release"],
                              "loans": snapshot["snapshot"]["loans"], "loan_months": snapshot["snapshot"]["monthly_rows"],
                              "descriptive_status": "verified_rebuild",
                              "model_status": snapshot["model_readiness"]["status"]})
            except (OSError, ValueError, KeyError):
                result.append({"case_id": path.name, "descriptive_status": "evidence_unavailable_or_changed"})
        return {"module_id": "P2", "workspaces": [{"id": "P2", "state": "implemented_descriptive"},
                *[{"id": name, "state": "planned"} for name in ["P1", "P3", "P4", "P5"]]], "runs": result}

    def snapshot(self, case_id):
        return copy.deepcopy(self.case(case_id)["snapshot"])

    def monitoring(self, case_id):
        from .monitoring import build
        return build(self.case(case_id)["snapshot"])

    def fhfa_nmdb_performance(self):
        from .nmdb_aggregate import read
        return read(self.root)

    def cfpb_mortgage_trends(self, query=None):
        from .cfpb_mortgage_trends import read
        return read(self.root, query)

    def fhfa_pudb_profile(self):
        from .fhfa_pudb import read
        return read(self.root)

    def hud_fha_iif_profile(self):
        from .hud_fha_iif import read
        return read(self.root)

    def studies(self, case_id):
        from .study_registry import list_studies
        return list_studies(self, case_id)

    def episode_followup(self, case_id):
        from .episode_followup import build
        with self._supplement_locks["episode_followup"]:
            case = self.case(case_id)
            if "episode_followup" not in case:
                case["episode_followup"] = build(self.root, case)
            return copy.deepcopy(case["episode_followup"])

    def period_transitions(self, case_id):
        from .period_transitions import build
        with self._supplement_locks["period_transitions"]:
            case = self.case(case_id)
            if "period_transitions" not in case:
                projection = build(self.root, case)
                self.case(case_id)
                case["period_transitions"] = projection
            return copy.deepcopy(case["period_transitions"])

    def report(self, case_id, query):
        case = self.case(case_id)
        snapshot = case["snapshot"]
        allowed = {"run", "segment", "basis", "horizon", "from", "to", "transition_year"}
        if not isinstance(query, dict) or set(query) - allowed:
            raise ValueError("Unsupported report parameter")
        if "run" in query and query["run"] != case_id:
            raise ValueError("Report run must match the selected case")
        filters = filters_from({key: value for key, value in query.items() if key != "run"})
        result = copy.deepcopy(case["report"])
        selected = filters["segment"]
        for table in result["tables"]:
            name = table["table_id"]
            applied = []
            if name == "portfolio_monthly":
                table["rows"] = copy.deepcopy(snapshot["snapshot"]["monthly"] if selected == "all" else
                                              snapshot["monthly_by_segment"].get(selected, []))
                table["rows"] = [r for r in table["rows"] if
                    (not filters["from"] or r["period"][:7] >= filters["from"]) and
                    (not filters["to"] or r["period"][:7] <= filters["to"])]
                applied = ["segment", "reporting_month_range"]
            elif name in {"portfolio_profile", "segmented_transitions", "vintage_competing_risk"}:
                table["rows"] = [r for r in table["rows"] if selected == "all" or r.get("segment") == selected]
                applied = ["segment"]
                if name == "vintage_competing_risk":
                    table["rows"] = [r for r in table["rows"] if r["observation_age"] == int(filters["horizon"])]
                    if selected == "all":
                        table["rows"] = [r for r in table["rows"] if r["segment"] == "all"]
                    applied.append("horizon")
            elif name == "state_transitions" and selected != "all":
                table["rows"] = []
                table["not_applicable_reason"] = "Use segmented_transitions for segment-filtered matrices."
            elif name == "label_outcomes" and selected != "all":
                table["rows"] = [{"outcome": r["outcome"], "loans": r["loans"]} for r in snapshot["segment_outcomes"] if r["segment"] == selected]
                applied = ["segment"]
            table["filters_applied"] = applied
        monitoring = self.monitoring(case_id)
        followup = self.episode_followup(case_id)
        periods = self.period_transitions(case_id)
        if any(value["case_id"] != case_id or value["pipeline_run"] != snapshot["pipeline_run"]
               for value in (monitoring, followup, periods)):
            raise ValueError("Supplemental evidence must belong to the selected case and pipeline")
        followup["rows"] = [r for r in followup["rows"] if r["segment"] == selected]
        followup["filter_context"] = {"segment": selected, "horizons_months": [6, 12]}
        followup["filters_applied"] = ["segment"]
        followup["scope_note"] = "Both 6/12m confirmation-based horizons; reporting date range and vintage horizon do not apply."
        monitoring["filters_applied"] = []
        year = filters["transition_year"]
        periods["rows"] = [r for r in periods["rows"] if r["segment"] == selected
                           and (year == "all" or r["reporting_year"] == int(year))]
        periods["lifetime_rows"] = [r for r in periods["lifetime_rows"] if r["segment"] == selected]
        periods["filters_applied"] = ["segment", "transition_year"]
        periods["filter_context"] = {"segment": selected, "transition_year": year}
        periods["scope_note"] = "Year filter applies only to rows; lifetime_rows retain the selected segment's whole-period comparator."
        supplemental = {"quality_monitoring": monitoring, "episode_followup": followup,
                        "period_transitions": periods}
        supplemental_digests = {
            name: hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
            for name, value in supplemental.items()}
        from crsl.reporting.export import _assert_safe
        package = {"schema_version": 2, "case_id": case_id, "target": snapshot["target"],
                "filter_context": filters, "report": result,
                "supplemental_evidence": supplemental,
                "supplemental_sha256": supplemental_digests,
                "lineage": {"pipeline_run": snapshot["pipeline_run"],
                            "case_receipt_sha256": case["complete_hash"],
                            "source_output_sha256": copy.deepcopy(case["manifest"]["outputs_sha256"]),
                            "method_source_sha256": {name: value["sha256"]
                                                    for name, value in self.method_sources.items()}},
                "scope_notes": {"monthly_range": "Applies only to portfolio_monthly.",
                                "loss": "Whole-sample observed loss; no segment filter is implied.",
                                "transitions": "Lifetime adjacent observed pairs, not the monthly-chart date range.",
                                "period_transitions": "Selected segment and opening reporting year; lifetime comparator remains whole-period. Date range and vintage horizon do not apply.",
                                "monitoring": "Whole frozen source sample; no segment or reporting-date filter.",
                                "episode_followup": "Selected segment; both 6/12m horizons after actual confirmation. Not cure/redefault probabilities."},
                "visibility": "private", "public_release_approved": False}
        _assert_safe(package)
        return package

    def evidence(self, case_id):
        case = self.case(case_id)
        receipt = case["manifest"]
        return {"case_id": case_id, "pipeline_run": receipt["pipeline_run"],
                "engine_commit": receipt["engine_commit"], "raw_sha256": receipt["raw_sha256"],
                "target_version": receipt["target_version"], "completed_at": receipt["completed_at"],
                "visibility": receipt["visibility"], "public_release_approved": False,
                "artifacts": [{"artifact": Path(item["path"]).parent.name + "/" + Path(item["path"]).name, "sha256": item["sha256"]}
                              for item in receipt["verified_inputs"]],
                "resource_measurement": read_json(case["path"] / "foundation-complete.json")["resource_measurement"],
                "review_kind": "research_review_not_credit_approval"}

    def loans(self, case_id, query):
        case = self.case(case_id)
        segment = query.get("segment", "all")
        if segment not in {"all", "relief", "non_relief", "unknown"}:
            raise ValueError("Unsupported loan segment")
        outcome = query.get("outcome", "all")
        if outcome not in {"all", "positive", "negative", "unavailable"}:
            raise ValueError("Unsupported endpoint filter")
        prefix = query.get("q", "").strip().lower()
        if prefix and not re.fullmatch(r"[0-9a-f]{3,24}", prefix):
            raise ValueError("Use a 3–24 character private loan-key prefix")
        limit = int(query.get("limit", "20"))
        if not 1 <= limit <= 50:
            raise ValueError("Loan page limit must be 1–50")
        predicates, parameters = [], []
        if segment != "all":
            predicates.append("segment=?")
            parameters.append(segment)
        if outcome == "unavailable":
            predicates.append("target IS NULL")
        elif outcome != "all":
            predicates.append("target=?")
            parameters.append(1 if outcome == "positive" else 0)
        if prefix:
            predicates.append("loan_key LIKE ?")
            parameters.append(prefix + "%")
        where = " WHERE " + " AND ".join(predicates) if predicates else ""
        with duckdb.connect() as db:
            db.read_parquet(str(case["path"] / "loan-index.parquet")).create_view("loan_index")
            count = db.execute("SELECT COUNT(*) FROM loan_index" + where, parameters).fetchone()[0]
            result = rows(db, "SELECT loan_key,origination_year,segment,classic_fico,original_ltv,outcome FROM loan_index" + where + " ORDER BY loan_key LIMIT ?", parameters + [limit])
        return {"case_id": case_id, "visibility": "private", "total_matching": count,
                "limit": limit, "rows": result, "identifier_kind": "run_scoped_pseudonymous_key"}

    def timeline(self, case_id, loan_key):
        if not TOKEN_PATTERN.fullmatch(loan_key):
            raise ValueError("Invalid private loan key")
        case = self.case(case_id)
        manifest = case["manifest"]
        with duckdb.connect() as db:
            db.execute("SET memory_limit='1GB'")
            db.execute("SET threads=2")
            db.read_parquet(str(case["path"] / "loan-index.parquet")).create_view("loan_index")
            raw = db.execute("SELECT loan_id FROM loan_index WHERE loan_key=?", [loan_key]).fetchone()
            if raw is None:
                raise KeyError("Private loan key not found in this run")
            raw_id = raw[0]
            for table, run in [("dim_loan", manifest["canonical_run"]), ("fact_loan_month", manifest["canonical_run"]),
                               ("labels", manifest["label_run"]), ("episodes", manifest["portfolio_run"])]:
                db.read_parquet(str(contained(self.root, run) / (table + ".parquet"))).create_view(table)
            static = rows(db, """SELECT origination_year,classic_fico,original_dti,original_ltv,original_cltv,
                original_upb,original_term,original_interest_rate,occupancy,loan_purpose,property_type,
                first_payment_date,is_relief_refinance,is_harp_subset FROM dim_loan WHERE loan_id=?""", [raw_id])[0]
            label = rows(db, """SELECT landmark,horizon_end,eligibility_reason,outcome,target,label_known_month
                FROM labels WHERE loan_id=?""", [raw_id])[0]
            monthly = rows(db, """SELECT period,delinquency_state,terminal_type,current_upb,current_rate,
                loan_age,modification,assistance,payment_deferral
                FROM fact_loan_month WHERE loan_id=? ORDER BY period""", [raw_id])
            events = rows(db, "SELECT confirmation_month,event_type FROM episodes WHERE loan_id=? ORDER BY confirmation_month,event_type", [raw_id])
        return json_ready({"case_id": case_id, "loan_key": loan_key, "visibility": "private",
                           "target_version": TARGET["version"], "static": static, "label": label,
                           "months": monthly, "events": events,
                           "limitation": "Source-based retrospective timeline; no model prediction or treatment effect."})
