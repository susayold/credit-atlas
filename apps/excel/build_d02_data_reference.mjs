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
  { sheet: "NSMO categories", file: "nsmo-v70-value-labels.csv", table: "NsmoCategories", headers: {
    format_name: "SAS format", format_value: "Category code (preserved)", format_label: "Category label",
  } },
  { sheet: "NSMO wave coverage", file: "nsmo-v70-wave-coverage.csv", table: "NsmoWaveCoverage", headers: {
    csv_column: "CSV field name", sas_label: "SAS label / question", sas_format: "SAS format", question_refs: "Question reference",
    codebook_variant_flags: "Codebook variation flags", observed_response_waves: "Waves with observed responses",
    entirely_not_asked_waves: "Entirely not asked (-3)", partially_not_asked_waves: "Partially not asked (-3)",
    not_applicable_waves: "Not applicable (-2)", waves_with_missing_code: "Waves with missing code", interpretation: "Interpretation / limitation",
  } },
  { sheet: "NSMO item wording", file: "nsmo-v70-wave-item-comparability.csv", table: "NsmoItemWording", headers: {
    field: "CSV field name", sas_label: "SAS label / question", observed_response_waves: "Waves with observed responses",
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
];

const wb = Workbook.create();
const guide = wb.worksheets.add("Start here");
guide.showGridLines = false;
const guideRows = [
  ["CreditAtlas · D02 data reference workbook", ""],
  ["Purpose", "Excel copy of the D02 reference tables and public aggregate datasets, arranged by source for filtering and review."],
  ["NSMO", "Field dictionary, category labels, wave coverage, item wording, response mode and usable-response disposition by wave. Values -2 and -3 remain distinct source codes."],
  ["Response mode", "Tables 3–6 show aggregate returns, usability exclusions and 2013–2024 origination scope. The v7.0 PUF has 62,359 mortgages from waves 1–46; no row-level mode link is published."],
  ["NMDB", "National quarterly aggregate mortgage performance through 2026Q2. One row is a market × series × quarter, not a loan."],
  ["HUD FHA", "Monthly portfolio trend and published subgroup aggregates through August 2026. These are not NSMO loan records."],
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
  if (source.sheet === "NSMO returns") {
    for (const name of header.filter((item) => item.includes("(%)"))) {
      const index = header.indexOf(name);
      sheet.getRange(`${columnName(index + 1)}2:${columnName(index + 1)}${values.length + 1}`).format.numberFormat = '0.00"%"';
    }
  }
}

const definitions = wb.worksheets.add("NMDB definitions");
definitions.showGridLines = false;
const definitionRows = [
  ["Topic", "Definition / use", "Source note"],
  ["P3089DL", "Active loans 30–60 days past due divided by active loans at quarter end.", "Quarter-end performance category."],
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
console.log(JSON.stringify({ status: "exported", output, dataSheets: sources.length + 1 }));

function columnName(index) {
  let result = "";
  while (index > 0) {
    const remainder = (index - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    index = Math.floor((index - 1) / 26);
  }
  return result;
}
