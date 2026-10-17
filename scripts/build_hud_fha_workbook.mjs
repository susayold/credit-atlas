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
      if (["flow_identity_difference", "recomputed_cure_ratio_pct", "prior_ending_plus_adjustment_difference"].includes(key)) return "—";
      const value = row[map.get(key)];
      if (value === "" || value == null) return "—";
      if (key === "partial_period") return String(value).toLowerCase() === "true";
      if (key === "dimension") return ({
        loan_purpose: "Loan purpose", refinance: "Refinance", credit_score: "Origination credit score",
        fiscal_year_cohort: "Fiscal-year cohort", origination_loan_amount: "Loan amount at origination",
        property_type: "Property type", purchase_loan_type: "Purchase loan type",
        down_payment_assistance: "Down payment assistance",
      })[value] ?? value;
      return typeof value === "string" && /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : value;
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
  ["New 90+ reasons", "Table 2: số khoản mới vào nhóm 90+ và phân phối lý do báo cáo theo kỳ tài khóa; July/August 2026 là kỳ chưa đủ tháng."],
  ["Foreclosure", "Table 4: IIF, foreclosure starts, in-foreclosure stock, claims, 6-month average và rate HUD annualized."],
  ["REO recovery", "Table 5: recovery theo bang/lãnh thổ, cùng số disposition và thay đổi theo percentage points."],
  ["REO losses", "Table 6: các thành phần loss/cost, số tiền bình quân, số disposition và thời lượng các stage."],
  ["Định nghĩa 90-day", "Ít nhất 3 tháng delinquent, loại các khoản đang foreclosure hoặc bankruptcy processing."],
  ["Định nghĩa serious", "HUD định nghĩa bằng 90+ delinquency + in-foreclosure + in-bankruptcy rates."],
  ["Giới hạn", "Aggregate only; không có loan-level events/labels. IIF shares được làm tròn; các dòng refinance con lồng nhau, không cộng chúng với category cha."],
  ["Trích xuất", "Giá trị được đối chiếu từ text của PDF HUD công khai; PDF binary trả HTTP 403 khi tải trực tiếp. Không có raw-PDF SHA-256."],
  ["Nguồn chỉ mục", "https://www.hud.gov/hud-partners/single-family-loan-performance"],
  ["Báo cáo PDF", "https://www.hud.gov/sites/default/files/Housing/documents/FHALPT_AUG2026.pdf · Tables 1–6, report pages 2–8"],
  ["Coverage caveat", "Credit-score reporting became mandatory in July 2008; streamline refinances are excluded from score bands. FY2026 is partial with shorter exposure time."],
  ["Cách đọc Table 2", "Lý do là descriptive distribution, không phải predictor importance hoặc nguyên nhân nhân quả; shares cộng thành 100%."],
  ["Cách đọc Table 4", "Foreclosure starts (flow), in-foreclosure (stock), claims paid và annualized rate là chỉ số khác nhau, không thay thế nhau."],
  ["Cách đọc Table 5–6", "Recovery có thể vượt 100%; blank là publisher không báo cáo. Loss components không phải danh mục cộng được và không cộng thành net loss."],
      ["Production transitions", "HUD FHA Single Family Production Report · Table 2 · 13 monthly flow/stock observations from Aug 2025 through Aug 2026. This is a separate report and series."],
      ["Transition identity", "Ending serious-delinquency inventory = beginning + entries − cures − claims − prepayments from serious delinquency inventory."],
      ["Late posting", "Beginning inventory in each later month reconciles to the prior ending inventory plus the published late-posting adjustment."],
      ["Cure ratio", "HUD defines this as same-month cures divided by entries. It is not a matched-cohort cure probability; it may exceed 100%."],
      ["Serious delinquency", "Inventory includes 90+ day delinquency, in-foreclosure and in-bankruptcy loans; excludes HECM."],
      ["Production report source", "https://www.hud.gov/sites/default/files/Housing/documents/FHAProd_AUG2026.pdf · Table 2, report page 3. Direct PDF download returned HTTP 403; no raw PDF hash is claimed."],
      ["Cross-report caveat", "HUD says Table 2 inventory may not reconcile fully with FHA Loan Performance Trends because timing and data sources differ."],
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
const reason = await addTable("New 90+ reasons", path.join(root, "docs/data/hud-fha-new-90plus-reasons-2026-08.csv"), [
  ["fiscal_period", "Fiscal period"], ["new_90plus_count", "New 90+ loans"],
  ["reduction_income_pct", "Income reduction %"], ["unemployed_pct", "Unemployed %"],
  ["excessive_obligations_pct", "Excessive obligations %"], ["death_illness_pct", "Death / illness %"],
  ["marital_difficulties_pct", "Marital difficulties %"], ["no_contact_pct", "Unable to contact %"],
  ["national_emergency_pct", "National emergency %"], ["other_pct", "Other reason %"],
  ["source_table", "HUD table"], ["source_page", "PDF page"], ["partial_period", "Partial period"],
], "HUDFHANew90PlusReasons", [20, 18, 20, 16, 24, 20, 22, 20, 24, 18, 12, 12, 16]);
workbook.worksheets.getItem("New 90+ reasons").getRange("B2:B23").setNumberFormat("#,##0");
workbook.worksheets.getItem("New 90+ reasons").getRange("C2:J23").setNumberFormat('0.00"%"');
const foreclosure = await addTable("Foreclosure", path.join(root, "docs/data/hud-fha-foreclosure-statistics-2026-08.csv"), [
  ["fiscal_year", "Fiscal year"], ["month", "Month"], ["active_iif_count", "Active IIF"],
  ["foreclosure_starts", "Foreclosure starts"], ["in_foreclosure_count", "In foreclosure"],
  ["foreclosure_claims_paid", "Claims paid"], ["foreclosure_starts_6m_moving_avg", "6-month starts average"],
  ["annualized_foreclosure_rate_pct", "Annualized foreclosure rate %"], ["source_table", "HUD table"], ["source_page", "PDF page"],
], "HUDFHAForeclosure", [14, 14, 18, 20, 20, 18, 24, 26, 12, 12]);
workbook.worksheets.getItem("Foreclosure").getRange("C2:G38").setNumberFormat("#,##0");
workbook.worksheets.getItem("Foreclosure").getRange("H2:H38").setNumberFormat('0.00"%"');
const recovery = await addTable("REO recovery", path.join(root, "docs/data/hud-fha-reo-recovery-2026-08.csv"), [
  ["state_or_territory", "State / territory"], ["dispositions_jul2026", "Dispositions · Jul 2026"],
  ["recovery_jul2026_pct", "Recovery · Jul 2026 %"], ["recovery_jun2026_pct", "Recovery · Jun 2026 %"],
  ["recovery_jul2025_pct", "Recovery · Jul 2025 %"], ["change_from_jun2026_pp", "Change vs Jun 2026 (pp)"],
  ["change_from_jul2025_pp", "Change vs Jul 2025 (pp)"], ["source_table", "HUD table"], ["source_page", "PDF page"],
], "HUDFHAReoRecovery", [20, 23, 24, 24, 24, 25, 25, 12, 12]);
workbook.worksheets.getItem("REO recovery").getRange("B2:B51").setNumberFormat("#,##0");
workbook.worksheets.getItem("REO recovery").getRange("C2:E51").setNumberFormat('0.0"%"');
workbook.worksheets.getItem("REO recovery").getRange("F2:G51").setNumberFormat('0.0" pp"');
const losses = await addTable("REO loss detail", path.join(root, "docs/data/hud-fha-reo-loss-components-2026-08.csv"), [
  ["disposition_month", "Disposition month"], ["claim_expenses_pct", "Claim expenses %"],
  ["holding_costs_pct", "Holding costs %"], ["loss_on_collateral_pct", "Loss on collateral %"],
  ["sales_expense_pct", "Sales expenses %"], ["program_discounts_pct", "Program discounts %"],
  ["net_loss_rate_pct", "Net loss rate %"], ["average_dollar_loss", "Average dollar loss ($)"],
  ["average_unpaid_balance", "Average unpaid balance ($)"], ["dispositions", "Dispositions"], ["discounts", "Discounts"],
  ["delinquency_stage_months", "Delinquency (months)"], ["foreclosure_stage_months", "Foreclosure (months)"],
  ["deed_transfer_stage_months", "Deed transfer (months)"], ["reo_stage_months", "REO (months)"],
  ["all_stages_months", "All stages (months)"], ["source_table", "HUD table"], ["source_page", "PDF page"],
], "HUDFHAReoLoss", [18, 19, 18, 22, 20, 22, 19, 23, 26, 16, 14, 22, 23, 23, 15, 20, 12, 12]);
workbook.worksheets.getItem("REO loss detail").getRange("B2:G14").setNumberFormat('0.00"%"');
workbook.worksheets.getItem("REO loss detail").getRange("H2:I14").setNumberFormat("$#,##0");
workbook.worksheets.getItem("REO loss detail").getRange("J2:K14").setNumberFormat("#,##0");
workbook.worksheets.getItem("REO loss detail").getRange("L2:P14").setNumberFormat('0.0" months"');

const transitions = await addTable("Delinquency flow", path.join(root, "docs/data/hud-fha-production-transitions-2026-08.csv"), [
  ["period", "Period"], ["performance_year", "Performance year"], ["month", "Month"],
  ["beginning_serious_delinquency_inventory", "Beginning serious-delinquency inventory"],
  ["serious_delinquency_entries", "Entering serious delinquency"],
  ["cures_leaving_serious_delinquency", "Cured / leaving serious delinquency"],
  ["claims", "Claims"],
  ["prepayments_from_serious_delinquency_inventory", "Prepayments from serious delinquency"],
  ["ending_serious_delinquency_inventory", "Ending serious-delinquency inventory"],
  ["late_posting_adjustment", "Late-posting adjustment"], ["cure_ratio_pct", "HUD cure ratio %"],
  ["source_table", "HUD table"], ["source_page", "Report page"],
  ["flow_identity_difference", "Flow identity difference"],
  ["recomputed_cure_ratio_pct", "Recomputed cure ratio %"],
  ["prior_ending_plus_adjustment_difference", "Beginning bridge difference"],
], "HUDFHAProductionTransitions", [14, 17, 12, 28, 22, 25, 13, 27, 27, 19, 18, 12, 14, 20, 20, 20]);
const transitionSheet = workbook.worksheets.getItem("Delinquency flow");
transitionSheet.freezePanes.freezeColumns(3);
transitionSheet.getRange("D2:J14").setNumberFormat("#,##0;(#,##0)");
transitionSheet.getRange("K2:K14").setNumberFormat('0.0"%"');
transitionSheet.getRange("N2:N14").formulas = Array.from({ length: 13 }, (_, index) => {
  const row = index + 2;
  return [`=I${row}-(D${row}+E${row}-F${row}-G${row}-H${row})`];
});
transitionSheet.getRange("O2:O14").formulas = Array.from({ length: 13 }, (_, index) => {
  const row = index + 2;
  return [`=ROUND(F${row}/E${row}*100,1)`];
});
transitionSheet.getRange("P3:P14").formulas = Array.from({ length: 12 }, (_, index) => {
  const row = index + 3;
  return [`=D${row}-(I${row - 1}+J${row})`];
});
transitionSheet.getRange("N2:N14").setNumberFormat("#,##0;(#,##0)");
transitionSheet.getRange("O2:O14").setNumberFormat('0.0"%"');
transitionSheet.getRange("P2:P14").setNumberFormat("#,##0;(#,##0)");
transitionSheet.getRange("P2").values = [["—"]];

workbook.recalculate();
console.log(JSON.stringify({ monthly, subgroup, reason, foreclosure, recovery, losses, transitions }));
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of ["Bat dau", "Monthly trend", "Subgroup rates", "New 90+ reasons", "Foreclosure", "REO recovery", "REO loss detail", "Delinquency flow"]) {
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
