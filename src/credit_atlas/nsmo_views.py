"""Verified aggregate-only serving contract for the separate NSMO D02 case."""

from __future__ import annotations

import csv
from pathlib import Path

from .nsmo import _PERFORMANCE_CODES
from .workspace import contained, read_json, sha256


_ROOT = "data/private/mortgage/nsmo-2026-05-27"
_RECEIPTS = "artifacts/private/nsmo-puf-20261015"
_STATE_AUDIT = "artifacts/private/nsmo-performance-state-audit-20261015/receipt.json"
_DOMAIN_AUDIT = "artifacts/private/nsmo-domain-aggregate-audit-20261015/receipt.json"
_TARGET_FEASIBILITY_AUDIT = "artifacts/private/nsmo-target-anchor-vintage-20261016/receipt.json"
_ORIGINATION_FEASIBILITY_AUDIT = "artifacts/private/nsmo-origination-feasibility-20261016/receipt.json"
_FHFA_DISCLAIMER = (
    "The opinions and analyses contained herein are solely of the users/authors "
    "of any data analyses or papers, and the FHFA cannot and does not attest to "
    "nor vouch for the quality, accuracy, or timeliness of the data, or analyses "
    "derived from these data after the data has been retrieved from FHFA.gov."
)
_STATUS_LABELS = {
    "1": "Delinquent: 30–59 days",
    "2": "Delinquent: 60–89 days",
    "3": "Delinquent: 90–119 days",
    "4": "Delinquent: 120–149 days",
    "5": "Delinquent: 150–179 days",
    "6": "Delinquent: 180+ days",
    "7": "Chapter 13 bankruptcy",
    "8": "Foreclosure / distressed disposition",
    "9": "Other adverse / charge-off",
    "A": "History no longer reported",
    "B": "Potentially closed",
    "C": "Current",
    "K": "Opened; performance not yet reported",
    "M": "Missing archive gap",
    "P": "Pre-open",
    "Q": "Opened during quarter",
    "S": "Servicer-suppressed",
}


class NsmoViews:
    """Read the private, hash-bound aggregate receipt and expose no row data."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._cached: tuple[tuple[int, int, int, int], dict] | None = None
        self._dictionary_cache: tuple[tuple[int, int, int, int, int, int, int, int], dict] | None = None

    def dictionary(self) -> dict:
        """Return only the sanitized, public v7.0 codebook/label crosswalk."""
        field_path = contained(self.root, "docs/data/nsmo-v70-field-dictionary.csv")
        labels_path = contained(self.root, "docs/data/nsmo-v70-value-labels.csv")
        coverage_path = contained(self.root, "docs/data/nsmo-v70-wave-coverage.csv")
        item_review_path = contained(self.root, "docs/data/nsmo-v70-wave-item-comparability.csv")
        if not all(path.is_file() for path in (field_path, labels_path, coverage_path, item_review_path)):
            raise ValueError("NSMO public field dictionary failed its v7.0 schema check")
        field_stat, labels_stat, coverage_stat, item_stat = (
            field_path.stat(), labels_path.stat(), coverage_path.stat(), item_review_path.stat())
        identity = (field_stat.st_mtime_ns, field_stat.st_size,
                    labels_stat.st_mtime_ns, labels_stat.st_size,
                    coverage_stat.st_mtime_ns, coverage_stat.st_size,
                    item_stat.st_mtime_ns, item_stat.st_size)
        if self._dictionary_cache and self._dictionary_cache[0] == identity:
            return self._dictionary_cache[1]
        with field_path.open(encoding="utf-8-sig", newline="") as stream:
            fields = list(csv.DictReader(stream))
        with labels_path.open(encoding="utf-8-sig", newline="") as stream:
            value_labels = list(csv.DictReader(stream))
        with coverage_path.open(encoding="utf-8-sig", newline="") as stream:
            wave_coverage = list(csv.DictReader(stream))
        with item_review_path.open(encoding="utf-8-sig", newline="") as stream:
            item_comparability = list(csv.DictReader(stream))
        required_fields = {"csv_column", "codebook_name", "codebook_part", "field_family",
                           "timing_class", "predictor_use", "sas_format", "sas_label"}
        required_labels = {"format_name", "format_value", "format_label"}
        required_coverage = {"csv_column", "observed_response_waves", "entirely_not_asked_waves",
                             "partially_not_asked_waves", "not_applicable_waves"}
        required_item_review = {"field", "assessment"}
        if (len(fields) != 587 or any(not required_fields.issubset(row) for row in fields)
                or len({row["csv_column"].casefold() for row in fields}) != 587
                or any(not required_labels.issubset(row) for row in value_labels)
                or any(not required_coverage.issubset(row) for row in wave_coverage)
                or not item_comparability
                or any(not required_item_review.issubset(row) for row in item_comparability)
                or len({row["field"].casefold() for row in item_comparability}) != len(item_comparability)
                or not {row["field"] for row in item_comparability}.issubset(
                    {row["csv_column"] for row in fields})
                or len(wave_coverage) != sum(row.get("field_family") == "survey_response" for row in fields)
                or {row["csv_column"] for row in wave_coverage}
                    != {row["csv_column"] for row in fields if row.get("field_family") == "survey_response"}):
            raise ValueError("NSMO public field dictionary failed its v7.0 schema check")
        report = {"schema_version": "nsmo-dictionary-v1", "field_count": len(fields),
                  "value_label_count": len(value_labels), "fields": fields,
                  "wave_coverage_count": len(wave_coverage), "wave_coverage": wave_coverage,
                  "item_comparability_count": len(item_comparability),
                  "item_comparability": item_comparability,
                  "value_labels": value_labels}
        self._dictionary_cache = (identity, report)
        return report

    def report(self) -> dict:
        audit_path = contained(self.root, f"{_RECEIPTS}/data-audit.json")
        stat = audit_path.stat()
        receipt_path = contained(self.root, f"{_RECEIPTS}/download-receipt.json")
        audit = read_json(audit_path)
        receipt = read_json(receipt_path)
        if audit.get("status") != "PASS":
            raise ValueError("NSMO aggregate profile is not verified")
        if receipt.get("dataset_release") != "NSMO Public Use File v7.0, page updated 2026-05-27":
            raise ValueError("NSMO release receipt is not the reviewed v7.0 release")
        expected_path = contained(self.root, f"{_ROOT}/puf/nsmo_v70_1324_puf.csv")
        source_stat = expected_path.stat()
        identity = (stat.st_mtime_ns, stat.st_size, source_stat.st_mtime_ns, source_stat.st_size)
        if self._cached and self._cached[0] == identity:
            return self._cached[1]
        expected_sha = receipt.get("csv_sha256")
        if (
            audit.get("csv_sha256") != expected_sha
            or audit.get("csv_bytes") != receipt.get("csv_bytes")
            or source_stat.st_size != receipt.get("csv_bytes")
            or sha256(expected_path) != expected_sha
        ):
            raise ValueError("NSMO PUF no longer matches its acquisition and audit receipts")

        rows = int(audit["row_count"])
        perf = audit["performance"]
        quarters = perf["quarterly_counts"]
        expected_cells = rows * int(perf["column_count"])
        if (
            audit.get("unique_nonblank_nsmoid") != rows
            or audit.get("duplicate_nsmoid_rows") != 0
            or audit.get("blank_nsmoid_rows") != 0
            or audit.get("bad_width_rows") != 0
            or int(perf.get("cell_count", -1)) != expected_cells
            or perf.get("unknown_status_counts")
            or len(quarters) != int(perf["column_count"])
        ):
            raise ValueError("NSMO aggregate audit invariants do not reconcile")

        public_quarters = []
        allowed_codes = set(_PERFORMANCE_CODES)
        for quarter in quarters:
            counts = quarter["status_counts_unweighted"]
            weights = quarter["status_weight_sums_descriptive_only"]
            if set(counts) - allowed_codes or sum(int(value) for value in counts.values()) != rows:
                raise ValueError("NSMO quarter status counts do not reconcile to the source sample")
            public_quarters.append({
                "quarter_end": quarter["quarter_end"],
                "status_counts": {code: int(value) for code, value in counts.items()},
                "status_weight_sums_descriptive_only": {
                    code: float(value) for code, value in weights.items()
                },
            })

        weights = audit["analysis_weight"]
        report = {
            "schema_version": "nsmo-profile-v1",
            "status": "AVAILABLE",
            "visibility": "local_private_research",
            "source": {
                "title": "FHFA/CFPB NSMO Public Use File v7.0",
                "release_date": "2026-05-27",
                "source_url": "https://www.fhfa.gov/data/nsmo",
                "notice_and_terms_url": "https://www.fhfa.gov/data/nsmo/puf",
                "source_sha256": expected_sha,
            },
            "sample": {
                "mortgages": rows,
                "columns": int(audit["column_count"]),
                "unique_nonblank_ids": int(audit["unique_nonblank_nsmoid"]),
                "origination_year_counts": audit["origination_year_counts"],
                "origination_month_counts": audit["origination_month_counts"],
                "survey_wave_counts": audit["survey_wave_counts"],
                "bad_width_rows": int(audit["bad_width_rows"]),
            },
            "analysis_weight": {
                "definition": "FHFA analysis weight (sampling weight × non-response adjustment)",
                "valid_n": int(weights["valid_n"]),
                "missing": int(weights["missing"]),
                "invalid": int(weights["invalid"]),
                "nonpositive": int(weights["nonpositive"]),
                "min": float(weights["min"]),
                "median": float(weights["median"]),
                "max": float(weights["max"]),
                "sum": float(weights["sum"]),
            },
            "performance": {
                "column_count": int(perf["column_count"]),
                "first_quarter_end": perf["first_quarter_end"],
                "last_quarter_end": perf["last_quarter_end"],
                "cell_count": int(perf["cell_count"]),
                "status_codes": [
                    {
                        "code": code,
                        "label": _STATUS_LABELS[code],
                        "family": _PERFORMANCE_CODES[code][0],
                    }
                    for code in sorted(allowed_codes)
                ],
                "quarterly_counts": public_quarters,
            },
            "limitations": [
                "Quarterly status counts use the fixed PUF row count as a descriptive reference, not an at-risk denominator or PD rate.",
                "Weighted status sums are descriptive only and are not event rates, incidence estimates, or PD.",
                "Quarterly snapshots do not establish exact event dates and may miss events between observations.",
                "Status codes for non-observation, pre-open, reporting gaps, history end, and suppression remain distinct from current and delinquent states.",
                "This source has its own sample/response process and is not pooled with Freddie D01 or counted as a Freddie vintage.",
                "No target, model, score, or credit decision is produced.",
            ],
            "required_fhfa_analysis_disclaimer": _FHFA_DISCLAIMER,
        }
        self._cached = (identity, report)
        return report

    def domains(self) -> dict:
        """Serve hash-bound private domain aggregates without any loan rows or IDs."""
        profile = self.report()
        source_sha = profile["source"]["source_sha256"]
        state = read_json(contained(self.root, _STATE_AUDIT))
        domains = read_json(contained(self.root, _DOMAIN_AUDIT))
        rows = int(profile["sample"]["mortgages"])
        for receipt, schema_name in ((state, "schema"), (domains, "schema")):
            if (receipt.get("status") != "PASS"
                    or receipt.get("sources", {}).get("puf_csv", {}).get("sha256") != source_sha
                    or int(receipt.get(schema_name, {}).get("rows", receipt.get(schema_name, {}).get("row_count", -1))) != rows):
                raise ValueError("NSMO domain audit is stale or does not match the verified PUF")
        if domains.get("sources", {}).get("field_dictionary_sha256") != sha256(
                contained(self.root, "docs/data/nsmo-v70-field-dictionary.csv")):
            raise ValueError("NSMO domain audit does not match the public field dictionary")
        source_docs = "data/private/mortgage/nsmo-2026-05-27/source_docs"
        if (domains.get("sources", {}).get("sas_labels_sha256") != sha256(
                    contained(self.root, f"{source_docs}/nsmo_v70_labels.sas"))
                or domains.get("sources", {}).get("sas_formats_sha256") != sha256(
                    contained(self.root, f"{source_docs}/nsmo_v70_formats.sas"))):
            raise ValueError("NSMO domain audit does not match official SAS labels/formats")

        state_rows = state.get("quarterly_state_matrix", [])
        scores = domains.get("quarterly_respondent_scores", [])
        forbearance = domains.get("quarterly_forbearance", [])
        if (len(state_rows) != 51 or len(scores) != 51 or len(forbearance) != 23
                or len(domains.get("origination_attributes", [])) != 30
                or len(domains.get("origination_scores", [])) != 5):
            raise ValueError("NSMO domain series have unexpected v7.0 quarter coverage")
        transitions = []
        for quarter in state_rows[:-1]:
            paired = quarter.get("paired_transition_to_next_quarter")
            if not paired:
                raise ValueError("NSMO transition matrix is incomplete")
            pairs = paired.get("observed_state_transitions", [])
            total = sum(int(item["n"]) for item in pairs)
            from_totals: dict[str, int] = {}
            for item in pairs:
                from_totals[item["from"]] = from_totals.get(item["from"], 0) + int(item["n"])
            transitions.append({
                "from_quarter_end": quarter["quarter_end"],
                "to_quarter_end": paired["next_quarter_end"],
                "all_pair_observation_classes": {
                    key: int(value) for key, value in paired.get("observation_classes", {}).items()
                },
                "observed_to_observed_n": total,
                "transitions": [
                    {"from": item["from"], "to": item["to"], "n": int(item["n"]),
                     "share_of_observed_from_state": int(item["n"]) / from_totals[item["from"]],
                     "weight_sum_descriptive_only": float(item["weight_sum_descriptive_only"])}
                    for item in pairs
                ],
            })

        return {
            "schema_version": "nsmo-domain-profile-v1",
            "status": "AVAILABLE",
            "source_sha256": source_sha,
            "termination": {
                "mortgages": rows,
                "status_labels": state["termination"]["code_labels_from_official_sas_formats"],
                "status_counts": state["termination"]["close_status_counts"],
                "date_consistency": state["termination"]["close_date_consistency"],
                "final_quarter_performance_by_termination": state["termination"]["final_2025q3_performance_by_close_status"],
                "codebook_note_issue": state["termination"]["codebook_note_issue"],
            },
            "origination_scores": domains["origination_scores"],
            "origination_attributes": domains["origination_attributes"],
            "quarterly_respondent_scores": scores,
            "quarterly_forbearance": forbearance,
            "observed_state_transitions": transitions,
            "limitations": domains["limitations"] + state["limitations"],
        }

    def target_feasibility(self) -> dict:
        """Serve source-bound exploratory target-support aggregates, never labels."""
        profile = self.report()
        receipt = read_json(contained(self.root, _TARGET_FEASIBILITY_AUDIT))
        source_sha = profile["source"]["source_sha256"]
        row_count = int(profile["sample"]["mortgages"])
        schema = receipt.get("schema", {})
        if (receipt.get("status") != "PASS"
                or receipt.get("target_created") is not False
                or receipt.get("source", {}).get("sha256") != source_sha
                or int(schema.get("rows", -1)) != row_count
                or int(schema.get("columns", -1)) != 587
                or int(schema.get("quarterly_status_columns", -1)) != 51):
            raise ValueError("NSMO target feasibility receipt is stale or does not match the verified PUF")

        quarter_source = receipt.get("baseline_quarter_state_aggregates", [])
        vintage_source = receipt.get("origination_vintage_baseline_aggregates", [])
        anchor = receipt.get("one_landmark_per_mortgage_support", {})
        anchor_vintages_source = anchor.get("outcomes_by_origination_vintage", [])
        anchor_quarters_source = anchor.get("outcomes_by_landmark_quarter_and_vintage", [])
        if not quarter_source or not vintage_source or not anchor_vintages_source:
            raise ValueError("NSMO target feasibility aggregates are incomplete")
        allowed_results = {
            "four_quarters_observed_no_event", "observed_90plus_event",
            "observed_other_adverse_state_7", "observed_other_adverse_state_8",
            "observed_other_adverse_state_9", "termination_competing_censor",
            "termination_same_month_ambiguous", "observation_censor_M",
            "observation_censor_S", "administratively_short_followup",
            "not_open_at_baseline",
        }

        def safe_counts(values: dict) -> dict[str, int]:
            if not isinstance(values, dict) or set(values) - allowed_results:
                raise ValueError("NSMO target feasibility result codes are invalid")
            result = {str(key): int(value) for key, value in values.items()}
            if any(value < 0 for value in result.values()):
                raise ValueError("NSMO target feasibility counts cannot be negative")
            return result

        quarter_rows = []
        quarter_totals: dict[str, dict[str, int]] = {}
        for item in quarter_source:
            state = str(item.get("baseline_state", ""))
            quarter = str(item.get("baseline_quarter", ""))
            if state not in {"C", "1", "2"} or not quarter:
                raise ValueError("NSMO target feasibility quarter group is invalid")
            raw_counts = dict(item.get("outcomes_unweighted", {}))
            baseline_snapshot_count = int(raw_counts.pop("eligible_snapshot", -1))
            if baseline_snapshot_count < 0:
                raise ValueError("NSMO target feasibility baseline denominator is invalid")
            counts = safe_counts(raw_counts)
            quarter_rows.append({
                "baseline_quarter": quarter,
                "baseline_state": state,
                "full_12m_snapshot_horizon_available": bool(item.get("full_12m_snapshot_horizon_available")),
                "baseline_snapshot_count": baseline_snapshot_count,
                "outcomes_unweighted": counts,
            })
            if item.get("full_12m_snapshot_horizon_available"):
                totals = quarter_totals.setdefault(state, {})
                for code, count in counts.items():
                    totals[code] = totals.get(code, 0) + count

        vintage_rows = []
        vintage_totals: dict[str, dict[str, int]] = {}
        c_unique = 0
        c_unique_outcomes: dict[str, int] = {}
        for item in vintage_source:
            state = str(item.get("baseline_state", ""))
            year = str(item.get("origination_year", ""))
            if state not in {"C", "1", "2"} or not year:
                raise ValueError("NSMO target feasibility vintage group is invalid")
            counts = safe_counts(item.get("full_horizon_baseline_snapshots_unweighted", {}))
            support = safe_counts(item.get("unique_mortgages_by_snapshot_outcome_class_nonexclusive", {}))
            unique_n = int(item.get("unique_mortgages_with_at_least_one_full_horizon_baseline", -1))
            if unique_n < 0 or unique_n > row_count or any(value > unique_n for value in support.values()):
                raise ValueError("NSMO target feasibility unique-loan support is invalid")
            vintage_rows.append({
                "origination_year": year,
                "baseline_state": state,
                "full_horizon_baseline_snapshots_unweighted": counts,
                "unique_mortgages_with_at_least_one_full_horizon_baseline": unique_n,
                "unique_mortgages_by_snapshot_outcome_class_nonexclusive": support,
            })
            totals = vintage_totals.setdefault(state, {})
            for code, count in counts.items():
                totals[code] = totals.get(code, 0) + count
            if state == "C":
                c_unique += unique_n
                for code, count in support.items():
                    c_unique_outcomes[code] = c_unique_outcomes.get(code, 0) + count
        if quarter_totals != vintage_totals:
            raise ValueError("NSMO target feasibility quarter and vintage totals do not reconcile")

        anchor_vintages = []
        anchor_totals: dict[str, int] = {}
        anchor_loan_count = 0
        for item in anchor_vintages_source:
            year = str(item.get("origination_year", ""))
            count = int(item.get("unique_mortgage_count", -1))
            outcomes = safe_counts(item.get("first_eligible_c_landmark_outcomes_unweighted", {}))
            if not year or count < 0 or sum(outcomes.values()) != count or count > row_count:
                raise ValueError("NSMO one-landmark support is invalid")
            anchor_vintages.append({"origination_year": year, "unique_mortgage_count": count,
                                    "outcomes_unweighted": outcomes})
            anchor_loan_count += count
            for code, value in outcomes.items():
                anchor_totals[code] = anchor_totals.get(code, 0) + value
        if anchor_loan_count != c_unique:
            raise ValueError("NSMO one-landmark cohort does not reconcile to unique C-landmark support")

        anchor_quarters = []
        anchor_quarter_totals: dict[str, int] = {}
        for item in anchor_quarters_source:
            year = str(item.get("origination_year", ""))
            quarter = str(item.get("landmark_quarter", ""))
            count = int(item.get("unique_mortgage_count", -1))
            outcomes = safe_counts(item.get("outcomes_unweighted", {}))
            if not year or not quarter or count < 0 or sum(outcomes.values()) != count:
                raise ValueError("NSMO one-landmark quarter group is invalid")
            anchor_quarters.append({"origination_year": year, "landmark_quarter": quarter,
                                    "unique_mortgage_count": count, "outcomes_unweighted": outcomes})
            for code, value in outcomes.items():
                anchor_quarter_totals[code] = anchor_quarter_totals.get(code, 0) + value
        if anchor_quarter_totals != anchor_totals:
            raise ValueError("NSMO one-landmark quarter and vintage totals do not reconcile")

        return {
            "schema_version": "nsmo-target-feasibility-v1",
            "status": "AVAILABLE",
            "source_sha256": source_sha,
            "target_created": False,
            "candidate_definition": receipt.get("candidate_definition_for_feasibility_only", {}),
            "repeated_landmarks": {
                "quarter_state_rows": quarter_rows,
                "origination_vintage_rows": vintage_rows,
                "c_state_summary": {
                    "unique_mortgages_with_at_least_one_full_horizon_baseline": c_unique,
                    "unique_mortgages_by_snapshot_outcome_class_nonexclusive": c_unique_outcomes,
                },
            },
            "one_landmark_per_mortgage": {
                "selection_rule": anchor.get("selection_rule", ""),
                "origination_vintage_rows": anchor_vintages,
                "landmark_quarter_vintage_rows": anchor_quarters,
                "summary": {"unique_mortgages": anchor_loan_count, "outcomes_unweighted": anchor_totals},
            },
            "limitations": [
                "Exploratory feasibility counts only; this API creates no target labels, rates, PD, or model matrix.",
                "Repeated quarterly landmarks are not independent; unique-outcome supports may overlap between classes.",
                "Code 3–6 means 90+ days past due observed at a quarterly snapshot, not a dated default event.",
                "Same-month closure ordering is unknown; termination and M/S gaps are retained as distinct outcomes/censoring.",
                "Analysis weights are not used to compute rates or uncertainty; no survey variance method is specified.",
            ],
        }

    def origination_feasibility(self) -> dict:
        """Serve source-bound origination-window support aggregates only."""
        profile = self.report()
        receipt = read_json(contained(self.root, _ORIGINATION_FEASIBILITY_AUDIT))
        source_sha = profile["source"]["source_sha256"]
        row_count = int(profile["sample"]["mortgages"])
        schema = receipt.get("schema", {})
        reconciliation = receipt.get("reconciliation", {})
        if (receipt.get("status") != "PASS"
                or receipt.get("target_created") is not False
                or receipt.get("source", {}).get("sha256") != source_sha
                or int(schema.get("rows", -1)) != row_count
                or int(schema.get("columns", -1)) != 587
                or int(schema.get("quarterly_status_columns", -1)) != 51
                or reconciliation.get("reconciles") is not True
                or int(reconciliation.get("classified_rows", -1)) != row_count
                or int(reconciliation.get("origination_vintage_rows", -1)) != row_count):
            raise ValueError("NSMO origination feasibility receipt is stale or does not match the verified PUF")

        allowed_results = {
            "observed_90plus", "all_in_window_snapshots_observed_no_90plus",
            "observed_other_adverse_state_7", "observed_other_adverse_state_8",
            "observed_other_adverse_state_9", "termination_competing_censor",
            "termination_same_month_ambiguous", "observation_censor_K",
            "observation_censor_M", "observation_censor_S",
            "administratively_short_followup",
        }

        def checked_counts(value: object) -> dict[str, int]:
            if not isinstance(value, dict) or set(value) - allowed_results:
                raise ValueError("NSMO origination feasibility result codes are invalid")
            counts = {str(code): int(count) for code, count in value.items()}
            if any(count < 0 for count in counts.values()):
                raise ValueError("NSMO origination feasibility counts cannot be negative")
            return counts

        overall = checked_counts(receipt.get("outcomes_unweighted"))
        vintage_source = receipt.get("outcomes_by_origination_year_unweighted")
        quarter_source = receipt.get("available_snapshot_count_by_origination_year_unweighted")
        if not isinstance(vintage_source, dict) or not isinstance(quarter_source, dict):
            raise ValueError("NSMO origination feasibility vintage aggregates are incomplete")
        if sum(overall.values()) != row_count or set(vintage_source) != set(quarter_source):
            raise ValueError("NSMO origination feasibility aggregates do not reconcile to the PUF")

        vintage_rows = []
        vintage_totals: dict[str, int] = {}
        for year, values in sorted(vintage_source.items()):
            if not str(year).isdigit() or not isinstance(values, dict):
                raise ValueError("NSMO origination feasibility vintage key is invalid")
            counts = checked_counts(values)
            if sum(counts.values()) != sum(int(v) for v in quarter_source[year].values()):
                raise ValueError("NSMO origination feasibility vintage snapshot support does not reconcile")
            for code, count in counts.items():
                vintage_totals[code] = vintage_totals.get(code, 0) + count
            vintage_rows.append({"origination_year": str(year), "outcomes_unweighted": counts})
        if vintage_totals != overall:
            raise ValueError("NSMO origination feasibility vintage totals do not reconcile")

        return {
            "schema_version": "nsmo-origination-feasibility-v1",
            "status": "AVAILABLE",
            "source_sha256": source_sha,
            "target_created": False,
            "candidate_definition": receipt.get("candidate_definition_for_feasibility_only", {}),
            "outcomes_unweighted": overall,
            "outcomes_by_origination_year": vintage_rows,
            "limitations": [
                "Exploratory support counts only; no target labels, rates, PD, or model matrix are created.",
                "The opening quarter is excluded because code Q means the mortgage opened during that quarter.",
                "Origination month has no day; quarterly snapshots can miss events between reports.",
                "No observed 90+ snapshot is not proof that no delinquency event occurred.",
                "Termination cause is unknown and same-month snapshot ordering is ambiguous.",
                "Counts are unweighted; no design-based variance or population rate is available.",
            ],
        }
