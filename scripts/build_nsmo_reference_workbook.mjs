import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [rootArg, outputArg, previewArg] = process.argv.slice(2);
if (!rootArg || !outputArg) throw new Error("usage: build_nsmo_reference_workbook.mjs <root> <output.xlsx> [preview.png]");
const root = path.resolve(rootArg);
const output = path.resolve(outputArg);
const previewPath = previewArg ? path.resolve(previewArg) : null;
const sources = [
  ["Tu dien 587 truong", "nsmo-v70-field-dictionary.csv", {
    codebook_order: "Thứ tự codebook", csv_column: "Tên cột CSV (giữ nguyên)", codebook_name: "Tên biến theo codebook",
    codebook_part: "Phần codebook", survey_wave_ranges: "Wave ghi trong codebook", survey_question_refs: "Mã câu hỏi",
    codebook_condition: "Điều kiện / routing", wave_variant_flags: "Cờ biến thể wave", quarter: "Quý", pdf_page: "Trang PDF",
    printed_page: "Trang in", field_family: "Nhóm trường", timing_class: "Thời điểm dữ liệu",
    predictor_use: "Quy tắc dùng làm predictor", sas_length: "Độ dài SAS", sas_format: "SAS format", sas_label: "Nhãn SAS / mô tả",
  }],
  ["Nhan va category", "nsmo-v70-value-labels.csv", {
    format_name: "Tên SAS format", format_value: "Mã category (giữ nguyên)", format_label: "Nhãn category",
  }],
  ["Coverage theo wave", "nsmo-v70-wave-coverage.csv", {
    csv_column: "Tên cột CSV (giữ nguyên)", sas_label: "Nhãn SAS / câu hỏi", sas_format: "SAS format",
    question_refs: "Mã câu hỏi", codebook_variant_flags: "Cờ biến thể codebook", observed_response_waves: "Wave có phản hồi quan sát",
    entirely_not_asked_waves: "Wave hoàn toàn không được hỏi (-3)", partially_not_asked_waves: "Wave được hỏi một phần (-3)",
    not_applicable_waves: "Wave không áp dụng (-2)", waves_with_missing_code: "Wave có mã thiếu", interpretation: "Cách diễn giải / giới hạn",
  }],
  ["So sanh wording item", "nsmo-v70-wave-item-comparability.csv", {
    field: "Tên cột CSV (giữ nguyên)", sas_label: "Nhãn SAS / câu hỏi", observed_response_waves: "Wave có phản hồi quan sát",
    not_asked_waves: "Wave không được hỏi", question_refs: "Mã câu hỏi", sas_format: "SAS format",
    scale_labels: "Nhãn thang trả lời", exact_item_phrase_found_in_packages: "Số gói questionnaire có wording",
    assessment: "Đánh giá / giới hạn trend",
  }],
];

const wb = Workbook.create();
const guide = wb.worksheets.add("Bat dau");
guide.showGridLines = false;
const guideRows = [
  ["CreditAtlas · NSMO v7.0 reference workbook", ""],
  ["Mục đích", "Tra cứu codebook, nhãn category, coverage theo wave và ghi chú wording; workbook không chứa hồ sơ khoản vay."],
  ["Nguồn", "Bốn bảng metadata đã làm sạch trong docs/data; CSV gốc vẫn được dùng để app kiểm tra schema và tái tạo workbook."],
  ["Cách dùng", "Bốn sheet dữ liệu là Excel Table: dùng bộ lọc ở tiêu đề, tìm mã biến/category và thêm ghi chú nội bộ ở cột mới."],
  ["Mã category", "Giữ nguyên mã SAS/CSV, gồm -2 và -3; không tự gộp missing, not asked hoặc not applicable."],
  ["Coverage", "Phản ánh availability/mã quan sát theo wave; không tự chứng minh cùng cách đo hoặc đủ điều kiện làm predictor."],
  ["So sánh item", "Wording được rà trên questionnaire packages; đọc cột đánh giá trước khi so sánh trend giữa wave."],
  ["Làm mới", "Chạy scripts/build_nsmo_reference_workbook.mjs với root project và đường dẫn output .xlsx."],
];
guide.getRange(`A1:B${guideRows.length}`).values = guideRows;
guide.getRange("A1:B1").merge();
guide.getRange("A1:B1").format = {
  fill: "#243B53", font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" },
  verticalAlignment: "center", wrapText: true,
};
guide.getRange("A2:A8").format = { font: { bold: true, color: "#243B53" }, verticalAlignment: "top", wrapText: true };
guide.getRange("A2:B8").format.verticalAlignment = "top";
guide.getRange("A1:B8").format.wrapText = true;
guide.getRange("A:A").format.columnWidth = 25;
guide.getRange("B:B").format.columnWidth = 105;
guide.getRange("A1:B1").format.rowHeight = 32;
guide.getRange("A2:B8").format.rowHeight = 42;

for (let i = 0; i < sources.length; i += 1) {
  const [sheetName, fileName, labels] = sources[i];
  const csv = await fs.readFile(path.join(root, "docs", "data", fileName), "utf8");
  const imported = await Workbook.fromCSV(csv, { sheetName: "Source" });
  const raw = imported.worksheets.getItem("Source").getUsedRange().values;
  const headers = raw[0].map((header) => labels[String(header)] ?? String(header));
  const rows = raw.slice(1).map((row) => row.map((value) => value == null ? "" : String(value)));
  const sheet = wb.worksheets.add(sheetName);
  sheet.showGridLines = false;
  sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length).values = [headers, ...rows];
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
    fill: "#243B53", font: { bold: true, color: "#FFFFFF", size: 10 },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
  };
  sheet.getRangeByIndexes(1, 0, rows.length, headers.length).format = {
    verticalAlignment: "top", wrapText: true,
  };
  sheet.getRangeByIndexes(0, 0, 1, headers.length).format.rowHeight = 42;
  const table = sheet.tables.add(`A1:${columnName(headers.length)}${rows.length + 1}`, true, `NSMOReference${i + 1}`);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  for (let col = 0; col < headers.length; col += 1) {
    const sampleWidths = rows.slice(0, 25).map((row) => String(row[col] ?? "").length);
    const width = Math.min(58, Math.max(16, headers[col].length + 2, Math.min(42, ...sampleWidths, 42) + 2));
    sheet.getRange(`${columnName(col + 1)}:${columnName(col + 1)}`).format.columnWidth = width;
  }
  sheet.freezePanes.freezeColumns(1);
}

function columnName(index) {
  let output = "";
  while (index > 0) {
    const remainder = (index - 1) % 26;
    output = String.fromCharCode(65 + remainder) + output;
    index = Math.floor((index - 1) / 26);
  }
  return output;
}

const inspection = await wb.inspect({ kind: "workbook,sheet,table", maxChars: 5000, tableMaxRows: 3, tableMaxCols: 4 });
console.log(inspection.ndjson);
if (previewPath) {
  const preview = await wb.render({ sheetName: "Bat dau", autoCrop: "all", scale: 1, format: "png" });
  await fs.mkdir(path.dirname(previewPath), { recursive: true });
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(path.dirname(output), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(output);
