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
_FIRST_OBSERVED_TRANSITION_AUDIT = "artifacts/private/nsmo-first-observed-transition-support-20261016/receipt.json"
_SURVEY_RETURNS_CSV = "docs/data/nsmo-v70-survey-returns.csv"
_SURVEY_RETURNS_SHA256 = "d34d6c14ec0febb0a5c1d60c46c9dadc49e58e2121e0ed3b65140bb7c0da0811"
_USABLE_RESPONSES_CSV = "docs/data/nsmo-v70-usable-responses.csv"
_USABLE_RESPONSES_SHA256 = "a3c96a3db82e8ff24d90a6fea365d6c2933012b2ff23bc23c0c5c19cdb17ef23"
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

    def survey_returns(self) -> dict:
        """Return FHFA's public, wave-level survey return counts, never loan rows."""
        path = contained(self.root, _SURVEY_RETURNS_CSV)
        if not path.is_file() or sha256(path) != _SURVEY_RETURNS_SHA256:
            raise ValueError("NSMO survey-return table does not match the reviewed FHFA v7.0 extraction")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            source_rows = list(csv.DictReader(stream))
        required = {
            "survey_wave", "average_sampling_weight", "surveys_mailed", "postal_nondelivery",
            "surveys_delivered", "surveys_completed_total", "completed_by_mail", "online_english",
            "online_spanish", "opt_out", "completion_pct_of_mailed", "completion_pct_of_delivered",
            "mail_share_pct_of_completed", "online_share_pct_of_completed",
            "included_in_nsmo_v70_puf", "source_note", "source_pdf_page",
        }
        if len(source_rows) != 48 or not required.issubset(source_rows[0] if source_rows else set()):
            raise ValueError("NSMO survey-return table failed its 48-wave schema check")
        count_fields = (
            "surveys_mailed", "postal_nondelivery", "surveys_delivered", "surveys_completed_total",
            "completed_by_mail", "online_english", "online_spanish", "opt_out",
        )
        rows = []
        for expected_wave, source in enumerate(source_rows, start=1):
            if int(source["survey_wave"]) != expected_wave:
                raise ValueError("NSMO survey-return waves are missing, duplicated, or out of order")
            row = {
                "survey_wave": expected_wave,
                "average_sampling_weight": float(source["average_sampling_weight"]),
                **{field: int(source[field]) for field in count_fields},
                "completion_pct_of_mailed": float(source["completion_pct_of_mailed"]),
                "completion_pct_of_delivered": float(source["completion_pct_of_delivered"]),
                "mail_share_pct_of_completed": float(source["mail_share_pct_of_completed"]),
                "online_share_pct_of_completed": float(source["online_share_pct_of_completed"]),
                "online_english_share_pct_of_completed": float(source["online_english_share_pct_of_completed"]),
                "online_spanish_share_pct_of_completed": float(source["online_spanish_share_pct_of_completed"]),
                "included_in_nsmo_v70_puf": source["included_in_nsmo_v70_puf"].casefold() == "true",
                "source_note": source["source_note"],
                "source_pdf_page": int(source["source_pdf_page"]),
            }
            if row["included_in_nsmo_v70_puf"] != (expected_wave <= 46):
                raise ValueError("NSMO PUF wave coverage does not match the v7.0 release")
            if (row["surveys_mailed"] != row["postal_nondelivery"] + row["surveys_delivered"]
                    or row["surveys_completed_total"] != row["completed_by_mail"] + row["online_english"] + row["online_spanish"]
                    or row["surveys_completed_total"] > row["surveys_delivered"]):
                raise ValueError(f"NSMO survey-return counts do not reconcile for wave {expected_wave}")
            rows.append(row)

        def aggregate(selected: list[dict]) -> dict:
            totals = {field: sum(row[field] for row in selected) for field in count_fields}
            complete = totals["surveys_completed_total"]
            mailed = totals["surveys_mailed"]
            delivered = totals["surveys_delivered"]
            return {
                **totals,
                "waves": len(selected),
                "completion_pct_of_mailed": round(100 * complete / mailed, 2),
                "completion_pct_of_delivered": round(100 * complete / delivered, 2),
                "mail_share_pct_of_completed": round(100 * totals["completed_by_mail"] / complete, 2),
                "online_share_pct_of_completed": round(100 * (totals["online_english"] + totals["online_spanish"]) / complete, 2),
            }

        report_totals = aggregate(rows)
        expected_totals = {
            "surveys_mailed": 281942, "postal_nondelivery": 9494, "surveys_delivered": 272448,
            "surveys_completed_total": 76405, "completed_by_mail": 41254,
            "online_english": 34529, "online_spanish": 622, "opt_out": 1259,
        }
        if any(report_totals[field] != value for field, value in expected_totals.items()):
            raise ValueError("NSMO survey-return counts do not match FHFA Table 3 totals")
        puf_returns = aggregate(rows[:46])
        usability_path = contained(self.root, _USABLE_RESPONSES_CSV)
        if not usability_path.is_file() or sha256(usability_path) != _USABLE_RESPONSES_SHA256:
            raise ValueError("NSMO usable-response table does not match the reviewed FHFA v7.0 extraction")
        with usability_path.open(encoding="utf-8-sig", newline="") as stream:
            usability_source = list(csv.DictReader(stream))
        usability_fields = (
            "surveys_completed_total", "duplicate_or_ineligible", "answered_no_to_q1",
            "did_not_finish_survey", "wrong_loan", "usable_responses_table4",
            "usable_responses_origination_2013_2024_tables5_6", "gap_to_usable_table4",
        )
        if len(usability_source) != 46:
            raise ValueError("NSMO usable-response table must contain waves 1–46")
        usability_rows = []
        for expected_wave, source in enumerate(usability_source, start=1):
            row = {"survey_wave": expected_wave, **{field: int(source[field]) for field in usability_fields},
                   "source_pdf_page_table4": int(source["source_pdf_page_table4"]),
                   "source_pdf_pages_tables5_6": source["source_pdf_pages_tables5_6"],
                   "source_note": source["source_note"]}
            if int(source["survey_wave"]) != expected_wave:
                raise ValueError("NSMO usable-response waves are missing, duplicated, or out of order")
            if row["surveys_completed_total"] != rows[expected_wave - 1]["surveys_completed_total"]:
                raise ValueError(f"Table 3 and Table 4 returned counts disagree in wave {expected_wave}")
            if row["surveys_completed_total"] != (
                    row["duplicate_or_ineligible"] + row["answered_no_to_q1"]
                    + row["did_not_finish_survey"] + row["wrong_loan"] + row["usable_responses_table4"]):
                raise ValueError(f"Table 4 dispositions do not reconcile in wave {expected_wave}")
            if row["gap_to_usable_table4"] != (
                    row["usable_responses_table4"] - row["usable_responses_origination_2013_2024_tables5_6"]):
                raise ValueError(f"Table 4 to Tables 5/6 scope gap does not reconcile in wave {expected_wave}")
            usability_rows.append(row)
        usability_totals = {field: sum(row[field] for row in usability_rows) for field in usability_fields}
        expected_usability_totals = {
            "surveys_completed_total": 74193, "duplicate_or_ineligible": 2009,
            "answered_no_to_q1": 4102, "did_not_finish_survey": 2592,
            "wrong_loan": 2339, "usable_responses_table4": 63151,
            "usable_responses_origination_2013_2024_tables5_6": 62359, "gap_to_usable_table4": 792,
        }
        if usability_totals != expected_usability_totals:
            raise ValueError("NSMO usable-response totals do not match FHFA Tables 4–6")
        gap_wave7 = usability_rows[6]["gap_to_usable_table4"]
        gap_waves45_46 = sum(row["gap_to_usable_table4"] for row in usability_rows[44:46])
        if (gap_wave7, gap_waves45_46, sum(row["gap_to_usable_table4"] for row in usability_rows)) != (295, 497, 792):
            raise ValueError("NSMO release-scope gap does not match the reviewed wave-7 and wave-45/46 breakdown")
        usability = {
            "completed_returns": usability_totals["surveys_completed_total"],
            "usable_responses_table4": usability_totals["usable_responses_table4"],
            "usable_share_of_returned_pct": round(100 * 63151 / 74193, 2),
            "usable_share_of_mailed_pct": 23.33,
            "puf_v70_rows_and_tables5_6_2013_2024": usability_totals["usable_responses_origination_2013_2024_tables5_6"],
            "usable_table4_minus_puf_scope": usability_totals["gap_to_usable_table4"],
            "wave_7_remote_rural_scope_gap": gap_wave7,
            "wave_45_46_origination_scope_gap": gap_waves45_46,
            "exclusions_by_disposition": {
                "duplicate_or_ineligible": usability_totals["duplicate_or_ineligible"],
                "answered_no_to_q1": usability_totals["answered_no_to_q1"],
                "did_not_finish_survey": usability_totals["did_not_finish_survey"],
                "wrong_loan": usability_totals["wrong_loan"],
            },
            "waves": usability_rows,
            "limitation": "Table 4–6 scope reconciliation is aggregate-only; no respondent-level reason, response mode, or row linkage is exposed.",
        }
        return {
            "status": "AVAILABLE",
            "source": "https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf",
            "source_table": "Table 3 · printed pages 10–11",
            "table_sha256": _SURVEY_RETURNS_SHA256,
            "puf_v70": puf_returns,
            "usability": usability,
            "all_reported_waves": report_totals,
            "mode_shift": {
                "wave_1_online_share_pct": rows[0]["online_share_pct_of_completed"],
                "wave_46_online_share_pct": rows[45]["online_share_pct_of_completed"],
                "change_percentage_points": round(rows[45]["online_share_pct_of_completed"] - rows[0]["online_share_pct_of_completed"], 2),
            },
            "waves": rows,
            "limitations": [
                "FHFA publishes mail/online return counts by wave only; the v7.0 PUF has no respondent-level response-mode field.",
                "Wave-level response-mode mix cannot be linked to a mortgage row or its performance outcome.",
                "These are completed-survey composition and response counts, not mode-adjusted estimates or credit-risk rates.",
                "Waves 47–48 appear in the report but are outside the v7.0 PUF, which covers waves 1–46.",
            ],
        }

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

        allowed_statuses = set("C123456789ABKMPSQ") | {"<BLANK>"}
        same_month_source = receipt.get("same_month_ambiguous_snapshot_status_counts_by_baseline_state", {})
        if not isinstance(same_month_source, dict):
            raise ValueError("NSMO same-month ambiguity aggregates are invalid")
        same_month_by_state: dict[str, dict[str, int]] = {}
        for state in ("C", "1", "2"):
            raw = same_month_source.get(state, {})
            if not isinstance(raw, dict) or set(raw) - allowed_statuses:
                raise ValueError("NSMO same-month snapshot status codes are invalid")
            counts = {str(code): int(value) for code, value in raw.items()}
            if any(value < 0 for value in counts.values()) or sum(counts.values()) != quarter_totals.get(state, {}).get("termination_same_month_ambiguous", 0):
                raise ValueError("NSMO same-month state totals do not reconcile to ambiguous closures")
            same_month_by_state[state] = counts

        same_month_vintage_source = receipt.get("same_month_ambiguous_snapshot_status_counts_by_vintage_and_baseline_state")
        if not isinstance(same_month_vintage_source, list):
            raise ValueError("NSMO same-month vintage aggregates are missing")
        same_month_vintage_rows = []
        same_month_vintage_totals: dict[tuple[str, str], int] = {}
        same_month_status_totals: dict[str, dict[str, int]] = {}
        seen_same_month_keys: set[tuple[str, str]] = set()
        for item in same_month_vintage_source:
            year, state = str(item.get("origination_year", "")), str(item.get("baseline_state", ""))
            key = (year, state)
            raw = item.get("snapshot_status_counts_unweighted", {})
            if (not year.isdigit() or state not in {"C", "1", "2"} or key in seen_same_month_keys
                    or not isinstance(raw, dict) or set(raw) - allowed_statuses):
                raise ValueError("NSMO same-month vintage key or status is invalid")
            seen_same_month_keys.add(key)
            counts = {str(code): int(value) for code, value in raw.items()}
            if any(value < 0 for value in counts.values()):
                raise ValueError("NSMO same-month vintage count cannot be negative")
            same_month_vintage_rows.append({"origination_year": year, "baseline_state": state,
                                            "snapshot_status_counts_unweighted": counts})
            same_month_vintage_totals[key] = sum(counts.values())
            state_total = same_month_status_totals.setdefault(state, {})
            for code, value in counts.items():
                state_total[code] = state_total.get(code, 0) + value
        for row in vintage_rows:
            key = (row["origination_year"], row["baseline_state"])
            expected = row["full_horizon_baseline_snapshots_unweighted"].get("termination_same_month_ambiguous", 0)
            if same_month_vintage_totals.get(key, 0) != expected:
                raise ValueError("NSMO same-month vintage statuses do not reconcile to ambiguous closures")
        if any(same_month_status_totals.get(state, {}) != same_month_by_state[state]
               for state in ("C", "1", "2")):
            raise ValueError("NSMO same-month status totals do not reconcile by baseline state")

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
            "same_month_ambiguity": {
                "snapshot_status_counts_by_baseline_state": same_month_by_state,
                "snapshot_status_counts_by_vintage_and_baseline_state": same_month_vintage_rows,
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

    def first_observed_transition_support(self) -> dict:
        """Serve identity-free transition support bound to the verified PUF."""
        profile = self.report()
        receipt = read_json(contained(self.root, _FIRST_OBSERVED_TRANSITION_AUDIT))
        source_sha = profile["source"]["source_sha256"]
        row_count = int(profile["sample"]["mortgages"])
        schema = receipt.get("schema", {})
        checks = receipt.get("checks", {})
        summary = receipt.get("all_vintages", {})
        if (receipt.get("status") != "PASS"
                or receipt.get("definition", {}).get("target_or_label_created") is not False
                or receipt.get("definition", {}).get("risk_set_or_event_incidence") is not False
                or receipt.get("source", {}).get("sha256") != source_sha
                or int(schema.get("rows", -1)) != row_count
                or int(schema.get("columns", -1)) != 587
                or int(schema.get("quarterly_status_columns", -1)) != 51
                or int(checks.get("unique_mortgage_ids", -1)) != row_count
                or any(int(checks.get(key, -1)) != 0 for key in
                       ("width_errors", "empty_mortgage_ids", "duplicate_mortgage_ids"))
                or summary.get("first_event_partition_reconciles") is not True):
            raise ValueError("NSMO first-observed transition receipt is stale or does not match the verified PUF")

        def state_counts(name: str, *, unique: bool = False) -> dict[str, int]:
            value = summary.get(name)
            if not isinstance(value, dict) or set(value) - {"C", "1", "2"}:
                raise ValueError("NSMO transition source-state aggregates are invalid")
            counts = {str(state): int(count) for state, count in value.items()}
            if any(count < 0 or count > row_count for count in counts.values()):
                raise ValueError("NSMO transition support count is out of range")
            return counts

        repeated = state_counts("repeated_90plus_transition_count_by_source_state")
        unique = state_counts("unique_mortgages_with_any_90plus_transition_by_source_state", unique=True)
        first_by_state = state_counts("first_observed_90plus_event_by_prior_baseline_state", unique=True)
        if set(repeated) != set(unique) or set(unique) != set(first_by_state):
            raise ValueError("NSMO transition support states do not reconcile")

        rows = receipt.get("by_origination_vintage_and_source_state")
        if not isinstance(rows, list) or not rows:
            raise ValueError("NSMO transition support vintage groups are missing")
        clean_rows = []
        seen: set[tuple[str, str]] = set()
        repeated_totals: dict[str, int] = {}
        unique_totals: dict[str, int] = {}
        first_totals: dict[str, int] = {}
        for item in rows:
            year, state = str(item.get("origination_year", "")), str(item.get("source_state", ""))
            key = (year, state)
            if not year.isdigit() or state not in {"C", "1", "2"} or key in seen:
                raise ValueError("NSMO transition support vintage key is invalid")
            seen.add(key)
            repeated_n = int(item.get("repeated_90plus_transition_count", -1))
            unique_n = int(item.get("unique_mortgages_with_any_90plus_transition", -1))
            first_n = int(item.get("first_observed_90plus_event_count", -1))
            if min(repeated_n, unique_n, first_n) < 0 or unique_n > repeated_n or first_n > unique_n:
                raise ValueError("NSMO transition support vintage counts are invalid")
            clean_rows.append({"origination_year": year, "source_state": state,
                               "repeated_90plus_transition_count": repeated_n,
                               "unique_mortgages_with_any_90plus_transition": unique_n,
                               "first_observed_90plus_event_count": first_n})
            repeated_totals[state] = repeated_totals.get(state, 0) + repeated_n
            unique_totals[state] = unique_totals.get(state, 0) + unique_n
            first_totals[state] = first_totals.get(state, 0) + first_n

        if (repeated_totals != repeated or unique_totals != unique or first_totals != first_by_state
                or sum(first_by_state.values()) != int(summary.get("first_observed_90plus_event_with_baseline_source_state", -1))
                or (int(summary.get("first_observed_90plus_event_count", -1)) !=
                    int(summary.get("first_observed_90plus_event_with_baseline_source_state", -1))
                    + int(summary.get("first_observed_90plus_event_without_observed_prior", -1))
                    + int(summary.get("first_observed_90plus_event_after_other_adverse_state", -1)))):
            raise ValueError("NSMO transition support totals do not reconcile")

        return {
            "schema_version": "nsmo-first-observed-transition-support-v1",
            "status": "AVAILABLE",
            "source_sha256": source_sha,
            "target_created": False,
            "definition": receipt["definition"],
            "all_vintages": {
                "repeated_90plus_transition_count_by_source_state": repeated,
                "unique_mortgages_with_any_90plus_transition_by_source_state": unique,
                "first_observed_90plus_event_count": int(summary["first_observed_90plus_event_count"]),
                "first_observed_90plus_event_with_baseline_source_state": int(summary["first_observed_90plus_event_with_baseline_source_state"]),
                "first_observed_90plus_event_without_observed_prior": int(summary["first_observed_90plus_event_without_observed_prior"]),
                "first_observed_90plus_event_after_other_adverse_state": int(summary["first_observed_90plus_event_after_other_adverse_state"]),
                "first_observed_90plus_event_by_prior_baseline_state": first_by_state,
            },
            "by_origination_vintage_and_source_state": clean_rows,
            "limitations": receipt.get("limitations", []),
        }
