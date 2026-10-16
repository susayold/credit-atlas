import fs from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [rootArg, outputArg, previewDirArg] = process.argv.slice(2);
if (!rootArg || !outputArg) {
  throw new Error("usage: build_fhfa_pudb_analyst_review.mjs <private-root> <output.xlsx> [preview-dir]");
}
const root = path.resolve(rootArg);
const output = path.resolve(outputArg);
const previewDir = previewDirArg ? path.resolve(previewDirArg) : null;
const sourceDir = path.join(root, "data/private/fhfa-enterprise-pudb/2025");
const expectedRecords = 2_093_767;
const minimumDisplayCount = 30;
const fontName = "Aptos";

const hashBytes = (bytes) => createHash("sha256").update(bytes).digest("hex");
async function hashFile(file) {
  const data = await fs.readFile(file);
  return hashBytes(data);
}
function safeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}
function asText(value) {
  return value === null || value === undefined ? "" : String(value).trim();
}
function normField(value) {
  return asText(value).replace(/[\s\u00a0]+/g, "");
}
function columnName(number) {
  let result = "";
  while (number > 0) {
    const remainder = (number - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    number = Math.floor((number - 1) / 26);
  }
  return result;
}
function fieldGroup(field) {
  if (field === "record_num_sf_ctf") return "Source identifier";
  if (/^(race|ethnicity|sex|age_|borr_num|fthb)/.test(field)) return "Borrower / co-borrower";
  if (/^(state_|cbsa_|county_|tract_|area_|county_lower|county_mid)/.test(field)) return "Geography / neighborhood";
  if (/^(year_|enterprise|same_year)/.test(field)) return "Reference / acquisition context";
  return "Mortgage / acquisition characteristic";
}
function useBoundary(field) {
  if (field === "record_num_sf_ctf") return "Source-scoped sequential key; not exported as a record and never join to another loan file.";
  if (/^(race|ethnicity|sex|age_)/.test(field)) return "Descriptive acquisition mix only; not a causal or disparate-treatment finding.";
  return "Acquisition/origination attribute only; this source has no repayment or default target.";
}
function sourceCodeLabels(valueText) {
  const labels = new Map();
  for (const line of asText(valueText).split(/\r?\n/)) {
    const match = line.match(/^\s*([^=]+?)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    const code = normField(match[1]).toUpperCase();
    if (!code) continue;
    labels.set(code === "<BLANK>" ? "<BLANK>" : code, match[2].trim());
  }
  return labels;
}

const receiptFiles = (await fs.readdir(sourceDir))
  .filter((name) => /^receipt-v\d+-[a-f0-9]{12}\.json$/i.test(name));
if (!receiptFiles.length) throw new Error("No versioned FHFA PUDB profiling receipt is available under private data");
const receipts = await Promise.all(receiptFiles.map(async (name) => ({
  name,
  mtime: (await fs.stat(path.join(sourceDir, name))).mtimeMs,
  value: JSON.parse(await fs.readFile(path.join(sourceDir, name), "utf8")),
})));
receipts.sort((left, right) => right.mtime - left.mtime);
const receipt = receipts[0].value;
if (receipt.status !== "PASS" || !/^profile-v4-[a-f0-9]{12}\.json$/i.test(receipt.profile_file || "")) {
  throw new Error("A schema-v4 PASS receipt is required for the complete 66-field missingness workbook");
}
const profilePath = path.join(sourceDir, receipt.profile_file);
const profileBytes = await fs.readFile(profilePath);
const profile = JSON.parse(profileBytes.toString("utf8"));
if (hashBytes(profileBytes) !== receipt.profile_sha256) throw new Error("PUDB profile does not match its private receipt");
if (profile.schema_version !== 4 || profile.rows !== expectedRecords || profile.columns !== 66
    || profile.unique_record_keys !== expectedRecords || profile.duplicate_record_keys !== 0) {
  throw new Error("PUDB source profile failed the analyst workbook contract");
}
if (Object.keys(profile.blank_counts || {}).length !== profile.columns) {
  throw new Error("PUDB schema-v4 profile must provide explicit blank counts for every source field");
}
const archivePath = path.join(sourceDir, "2025_pudb_sf_ctf.zip");
if (await hashFile(archivePath) !== profile.archive_sha256) throw new Error("PUDB source ZIP does not match its verified profile");

const dictionaryName = "2025-enterprise-pudb-data-dictionary.xlsx";
const dictionaryPath = path.join(sourceDir, dictionaryName);
const dictionaryHash = await hashFile(dictionaryPath);
const receiptDictionaryHash = receipt.acquisitions?.[dictionaryName]?.sha256;
if (receiptDictionaryHash && dictionaryHash !== receiptDictionaryHash) {
  throw new Error("FHFA PUDB data dictionary does not match its private acquisition receipt");
}
const officialBook = await SpreadsheetFile.importXlsx(new Uint8Array(await fs.readFile(dictionaryPath)));
const officialSheet = officialBook.worksheets.getItem("SF CTF");
const officialValues = officialSheet.getUsedRange().values;
const headerIndex = officialValues.findIndex((row) => row.some((cell) => asText(cell) === "Header Name"));
if (headerIndex < 0) throw new Error("FHFA dictionary no longer has the expected SF CTF field table");
const sourceHeaders = officialValues[headerIndex].map(asText);
const columnIndex = Object.fromEntries(sourceHeaders.map((name, index) => [name, index]));
for (const required of ["Field #", "Field Width", "Header Name", "Field Name", "Values", "Description / Comments"]) {
  if (!(required in columnIndex)) throw new Error(`Missing expected FHFA dictionary column: ${required}`);
}

const fieldRecords = [];
for (const row of officialValues.slice(headerIndex + 1)) {
  const rawHeader = asText(row[columnIndex["Header Name"]]);
  if (!rawHeader) continue;
  // FHFA wraps long single field codes over lines; only commas separate the
  // grouped race-field headers. Strip internal line breaks from every name.
  const expanded = (rawHeader.includes(",") ? rawHeader.split(",") : [rawHeader]).map(normField).filter(Boolean);
  for (const field of expanded) {
    fieldRecords.push({
      field,
      fieldNumber: asText(row[columnIndex["Field #"]]),
      width: asText(row[columnIndex["Field Width"]]),
      label: asText(row[columnIndex["Field Name"]]),
      values: asText(row[columnIndex["Values"]]),
      description: asText(row[columnIndex["Description / Comments"]]),
    });
  }
}
const fieldNames = fieldRecords.map((item) => item.field);
if (fieldNames.length !== profile.columns || new Set(fieldNames).size !== profile.columns) {
  throw new Error(`FHFA dictionary expansion did not produce 66 unique fields (got ${fieldNames.length})`);
}
const dictionaryHeadersHash = hashBytes(Buffer.from(fieldNames.join("\n"), "utf8"));
if (dictionaryHeadersHash !== profile.headers_sha256) {
  throw new Error("Expanded FHFA dictionary field order does not match the verified source schema");
}

const codebook = new Map(fieldRecords.map((item) => [item.field, item]));
const categories = profile.category_counts || {};
const categoryRows = [];
const categoryAddress = new Map();
for (const field of Object.keys(categories)) {
  const detail = codebook.get(field);
  if (!detail) throw new Error(`Aggregate category profile has no FHFA dictionary entry: ${field}`);
  const fieldTotal = Object.values(categories[field]).reduce((sum, count) => sum + safeNumber(count), 0);
  if (fieldTotal !== expectedRecords) throw new Error(`One-dimensional category counts do not reconcile for ${field}`);
  const title = detail.label || field;
  const labels = sourceCodeLabels(detail.values);
  const values = Object.entries(categories[field]).sort((left, right) => {
    if (left[0] === "<BLANK>") return 1;
    if (right[0] === "<BLANK>") return -1;
    return left[0].localeCompare(right[0], undefined, { numeric: true });
  });
  for (const [code, rawCount] of values) {
    const count = safeNumber(rawCount);
    const suppressed = count > 0 && count < minimumDisplayCount;
    const row = categoryRows.length + 6;
    categoryAddress.set(`${field}\u0000${code}`, { row, count, suppressed, title });
    categoryRows.push([
      field,
      title,
      code,
      labels.get(code.toUpperCase()) || (code === "<BLANK>" ? "Source blank" : code),
      suppressed ? `Suppressed (<${minimumDisplayCount})` : count,
      null,
      expectedRecords - safeNumber(categories[field]["<BLANK>"] || 0),
      null,
      suppressed ? "Suppressed for small count" : "Source aggregate",
    ]);
  }
}
if (!categoryRows.length) throw new Error("No one-dimensional FHFA PUDB categories were present in the source profile");

const missingByField = fieldRecords.map((field) => {
  const blanks = safeNumber(profile.blank_counts?.[field.field] || 0);
  return { ...field, blanks, nonblank: expectedRecords - blanks };
}).sort((left, right) => right.blanks - left.blanks || left.field.localeCompare(right.field));
const missingRows = missingByField.map((field) => {
  const smallCount = field.blanks > 0 && field.blanks < minimumDisplayCount;
  return [
    field.field,
    field.label,
    fieldGroup(field.field),
    smallCount ? `Suppressed (<${minimumDisplayCount})` : field.blanks,
    null,
    null,
    smallCount ? "Suppressed for small count" : "Source blank count",
  ];
});
const missingAddress = new Map(missingByField.map((field, index) => [field.field, index + 6]));

const workbook = Workbook.create();
const overview = workbook.worksheets.add("Overview");
const category = workbook.worksheets.add("Category Mix");
const missingness = workbook.worksheets.add("Missingness");
const dictionary = workbook.worksheets.add("Data Dictionary");
const methods = workbook.worksheets.add("Sources & Methods");
for (const sheet of [overview, category, missingness, dictionary, methods]) sheet.showGridLines = false;

function styleTitle(sheet, title, subtitle, endColumn) {
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = { font: { name: fontName, size: 15, bold: true, color: "#183247" }, verticalAlignment: "center" };
  sheet.getRange("A2:B2").values = [["Scope", subtitle]];
  sheet.getRange("A2").format = { font: { name: fontName, size: 10, bold: true, color: "#526777" }, verticalAlignment: "top" };
  sheet.getRange("B2").format = {
    font: { name: fontName, size: 10, italic: true, color: "#526777" },
    verticalAlignment: "top", wrapText: true,
  };
  sheet.getRange(`A1:${endColumn}1`).format.rowHeight = 28;
  sheet.getRange("A2:B2").format.rowHeight = 64;
}
function styleTable(sheet, address, name, columnCount, dataCount, frozenRows = 5, frozenColumns = 1) {
  const table = sheet.tables.add(address, true, name);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.getRangeByIndexes(frozenRows - 1, 0, 1, columnCount).format = {
    fill: "#183247", font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
  };
  sheet.getRangeByIndexes(frozenRows, 0, dataCount, columnCount).format = {
    font: { name: fontName, size: 10, color: "#243746" },
    verticalAlignment: "center", wrapText: true,
  };
  sheet.getRangeByIndexes(frozenRows - 1, 0, 1, columnCount).format.rowHeight = 34;
  sheet.freezePanes.freezeRows(frozenRows);
  if (frozenColumns > 0) sheet.freezePanes.freezeColumns(frozenColumns);
}
function setColumnWidths(sheet, widths, rows = 100) {
  for (const [index, width] of widths.entries()) {
    const column = columnName(index + 1);
    sheet.getRange(`${column}1:${column}${rows}`).format.columnWidth = width;
  }
}

// One-dimensional source categories: values <30 are omitted from the workbook.
styleTitle(category, "FHFA Enterprise PUDB · 2025 category mix", "Single-dimension counts from verified source rows. Percentages are formulas; counts below 30 and their shares are suppressed.", "I");
category.getRange("A3:B3").values = [["Source records", profile.rows]];
category.getRange("A3:B3").format = { font: { name: fontName, size: 10, bold: true, color: "#183247" }, verticalAlignment: "center" };
category.getRange("B3").format.numberFormat = "#,##0";
const categoryHeaders = ["Source field", "FHFA field", "Code", "FHFA category label", "Records", "Share of file", "Nonblank field records", "Share of nonblank", "Display status"];
category.getRangeByIndexes(4, 0, 1, categoryHeaders.length).values = [categoryHeaders];
category.getRangeByIndexes(5, 0, categoryRows.length, categoryHeaders.length).values = categoryRows;
for (let index = 0; index < categoryRows.length; index++) {
  const row = index + 6;
  category.getRange(`F${row}`).formulas = [[`=IF(ISNUMBER(E${row}),E${row}/$B$3,"")`]];
  category.getRange(`H${row}`).formulas = [[`=IF(AND(ISNUMBER(E${row}),C${row}<>"<BLANK>"),E${row}/G${row},"")`]];
}
styleTable(category, `A5:I${categoryRows.length + 5}`, "PudbCategoryMix", categoryHeaders.length, categoryRows.length, 5, 3);
category.getRange(`E6:E${categoryRows.length + 5}`).format.numberFormat = "#,##0;(#,##0);-";
category.getRange(`G6:G${categoryRows.length + 5}`).format.numberFormat = "#,##0;(#,##0);-";
category.getRange(`F6:F${categoryRows.length + 5}`).format.numberFormat = "0.000%";
category.getRange(`H6:H${categoryRows.length + 5}`).format.numberFormat = "0.000%";
setColumnWidths(category, [25, 36, 13, 46, 16, 16, 23, 19, 28], categoryRows.length + 5);

// All 66 fields receive an actual source-blank count; derived measures remain formulas.
styleTitle(missingness, "FHFA Enterprise PUDB · field completeness", "Source blanks are counted from all 2,093,767 rows; no values are imputed. Positive counts below 30 are suppressed.", "G");
missingness.getRange("A3:B3").values = [["Source records", profile.rows]];
missingness.getRange("A3:B3").format = { font: { name: fontName, size: 10, bold: true, color: "#183247" }, verticalAlignment: "center" };
missingness.getRange("B3").format.numberFormat = "#,##0";
const missingHeaders = ["Source field", "FHFA field", "Field group", "Source blanks", "Records observed", "Missing %", "Display status"];
missingness.getRangeByIndexes(4, 0, 1, missingHeaders.length).values = [missingHeaders];
missingness.getRangeByIndexes(5, 0, missingRows.length, missingHeaders.length).values = missingRows;
for (let index = 0; index < missingRows.length; index++) {
  const row = index + 6;
  missingness.getRange(`E${row}`).formulas = [[`=IF(ISNUMBER(D${row}),$B$3-D${row},"")`]];
  missingness.getRange(`F${row}`).formulas = [[`=IF(ISNUMBER(D${row}),D${row}/$B$3,"")`]];
}
styleTable(missingness, `A5:G${missingRows.length + 5}`, "PudbMissingness", missingHeaders.length, missingRows.length, 5, 1);
missingness.getRange(`D6:E${missingRows.length + 5}`).format.numberFormat = "#,##0;(#,##0);-";
missingness.getRange(`F6:F${missingRows.length + 5}`).format.numberFormat = "0.00%";
setColumnWidths(missingness, [28, 47, 34, 20, 22, 16, 29], missingRows.length + 5);

// Field definitions are expanded to the exact verified source-header order.
styleTitle(dictionary, "FHFA Enterprise PUDB · data dictionary", "2025 Single-Family Census Tract File. Definitions and source codes are expanded from FHFA’s release-matched dictionary.", "F");
const dictionaryHeaders = ["Source order", "Source field", "FHFA field name", "Field width", "FHFA values / codes", "FHFA description / comments", "CreditAtlas use boundary"];
const dictionaryRows = fieldRecords.map((item, index) => [
  index + 1, item.field, item.label, item.width, item.values, item.description, useBoundary(item.field),
]);
dictionary.getRangeByIndexes(3, 0, 1, dictionaryHeaders.length).values = [dictionaryHeaders];
dictionary.getRangeByIndexes(4, 0, dictionaryRows.length, dictionaryHeaders.length).values = dictionaryRows;
styleTable(dictionary, `A4:G${dictionaryRows.length + 3}`, "PudbDictionary", dictionaryHeaders.length, dictionaryRows.length, 4, 2);
setColumnWidths(dictionary, [13, 30, 40, 14, 65, 84, 62], dictionaryRows.length + 3);
dictionary.getRange(`A5:A${dictionaryRows.length + 4}`).format.horizontalAlignment = "right";
dictionary.getRange(`A5:G${dictionaryRows.length + 4}`).format.verticalAlignment = "top";
dictionary.getRange(`A5:G${dictionaryRows.length + 4}`).format.rowHeight = 72;

// Executive view links to the underlying filtered tables rather than recalculating counts.
styleTitle(overview, "CreditAtlas · FHFA Enterprise PUDB 2025", "Analyst workbook · annual acquisition composition and source quality · aggregate-only; no payment performance or default target.", "M");
const summaryRows = [
  ["Evidence summary", "Verified value"],
  ["FHFA release date", profile.source_release_date],
  ["Acquisition year", profile.acquisition_year],
  ["Census geography year", profile.census_year],
  ["Source records", null],
  ["Unique source keys", profile.unique_record_keys],
  ["Source fields", profile.columns],
  ["Duplicate / malformed rows", `${profile.duplicate_record_keys} / ${profile.malformed_rows}`],
  ["Repayment outcomes", "None in this source"],
];
overview.getRangeByIndexes(3, 0, summaryRows.length, 2).values = summaryRows;
overview.getRange("B8").formulas = [["='Category Mix'!$B$3"]];
styleTable(overview, "A4:B12", "PudbSummary", 2, summaryRows.length - 1, 4, 1);
overview.getRange("B8").format.numberFormat = "#,##0";
overview.getRange("B9:B10").format.numberFormat = "#,##0";
setColumnWidths(overview, [35, 42, 17, 34, 21, 17, 4, 28, 20, 18, 4, 17, 17], 32);

const enterpriseEntries = [
  ["Fannie Mae", categoryAddress.get("enterprise\u00001")],
  ["Freddie Mac", categoryAddress.get("enterprise\u00002")],
];
if (enterpriseEntries.some(([, entry]) => !entry || entry.suppressed)) throw new Error("Enterprise totals are missing or suppressed unexpectedly");
overview.getRange("D4:F4").values = [["Enterprise acquisitions", "Records", "Share of file"]];
overview.getRange("D5:F6").values = enterpriseEntries.map(([label]) => [label, null, null]);
for (let index = 0; index < enterpriseEntries.length; index++) {
  const outputRow = index + 5;
  const sourceRow = enterpriseEntries[index][1].row;
  overview.getRange(`E${outputRow}`).formulas = [[`='Category Mix'!E${sourceRow}`]];
  overview.getRange(`F${outputRow}`).formulas = [[`='Category Mix'!F${sourceRow}`]];
}
overview.getRange("D4:F6").format.font = { name: fontName, size: 10, color: "#243746" };
overview.getRange("D4:F4").format = { fill: "#183247", font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
overview.getRange("D4:F4").format.rowHeight = 34;
overview.getRange("E5:E6").format.numberFormat = "#,##0";
overview.getRange("F5:F6").format.numberFormat = "0.0%";
overview.getRange("D4:F6").format.verticalAlignment = "center";
const enterpriseChart = overview.charts.add("doughnut", [overview.getRange("D4:D6"), overview.getRange("F4:F6")]);
enterpriseChart.title = "2025 Enterprise acquisition mix";
enterpriseChart.titleTextStyle.typeface = fontName;
enterpriseChart.titleTextStyle.fontSize = 12;
enterpriseChart.legend = { position: "top", textStyle: { typeface: fontName, fontSize: 10 } };
enterpriseChart.setPosition("H4", "M18");

overview.getRange("A15:C15").values = [["Most-missing fields", "Source blanks", "Missing %"]];
const topMissing = missingByField.slice(0, 5);
overview.getRangeByIndexes(15, 0, topMissing.length, 3).values = topMissing.map((field) => [field.field, null, null]);
for (let index = 0; index < topMissing.length; index++) {
  const overviewRow = index + 16;
  const sourceRow = missingAddress.get(topMissing[index].field);
  overview.getRange(`B${overviewRow}`).formulas = [[`='Missingness'!D${sourceRow}`]];
  overview.getRange(`C${overviewRow}`).formulas = [[`='Missingness'!F${sourceRow}`]];
}
overview.getRange("A15:C15").format = { fill: "#183247", font: { name: fontName, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
overview.getRange("A15:C15").format.rowHeight = 34;
overview.getRange("B16:B20").format.numberFormat = "#,##0";
overview.getRange("C16:C20").format.numberFormat = "0.00%";
overview.getRange("A23").values = [["How to use this workbook"]];
overview.getRange("A23").format = { font: { name: fontName, size: 11, bold: true, color: "#183247" } };
overview.getRange("A24:B24").values = [["Workflow", "Filter Category Mix by field or code; inspect Missingness and the exact FHFA field codes before interpreting results."]];
overview.getRange("A24").format = { font: { name: fontName, size: 10, bold: true, color: "#183247" }, verticalAlignment: "top" };
overview.getRange("B24").format = { font: { name: fontName, size: 10, color: "#243746" }, wrapText: true, verticalAlignment: "top" };
overview.getRange("A24:B24").format.rowHeight = 48;

styleTitle(methods, "FHFA PUDB · sources, calculations and limitations", "Read this sheet before reusing any number, definition or category.", "D");
const methodRows = [
  ["Item", "Evidence / method", "Source or interpretation", "CreditAtlas control"],
  ["Primary data", "2025 Enterprise Single-Family Census Tract File · 2,093,767 rows × 66 source fields", "https://www.fhfa.gov/document/d/pud/2025_pudb_sf_ctf.zip", `Archive SHA-256 prefix ${profile.archive_sha256.slice(0, 12)}`],
  ["Visibility", "Private local analyst workbook; contains field definitions and suppressed aggregate counts.", "No loan-level data or record identifiers are exported.", "Do not upload this workbook or its private profile to public GitHub."],
  ["Release dictionary", "2025 SF CTF field names, definitions and category coding", "https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-data-dictionary.xlsx", `Dictionary SHA-256 prefix ${dictionaryHash.slice(0, 12)}`],
  ["Official reconciliation", "FHFA 2025 Enterprise record-count workbook; source reader matched the published Enterprise totals", "https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-record-count.xlsx", `Fannie ${profile.enterprise_counts["1"]}; Freddie ${profile.enterprise_counts["2"]}`],
  ["Publisher page", "Release notes and data-use scope", "https://www.fhfa.gov/data/pudb", `Retrieved ${receipt.retrieved_at || "date not recorded in receipt"}`],
  ["Category count", "Count of source records with the listed code in one field; each field is analyzed independently.", "No cross-tab or borrower-level rows are present in this workbook.", "Counts below 30 and associated shares are suppressed."],
  ["File share", "Category count divided by all 2,093,767 source records.", "Calculated by Excel formulas in Category Mix.", "Blank source values appear as a separate category when observed."],
  ["Valid-field share", "Category count divided by nonblank records for that field.", "Calculated by Excel formulas in Category Mix.", "Source blanks are excluded from this denominator."],
  ["Missingness", "Source-empty cells counted across all 66 fields and 2,093,767 rows.", "No filling, imputation, or projection was performed.", "Counts below 30 are suppressed."],
  ["Credit-risk meaning", "Acquisition/origination composition, not application approval coverage.", "No delinquency, default, prepayment, foreclosure, realized-loss or recovery history exists here.", "Do not derive or train PD/LGD/default models from this file."],
  ["Fair-lending boundary", "Demographic and census-tract fields are descriptive characteristics of acquired loans.", "Not the full applicant/denial population; no causal or disparate-treatment conclusion follows.", "Do not describe this as an approval/fairness test."],
  ["Linkage boundary", "record_num_sf_ctf is source-specific and unrelated to identifiers in other FHFA files.", "No identifiers or loan-level observations are exported.", "Never join this source to D01, servicing, HMDA or another loan panel."],
  ["Time-series boundary", "One acquisition year (2025), using 2020 census geography.", "Historical release comparisons require matching annual files, dictionaries, geography and explicit schema review.", "Do not infer a trend from this single annual release."],
  ["Refresh procedure", "Re-run the private-source profile, then rebuild with the app’s host-provided artifact-tool runtime.", "python scripts/acquire_fhfa_pudb_ctf.py --profile-existing; node apps/excel/build_fhfa_pudb_analyst_review.mjs <private-root> <output.xlsx>", "Preserve each versioned receipt; do not overwrite source or prior profile evidence."],
];
methods.getRangeByIndexes(3, 0, methodRows.length, methodRows[0].length).values = methodRows;
styleTable(methods, `A4:D${methodRows.length + 3}`, "PudbSourcesMethods", 4, methodRows.length - 1, 4, 1);
setColumnWidths(methods, [28, 72, 72, 64], methodRows.length + 3);
methods.getRange(`A5:D${methodRows.length + 3}`).format.verticalAlignment = "top";
methods.getRange(`A5:D${methodRows.length + 3}`).format.rowHeight = 58;

workbook.recalculate();
const formulaRanges = [
  category.getRange(`F6:F${categoryRows.length + 5}`).values,
  category.getRange(`H6:H${categoryRows.length + 5}`).values,
  missingness.getRange(`E6:F${missingRows.length + 5}`).values,
  overview.getRange("B4:F20").values,
];
for (const rangeValues of formulaRanges) {
  for (const row of rangeValues) {
    for (const value of row) {
      if (typeof value === "string" && /^#(REF!|DIV\/0!|VALUE!|NAME\?|N\/A)/i.test(value)) {
        throw new Error(`Workbook contains a formula error: ${value}`);
      }
    }
  }
}
const expectedShares = overview.getRange("F5:F6").values.flat().map(Number);
if (expectedShares.length !== 2 || expectedShares.some((value) => !Number.isFinite(value) || value <= 0 || value >= 1)) {
  throw new Error(`Enterprise share formulas did not calculate: ${JSON.stringify(expectedShares)}`);
}

if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  const renderRanges = {
    "Overview": "A1:M24",
    "Category Mix": "A1:I22",
    "Missingness": "A1:G22",
    "Data Dictionary": "A1:G16",
    "Sources & Methods": "A1:D18",
  };
  for (const [sheetName, range] of Object.entries(renderRanges)) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName.toLowerCase().replaceAll(" ", "-")}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}

await fs.mkdir(path.dirname(output), { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(output);
console.log(JSON.stringify({
  status: "PASS",
  output,
  rows: profile.rows,
  fields: profile.columns,
  dictionary_fields: fieldNames.length,
  category_rows: categoryRows.length,
  missingness_fields: missingRows.length,
  suppressed_categories: categoryRows.filter((row) => String(row[4]).startsWith("Suppressed")).length,
  formula_check: "PASS",
  archive_sha256_prefix: profile.archive_sha256.slice(0, 12),
  dictionary_sha256_prefix: dictionaryHash.slice(0, 12),
}, null, 2));
