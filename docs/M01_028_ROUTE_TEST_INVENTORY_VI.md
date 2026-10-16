# M01-028 — Inventory route API và reference kiểm thử

Sinh tự động từ `src/credit_atlas/server.py`, `apps/web`, `tests` và
`scripts/browser_*.py`. Chỉ đọc mã nguồn; không mở artifact hoặc dữ liệu
private. Danh sách cho biết nơi có chuỗi route trực tiếp, không chứng minh
route đã được kiểm thử đầy đủ, đúng payload hay đã qua browser acceptance.

- Root được quét: `credit-atlas-public`
- Path literals trong server: **176**
- `HTTP tests` và `Browser QA` là reference tĩnh; cần đọc evidence/receipt
  riêng trước khi xem là nghiệm thu.
- Report alias thường được tải qua UI link; route base trong browser script
  không tự chứng minh rằng alias trả đúng attachment.

| API route | UI reference | HTTP-test reference | Browser-QA reference |
|---|---|---|---|
| `/api/abs-benchmark` | `apps/web/app.js` | — | `scripts/browser_abs_benchmark_qa.py`, `scripts/browser_abs_qa.py` |
| `/api/abs-benchmark-report` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py` |
| `/api/abs-period` | `apps/web/app.js`, `apps/web/monitor.js` | `tests/test_abs_views.py` | `scripts/browser_kpi_analysis_qa.py`, `scripts/browser_remaining_domains_qa.py` |
| `/api/abs-report` | `apps/web/app.js` | `tests/test_abs_views.py` | `scripts/browser_remaining_domains_qa.py` |
| `/api/abs-view` | `apps/web/app.js`, `apps/web/monitor.js` | `tests/test_abs_views.py` | `scripts/browser_abs_benchmark_qa.py` |
| `/api/abs-views` | `apps/web/app.js`, `apps/web/monitor.js` | — | `scripts/browser_abs_benchmark_qa.py` |
| `/api/absee-dictionary` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py`, `scripts/browser_absee_dictionary_qa.py` |
| `/api/absee-dictionary-report` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py` |
| `/api/absee-profile` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py`, `scripts/browser_absee_profile_qa.py`, `scripts/browser_nissan_2024b_external_qa.py`, `scripts/browser_toyota_2024b_validation_qa.py` |
| `/api/absee-profile-report` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py` |
| `/api/affordability-assess` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_affordability_qa.py` |
| `/api/affordability-excel-import` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/affordability-excel-template` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/affordability-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_affordability_qa.py`, `scripts/browser_qa.py` |
| `/api/bank-report` | `apps/web/app.js` | `tests/test_bank_views.py` | `scripts/browser_qa.py` |
| `/api/bank-timeline` | `apps/web/app.js` | `tests/test_bank_views.py` | — |
| `/api/bank-view` | `apps/web/app.js` | `tests/test_bank_views.py` | — |
| `/api/bank-views` | `apps/web/app.js` | `tests/test_bank_views.py` | — |
| `/api/bankruptcy-model-report` | `apps/web/app.js` | `tests/test_bankruptcy_model_views.py` | — |
| `/api/bankruptcy-model-view` | `apps/web/app.js` | `tests/test_bankruptcy_model_views.py` | — |
| `/api/bankruptcy-model-views` | `apps/web/app.js` | `tests/test_bankruptcy_model_views.py` | — |
| `/api/bankruptcy-report` | `apps/web/app.js` | `tests/test_bankruptcy_views.py` | `scripts/browser_bankruptcy_qa.py` |
| `/api/bankruptcy-view` | `apps/web/app.js` | `tests/test_bankruptcy_views.py` | — |
| `/api/bankruptcy-views` | `apps/web/app.js` | `tests/test_bankruptcy_views.py` | — |
| `/api/bond-report` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/bond-scenario` | `apps/web/app.js` | `tests/test_market_views.py` | — |
| `/api/business-archive` | `apps/web/app.js` | `tests/test_business_archive_http.py` | `scripts/browser_business_archive_qa.py` |
| `/api/business-archive-report` | `apps/web/app.js` | `tests/test_business_archive_http.py` | — |
| `/api/business-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_remaining_domains_qa.py`, `scripts/browser_sba_june_acceptance.py` |
| `/api/cfpb-mortgage-trends` | `apps/web/app.js` | `tests/test_cfpb_mortgage_trends.py` | `scripts/browser_qa.py` |
| `/api/cfpb-mortgage-trends-report` | `apps/web/app.js` | `tests/test_cfpb_mortgage_trends.py` | `scripts/browser_qa.py` |
| `/api/corporate-memo` | `apps/web/corporate-memos.js` | `tests/test_http_boundary.py` | `scripts/browser_corporate_memo_qa.py` |
| `/api/corporate-memo-report` | `apps/web/corporate-memos.js` | `tests/test_http_boundary.py` | — |
| `/api/corporate-memos` | `apps/web/corporate-memos.js` | `tests/test_http_boundary.py` | `scripts/browser_corporate_memo_qa.py` |
| `/api/country-report` | `apps/web/app.js` | `tests/test_country_views.py` | `scripts/browser_remaining_domains_qa.py` |
| `/api/country-view` | `apps/web/app.js` | — | `scripts/browser_sovereign_defaults_qa.py` |
| `/api/country-views` | `apps/web/app.js` | — | `scripts/browser_sovereign_defaults_qa.py` |
| `/api/episode-followup` | `apps/web/app.js`, `apps/web/monitor.js` | — | `scripts/browser_cure_acceptance.py`, `scripts/browser_qa.py` |
| `/api/evidence` | `apps/web/app.js` | — | `scripts/browser_source_run_acceptance.py` |
| `/api/exposure-aggregates` | `apps/web/app.js`, `apps/web/monitor.js` | — | `scripts/browser_monitor_qa.py`, `scripts/browser_product_workbench_qa.py` |
| `/api/exposure-convergence` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py` | `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-convergence-report` | `apps/web/app.js` | — | `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-convergence-studies` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py` | — |
| `/api/exposure-ecl` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py`, `tests/test_exposure_ecl_views.py` | `scripts/browser_p4_acceptance_qa.py`, `scripts/browser_product_workbench_qa.py` |
| `/api/exposure-ecl-report` | `apps/web/app.js` | `tests/test_exposure_ecl_views.py` | `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-ecl-studies` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py` | — |
| `/api/exposure-excel-import` | `apps/web/app.js` | `tests/test_excel_http.py`, `tests/test_excel_http_errors.py` | `scripts/browser_exposure_qa.py` |
| `/api/exposure-excel-report` | `apps/web/app.js` | — | `scripts/browser_product_workbench_qa.py`, `scripts/browser_qa.py` |
| `/api/exposure-excel-template` | `apps/web/app.js` | `tests/test_excel_http.py` | `scripts/browser_qa.py` |
| `/api/exposure-imports` | `apps/web/app.js` | `tests/test_exposure_views.py` | — |
| `/api/exposure-movement` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py`, `tests/test_exposure_movement_views.py` | `scripts/browser_movement_scope_qa.py`, `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-movement-report` | `apps/web/app.js` | `tests/test_exposure_movement_views.py` | `scripts/browser_movement_scope_qa.py`, `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-movements` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py` | — |
| `/api/exposure-report` | `apps/web/app.js` | `tests/test_exposure_views.py` | `scripts/browser_p4_acceptance_qa.py`, `scripts/browser_p4_concentration_qa.py` |
| `/api/exposure-scenario` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py`, `tests/test_exposure_scenario_views.py` | `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-scenario-report` | `apps/web/app.js` | `tests/test_exposure_scenario_views.py` | `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-scenarios` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py` | — |
| `/api/exposure-tail` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py`, `tests/test_exposure_tail_views.py` | `scripts/browser_p4_acceptance_qa.py`, `scripts/browser_product_workbench_qa.py` |
| `/api/exposure-tail-report` | `apps/web/app.js` | `tests/test_exposure_tail_views.py` | `scripts/browser_p4_acceptance_qa.py` |
| `/api/exposure-tail-studies` | `apps/web/app.js` | `tests/test_exposure_catalog_http.py` | — |
| `/api/fannie-samples` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_fannie_samples_qa.py`, `scripts/browser_qa.py` |
| `/api/fannie-samples-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py` |
| `/api/fed-bank-mortgage-context` | `apps/web/app.js` | `tests/test_fed_bank_mortgage_context.py` | `scripts/browser_qa.py` |
| `/api/fhfa-nmdb-performance` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/fhfa-nmdb-performance-report` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/fhfa-pudb-profile` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/fhfa-pudb-profile-report` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/finding-history` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/finding-report` | `apps/web/app.js` | — | `scripts/browser_finding_review_acceptance.py` |
| `/api/findings` | `apps/web/app.js` | `tests/test_http_boundary.py`, `tests/test_private_loan_scope.py` | `scripts/browser_finding_review_acceptance.py`, `scripts/browser_qa.py` |
| `/api/health` | — | `tests/test_hmda_cohort_views.py`, `tests/test_http_boundary.py` | — |
| `/api/hmda-aggregates` | `apps/web/app.js` | — | — |
| `/api/hmda-cohort` | `apps/web/app.js` | `tests/test_hmda_cohort_views.py`, `tests/test_workspace_catalog_http.py` | — |
| `/api/hmda-cohort-report` | `apps/web/app.js` | `tests/test_hmda_cohort_views.py` | — |
| `/api/hmda-cohorts` | `apps/web/app.js` | `tests/test_workspace_catalog_http.py` | — |
| `/api/hmda-labeled-aggregates` | `apps/web/app.js` | — | — |
| `/api/hmda-labeled-report` | `apps/web/app.js` | `tests/test_hmda_reference_views.py`, `tests/test_workspace_catalog_http.py` | `scripts/browser_qa.py` |
| `/api/hmda-reference` | `apps/web/app.js` | `tests/test_hmda_reference_views.py`, `tests/test_workspace_catalog_http.py` | — |
| `/api/hmda-references` | `apps/web/app.js` | `tests/test_workspace_catalog_http.py` | — |
| `/api/hmda-report` | `apps/web/app.js` | `tests/test_hmda_views.py`, `tests/test_workspace_catalog_http.py` | `scripts/browser_qa.py` |
| `/api/hmda-view` | `apps/web/app.js` | `tests/test_hmda_views.py`, `tests/test_workspace_catalog_http.py` | — |
| `/api/hmda-views` | `apps/web/app.js` | `tests/test_workspace_catalog_http.py` | — |
| `/api/hud-fha-iif-profile` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/hud-fha-iif-profile-report` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/hud-fha-performance` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/kpi-workbook` | `apps/web/monitor.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py` |
| `/api/lendingclub-full-source` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_lendingclub_full_source_qa.py` |
| `/api/lendingclub-full-source-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/lendingclub-source` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_lendingclub_source_qa.py` |
| `/api/lendingclub-source-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/loans` | `apps/web/app.js` | — | `scripts/browser_lifecycle_acceptance.py`, `scripts/browser_qa.py` |
| `/api/managed-pool` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py`, `scripts/browser_managed_pool_qa.py` |
| `/api/managed-pool-report` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py` |
| `/api/market-daily` | — | `tests/test_workspace_catalog_http.py` | — |
| `/api/market-report` | `apps/web/app.js` | `tests/test_market_views.py`, `tests/test_workspace_catalog_http.py` | `scripts/browser_qa.py` |
| `/api/market-view` | `apps/web/app.js` | `tests/test_market_views.py`, `tests/test_workspace_catalog_http.py` | — |
| `/api/market-views` | `apps/web/app.js` | `tests/test_workspace_catalog_http.py` | — |
| `/api/monitor-review` | `apps/web/monitor-reviews.js` | `tests/test_monitor_reviews.py` | `scripts/browser_monitor_review_qa.py` |
| `/api/monitor-review-report` | `apps/web/monitor-reviews.js` | `tests/test_monitor_reviews.py` | — |
| `/api/monitor-reviews` | `apps/web/monitor-reviews.js` | `tests/test_monitor_reviews.py` | `scripts/browser_monitor_review_qa.py` |
| `/api/monitoring` | `apps/web/app.js`, `apps/web/monitor.js` | — | `scripts/browser_panel_quality_acceptance.py`, `scripts/browser_qa.py` |
| `/api/mortgage-macro-context` | `apps/web/app.js` | `tests/test_mortgage_macro_context.py` | `scripts/browser_qa.py` |
| `/api/mortgage-provenance` | `apps/web/app.js` | — | `scripts/browser_mortgage_provenance.py`, `scripts/browser_qa.py` |
| `/api/mortgage-provenance-report` | `apps/web/app.js` | — | — |
| `/api/nmdb-performance` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nmdb-state-performance` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-dictionary` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | `scripts/browser_nsmo_wave_coverage_qa.py` |
| `/api/nsmo-domains` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-first-entry-risk-set-feasibility` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-first-observed-transition-support` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-horizon-sensitivity` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-origination-feasibility` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-profile` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-survey-returns` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/nsmo-target-feasibility` | `apps/web/nsmo.js` | `tests/test_nsmo_views.py` | — |
| `/api/observed-loss-details` | `apps/web/app.js` | — | `scripts/browser_observed_loss_details.py`, `scripts/browser_qa.py` |
| `/api/observed-loss-details-report` | `apps/web/app.js` | — | — |
| `/api/period-transitions` | `apps/web/app.js`, `apps/web/monitor.js` | — | `scripts/browser_qa.py`, `scripts/browser_transition_acceptance.py` |
| `/api/pool-history` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py`, `scripts/browser_pool_history_qa.py` |
| `/api/pool-history-report` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py` |
| `/api/portfolio-review` | `apps/web/app.js` | `tests/test_portfolio_reviews.py` | — |
| `/api/portfolio-review-report` | `apps/web/app.js` | `tests/test_portfolio_reviews.py` | — |
| `/api/portfolio-reviews` | `apps/web/app.js` | `tests/test_portfolio_reviews.py` | — |
| `/api/report` | `apps/web/app.js` | — | `scripts/browser_qa.py`, `scripts/browser_transition_acceptance.py` |
| `/api/retail-client-explanation` | `apps/web/app.js` | `tests/test_retail_cohort_explanation_views.py` | `scripts/browser_retail_cohort_explanations_qa.py` |
| `/api/retail-client-explanation-report` | `apps/web/app.js` | `tests/test_retail_cohort_explanation_views.py` | `scripts/browser_retail_cohort_explanations_qa.py` |
| `/api/retail-cohort-explanations` | `apps/web/app.js` | — | `scripts/browser_product_workbench_qa.py` |
| `/api/retail-data-contract` | `apps/web/app.js` | — | `scripts/browser_remaining_domains_qa.py`, `scripts/browser_retail_data_contract.py` |
| `/api/retail-data-contract-report` | `apps/web/app.js` | — | `scripts/browser_remaining_domains_qa.py` |
| `/api/retail-dossier` | `apps/web/app.js` | — | `scripts/browser_remaining_domains_qa.py`, `scripts/browser_retail_dossier.py` |
| `/api/retail-dossier-report` | `apps/web/app.js` | — | `scripts/browser_remaining_domains_qa.py` |
| `/api/retail-explanation` | `apps/web/app.js` | `tests/test_retail_cohort_explanation_views.py`, `tests/test_retail_explanation_views.py` | `scripts/browser_product_workbench_qa.py`, `scripts/browser_retail_explanations_qa.py` |
| `/api/retail-explanation-clients` | `apps/web/app.js` | `tests/test_retail_cohort_explanation_views.py` | — |
| `/api/retail-explanation-report` | `apps/web/app.js` | `tests/test_retail_explanation_views.py` | `scripts/browser_retail_explanations_qa.py` |
| `/api/retail-explanations` | `apps/web/app.js` | — | `scripts/browser_product_workbench_qa.py` |
| `/api/retail-policies` | `apps/web/app.js` | `tests/test_retail_policy_http.py` | `scripts/browser_task_race_qa.py` |
| `/api/retail-policy` | `apps/web/app.js`, `apps/web/monitor.js` | `tests/test_retail_policy_http.py` | `scripts/browser_kpi_analysis_qa.py`, `scripts/browser_retail_policy_qa.py` |
| `/api/retail-policy-preview` | `apps/web/app.js` | `tests/test_retail_policy_http.py` | `scripts/browser_retail_policy_qa.py` |
| `/api/retail-policy-report` | `apps/web/app.js` | `tests/test_retail_policy_http.py` | — |
| `/api/retail-source-quality` | `apps/web/monitor.js` | `tests/test_retail_source_quality.py` | `scripts/browser_retail_source_quality_qa.py` |
| `/api/retail-source-quality-report` | — | `tests/test_retail_source_quality.py` | — |
| `/api/retail-subgroup` | `apps/web/app.js` | `tests/test_retail_subgroup_views.py` | `scripts/browser_remaining_domains_qa.py` |
| `/api/retail-subgroup-report` | `apps/web/app.js` | `tests/test_retail_subgroup_views.py` | `scripts/browser_remaining_domains_qa.py` |
| `/api/retail-subgroups` | `apps/web/app.js` | `tests/test_retail_subgroup_views.py` | — |
| `/api/runs` | `apps/web/app.js` | — | `scripts/browser_abs_qa.py`, `scripts/browser_bank_qa.py`, `scripts/browser_bankruptcy_model_qa.py`, `scripts/browser_bankruptcy_qa.py`, `scripts/browser_country_qa.py`, `scripts/browser_exposure_qa.py`, `scripts/browser_hmda_qa.py`, `scripts/browser_market_qa.py`, `scripts/browser_qa.py`, `scripts/browser_retail_cohort_explanations_qa.py`, `scripts/browser_retail_explanations_qa.py`, `scripts/browser_retail_policy_qa.py`, `scripts/browser_retail_subgroups_qa.py`, `scripts/browser_sec_qa.py`, `scripts/browser_source_run_acceptance.py`, `scripts/browser_suite_qa.py` |
| `/api/sec-annual-debt-bridge` | `apps/web/app.js` | — | `scripts/browser_annual_debt_bridge_qa.py` |
| `/api/sec-annual-debt-bridge-report` | `apps/web/app.js` | — | — |
| `/api/sec-coverage` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py`, `scripts/browser_sec_coverage_qa.py` |
| `/api/sec-coverage-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py` |
| `/api/sec-debt` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py`, `scripts/browser_sec_debt_qa.py`, `scripts/browser_sec_debt_workbook_qa.py` |
| `/api/sec-debt-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/sec-debt-workbook` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py`, `scripts/browser_sec_debt_workbook_qa.py` |
| `/api/sec-events` | `apps/web/app.js` | `tests/test_sec_events.py` | `scripts/browser_sec_events_qa.py` |
| `/api/sec-events-report` | `apps/web/app.js` | `tests/test_sec_events.py` | — |
| `/api/sec-facilities` | `apps/web/app.js` | `tests/test_facilities.py` | `scripts/browser_facilities_qa.py` |
| `/api/sec-facilities-report` | `apps/web/app.js` | `tests/test_facilities.py` | — |
| `/api/sec-note-rules` | `apps/web/app.js` | `tests/test_note_rules.py` | `scripts/browser_note_rules_qa.py` |
| `/api/sec-note-rules-report` | `apps/web/app.js` | `tests/test_note_rules.py` | — |
| `/api/sec-note-schedule` | `apps/web/app.js` | `tests/test_note_schedules.py` | `scripts/browser_note_schedule_qa.py` |
| `/api/sec-note-schedule-report` | `apps/web/app.js` | `tests/test_note_schedules.py` | — |
| `/api/sec-report` | `apps/web/app.js`, `apps/web/monitor.js` | `tests/test_sec_views.py`, `tests/test_workspace_catalog_http.py` | `scripts/browser_kpi_analysis_qa.py`, `scripts/browser_sec_normalization_acceptance.py` |
| `/api/sec-trend` | `apps/web/app.js` | `tests/test_sec_trends.py` | `scripts/browser_sec_trends_qa.py` |
| `/api/sec-trend-report` | `apps/web/app.js` | `tests/test_sec_trends.py` | — |
| `/api/sec-view` | `apps/web/app.js` | `tests/test_workspace_catalog_http.py` | — |
| `/api/sec-views` | `apps/web/app.js` | `tests/test_workspace_catalog_http.py` | — |
| `/api/sec-workbook` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_qa.py`, `scripts/browser_sec_workbook_qa.py` |
| `/api/snapshot` | `apps/web/app.js`, `apps/web/monitor.js` | `tests/test_http_boundary.py` | `scripts/browser_competing_acceptance.py`, `scripts/browser_kpi_analysis_qa.py`, `scripts/browser_portfolio_acceptance.py`, `scripts/browser_qa.py` |
| `/api/sovereign-defaults` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_remaining_domains_qa.py`, `scripts/browser_sovereign_archive_qa.py`, `scripts/browser_sovereign_defaults_qa.py` |
| `/api/sovereign-defaults-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_remaining_domains_qa.py` |
| `/api/studies` | `apps/web/app.js` | — | `scripts/browser_qa.py` |
| `/api/suite-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/suite-view` | `apps/web/app.js`, `apps/web/monitor.js` | `tests/test_http_boundary.py` | `scripts/browser_kpi_analysis_qa.py`, `scripts/browser_product_workbench_qa.py`, `scripts/browser_remaining_domains_qa.py` |
| `/api/suite-views` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |
| `/api/timeline` | `apps/web/app.js` | — | `scripts/browser_cure_acceptance.py`, `scripts/browser_lifecycle_acceptance.py`, `scripts/browser_qa.py` |
| `/api/utility-debt-service` | `apps/web/app.js` | `tests/test_http_boundary.py` | `scripts/browser_utility_debt_qa.py` |
| `/api/utility-debt-service-report` | `apps/web/app.js` | `tests/test_http_boundary.py` | — |

## Evidence review — 16/10/2026

The API serves 176 distinct path literals. A source-only reference count finds
50 routes with no direct route string in a test file and 69 with no direct
route string in a browser-QA script; these are triage signals, not proof of
missing coverage, because generic dispatch or helper-based tests may cover
routes without repeating their literal path.

The CFPB Mortgage Performance Trends view and report now have direct HTTP
contract coverage for selected-county payloads, the server attachment name,
invalid query rejection, and tampered-source failure behavior in
`tests/test_cfpb_mortgage_trends.py`. The response marks the aggregate report
private and not approved for public release.

P4 Portfolio catalog routes now
have direct HTTP contract tests for `/api/exposure-imports`,
`/api/exposure-convergence-studies`, `/api/exposure-tail-studies`,
`/api/exposure-ecl-studies`, `/api/exposure-scenarios`, and
`/api/exposure-movements`. The five study catalogs require exactly their
source ID and return the catalog payload unchanged; malformed or extra
filters fail with HTTP 400. Evidence: `tests/test_exposure_views.py` and
`tests/test_exposure_catalog_http.py`.

Portfolio Excel template/import and source-bound review/report have their
own HTTP or browser checks. New direct HTTP contracts cover the HMDA, SEC,
and Market catalogs plus SEC/Market snapshots. HTTP tests also exercise
HMDA aggregate/labeled reports, SEC issuer reports, Market reports and
daily-series response forwarding, cache headers, and download attachment
behavior; see `tests/test_workspace_catalog_http.py`. These contracts use
controlled service responses and do not replace real-source data QA or
full browser acceptance for every UI download path. M01-028 stays Partial
until remaining report families, real-source failure paths and UI download
flows have independent evidence.
