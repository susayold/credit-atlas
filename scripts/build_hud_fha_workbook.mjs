import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(process.argv[2]);
const outputPath = path.resolve(process.argv[3]);
const previewDir = process.argv[4] ? path.resolve(process.argv[4]) : null;
const workbook = Workbook.create();

function addTable(sheetName, sourcePath, headers, tableName, widths) {
  return fs.readFile(sourcePath, "utf8").then(async (csv) => {
    const imported = await Workbook.fromCSV(csv, { sheetName: "Source" });
    const raw = imported.worksheets.getItem("Source").getUsedRange().values;
    const map = new Map(raw[0].map((header, index) => [String(header), index]));
    const rows = raw.slice(1).map((row) => headers.map(([key]) => {
      const value = row[map.get(key)];
      if (value === "" || value == null) return "—";
      if (key === "dimension") return ({
        loan_purpose: "Loan purpose", refinance: "Refinance", credit_score: "Origination credit score",
        fiscal_year_cohort: "Fiscal-year cohort", origination_loan_amount: "Loan amount at origination",
        property_type: "Property type", purchase_loan_type: "Purchase loan type",
        down_payment_assistance: "Down payment assistance",
      })[value] ?? value;
      return typeof value === "string" && /^\d+(\.\d+)?$/.test(value) ? Number(value) : value;
    }));
    const sheet = workbook.worksheets.add(sheetName);
    sheet.showGridLines = false;
    sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length).values = [headers.map(([, label]) => label), ...rows];
    sheet.freezePanes.freezeRows(1);
    if (sheetName === "Subgroup rates") sheet.freezePanes.freezeColumns(3);
    sheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
      fill: "#243B53", font: { bold: true, color: "#FFFFFF", size: 10 },
      horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
    };
    sheet.getRangeByIndexes(1, 0, rows.length, headers.length).format = { verticalAlignment: "top", wrapText: true };
    sheet.getRangeByIndexes(0, 0, 1, headers.length).format.rowHeight = 38;
    const lastColumn = columnName(headers.length);
    const table = sheet.tables.add(`A1:${lastColumn}${rows.length + 1}`, true, tableName);
    table.style = "TableStyleMedium2";
    table.showFilterButton = true;
    widths.forEach((width, index) => {
      sheet.getRange(`${columnName(index + 1)}:${columnName(index + 1)}`).format.columnWidth = width;
    });
    return { sheetName, rows: rows.length, cols: headers.length };
  });
}

const start = workbook.worksheets.add("Bat dau");
start.showGridLines = false;
const intro = [
  ["CreditAtlas · HUD FHA portfolio benchmark", ""],
  ["Mục đích", "Benchmark tổng hợp từ FHA Single-Family Loan Performance Trends, kỳ báo cáo August 2026; nguồn độc lập với NSMO và Freddie Mac."],
  ["Monthly", "13 tháng từ Aug-2025 đến Aug-2026; NSA và SA dùng cùng IIF end-of-month count."],
  ["Subgroups", "60 dòng Table 3: loan purpose, refinance, credit score, fiscal-year cohort, origination amount, property, purchase type và DPA."],
  ["Định nghĩa 90-day", "Ít nhất 3 tháng delinquent, loại các khoản đang foreclosure hoặc bankruptcy processing."],
  ["Định nghĩa serious", "HUD định nghĩa bằng 90+ delinquency + in-foreclosure + in-bankruptcy rates."],
  ["Giới hạn", "Aggregate only; không có loan-level events/labels. IIF shares được làm tròn; các dòng refinance con lồng nhau, không cộng chúng với category cha."],
  ["Trích xuất", "Giá trị được đối chiếu từ text của PDF HUD công khai; PDF binary trả HTTP 403 khi tải trực tiếp. Không có raw-PDF SHA-256."],
  ["Nguồn chỉ mục", "https://www.hud.gov/hud-partners/single-family-loan-performance"],
  ["Báo cáo PDF", "https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf · Table 1 p.2, Table 3 pp.4–5"],
  ["Coverage caveat", "Credit-score reporting became mandatory in July 2008; streamline refinances are excluded from score bands. FY2026 is partial with shorter exposure time."],
];
start.getRange(`A1:B${intro.length}`).values = intro;
start.getRange("A1:B1").merge();
start.getRange("A1:B1").format = { fill: "#243B53", font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" }, verticalAlignment: "center", wrapText: true };
start.getRange(`A2:A${intro.length}`).format = { font: { bold: true, color: "#243B53" }, verticalAlignment: "top", wrapText: true };
start.getRange(`A1:B${intro.length}`).format.wrapText = true;
start.getRange("A:A").format.columnWidth = 22;
start.getRange("B:B").format.columnWidth = 112;
start.getRange("A1:B1").format.rowHeight = 32;
start.getRange(`A2:B${intro.length}`).format.rowHeight = 42;

const monthly = await addTable("Monthly trend", path.join(root, "docs/data/hud-fha-performance-2026-08.csv"), [
  ["month", "Tháng"], ["adjustment", "Seasonal adjustment"], ["active_iif_count", "Active IIF · EOM"],
  ["delinquency_30d_pct", "30-day delinquency %"], ["delinquency_60d_pct", "60-day delinquency %"],
  ["delinquency_90d_pct", "90-day delinquency %"], ["foreclosure_pct", "In foreclosure %"],
  ["bankruptcy_pct", "In bankruptcy %"], ["serious_delinquency_pct", "Serious delinquency %"],
  ["source_table", "HUD table"], ["source_page", "PDF page"],
], "HUDFHAMonthly", [14, 20, 20, 19, 19, 19, 18, 18, 22, 12, 12]);
workbook.worksheets.getItem("Monthly trend").getRange("C2:C27").setNumberFormat("#,##0");
workbook.worksheets.getItem("Monthly trend").getRange("D2:I27").setNumberFormat("0.00");
const subgroup = await addTable("Subgroup rates", path.join(root, "docs/data/hud-fha-performance-2026-08-subgroups.csv"), [
  ["dimension", "Dimension"], ["parent_category", "Parent category"], ["category", "Category"],
  ["iif_count", "IIF count"], ["iif_share_pct", "IIF share %"], ["share_denominator", "Share denominator"],
  ["all_past_due_pct", "All past due %"], ["delinquency_30d_pct", "30-day %"],
  ["delinquency_60d_pct", "60-day %"], ["delinquency_90plus_pct", "90+ day %"],
  ["foreclosure_pct", "Foreclosure %"], ["bankruptcy_pct", "Bankruptcy %"],
  ["serious_delinquency_pct", "Serious delinquency %"], ["source_table", "HUD table"], ["source_page", "PDF page"],
], "HUDFHASubgroups", [24, 18, 27, 16, 16, 26, 17, 14, 14, 14, 15, 15, 22, 12, 12]);
workbook.worksheets.getItem("Subgroup rates").getRange("C:C").format.columnWidth = 32;
workbook.worksheets.getItem("Subgroup rates").getRange("D:D").format.columnWidth = 21;
workbook.worksheets.getItem("Subgroup rates").getRange("E:E").format.columnWidth = 19;
workbook.worksheets.getItem("Subgroup rates").getRange("F:F").format.columnWidth = 34;
workbook.worksheets.getItem("Subgroup rates").getRange("D2:D61").setNumberFormat("#,##0");
workbook.worksheets.getItem("Subgroup rates").getRange("E2:E61").setNumberFormat("0.00");
workbook.worksheets.getItem("Subgroup rates").getRange("E2:E61").format.horizontalAlignment = "center";
workbook.worksheets.getItem("Subgroup rates").getRange("G2:M61").setNumberFormat("0.00");
console.log(JSON.stringify({ monthly, subgroup }));
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of ["Bat dau", "Monthly trend", "Subgroup rates"]) {
    const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "-")}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
await (await SpreadsheetFile.exportXlsx(workbook)).save(outputPath);

function columnName(index) {
  let output = "";
  while (index > 0) { const remainder = (index - 1) % 26; output = String.fromCharCode(65 + remainder) + output; index = Math.floor((index - 1) / 26); }
  return output;
}
