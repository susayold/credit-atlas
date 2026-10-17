import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [rootArg, outputArg, previewArg] = process.argv.slice(2);
if (!rootArg || !outputArg) throw new Error("usage: build_d02_data_reference.mjs <root> <output.xlsx>");
const root = path.resolve(rootArg);
const output = path.resolve(outputArg);
const previewPath = previewArg ? path.resolve(previewArg) : null;

const sources = [
  { sheet: "NSMO fields", file: "nsmo-v70-field-dictionary.csv", table: "NsmoFields", headers: {
    codebook_order: "Codebook order", csv_column: "CSV field name", codebook_name: "Codebook variable name",
    codebook_part: "Codebook section", survey_wave_ranges: "Waves in codebook", survey_question_refs: "Question reference",
    codebook_condition: "Routing / condition", wave_variant_flags: "Wave variation flags", quarter: "Quarter",
    pdf_page: "PDF page", printed_page: "Printed page", field_family: "Field group", timing_class: "Timing",
    predictor_use: "Predictor-use gate", sas_length: "SAS length", sas_format: "SAS format", sas_label: "SAS label / description",
  } },
  { sheet: "NSMO feature gates", file: "nsmo-v70-predictor-gates.csv", table: "NsmoFeatureGates", headers: {
    codebook_order: "Codebook order", csv_column: "CSV field name", codebook_name: "Codebook name",
    field_family: "Field family", timing_class: "Measurement timing", publisher_predictor_gate: "Publisher gate",
    eligibility_bucket: "CreditAtlas use boundary", intended_scope: "Intended scope", decision_status: "Current approval status",
    required_review: "Open review before use", sas_label: "Variable label",
  }, numeric: new Set(["codebook_order"]) },
  { sheet: "NSMO routing", file: "nsmo-v70-routing-review.csv", table: "NsmoRoutingReview", headers: {
    codebook_order: "Codebook order", csv_column: "CSV field name", codebook_name: "Codebook name",
    survey_question_refs: "Original codebook question reference", resolved_question_refs: "Reconciled question number",
    question_reference_status: "Question-reference reconciliation", reference_evidence: "Reference evidence",
    questionnaire_wave_coverage: "Questionnaire package wave coverage", label_phrase_check: "Label phrase check",
    survey_wave_ranges: "Codebook wave range",
    codebook_condition: "Codebook routing condition", routing_gate_fields: "Routing gate field(s)",
    routing_gate_questions: "Routing gate question(s)", routing_gate_resolution: "Gateway resolution",
    wave_variant_flags: "Wave variation flags",
    route_review_status: "Routing review status", predictor_use: "Publisher predictor gate",
    routing_review_required: "Open routing check",
  }, numeric: new Set(["codebook_order"]) },
  { sheet: "NSMO question refs", file: "nsmo-v70-question-reference-reconciliation.csv", table: "NsmoQuestionRefs", headers: {
    csv_column: "CSV field name", question_ref: "Question ref", questionnaire_wave_coverage: "Questionnaire waves",
    label_phrase_check: "Label phrase check", reference_basis: "Reference basis / evidence",
    codebook_page: "Codebook PDF page", printed_page: "Printed codebook page",
  } },
  { sheet: "NSMO categories", file: "nsmo-v70-value-labels.csv", table: "NsmoCategories", headers: {
    format_name: "SAS format", format_value: "Category code (preserved)", format_label: "Category label",
  } },
  { sheet: "NSMO wave coverage", file: "nsmo-v70-wave-coverage.csv", table: "NsmoWaveCoverage", headers: {
    csv_column: "CSV field name", sas_label: "SAS label / question", sas_format: "SAS format", question_refs: "Question reference",
    codebook_variant_flags: "Codebook variation flags", puf_nonmissing_value_waves: "PUF waves with nonmissing values (may be imputed)",
    entirely_not_asked_waves: "Entirely not asked (-3)", partially_not_asked_waves: "Partially not asked (-3)",
    not_applicable_waves: "Not applicable (-2)", waves_with_missing_code: "Waves with missing code", interpretation: "Interpretation / limitation",
  } },
  { sheet: "NSMO item wording", file: "nsmo-v70-wave-item-comparability.csv", table: "NsmoItemWording", headers: {
    field: "CSV field name", sas_label: "SAS label / question", puf_nonmissing_value_waves: "PUF waves with nonmissing values (may be imputed)",
    not_asked_waves: "Waves not asked", question_refs: "Question reference", sas_format: "SAS format",
    scale_labels: "Response-scale labels", exact_item_phrase_found_in_packages: "Questionnaire packages with exact phrase",
    assessment: "Comparability assessment",
  } },
  { sheet: "NSMO returns", file: "nsmo-v70-survey-returns.csv", table: "NsmoSurveyReturns", headers: {
    survey_wave: "Survey wave", average_sampling_weight: "Average sampling weight", surveys_mailed: "Surveys mailed",
    postal_nondelivery: "Postal non-delivery", surveys_delivered: "Surveys delivered",
    surveys_completed_total: "Surveys completed", completed_by_mail: "Completed by mail",
    online_english: "Online English", online_spanish: "Online Spanish", opt_out: "Opt-outs",
    completion_pct_of_mailed: "Completion (%) of mailed", completion_pct_of_delivered: "Completion (%) of delivered",
    mail_share_pct_of_completed: "Mail share (%) of completed", online_share_pct_of_completed: "Online share (%) of completed",
    online_english_share_pct_of_completed: "Online English share (%)", online_spanish_share_pct_of_completed: "Online Spanish share (%)",
    included_in_nsmo_v70_puf: "Included in v7.0 PUF", source_note: "FHFA table note", source_pdf_page: "Report page",
  }, numeric: new Set(["survey_wave", "average_sampling_weight", "surveys_mailed", "postal_nondelivery", "surveys_delivered", "surveys_completed_total", "completed_by_mail", "online_english", "online_spanish", "opt_out", "completion_pct_of_mailed", "completion_pct_of_delivered", "mail_share_pct_of_completed", "online_share_pct_of_completed", "online_english_share_pct_of_completed", "online_spanish_share_pct_of_completed", "source_pdf_page"]), bool: new Set(["included_in_nsmo_v70_puf"]) },
  { sheet: "NSMO usability", file: "nsmo-v70-usable-responses.csv", table: "NsmoUsability", headers: {
    survey_wave: "Survey wave", surveys_completed_total: "Completed returns · Table 4",
    duplicate_or_ineligible: "Duplicate / ineligible", answered_no_to_q1: "Answered no to Q1",
    did_not_finish_survey: "Did not finish", wrong_loan: "Wrong loan",
    usable_responses_table4: "Usable returns · Table 4",
    usable_responses_origination_2013_2024_tables5_6: "Usable · 2013–2024 origination tables",
    gap_to_usable_table4: "Outside Table 5/6 scope",
    source_pdf_page_table4: "Table 4 PDF page", source_pdf_pages_tables5_6: "Tables 5/6 PDF pages",
    source_note: "Publisher scope note",
  }, numeric: new Set(["survey_wave", "surveys_completed_total", "duplicate_or_ineligible", "answered_no_to_q1", "did_not_finish_survey", "wrong_loan", "usable_responses_table4", "usable_responses_origination_2013_2024_tables5_6", "gap_to_usable_table4", "source_pdf_page_table4"]) },
  { sheet: "NMDB quarterly", file: "nmdb-performance-national-quarterly-2026q2.csv", table: "NmdbQuarterly", headers: {
    source: "Source", frequency: "Frequency", geo_level: "Geography level", geo_id: "Geography ID", geo_name: "Geography name",
    market: "Mortgage market", period: "Quarter", year: "Year", quarter: "Quarter number", month: "Quarter-end month",
    suppressed: "Suppressed", series_id: "Series ID", value_pct: "Rate (%)",
  }, numeric: new Set(["year", "quarter", "value_pct"]), bool: new Set(["suppressed"]) },
  { sheet: "FHFA HPI state", file: "fhfa-state-all-transactions-hpi-quarterly-2026q2.csv", table: "FhfaStateHpi", headers: {
    state_code: "State / DC", year: "Year", quarter: "Quarter",
    index_nsa: "All-transactions HPI (NSA; 1980Q1=100)",
  }, numeric: new Set(["year", "quarter", "index_nsa"]) },
  { sheet: "HUD monthly", file: "hud-fha-performance-2026-08.csv", table: "HudMonthly", headers: {
    month: "Month", adjustment: "Seasonal adjustment", active_iif_count: "Active FHA-insured loans",
    delinquency_30d_pct: "30-day delinquency (%)", delinquency_60d_pct: "60-day delinquency (%)",
    delinquency_90d_pct: "90-day delinquency (%)", foreclosure_pct: "Foreclosure (%)", bankruptcy_pct: "Bankruptcy (%)",
    serious_delinquency_pct: "Serious delinquency (%)", source_table: "HUD source table", source_page: "Report page",
  }, numeric: new Set(["active_iif_count", "delinquency_30d_pct", "delinquency_60d_pct", "delinquency_90d_pct", "foreclosure_pct", "bankruptcy_pct", "serious_delinquency_pct"]) },
  { sheet: "HUD subgroups", file: "hud-fha-performance-2026-08-subgroups.csv", table: "HudSubgroups", headers: {
    dimension: "Dimension", parent_category: "Parent category", category: "Category", iif_count: "Active FHA-insured loans",
    iif_share_pct: "Share of active loans (%)", share_denominator: "Share denominator", all_past_due_pct: "Any past due (%)",
    delinquency_30d_pct: "30-day delinquency (%)", delinquency_60d_pct: "60-day delinquency (%)",
    delinquency_90plus_pct: "90+ delinquency (%)", foreclosure_pct: "Foreclosure (%)", bankruptcy_pct: "Bankruptcy (%)",
    serious_delinquency_pct: "Serious delinquency (%)", source_table: "HUD source table", source_page: "Report page",
  }, numeric: new Set(["iif_count", "iif_share_pct", "all_past_due_pct", "delinquency_30d_pct", "delinquency_60d_pct", "delinquency_90plus_pct", "foreclosure_pct", "bankruptcy_pct", "serious_delinquency_pct"]) },
  { sheet: "HUD 90+ reasons", file: "hud-fha-new-90plus-reasons-2026-08.csv", table: "Hud90PlusReasons", headers: {
    fiscal_period: "Fiscal period", new_90plus_count: "New 90+ loans", reduction_income_pct: "Income reduction (%)",
    unemployed_pct: "Unemployed (%)", excessive_obligations_pct: "Excessive obligations (%)",
    death_illness_pct: "Death / illness (%)", marital_difficulties_pct: "Marital difficulties (%)",
    no_contact_pct: "Unable to contact (%)", national_emergency_pct: "National emergency (%)",
    other_pct: "Other reason (%)", source_table: "HUD source table", source_page: "Report page", partial_period: "Partial period",
  }, numeric: new Set(["new_90plus_count", "reduction_income_pct", "unemployed_pct", "excessive_obligations_pct", "death_illness_pct", "marital_difficulties_pct", "no_contact_pct", "national_emergency_pct", "other_pct", "source_page"]), bool: new Set(["partial_period"]) },
  { sheet: "HUD foreclosure", file: "hud-fha-foreclosure-statistics-2026-08.csv", table: "HudForeclosure", headers: {
    fiscal_year: "Fiscal year", month: "Month", active_iif_count: "Active FHA-insured loans",
    foreclosure_starts: "Foreclosure starts", in_foreclosure_count: "Loans in foreclosure",
    foreclosure_claims_paid: "Foreclosure claims paid", foreclosure_starts_6m_moving_avg: "6-month starts average",
    annualized_foreclosure_rate_pct: "Annualized foreclosure rate (%)", source_table: "HUD source table", source_page: "Report page",
  }, numeric: new Set(["fiscal_year", "active_iif_count", "foreclosure_starts", "in_foreclosure_count", "foreclosure_claims_paid", "foreclosure_starts_6m_moving_avg", "annualized_foreclosure_rate_pct", "source_page"]) },
  { sheet: "HUD REO recovery", file: "hud-fha-reo-recovery-2026-08.csv", table: "HudReoRecovery", headers: {
    state_or_territory: "State / territory", dispositions_jul2026: "Dispositions · Jul 2026",
    recovery_jul2026_pct: "Recovery · Jul 2026 (%)", recovery_jun2026_pct: "Recovery · Jun 2026 (%)",
    recovery_jul2025_pct: "Recovery · Jul 2025 (%)", change_from_jun2026_pp: "Change vs Jun 2026 (pp)",
    change_from_jul2025_pp: "Change vs Jul 2025 (pp)", source_table: "HUD source table", source_page: "Report page",
  }, numeric: new Set(["dispositions_jul2026", "recovery_jul2026_pct", "recovery_jun2026_pct", "recovery_jul2025_pct", "change_from_jun2026_pp", "change_from_jul2025_pp", "source_page"]) },
  { sheet: "HUD REO loss", file: "hud-fha-reo-loss-components-2026-08.csv", table: "HudReoLoss", headers: {
    disposition_month: "Disposition month", claim_expenses_pct: "Claim expenses (%)", holding_costs_pct: "Holding costs (%)",
    loss_on_collateral_pct: "Loss on collateral (%)", sales_expense_pct: "Sales expenses (%)",
    program_discounts_pct: "Program discounts (%)", net_loss_rate_pct: "Net loss rate (%)",
    average_dollar_loss: "Average dollar loss ($)", average_unpaid_balance: "Average unpaid balance ($)",
    dispositions: "Dispositions", discounts: "Discounts", delinquency_stage_months: "Delinquency stage (months)",
    foreclosure_stage_months: "Foreclosure stage (months)", deed_transfer_stage_months: "Deed transfer stage (months)",
    reo_stage_months: "REO stage (months)", all_stages_months: "All stages (months)",
    source_table: "HUD source table", source_page: "Report page",
  }, numeric: new Set(["claim_expenses_pct", "holding_costs_pct", "loss_on_collateral_pct", "sales_expense_pct", "program_discounts_pct", "net_loss_rate_pct", "average_dollar_loss", "average_unpaid_balance", "dispositions", "discounts", "delinquency_stage_months", "foreclosure_stage_months", "deed_transfer_stage_months", "reo_stage_months", "all_stages_months", "source_page"]) },
];

const wb = Workbook.create();
const guide = wb.worksheets.add("Start here");
guide.showGridLines = false;
const guideRows = [
  ["CreditAtlas · D02 data reference workbook", ""],
  ["Purpose", "Excel copy of the D02 reference tables and public aggregate datasets, arranged by source for filtering and review."],
  ["NSMO", "Field dictionary, feature timing gates, a 319-field routing review, category labels, wave coverage, item wording, response mode and usable-response disposition by wave. Values -2 and -3 remain distinct source codes."],
  ["Model gates", "The feature-gates sheet classifies all 587 fields by timing and scope. It is a review inventory, not an approved feature allowlist; no model feature is currently approved."],
  ["Item routing", "The routing sheet crosswalks all 319 survey-response fields to question references and codebook conditions. Seven previously missing references are reconciled to questionnaire question numbers; a historical wording variant remains flagged."],
  ["Question references", "The reconciliation sheet preserves original references beside the questionnaire number and evidence; it does not claim full wave/mode routing is resolved."],
  ["Response mode", "Tables 3–6 show aggregate returns, usability exclusions and 2013–2024 origination scope. The v7.0 PUF has 62,359 mortgages from waves 1–46; no row-level mode link is published."],
  ["X-variable imputation", "FHFA may impute missing survey responses into X variables. The public PUF has no item-level J flags to identify each imputed value; selected Z fields mark actual answers only for certain items. Wave coverage is nonmissing PUF-value availability, not a borrower response rate."],
  ["NMDB", "National quarterly aggregate mortgage performance through 2026Q2. One row is a market × series × quarter, not a loan."],
  ["FHFA HPI", "Quarterly state/DC All-Transactions HPI through 2026Q2. Index, not dollar value; current history is retrospective and not point-in-time."],
  ["HUD FHA", "Monthly trend, subgroups, new-90+ reason shares, foreclosure pipeline, REO recovery by geography and REO loss components through August 2026. These are not NSMO loan records."],
  ["HUD interpretation", "New-90+ reason shares sum to 100% and describe reported reasons, not predictive drivers. Foreclosure starts/claims/rates are separate measures. REO recovery percentages may exceed 100%; negative changes are percentage-point changes. Loss components are not exhaustive or additive."],
  ["Use", "Each data sheet has an Excel Table with filters. The top row and first identifier column remain fixed while scrolling."],
  ["Interpretation", "Keep the source population, denominator and metric definition with each dataset. Do not join these separate programs into NSMO mortgage rows."],
  ["Refresh", "The CSV files in docs/data remain the canonical app inputs. Rebuild this workbook after updating those source tables."],
  ["Source files", "See docs/data and the source review pages for source URLs, versions, receipts and detailed limitations."],
];
guide.getRange(`A1:B${guideRows.length}`).values = guideRows;
guide.getRange("A1:B1").merge();
guide.getRange("A1:B1").format = { fill: "#243B53", font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" }, verticalAlignment: "center", wrapText: true };
guide.getRange(`A2:A${guideRows.length}`).format = { font: { bold: true, color: "#243B53" }, verticalAlignment: "top", wrapText: true };
guide.getRange(`A1:B${guideRows.length}`).format.wrapText = true;
guide.getRange("A:A").format.columnWidth = 22;
guide.getRange("B:B").format.columnWidth = 112;
guide.getRange("A1:B1").format.rowHeight = 34;
guide.getRange(`A2:B${guideRows.length}`).format.rowHeight = 38;

for (const source of sources) {
  const csv = await fs.readFile(path.join(root, "docs", "data", source.file), "utf8");
  const imported = await Workbook.fromCSV(csv, { sheetName: "Source" });
  const sourceRows = imported.worksheets.getItem("Source").getUsedRange().values;
  const rawHeaders = sourceRows[0].map((name) => String(name).replace(/^\uFEFF/, ""));
  const header = rawHeaders.map((name) => source.headers[name] ?? name);
  const rows = sourceRows.slice(1).filter((row) => row.some((cell) => cell !== null && cell !== ""));
  const values = rows.map((row) => row.map((cell, index) => {
    if (cell == null || cell === "") return "";
    const name = rawHeaders[index];
    if (source.numeric?.has(name)) return Number(cell);
    if (source.bool?.has(name)) return ["1", "true"].includes(String(cell).toLowerCase());
    return String(cell);
  }));
  const sheet = wb.worksheets.add(source.sheet);
  sheet.showGridLines = false;
  sheet.getRangeByIndexes(0, 0, values.length + 1, header.length).values = [header, ...values];
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  const lastCol = columnName(header.length);
  const table = sheet.tables.add(`A1:${lastCol}${values.length + 1}`, true, source.table);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.getRangeByIndexes(0, 0, 1, header.length).format = {
    fill: "#243B53", font: { bold: true, color: "#FFFFFF", size: 10 },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
  };
  sheet.getRangeByIndexes(1, 0, values.length, header.length).format = { verticalAlignment: "top", wrapText: true };
  sheet.getRangeByIndexes(0, 0, 1, header.length).format.rowHeight = 42;
  for (let index = 0; index < header.length; index += 1) {
    const samples = values.slice(0, 50).map((row) => String(row[index] ?? "").length);
    const width = Math.min(60, Math.max(14, Math.min(46, Math.max(header[index].length, ...samples) + 2)));
    sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width;
  }
  if (source.sheet.startsWith("NMDB")) {
    const rateColumn = header.indexOf("Rate (%)");
    sheet.getRange(`${columnName(rateColumn + 1)}2:${columnName(rateColumn + 1)}${values.length + 1}`).format.numberFormat = '0.0"%"';
  }
  if (source.sheet === "FHFA HPI state") {
    const indexColumn = header.indexOf("All-transactions HPI (NSA; 1980Q1=100)");
    sheet.getRange(`${columnName(indexColumn + 1)}2:${columnName(indexColumn + 1)}${values.length + 1}`).format.numberFormat = "0.00";
  }
  if (source.sheet === "NSMO returns") {
    for (const name of header.filter((item) => item.includes("(%)"))) {
      const index = header.indexOf(name);
      sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${values.length + 1}`).format.numberFormat = '0.00"%"';
    }
  }
  for (const name of header.filter((item) => item.includes("(%)"))) {
    const index = header.indexOf(name);
    sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${values.length + 1}`).format.numberFormat = '0.00"%"';
  }
  for (const name of header.filter((item) => item.includes("(pp)"))) {
    const index = header.indexOf(name);
    sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${values.length + 1}`).format.numberFormat = '0.00" pp"';
  }
  for (const name of header.filter((item) => /count|loans|starts|claims|dispositions|discounts|\(\$\)/i.test(item))) {
    const index = header.indexOf(name);
    sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${values.length + 1}`).format.numberFormat = "#,##0";
  }
}

const definitions = wb.worksheets.add("NMDB definitions");
definitions.showGridLines = false;
const definitionRows = [
  ["Topic", "Definition / use", "Source note"],
  ["P3089DL", "Active loans in the combined 30–59 and 60–89 days-past-due categories divided by active loans at quarter end.", "FHFA combines these categories in P3089DL; label as 30–89 DPD."],
  ["P90DL", "Active loans at least 90 days past due divided by active loans at quarter end.", "Serious delinquency category, excluding foreclosure/bankruptcy series."],
  ["PFORECL", "Active loans in foreclosure, bankruptcy or deed-in-lieu divided by active loans at quarter end.", "Separate published category."],
  ["PFORB", "Active loans reported in forbearance divided by active loans at quarter end.", "Published from 2019Q4; earlier source cells are blank."],
  ["Denominator", "Active mortgages with performance data at quarter end.", "Not a fixed-horizon cohort denominator."],
  ["Preliminary periods", "FHFA states the latest two quarters may be revised as reporting lags close.", "Treat 2026Q1–2026Q2 as preliminary."],
  ["History limitation", "Seriously past-due loans may be undercounted between 2006 and 2012 due to credit-history purges.", "Avoid attributing the period only to changing borrower risk."],
  ["Scope", "Aggregate 5% NMDB sample; no individual loan records or model-ready outcomes.", "Do not pool with NSMO or HUD FHA."],
  ["Source", "FHFA NMDB Residential Mortgage Performance Statistics, 2002Q1–2026Q2.", "https://www.fhfa.gov/data/nmdb"],
];
definitions.getRangeByIndexes(0, 0, definitionRows.length, 3).values = definitionRows;
definitions.freezePanes.freezeRows(1);
definitions.freezePanes.freezeColumns(1);
const defTable = definitions.tables.add(`A1:C${definitionRows.length}`, true, "NmdbDefinitions");
defTable.style = "TableStyleMedium2";
definitions.getRange("A1:C1").format = { fill: "#243B53", font: { bold: true, color: "#FFFFFF" }, wrapText: true, rowHeight: 34 };
definitions.getRange("A:A").format.columnWidth = 24;
definitions.getRange("B:B").format.columnWidth = 96;
definitions.getRange("C:C").format.columnWidth = 72;
definitions.getRange(`A2:C${definitionRows.length}`).format = { verticalAlignment: "top", wrapText: true };

const hudDefinitions = wb.worksheets.add("HUD definitions");
hudDefinitions.showGridLines = false;
const hudRows = [
  ["Topic", "Definition / use", "Interpretation boundary"],
  ["New 90+ reasons", "Distribution of reported reasons among newly 90+ FHA loans; reason shares sum to 100%.", "Descriptive reason coding, not a predictor contribution or causal explanation. Q4 July/August 2026 are partial periods."],
  ["Foreclosure starts", "New starts during the month; the 6-month moving average smooths monthly counts.", "A flow measure, distinct from the stock in foreclosure or paid claims."],
  ["In foreclosure", "Count of active loans in the foreclosure process at the reporting date.", "A stock measure, not the monthly foreclosure-start rate."],
  ["Annualized foreclosure rate", "HUD-reported monthly foreclosure claims divided by beginning insurance-in-force (IIF), annualized.", "Not directly comparable with the in-foreclosure portfolio share."],
  ["REO recovery", "Proceeds/recovery as a percentage of unpaid principal balance at default, by state/territory.", "May exceed 100%; small disposition counts can make geography rates volatile. Blank means publisher did not report a value."],
  ["REO recovery change", "Difference between reported recovery rates, in percentage points.", "Negative values indicate a lower recovery rate than the comparison period."],
  ["Loss components", "HUD-reported loss/cost categories, average dollar amounts, counts and stage durations.", "Categories are not exhaustive and do not sum to the net loss rate."],
  ["Scope", "HUD FHA Single-Family Loan Performance Trends, August 2026; aggregate portfolio evidence.", "Keep separate from NSMO loan-level records, targets and model-training samples."],
  ["Source", "https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf", "Tables 1–6; report pages 2–8."],
];
hudDefinitions.getRangeByIndexes(0, 0, hudRows.length, 3).values = hudRows;
hudDefinitions.freezePanes.freezeRows(1);
hudDefinitions.freezePanes.freezeColumns(1);
const hudTable = hudDefinitions.tables.add(`A1:C${hudRows.length}`, true, "HudDefinitions");
hudTable.style = "TableStyleMedium2";
hudDefinitions.getRange("A1:C1").format = { fill: "#243B53", font: { bold: true, color: "#FFFFFF" }, wrapText: true, rowHeight: 34 };
hudDefinitions.getRange("A:A").format.columnWidth = 28;
hudDefinitions.getRange("B:B").format.columnWidth = 90;
hudDefinitions.getRange("C:C").format.columnWidth = 98;
hudDefinitions.getRange(`A2:C${hudRows.length}`).format = { verticalAlignment: "top", wrapText: true };

const hpiDefinitions = wb.worksheets.add("FHFA HPI definitions");
hpiDefinitions.showGridLines = false;
const hpiRows = [
  ["Topic", "Definition / use", "Source note"],
  ["Index", "FHFA All-Transactions House Price Index for states and DC; repeat-sales index using sales prices and appraisal data.", "This is an index, not a median dollar house price or property-level valuation."],
  ["Frequency", "Quarterly; latest row in this snapshot is 2026Q2.", "Current two-quarter file is a downloaded snapshot and may be revised in future releases."],
  ["Seasonal adjustment", "Not seasonally adjusted (NSA).", "Compare consistent quarters or calculate year-over-year changes to reduce seasonal effects."],
  ["Base", "1980Q1=100.", "Index points are relative to the base period; do not read as dollars or percent change."],
  ["Coverage", "50 states plus District of Columbia, 1975Q1–2026Q2.", "One row per state/DC and quarter; no loan, borrower or property identifiers."],
  ["Credit-risk use", "Aggregate housing-market context for portfolio or cohort review when geography and denominator align.", "Do not treat as an individual collateral value, LTV, borrower predictor or observed loan outcome."],
  ["Point-in-time boundary", "Current historical series does not preserve prior publication vintages.", "Do not use as-of model feature until release availability, revisions and observation lag are handled."],
  ["Source data", "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_state.csv", "FHFA HPI datasets, dictionary and downloadable-file specification."],
];
hpiDefinitions.getRangeByIndexes(0, 0, hpiRows.length, 3).values = hpiRows;
hpiDefinitions.freezePanes.freezeRows(1);
hpiDefinitions.freezePanes.freezeColumns(1);
const hpiTable = hpiDefinitions.tables.add(`A1:C${hpiRows.length}`, true, "FhfaHpiDefinitions");
hpiTable.style = "TableStyleMedium2";
hpiDefinitions.getRange("A1:C1").format = { fill: "#243B53", font: { bold: true, color: "#FFFFFF" }, wrapText: true, rowHeight: 34 };
hpiDefinitions.getRange("A:A").format.columnWidth = 25;
hpiDefinitions.getRange("B:B").format.columnWidth = 88;
hpiDefinitions.getRange("C:C").format.columnWidth = 94;
hpiDefinitions.getRange(`A2:C${hpiRows.length}`).format = { verticalAlignment: "top", wrapText: true };

wb.recalculate();
const inspection = await wb.inspect({ kind: "workbook,sheet,table", maxChars: 6000, tableMaxRows: 2, tableMaxCols: 5 });
console.log(inspection.ndjson);
if (previewPath) {
  const preview = await wb.render({ sheetName: "Start here", autoCrop: "all", scale: 1, format: "png" });
  await fs.mkdir(path.dirname(previewPath), { recursive: true });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(path.dirname(output), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(output);
console.log(JSON.stringify({ status: "exported", output, workbookSheets: sources.length + 4 }));

function columnName(index) {
  let result = "";
  while (index > 0) {
    const remainder = (index - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    index = Math.floor((index - 1) / 26);
  }
  return result;
}
