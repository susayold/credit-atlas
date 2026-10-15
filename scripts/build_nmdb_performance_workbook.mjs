import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [rootArg, outputArg, previewArg] = process.argv.slice(2);
if (!rootArg || !outputArg) throw new Error("usage: build_nmdb_performance_workbook.mjs <root> <output.xlsx> [preview.png]");
const root = path.resolve(rootArg);
const output = path.resolve(outputArg);
const csv = await fs.readFile(path.join(root, "docs/data/nmdb-performance-national-quarterly-2026q2.csv"), "utf8");
const imported = await Workbook.fromCSV(csv, { sheetName: "Source" });
const raw = imported.worksheets.getItem("Source").getUsedRange().values;
const sourceHeaders = raw[0].map(String);
const dataRows = raw.slice(1).filter((row) => row.some((cell) => cell !== null && cell !== ""));
const index = Object.fromEntries(sourceHeaders.map((key, i) => [key, i]));
if (dataRows.length !== 1568) throw new Error(`Expected 1,568 curated national rows; got ${dataRows.length}`);

const wb = Workbook.create();
const guide = wb.worksheets.add("Bat dau");
guide.showGridLines = false;
const guideRows = [
  ["CreditAtlas · FHFA NMDB performance", ""],
  ["Phạm vi", "Thống kê mortgage performance cấp quốc gia, theo quý, từ 2002Q1 đến 2026Q2; 4 market × 4 series."],
  ["Grain", "Mỗi dòng là một market × performance series × quarter. Đây là dữ liệu aggregate, không phải từng mortgage."],
  ["Nguồn", "FHFA NMDB Residential Mortgage Performance Statistics; phát hành 30/09/2026. Nguồn ZIP và hash được ghi trong receipt/docs."],
  ["Sử dụng", "Lọc ở hàng tiêu đề trong sheet Quarterly data; Latest KPIs cho quý mới nhất; Definitions ghi định nghĩa và giới hạn."],
  ["Giá trị", "Rate được giữ theo đơn vị điểm phần trăm của FHFA (ví dụ 1.7 nghĩa là 1.7%), không phải tỷ lệ 0.017."],
  ["Ô trống", "PFORB chỉ được công bố từ 2019Q4; các quý trước để trống theo nguồn, không thay bằng 0."],
  ["Thận trọng", "Hai quý mới nhất là sơ bộ; xem Definitions về active-loan mẫu số, stale-account rule, reporting lag và giới hạn 2006–2012."],
  ["D02", "Benchmark bối cảnh thị trường riêng. Không ghép vào NSMO PUF, không tạo nhãn khoản vay/PD và không dùng làm tập train."],
];
guide.getRange(`A1:B${guideRows.length}`).values = guideRows;
guide.getRange("A1:B1").merge();
guide.getRange("A1:B1").format = { fill: "#243B53", font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" }, verticalAlignment: "center", wrapText: true };
guide.getRange("A2:A9").format = { font: { bold: true, color: "#243B53" }, verticalAlignment: "top", wrapText: true };
guide.getRange("A1:B9").format.wrapText = true;
guide.getRange("A:A").format.columnWidth = 20;
guide.getRange("B:B").format.columnWidth = 110;
guide.getRange("A1:B1").format.rowHeight = 34;
guide.getRange("A2:B9").format.rowHeight = 38;

const markets = ["All Mortgages", "Enterprise Acquisitions", "Government / Non-Conventional", "Other Conventional Market"];
const marketDefinitions = {
  "All Mortgages": "All first-lien, closed-end single-family mortgages in the NMDB sample.",
  "Enterprise Acquisitions": "Non-government loans acquired by Fannie Mae or Freddie Mac.",
  "Government / Non-Conventional": "Government insured, guaranteed or direct mortgages.",
  "Other Conventional Market": "Non-government, non-enterprise conventional loans; includes jumbo, FHLB AMA, credit-union, private-label and other portfolio loans.",
};
const seriesLabels = { P3089DL: "30–60 days past due", P90DL: "90+ days past due", PFORECL: "Foreclosure / bankruptcy / deed-in-lieu", PFORB: "In forbearance" };
const latestPeriod = "2026Q2";
const val = (row, field) => row[index[field]];
const latestSheet = wb.worksheets.add("Latest KPIs");
latestSheet.showGridLines = false;
const latestHeaders = ["Quarter", "Mortgage market", "Publisher market definition", "30–60 DPD (%)", "90+ DPD (%)", "Foreclosure / bankruptcy / DIL (%)", "Forbearance (%)"];
const latestRows = markets.map((market) => {
  const findValue = (series) => {
    const row = dataRows.find((item) => val(item, "period") === latestPeriod && val(item, "market") === market && val(item, "series_id") === series);
    const value = val(row, "value_pct");
    return value === "" || value == null ? null : Number(value);
  };
  return [latestPeriod, market, marketDefinitions[market], findValue("P3089DL"), findValue("P90DL"), findValue("PFORECL"), findValue("PFORB")];
});
latestSheet.getRangeByIndexes(0, 0, latestRows.length + 1, latestHeaders.length).values = [latestHeaders, ...latestRows];
styleTable(latestSheet, latestHeaders.length, latestRows.length, "NMDBLatest");
latestSheet.getRange("D2:G5").format.numberFormat = '0.0"%"';
latestSheet.getRange("A:A").format.columnWidth = 13;
latestSheet.getRange("B:B").format.columnWidth = 32;
latestSheet.getRange("C:C").format.columnWidth = 72;
latestSheet.getRange("D:G").format.columnWidth = 24;

const detail = wb.worksheets.add("Quarterly data");
detail.showGridLines = false;
const translated = {
  source: "Source", frequency: "Frequency", geo_level: "Geography level", geo_id: "Geography ID",
  geo_name: "Geography name", market: "Mortgage market", period: "Quarter", year: "Year",
  quarter: "Quarter no.", month: "Quarter-end month", suppressed: "Suppressed", series_id: "Series ID", value_pct: "Rate (%)",
};
const detailHeaders = sourceHeaders.map((field) => translated[field] ?? field);
const detailValues = dataRows.map((row) => row.map((cell, i) => {
  const field = sourceHeaders[i];
  if (field === "value_pct") return cell === "" || cell == null ? null : Number(cell);
  if (field === "year" || field === "quarter") return Number(cell);
  if (field === "suppressed") return String(cell) === "1";
  return cell == null ? "" : String(cell);
}));
detail.getRangeByIndexes(0, 0, detailValues.length + 1, detailHeaders.length).values = [detailHeaders, ...detailValues];
styleTable(detail, detailHeaders.length, detailValues.length, "NMDBQuarterly");
detail.getRange(`M2:M${detailValues.length + 1}`).format.numberFormat = '0.0"%"';
const widths = [12, 15, 20, 12, 25, 38, 13, 10, 13, 14, 14, 15, 12];
widths.forEach((width, i) => detail.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);

const definitions = wb.worksheets.add("Definitions");
definitions.showGridLines = false;
const definitionsRows = [
  ["Series ID", "Label", "Definition / use", "Source note"],
  ["P3089DL", seriesLabels.P3089DL, "Active loans at least 30 or 60 days past due divided by all active loans at quarter end.", "Quarter-end performance category."],
  ["P90DL", seriesLabels.P90DL, "Active loans at least 90, 120, 150 or 180 days past due divided by all active loans at quarter end.", "Serious delinquency category, excluding foreclosure/bankruptcy series."],
  ["PFORECL", seriesLabels.PFORECL, "Active loans in foreclosure, bankruptcy or deed-in-lieu divided by all active loans at quarter end.", "Separate mutually exclusive publisher category."],
  ["PFORB", seriesLabels.PFORB, "Active loans reported in forbearance divided by all active loans at quarter end.", "Published from 2019Q4; earlier source cells are blank."],
  ["Denominator", "Active mortgages", "Loans not closed or terminated for which performance data exist; recent originations are included as current until a valid performance code appears.", "Not a fixed-horizon cohort denominator."],
  ["Reporting", "Credit bureau status", "The series use bureau-reported performance and a stale-account rule; 3 months from 2012, 6 months before 2012, and a 24-month lookback for 180+ past due/foreclosure-related statuses.", "Definitions are in FHFA Data Dictionary and Technical Notes, pp. 5–7, 15–17."],
  ["Revisions", "Preliminary latest periods", "FHFA states the latest two quarters may be revised as reporting lags close.", "Treat 2026Q1 and 2026Q2 as preliminary."],
  ["History", "Credit purge", "FHFA warns that seriously past-due loans may be undercounted between 2006 and 2012 because credit histories are purged seven years after default.", "Avoid attributing this period solely to changing borrower risk."],
  ["Scope", "Aggregate only", "A 5% sample summarized nationally; no borrower or mortgage records, linked targets, or model-ready outcomes are present.", "Do not pool with NSMO or HUD FHA."],
  ["Source", "FHFA NMDB", "Quarterly data released 2026-09-30; coverage 2002Q1–2026Q2.", "https://www.fhfa.gov/data/nmdb"],
];
definitions.getRangeByIndexes(0, 0, definitionsRows.length, 4).values = definitionsRows;
styleTable(definitions, 4, definitionsRows.length - 1, "NMDBDefinitions");
definitions.getRange("A:A").format.columnWidth = 18;
definitions.getRange("B:B").format.columnWidth = 36;
definitions.getRange("C:C").format.columnWidth = 88;
definitions.getRange("D:D").format.columnWidth = 68;

function styleTable(sheet, columnCount, rowCount, tableName) {
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  const lastCol = columnName(columnCount);
  const table = sheet.tables.add(`A1:${lastCol}${rowCount + 1}`, true, tableName);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  sheet.getRangeByIndexes(0, 0, 1, columnCount).format = {
    fill: "#243B53", font: { bold: true, color: "#FFFFFF", size: 10 },
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

const inspection = await wb.inspect({ kind: "workbook,sheet,table", maxChars: 5000, tableMaxRows: 2, tableMaxCols: 5 });
console.log(inspection.ndjson);
if (previewArg) {
  const preview = await wb.render({ sheetName: "Latest KPIs", autoCrop: "all", scale: 1, format: "png" });
  const previewPath = path.resolve(previewArg);
  await fs.mkdir(path.dirname(previewPath), { recursive: true });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(path.dirname(output), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(output);
