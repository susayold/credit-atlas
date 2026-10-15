from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/COMPLETION_REQUIREMENTS_50.json"
DOC = ROOT / "docs/WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md"
SUBMISSIONS = ROOT / "data/private/structured/absee-mirror-f97dcd09916d/sec-submissions.json"
ACQUISITION = ROOT / "data/private/structured/woart-legal-source-bfc00b6802b5/acquisition-complete.json"
AUDIT = ROOT / "artifacts/private/woart-legal-audit-b6c2448187ce/receipt.json"
ABSEE_ACQUISITION = ROOT / "data/private/structured/woart-absee-history-948a4d8e4f18/acquisition-complete.json"
ABSEE_PROFILE = ROOT / "artifacts/private/woart-absee-official-profile-0c8de9d2359d/profile.json"
ABSEE_PROFILE_RECEIPT = ROOT / "artifacts/private/woart-absee-official-profile-0c8de9d2359d/receipt.json"
DELINQUENCY_AUDIT = ROOT / "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/audit.json"
DELINQUENCY_RECEIPT = ROOT / "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/receipt.json"
PANEL_RECEIPT = ROOT / "data/private/derived/woart-absee-panel-91efe12963d6/dataset-complete.json"
PANEL_AUDIT = ROOT / "artifacts/private/woart-absee-panel-audit-f689e9c70199/audit.json"
PANEL_AUDIT_RECEIPT = ROOT / "artifacts/private/woart-absee-panel-audit-f689e9c70199/receipt.json"
ZERO_BALANCE_AUDIT = ROOT / "artifacts/private/woart-absee-zero-balance-audit-75bdd262ce0b/audit.json"
ZERO_BALANCE_RECEIPT = ROOT / "artifacts/private/woart-absee-zero-balance-audit-75bdd262ce0b/receipt.json"
FIELD_SEMANTICS_AUDIT = ROOT / "artifacts/private/woart-absee-field-semantics-audit-fafadee77978/audit.json"
FIELD_SEMANTICS_RECEIPT = ROOT / "artifacts/private/woart-absee-field-semantics-audit-fafadee77978/receipt.json"
DICTIONARY_IMPL = ROOT / "src/credit_atlas/absee_dictionary.py"
APP_FRONTEND = ROOT / "apps/web/app.js"
APP_GUIDE = ROOT / "docs/ABS_APP_WORKFLOW.md"
APP_PROFILE_IMPL = ROOT / "src/credit_atlas/absee_profile.py"
OFFICIAL_KPI_REPORT = ROOT / "artifacts/private/woart-absee-official-kpi-report-635e871305b5/kpis.json"
OFFICIAL_KPI_RECEIPT = ROOT / "artifacts/private/woart-absee-official-kpi-report-635e871305b5/receipt.json"
FEATURE_AUDIT = ROOT / "artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/audit.json"
FEATURE_AUDIT_RECEIPT = ROOT / "artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/receipt.json"
PEER_ACQUISITION = ROOT / "data/private/structured/sec-auto-abs-peer-fe7022e04210/acquisition-complete.json"
PEER_PROFILE = ROOT / "artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/profile.json"
PEER_PROFILE_RECEIPT = ROOT / "artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/receipt.json"
PEER_2022_ACQUISITION = ROOT / "data/private/structured/sec-auto-abs-peer-e3083eb6930f/acquisition-complete.json"
PEER_2022_PROFILE = ROOT / "artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/profile.json"
PEER_2022_PROFILE_RECEIPT = ROOT / "artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/receipt.json"
TOYOTA_HISTORY_ACQUISITION = ROOT / "data/private/structured/toyota-2022b-absee-history-435918e7209a/acquisition-complete.json"
TOYOTA_PANEL_AUDIT = ROOT / "artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/audit.json"
TOYOTA_PANEL_RECEIPT = ROOT / "artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/receipt.json"
TOYOTA_TARGET_AUDIT = ROOT / "artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/audit.json"
TOYOTA_TARGET_RECEIPT = ROOT / "artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/receipt.json"
TOYOTA_EX103_ACQUISITION = ROOT / "data/private/structured/toyota-2022b-ex103-6e1500e4671f/acquisition-complete.json"
TOYOTA_EX103_PROFILE = ROOT / "artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/profile.json"
TOYOTA_EX103_RECEIPT = ROOT / "artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/receipt.json"
TOYOTA_TEMPORAL_AUDIT = ROOT / "artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/audit.json"
TOYOTA_TEMPORAL_RECEIPT = ROOT / "artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/receipt.json"
TOYOTA_10D_ACQUISITION = ROOT / "data/private/structured/toyota-2022b-10d-certificates-941fa44791c8/acquisition-complete.json"
TOYOTA_CERTIFICATE_AUDIT = ROOT / "artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/audit.json"
TOYOTA_CERTIFICATE_RECEIPT = ROOT / "artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/receipt.json"
TOYOTA_FEATURE_AUDIT = ROOT / "artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/audit.json"
TOYOTA_FEATURE_RECEIPT = ROOT / "artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/receipt.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
doc = json.loads(SUBMISSIONS.read_text(encoding="utf-8"))
filings = doc["filings"]["recent"]
if len(filings["form"]) != 52 or filings["filingDate"][-1] != "2025-01-13":
    # SEC submissions are reverse chronological; newest first.
    if not (len(filings["form"]) == 52 and filings["filingDate"][0] == "2026-09-29" and filings["filingDate"][-1] == "2025-01-13"):
        raise SystemExit("Unexpected SEC submissions snapshot; no ledger update made")
for path in (DOC, ACQUISITION, AUDIT):
    if not path.is_file():
        raise SystemExit(f"Required research evidence missing: {path}")
for path in (ABSEE_ACQUISITION, ABSEE_PROFILE, ABSEE_PROFILE_RECEIPT, DELINQUENCY_AUDIT, DELINQUENCY_RECEIPT,
             PANEL_RECEIPT, PANEL_AUDIT, PANEL_AUDIT_RECEIPT, ZERO_BALANCE_AUDIT, ZERO_BALANCE_RECEIPT,
             FIELD_SEMANTICS_AUDIT, FIELD_SEMANTICS_RECEIPT, OFFICIAL_KPI_REPORT, OFFICIAL_KPI_RECEIPT,
             FEATURE_AUDIT, FEATURE_AUDIT_RECEIPT, PEER_ACQUISITION, PEER_PROFILE, PEER_PROFILE_RECEIPT,
             PEER_2022_ACQUISITION,
             PEER_2022_PROFILE, PEER_2022_PROFILE_RECEIPT,
             TOYOTA_HISTORY_ACQUISITION, TOYOTA_PANEL_AUDIT, TOYOTA_PANEL_RECEIPT,
             TOYOTA_TARGET_AUDIT, TOYOTA_TARGET_RECEIPT, TOYOTA_EX103_ACQUISITION,
             TOYOTA_EX103_PROFILE, TOYOTA_EX103_RECEIPT,
             TOYOTA_TEMPORAL_AUDIT, TOYOTA_TEMPORAL_RECEIPT,
             TOYOTA_10D_ACQUISITION, TOYOTA_CERTIFICATE_AUDIT, TOYOTA_CERTIFICATE_RECEIPT,
             TOYOTA_FEATURE_AUDIT, TOYOTA_FEATURE_RECEIPT):
    if not path.is_file():
        raise SystemExit(f"Required official ABS-EE evidence missing: {path}")

absee_acquisition = json.loads(ABSEE_ACQUISITION.read_text(encoding="utf-8"))
absee_profile_receipt = json.loads(ABSEE_PROFILE_RECEIPT.read_text(encoding="utf-8"))
delinquency_receipt = json.loads(DELINQUENCY_RECEIPT.read_text(encoding="utf-8"))
panel_receipt = json.loads(PANEL_RECEIPT.read_text(encoding="utf-8"))
panel_audit = json.loads(PANEL_AUDIT.read_text(encoding="utf-8"))
panel_audit_receipt = json.loads(PANEL_AUDIT_RECEIPT.read_text(encoding="utf-8"))
zero_balance_audit = json.loads(ZERO_BALANCE_AUDIT.read_text(encoding="utf-8"))
zero_balance_receipt = json.loads(ZERO_BALANCE_RECEIPT.read_text(encoding="utf-8"))
field_semantics_audit = json.loads(FIELD_SEMANTICS_AUDIT.read_text(encoding="utf-8"))
field_semantics_receipt = json.loads(FIELD_SEMANTICS_RECEIPT.read_text(encoding="utf-8"))
kpi_report = json.loads(OFFICIAL_KPI_REPORT.read_text(encoding="utf-8"))
kpi_receipt = json.loads(OFFICIAL_KPI_RECEIPT.read_text(encoding="utf-8"))
feature_audit = json.loads(FEATURE_AUDIT.read_text(encoding="utf-8"))
feature_audit_receipt = json.loads(FEATURE_AUDIT_RECEIPT.read_text(encoding="utf-8"))
peer_acquisition = json.loads(PEER_ACQUISITION.read_text(encoding="utf-8"))
peer_profile = json.loads(PEER_PROFILE.read_text(encoding="utf-8"))
peer_profile_receipt = json.loads(PEER_PROFILE_RECEIPT.read_text(encoding="utf-8"))
peer_2022_acquisition = json.loads(PEER_2022_ACQUISITION.read_text(encoding="utf-8"))
peer_2022_profile = json.loads(PEER_2022_PROFILE.read_text(encoding="utf-8"))
peer_2022_profile_receipt = json.loads(PEER_2022_PROFILE_RECEIPT.read_text(encoding="utf-8"))
toyota_history_acquisition = json.loads(TOYOTA_HISTORY_ACQUISITION.read_text(encoding="utf-8"))
toyota_panel_audit = json.loads(TOYOTA_PANEL_AUDIT.read_text(encoding="utf-8"))
toyota_panel_receipt = json.loads(TOYOTA_PANEL_RECEIPT.read_text(encoding="utf-8"))
toyota_target_audit = json.loads(TOYOTA_TARGET_AUDIT.read_text(encoding="utf-8"))
toyota_target_receipt = json.loads(TOYOTA_TARGET_RECEIPT.read_text(encoding="utf-8"))
toyota_ex103_acquisition = json.loads(TOYOTA_EX103_ACQUISITION.read_text(encoding="utf-8"))
toyota_ex103_profile = json.loads(TOYOTA_EX103_PROFILE.read_text(encoding="utf-8"))
toyota_ex103_receipt = json.loads(TOYOTA_EX103_RECEIPT.read_text(encoding="utf-8"))
toyota_temporal_audit = json.loads(TOYOTA_TEMPORAL_AUDIT.read_text(encoding="utf-8"))
toyota_temporal_receipt = json.loads(TOYOTA_TEMPORAL_RECEIPT.read_text(encoding="utf-8"))
toyota_10d_acquisition = json.loads(TOYOTA_10D_ACQUISITION.read_text(encoding="utf-8"))
toyota_certificate_audit = json.loads(TOYOTA_CERTIFICATE_AUDIT.read_text(encoding="utf-8"))
toyota_certificate_receipt = json.loads(TOYOTA_CERTIFICATE_RECEIPT.read_text(encoding="utf-8"))
toyota_feature_audit = json.loads(TOYOTA_FEATURE_AUDIT.read_text(encoding="utf-8"))
toyota_feature_receipt = json.loads(TOYOTA_FEATURE_RECEIPT.read_text(encoding="utf-8"))
if (absee_acquisition.get("status") != "SEC_OFFICIAL_ABSEE_HISTORY_ACQUIRED"
        or absee_acquisition.get("period_count") != 20
        or absee_profile_receipt.get("status") != "OFFICIAL_XML_PROFILED_AND_CERTIFICATE_RECONCILIATION_COMPLETE"
        or absee_profile_receipt.get("periods") != 20
        or absee_profile_receipt.get("rows") != 880773
        or not absee_profile_receipt.get("all_monthly_balances_match_to_cent")
        or absee_profile_receipt.get("mirror_field_mismatch_periods") != 0
        or delinquency_receipt.get("status") != "XSD_DAY_DELINQUENCY_MAPPED_AND_CERTIFICATE_RECONCILED"
        or delinquency_receipt.get("checks") != 200
        or delinquency_receipt.get("failed_checks") != 0
        or not delinquency_receipt.get("all_amounts_and_counts_match")
        or panel_receipt.get("status") != "OFFICIAL_ABSEE_RAW_PANEL_PARQUET_BUILT"
        or panel_receipt.get("row_count") != 880773
        or panel_receipt.get("report_count") != 20
        or panel_audit_receipt.get("status") != "OFFICIAL_PARQUET_PANEL_AND_ADJACENT_STATE_AUDIT_PASS"
        or panel_audit_receipt.get("rows") != 880773
        or panel_audit_receipt.get("periods") != 20
        or panel_audit_receipt.get("adjacent_transition_pairs") != 19
        or panel_audit_receipt.get("balance_failures") != 0
        or panel_audit.get("nonzero_balance_asset_count_exact_periods") != 16
        or len(panel_audit.get("nonzero_balance_asset_count_differences", [])) != 4
        or zero_balance_receipt.get("status") != "XSD_ZERO_BALANCE_CODES_AND_EXIT_SCOPE_AUDITED"
        or zero_balance_receipt.get("periods") != 20
        or zero_balance_receipt.get("transition_pairs") != 19
        or zero_balance_receipt.get("zero_balance_code_counts") != {"1": 20837, "4": 939}
        or zero_balance_receipt.get("unclassified_missing_records") != 6445
        or field_semantics_receipt.get("status") != "AUTO_LOAN_XSD_FIELDS_PROFILED_AGAINST_OFFICIAL_PANEL"
        or field_semantics_receipt.get("periods") != 20
        or field_semantics_receipt.get("rows") != 880773
        or field_semantics_receipt.get("fields") != 15
        or field_semantics_receipt.get("decimal_parse_errors") != 0
        or field_semantics_receipt.get("xsd_fields_verified") != 15
        or field_semantics_audit.get("cross_field_checks", {}).get("code_4_without_chargeoff_amount") != 0
        or kpi_receipt.get("status") != "OFFICIAL_ABSEE_MONTHLY_KPI_REPORT_BUILT"
        or kpi_receipt.get("periods") != 20 or kpi_receipt.get("rows") != 880773
        or kpi_receipt.get("balance_checks_passed") != 20 or kpi_receipt.get("chargeoff_checks_passed") != 20
        or kpi_receipt.get("recovery_exact_tieout_periods") != 3
        or kpi_receipt.get("recovery_nonzero_delta_periods") != 17
        or feature_audit_receipt.get("status") != "OFFICIAL_ABSEE_FEATURE_ANOMALY_AUDIT_BUILT"
        or feature_audit_receipt.get("periods") != 20 or feature_audit_receipt.get("rows") != 880773
        or feature_audit_receipt.get("pti_gt_1_row_months") != 226
        or feature_audit_receipt.get("pti_gt_1_unique_assets") != 12
        or feature_audit_receipt.get("negative_recovery_row_months") != 561
        or feature_audit_receipt.get("negative_recovery_unique_assets") != 466
        or peer_acquisition.get("status") != "SEC_OFFICIAL_AUTO_ABS_PEER_PERIOD_ACQUIRED"
        or peer_acquisition.get("issuer") != "Toyota Auto Receivables 2026-C Owner Trust"
        or peer_profile_receipt.get("status") != "SEC_AUTO_ABS_PEER_XML_PROFILED"
        or peer_profile_receipt.get("rows") != 46601 or peer_profile_receipt.get("fields") != 57
        or peer_profile_receipt.get("common_fields_with_woart") != 57
        or peer_profile_receipt.get("duplicate_key_rows") != 0
        or peer_profile_receipt.get("decimal_parse_errors") != 0
        or peer_2022_acquisition.get("status") != "SEC_OFFICIAL_AUTO_ABS_PEER_PERIOD_ACQUIRED"
        or peer_2022_acquisition.get("issuer") != "Toyota Auto Receivables 2022-B Owner Trust"
        or peer_2022_profile_receipt.get("status") != "SEC_AUTO_ABS_PEER_XML_PROFILED"
        or peer_2022_profile_receipt.get("rows") != 20916 or peer_2022_profile_receipt.get("fields") != 62
        or peer_2022_profile_receipt.get("common_fields_with_woart") != 62
        or peer_2022_profile_receipt.get("duplicate_key_rows") != 0
        or peer_2022_profile_receipt.get("decimal_parse_errors") != 0
        or toyota_history_acquisition.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_ABSEE_HISTORY_ACQUIRED"
        or toyota_history_acquisition.get("period_count") != 51
        or toyota_panel_receipt.get("status") != "TOYOTA_2022B_LONGITUDINAL_PANEL_AUDITED"
        or toyota_panel_receipt.get("periods") != 51 or toyota_panel_receipt.get("rows") != 2508991
        or toyota_panel_receipt.get("transition_pairs") != 50
        or toyota_panel_receipt.get("unique_assets") != 77626
        or toyota_panel_receipt.get("default_or_exit_labels_qualified") is not False
        or toyota_target_receipt.get("status") != "TOYOTA_2022B_SERVICING_TARGET_FEASIBILITY_AUDITED"
        or toyota_target_receipt.get("periods") != 51 or toyota_target_receipt.get("chargeoff_events") != 1122
        or toyota_target_receipt.get("at_risk_row_months") != 2419178
        or toyota_target_receipt.get("labels_qualified_for_training") is not False
        or toyota_ex103_acquisition.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_EX103_ACQUIRED"
        or toyota_ex103_acquisition.get("report_count") != 51
        or toyota_ex103_receipt.get("status") != "TOYOTA_2022B_EX103_FIELD_NARRATIVES_PROFILED"
        or toyota_ex103_receipt.get("fields") != 32
        or toyota_ex103_receipt.get("changed_field_definitions") != 0
        or toyota_temporal_receipt.get("status") != "TOYOTA_2022B_TEMPORAL_SPLIT_FEASIBILITY_AUDITED"
        or toyota_temporal_receipt.get("horizons_with_two_way_oot_support") != 2
        or toyota_temporal_receipt.get("three_way_split_available") is not False
        or toyota_temporal_receipt.get("model_fitted") is not False
        or toyota_temporal_audit.get("candidate_horizons", {}).get("12", {}).get("test", {}).get("at_risk_row_months") != 486182
        or toyota_temporal_audit.get("candidate_horizons", {}).get("24", {}).get("status") != "NO_HONEST_TRAIN_TEST_SPLIT"
        or toyota_10d_acquisition.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_10D_CERTIFICATES_ACQUIRED"
        or toyota_10d_acquisition.get("period_count") != 51
        or toyota_certificate_receipt.get("status") != "TOYOTA_2022B_ABSEE_TO_10D_CERTIFICATE_TIEOUT_AUDITED"
        or toyota_certificate_receipt.get("periods") != 51
        or toyota_certificate_receipt.get("check_counts", {}).get("pool_balance_exact") != 51
        or toyota_certificate_receipt.get("check_counts", {}).get("positive_balance_count_matches") != 51
        or toyota_certificate_receipt.get("check_counts", {}).get("chargeoff_event_count_matches") != 51
        or toyota_certificate_receipt.get("check_counts", {}).get("chargeoff_amount_matches_gross_liquidations") != 51
        or sum(value for key, value in toyota_certificate_receipt.get("check_counts", {}).items() if key.startswith("bucket_")) != 408
        or toyota_certificate_receipt.get("check_counts", {}).get("recovered_amount_matches_aggregate_net_liquidation_proceeds") != 2
        or toyota_feature_receipt.get("status") != "TOYOTA_2022B_FEATURE_AVAILABILITY_AUDITED"
        or toyota_feature_receipt.get("horizon_months") != 12
        or toyota_feature_receipt.get("train_rows") != 999342 or toyota_feature_receipt.get("test_rows") != 486182
        or toyota_feature_audit.get("information_timing", {}).get("filing_lag_days", {}).get("median") != 27
        or toyota_feature_audit.get("candidate_static_field_stability", {}).get("obligorGeographicLocation", {}).get("assets_with_value_changes_after_first_observation") != 2870):
    raise SystemExit("Official ABS-EE profile evidence did not pass its recorded scope")

rows = {row["id"]: row for row in ledger["requirements"]}
targets = {
    "P5.01": "SEC original closing agreements and 2026 Omnibus SSA Amendment acquired and hash-verified; 19 critical clause-presence checks and selected term review documented. Conversion date/effectiveness support, complete amendment chain and project term integration remain open.",
    "P5.04": "Executed SSA/Indenture show distinct ordinary and acceleration distributions, including reviewer fee, reserve and certificate stages; research only, no new full-obligation implementation or conservation qualification.",
    "P5.05": "2026 amendment changes Defaulted/Delinquent Receivable definitions and threshold by Conversion Date; Conversion Date and period-level recomputation remain unavailable.",
    "P5.10": "At this legal-amendment checkpoint, SEC filing census and amendment provide event context; Conversion Date remains unavailable. The separate loan-level history checkpoint below adds asset-level day-bucket recomputation but does not fill the Conversion Date gap.",
}
before = {key: (rows[key]["checkpoint_status"], rows[key]["full_completion_proven"]) for key in targets}
for key, scope in targets.items():
    row = rows[key]
    if row["full_completion_proven"]:
        raise SystemExit(f"{key} unexpectedly accepted; no ledger update made")
    checkpoint = "woart-2025a-closing-documents-amendment-review-20261015"
    items = row.setdefault("partial_evidence", [])
    entry = next((item for item in items if item.get("checkpoint") == checkpoint), None)
    if entry is None:
        entry = {
            "checkpoint": checkpoint,
            "document": "docs/WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md",
            "source_metadata": "data/private/structured/absee-mirror-f97dcd09916d/sec-submissions.json",
            "acquisition": "data/private/structured/woart-legal-source-bfc00b6802b5/acquisition-complete.json",
            "source_audit": "artifacts/private/woart-legal-audit-b6c2448187ce/receipt.json",
            "scope": scope,
            "full_completion_proven": False,
        }
        items.append(entry)
    else:
        entry["scope"] = scope
        entry["acquisition"] = "data/private/structured/woart-legal-source-bfc00b6802b5/acquisition-complete.json"
        entry["source_audit"] = "artifacts/private/woart-legal-audit-b6c2448187ce/receipt.json"
    entry["evidence_sha256"] = {
        "docs/WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md": digest(DOC),
        "data/private/structured/absee-mirror-f97dcd09916d/sec-submissions.json": digest(SUBMISSIONS),
            "data/private/structured/woart-legal-source-bfc00b6802b5/acquisition-complete.json": digest(ACQUISITION),
            "artifacts/private/woart-legal-audit-b6c2448187ce/receipt.json": digest(AUDIT),
    }
after = {key: (rows[key]["checkpoint_status"], rows[key]["full_completion_proven"]) for key in targets}
if before != after:
    raise SystemExit("Requirement acceptance state changed unexpectedly; no ledger update made")

asset_targets = {
    "P5.02": "Official SEC ABS-EE snapshots acquired and converted into a private 20-month WOART panel (880,773 rows/62 fields) and 51-month Toyota 2022-B panel (2,508,991 rows/62 fields, 77,626 keys, 50 transitions). WOART balance totals and XSD delinquency buckets reconcile; counts match certificates in 16/20 periods, with four one-account differences. Toyota pool/positive-contract counts tie to 51 monthly 10-D certificates; four delinquency buckets tie in count and balance 408/408. H12's eight candidate features have full presence in train/test; filing lag is 20–30 days and geography changes in 2,870 loans, requiring availability/provenance policy. Toyota event/exit history, 32 stable EX-103 narratives and cross-sectional Toyota peer profiles are integrated in the app. Recovery field deltas, collateral eligibility/terms sign-off and individual-loan drilldown remain open.",
    "P5.03": "WOART monthly cash fields are summarized and compared to 20 certificate periods: asset charge-off sums match Defaulted Receivables 20/20; recovery sums tie exactly in 3/20 and retain deltas. Toyota 2022-B has 1,122 unique charge-off event assets over 51 filings; count and gross principal tie to 10-D 51/51. Asset recoveredAmount ties to certificate aggregate net liquidation proceeds in 2/51 only; signed deltas remain visible. Recovery-tail/LGD remain open; these are reported historical observations, not forecast or scenario outputs.",
    "P5.05": "SEC Auto Loan XSD identifies currentDelinquencyStatus as days past due and defines zeroBalanceCode values; WOART day-bucket amounts/counts match certificates. Toyota observed 1,122 first charge-off events and 58,196 keys exiting after zero-balance snapshots (code 1: 58,158; code 3: 38); EX-103 clarifies servicing event fields. Conversion Date and receivable-level 40 USD/10% threshold remain unknown, so amended default/trigger logic and waterfall effects are not proven.",
    "P5.10": "Official WOART ABS-EE panel covers 20 periods/880,773 rows, all balance and charge-off ties and 200 delinquency checks; Toyota 2022-B history adds 51 periods/2,508,991 rows, 77,626 keys, 50 transitions, 32 stable EX-103 field definitions and 1,122 charge-off events. Pool/positive contracts, liquidation counts/gross principal tie 51/51 to 10-D; delinquency bucket amount/count checks tie 408/408. Recovery field ties in 2/51 with deltas retained. H12's eight features are present in train/test; feature lag is median 27 days, and geographic values change for 2,870 loans. Risk-set feasibility has 2,419,178 at-risk row-months and 6/12/24-month competing-exit/censor classes; labels remain explicitly unqualified for training and are servicing-time, not origination PD. A purged temporal-support audit finds two-way OOT support for H6/H12 only, with loan overlap, no third validation/calibration window and no honest 12-month-test H24 split. Four WOART account-count deltas, 6,445 unclassified missing keys, Toyota recovery reconciliation, target validation and individual-loan drilldown remain open.",
}
asset_checkpoint = "woart-2025a-official-absee-history-profile-20261015"
for key, scope in asset_targets.items():
    row = rows[key]
    if row["full_completion_proven"]:
        raise SystemExit(f"{key} unexpectedly accepted; no ledger update made")
    items = row.setdefault("partial_evidence", [])
    entry = next((item for item in items if item.get("checkpoint") == asset_checkpoint), None)
    if entry is None:
        entry = {"checkpoint": asset_checkpoint,
                 "document": "docs/WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md",
                 "acquisition": "data/private/structured/woart-absee-history-948a4d8e4f18/acquisition-complete.json",
                 "profile": "artifacts/private/woart-absee-official-profile-0c8de9d2359d/profile.json",
                 "profile_receipt": "artifacts/private/woart-absee-official-profile-0c8de9d2359d/receipt.json",
                 "delinquency_audit": "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/audit.json",
                 "delinquency_receipt": "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/receipt.json",
                 "panel": "data/private/derived/woart-absee-panel-91efe12963d6/dataset-complete.json",
                 "panel_audit": "artifacts/private/woart-absee-panel-audit-f689e9c70199/audit.json",
                 "panel_audit_receipt": "artifacts/private/woart-absee-panel-audit-f689e9c70199/receipt.json",
                 "scope": scope, "full_completion_proven": False}
        items.append(entry)
    else:
        entry["scope"] = scope
        entry["panel"] = "data/private/derived/woart-absee-panel-91efe12963d6/dataset-complete.json"
        entry["panel_audit"] = "artifacts/private/woart-absee-panel-audit-f689e9c70199/audit.json"
        entry["panel_audit_receipt"] = "artifacts/private/woart-absee-panel-audit-f689e9c70199/receipt.json"
    entry["official_kpi_report"] = "artifacts/private/woart-absee-official-kpi-report-635e871305b5/kpis.json"
    entry["official_kpi_receipt"] = "artifacts/private/woart-absee-official-kpi-report-635e871305b5/receipt.json"
    entry["peer_acquisition"] = "data/private/structured/sec-auto-abs-peer-fe7022e04210/acquisition-complete.json"
    entry["peer_profile"] = "artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/profile.json"
    entry["peer_profile_receipt"] = "artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/receipt.json"
    entry["peer_2022_acquisition"] = "data/private/structured/sec-auto-abs-peer-e3083eb6930f/acquisition-complete.json"
    entry["peer_2022_profile"] = "artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/profile.json"
    entry["peer_2022_profile_receipt"] = "artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/receipt.json"
    entry["toyota_history_acquisition"] = "data/private/structured/toyota-2022b-absee-history-435918e7209a/acquisition-complete.json"
    entry["toyota_panel_audit"] = "artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/audit.json"
    entry["toyota_panel_receipt"] = "artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/receipt.json"
    entry["toyota_target_audit"] = "artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/audit.json"
    entry["toyota_target_receipt"] = "artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/receipt.json"
    entry["toyota_ex103_acquisition"] = "data/private/structured/toyota-2022b-ex103-6e1500e4671f/acquisition-complete.json"
    entry["toyota_ex103_profile"] = "artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/profile.json"
    entry["toyota_ex103_receipt"] = "artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/receipt.json"
    entry["toyota_temporal_split_audit"] = "artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/audit.json"
    entry["toyota_temporal_split_receipt"] = "artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/receipt.json"
    entry["toyota_10d_acquisition"] = "data/private/structured/toyota-2022b-10d-certificates-941fa44791c8/acquisition-complete.json"
    entry["toyota_certificate_tieout"] = "artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/audit.json"
    entry["toyota_certificate_tieout_receipt"] = "artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/receipt.json"
    entry["toyota_feature_availability_audit"] = "artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/audit.json"
    entry["toyota_feature_availability_receipt"] = "artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/receipt.json"
    entry["evidence_sha256"] = {
        "docs/WOART_2025A_EXECUTED_AGREEMENTS_RESEARCH_VI.md": digest(DOC),
        "data/private/structured/woart-absee-history-948a4d8e4f18/acquisition-complete.json": digest(ABSEE_ACQUISITION),
        "artifacts/private/woart-absee-official-profile-0c8de9d2359d/profile.json": digest(ABSEE_PROFILE),
        "artifacts/private/woart-absee-official-profile-0c8de9d2359d/receipt.json": digest(ABSEE_PROFILE_RECEIPT),
        "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/audit.json": digest(DELINQUENCY_AUDIT),
        "artifacts/private/woart-absee-delinquency-audit-56f1602d0baf/receipt.json": digest(DELINQUENCY_RECEIPT),
        "data/private/derived/woart-absee-panel-91efe12963d6/dataset-complete.json": digest(PANEL_RECEIPT),
        "artifacts/private/woart-absee-panel-audit-f689e9c70199/audit.json": digest(PANEL_AUDIT),
        "artifacts/private/woart-absee-panel-audit-f689e9c70199/receipt.json": digest(PANEL_AUDIT_RECEIPT),
        "artifacts/private/woart-absee-zero-balance-audit-75bdd262ce0b/audit.json": digest(ZERO_BALANCE_AUDIT),
        "artifacts/private/woart-absee-zero-balance-audit-75bdd262ce0b/receipt.json": digest(ZERO_BALANCE_RECEIPT),
        "artifacts/private/woart-absee-field-semantics-audit-fafadee77978/audit.json": digest(FIELD_SEMANTICS_AUDIT),
        "artifacts/private/woart-absee-field-semantics-audit-fafadee77978/receipt.json": digest(FIELD_SEMANTICS_RECEIPT),
        "src/credit_atlas/absee_dictionary.py": digest(DICTIONARY_IMPL),
        "apps/web/app.js": digest(APP_FRONTEND),
        "docs/ABS_APP_WORKFLOW.md": digest(APP_GUIDE),
        "src/credit_atlas/absee_profile.py": digest(APP_PROFILE_IMPL),
        "artifacts/private/woart-absee-official-kpi-report-635e871305b5/kpis.json": digest(OFFICIAL_KPI_REPORT),
        "artifacts/private/woart-absee-official-kpi-report-635e871305b5/receipt.json": digest(OFFICIAL_KPI_RECEIPT),
        "artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/audit.json": digest(FEATURE_AUDIT),
        "artifacts/private/woart-absee-feature-anomaly-audit-4458d2d6bb1a/receipt.json": digest(FEATURE_AUDIT_RECEIPT),
        "data/private/structured/sec-auto-abs-peer-fe7022e04210/acquisition-complete.json": digest(PEER_ACQUISITION),
        "artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/profile.json": digest(PEER_PROFILE),
        "artifacts/private/sec-auto-abs-peer-profile-0931a69b6d7d/receipt.json": digest(PEER_PROFILE_RECEIPT),
        "data/private/structured/sec-auto-abs-peer-e3083eb6930f/acquisition-complete.json": digest(PEER_2022_ACQUISITION),
        "artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/profile.json": digest(PEER_2022_PROFILE),
        "artifacts/private/sec-auto-abs-peer-profile-c431b5e89405/receipt.json": digest(PEER_2022_PROFILE_RECEIPT),
        "data/private/structured/toyota-2022b-absee-history-435918e7209a/acquisition-complete.json": digest(TOYOTA_HISTORY_ACQUISITION),
        "artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/audit.json": digest(TOYOTA_PANEL_AUDIT),
        "artifacts/private/toyota-2022b-absee-panel-audit-c9fbf983fa4e/receipt.json": digest(TOYOTA_PANEL_RECEIPT),
        "artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/audit.json": digest(TOYOTA_TARGET_AUDIT),
        "artifacts/private/toyota-2022b-target-feasibility-cb7b6624bc3f/receipt.json": digest(TOYOTA_TARGET_RECEIPT),
        "data/private/structured/toyota-2022b-ex103-6e1500e4671f/acquisition-complete.json": digest(TOYOTA_EX103_ACQUISITION),
        "artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/profile.json": digest(TOYOTA_EX103_PROFILE),
        "artifacts/private/toyota-2022b-ex103-profile-af05e72ef9c3/receipt.json": digest(TOYOTA_EX103_RECEIPT),
        "artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/audit.json": digest(TOYOTA_TEMPORAL_AUDIT),
        "artifacts/private/toyota-2022b-temporal-split-70fdbfa168fc/receipt.json": digest(TOYOTA_TEMPORAL_RECEIPT),
        "data/private/structured/toyota-2022b-10d-certificates-941fa44791c8/acquisition-complete.json": digest(TOYOTA_10D_ACQUISITION),
        "artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/audit.json": digest(TOYOTA_CERTIFICATE_AUDIT),
        "artifacts/private/toyota-2022b-certificate-tieout-cec933ed357e/receipt.json": digest(TOYOTA_CERTIFICATE_RECEIPT),
        "artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/audit.json": digest(TOYOTA_FEATURE_AUDIT),
        "artifacts/private/toyota-2022b-feature-availability-2d031c8fcb66/receipt.json": digest(TOYOTA_FEATURE_RECEIPT),
    }
ledger["as_of"] = "2026-10-15"
LEDGER.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "RECORDED_PARTIAL_ONLY", "requirements": list(targets) + list(asset_targets), "accepted_count": sum(row["full_completion_proven"] for row in ledger["requirements"]), "total": len(ledger["requirements"])}, ensure_ascii=False))
