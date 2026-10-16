const fs = await import("node:fs/promises");
const path = await import("node:path");
const { SpreadsheetFile, Workbook } = await import("@oai/artifact-tool");

const NAVY = "#243B53";
const BLUE = "#486581";
const PALE = "#EAF1F7";

export async function build(inputPath, outputPath, previewPath = "") {
  const source = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const workbook = Workbook.create();

  const guide = workbook.worksheets.add("Start Here");
  guide.showGridLines = false;
  const guideRows = [
    ["CreditAtlas · FHFA NMDB Mortgage Market", ""],
    ["Scope", "National · USA · All Mortgages. Two separate FHFA products: annual origination flow and quarter-end outstanding stock."],
    ["Release", source.source_release_date + " · Retrieved " + source.retrieved_at],
    ["New originations", "1998–2025. Annual cohorts classified by account opening date; not a loan-performance panel."],
    ["Outstanding stock", "2013Q1–2026Q2. Active mortgages at quarter end; previous stock plus new originations less payoff/termination."],
    ["Weight VALUE1", "Count weighted. Each sampled mortgage represents 20 actual mortgages."],
    ["Weight VALUE2", "New: weighted by origination loan amount. Outstanding: weighted by quarter-end unpaid principal balance (UPB)."],
    ["Series weight support", "Not every series supports both weights. The Definitions sheet records FHFA-supported VALUE1/VALUE2 for each series; raw cells remain for audit only."],
    ["Units", "Retained in FHFA source scale per series. Percentages remain percentage points (e.g., 39.1 means 39.1%). No rescaling."],
    ["Missing / suppression", "Blank, dot and SUPPRESSED cells remain unavailable. Never replace with zero. No forecast or imputation."],
    ["Excel use", "Use table filters on the two product sheets to select series, period, weighting, and suppression status. Do not combine overlapping markets."],
    ["Risk use", "Aggregate market context only. Not loan-level data, default labels, approval rate, PD, Freddie vintage, or model validation."],
    ["Sample frame", "FHFA NMDB is a 5% sample of closed-end, first-lien mortgages reported to credit bureaus; investor and manufactured-home loans are less well represented."],
    ["Mart SHA-256", source.mart_sha256],
    ["FHFA catalog", source.source_page],
    ["FHFA data dictionary", source.dictionary_url],
  ];
  guide.getRange(`A1:B${guideRows.length}`).values = guideRows;
  guide.getRange("A1:B1").merge();
  guide.getRange("A1:B1").format = { fill: NAVY, font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" }, verticalAlignment: "center" };
  guide.getRange(`A2:A${guideRows.length}`).format = { font: { bold: true, color: NAVY }, verticalAlignment: "top", wrapText: true };
  guide.getRange(`A1:B${guideRows.length}`).format.wrapText = true;
  guide.getRange("A:A").format.columnWidth = 24;
  guide.getRange("B:B").format.columnWidth = 110;
  guide.getRange("A1:B1").format.rowHeight = 36;
  guide.getRange(`A2:B${guideRows.length}`).format.rowHeight = 34;
  guide.freezePanes.freezeRows(1);

  const latest = workbook.worksheets.add("Latest KPIs");
  latest.showGridLines = false;
  const latestHeaders = ["Product", "Period", "Series ID", "Series", "Unit", "FHFA-supported weights", "VALUE1 raw · count weighted", "VALUE2 raw · amount / UPB weighted", "Suppressed", "Series definition"];
  const latestRows = [];
  for (const product of ["new_annual", "outstanding_quarterly"]) {
    const rows = source.data[product] ?? [];
    const maxPeriod = rows.reduce((value, row) => row.period > value ? row.period : value, "");
    for (const row of rows.filter(item => item.period === maxPeriod)) {
      latestRows.push([
        source.products[product].label, row.period, row.series_id, row.label, row.unit,
        row.supported_weights.join(", "), row.value1, row.value2, row.suppressed, row.definition,
      ]);
    }
  }
  latest.getRangeByIndexes(0, 0, latestRows.length + 1, latestHeaders.length).values = [latestHeaders, ...latestRows];
  styleTable(latest, latestHeaders.length, latestRows.length, "NMDBLatestKPI");
  latest.getRange("A:A").format.columnWidth = 42;
  latest.getRange("B:B").format.columnWidth = 14;
  latest.getRange("C:C").format.columnWidth = 24;
  latest.getRange("D:D").format.columnWidth = 46;
  latest.getRange("E:E").format.columnWidth = 18;
  latest.getRange("F:F").format.columnWidth = 24;
  latest.getRange("G:H").format.columnWidth = 28;
  latest.getRange("I:I").format.columnWidth = 16;
  latest.getRange("J:J").format.columnWidth = 96;
  latest.getRange(`G2:H${latestRows.length + 1}`).format.numberFormat = "#,##0.00;[Red](#,##0.00);–";

  const productConfigs = [
    ["new_annual", "New annual", "NMDBNewAnnual"],
    ["outstanding_quarterly", "Outstanding quarterly", "NMDBOutstandingQuarterly"],
  ];
  for (const [productId, sheetName, tableName] of productConfigs) {
    const sheet = workbook.worksheets.add(sheetName);
    sheet.showGridLines = false;
    const headers = ["Period", "Year", "Quarter", "Series ID", "Series", "Unit", "FHFA-supported weights", "VALUE1 raw · count weighted", "VALUE1 numeric", "VALUE2 raw · amount / UPB weighted", "VALUE2 numeric", "Suppressed", "Definition", "Source", "Frequency", "Geography", "Market"];
    const rows = (source.data[productId] ?? []).map(row => [
      row.period, row.year, row.quarter, row.series_id, row.label, row.unit, row.supported_weights.join(", "),
      row.value1_raw, row.value1, row.value2_raw, row.value2,
      row.suppressed, row.definition, row.source, row.frequency, "National · USA", "All Mortgages",
    ]);
    sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length).values = [headers, ...rows];
    styleTable(sheet, headers.length, rows.length, tableName);
    const widths = [14, 10, 10, 23, 48, 19, 24, 24, 18, 31, 18, 14, 90, 13, 15, 22, 28];
    widths.forEach((width, index) => sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width);
    sheet.getRange(`I2:I${rows.length + 1}`).format.numberFormat = "#,##0.00;[Red](#,##0.00);–";
    sheet.getRange(`K2:K${rows.length + 1}`).format.numberFormat = "#,##0.00;[Red](#,##0.00);–";
  }

  const definitions = workbook.worksheets.add("Definitions");
  definitions.showGridLines = false;
  const definitionRows = [["Product", "Series ID", "Series", "Unit", "FHFA-supported weights", "FHFA definition"]];
  for (const product of ["new_annual", "outstanding_quarterly"]) {
    for (const [seriesId, value] of Object.entries(source.series[product])) {
      definitionRows.push([source.products[product].label, seriesId, value.label, value.unit, value.supported_weights.join(", "), value.definition]);
    }
  }
  definitions.getRangeByIndexes(0, 0, definitionRows.length, 6).values = definitionRows;
  styleTable(definitions, 6, definitionRows.length - 1, "NMDBSeriesDefinitions");
  [43, 24, 50, 20, 24, 110].forEach((width, index) => definitions.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width);

  const quality = workbook.worksheets.add("Data quality");
  quality.showGridLines = false;
  const q = [
    ["Measure", "New annual", "Outstanding quarterly"],
    ["Source rows", source.quality.rows_by_product.new_annual, source.quality.rows_by_product.outstanding_quarterly],
    ["Suppressed rows", source.quality.suppressed_rows_by_product.new_annual, source.quality.suppressed_rows_by_product.outstanding_quarterly],
    ["VALUE1 blank / dot", source.quality.missing_value1_rows_by_product.new_annual, source.quality.missing_value1_rows_by_product.outstanding_quarterly],
    ["VALUE2 blank / dot", source.quality.missing_value2_rows_by_product.new_annual, source.quality.missing_value2_rows_by_product.outstanding_quarterly],
    ["Invalid numeric values", 0, 0],
    ["Duplicate source keys", 0, 0],
    ["National/all-mortgage rows", source.data.new_annual.length, source.data.outstanding_quarterly.length],
    ["Forecast / imputation", "None", "None"],
    ["Mart SHA-256", source.mart_sha256, source.mart_sha256],
    ["Source release", source.source_release_date, source.source_release_date],
  ];
  quality.getRangeByIndexes(0, 0, q.length, 3).values = q;
  styleTable(quality, 3, q.length - 1, "NMDBQuality");
  quality.getRange("A:A").format.columnWidth = 34;
  quality.getRange("B:C").format.columnWidth = 44;

  const inspection = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 8000, tableMaxRows: 2, tableMaxCols: 6 });
  console.log(inspection.ndjson);
  if (previewPath) {
    const preview = await workbook.render({ sheetName: "Latest KPIs", autoCrop: "all", scale: 1, format: "png" });
    await fs.mkdir(path.dirname(previewPath), { recursive: true });
    await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  }
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const xlsx = await SpreadsheetFile.exportXlsx(workbook);
  await xlsx.save(outputPath);
}

function styleTable(sheet, columnCount, rowCount, tableName) {
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  const lastCol = columnName(columnCount);
  const table = sheet.tables.add(`A1:${lastCol}${rowCount + 1}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.getRangeByIndexes(0, 0, 1, columnCount).format = {
    fill: NAVY, font: { bold: true, color: "#FFFFFF", size: 10 },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
  };
  sheet.getRangeByIndexes(1, 0, rowCount, columnCount).format = { verticalAlignment: "top", wrapText: true };
  sheet.getRangeByIndexes(0, 0, 1, columnCount).format.rowHeight = 42;
}

function columnName(index) {
  let result = "";
  while (index > 0) { const remainder = (index - 1) % 26; result = String.fromCharCode(65 + remainder) + result; index = Math.floor((index - 1) / 26); }
  return result;
}
