import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const [reportPath, outputPath, previewDir] = process.argv.slice(2);
if (!reportPath || !outputPath || !previewDir) {
  throw new Error('usage: node build_bondora_n14_readiness.mjs private-report.json output.xlsx preview-dir');
}
const report = JSON.parse(await fs.readFile(reportPath, 'utf8'));
if (report.status !== 'PASS_AGGREGATE_ONLY_DIAGNOSTIC' || report.row_level_ids_emitted !== false || report.model_fit_performed !== false) {
  throw new Error('Source readiness report controls failed');
}

const NAVY = '#17324D', BLUE = '#315E7D', PALE = '#E9F1F6', AMBER = '#FFF2D8', RED = '#FCE8E6';
const maturityCounts = report.maturity_proxy_diagnostic.counts;
const matureNullDiagnostics = report.maturity_proxy_diagnostic.proxy_mature_null_diagnostic_only;
const proxyMatureNull = maturityCounts.mature_by_file_date_proxy_null || 0;
const workbook = Workbook.create();

const summary = workbook.worksheets.add('Summary');
summary.showGridLines = false;
summary.getRange('A1:H1').merge();
summary.getRange('A1').values = [['Bondora · 12-MOB label and cohort support audit']];
summary.getRange('A1:H1').format = { fill: NAVY, font: { name: 'Aptos Display', size: 16, bold: true, color: '#FFFFFF' }, verticalAlignment: 'center', rowHeight: 40 };
summary.getRange('A2:H2').merge();
summary.getRange('A2').values = [['Aggregate-only qualification of the private 789,144-row public dataset snapshot · no loan IDs or loan-level rows']];
summary.getRange('A2:H2').format = { fill: PALE, font: { color: NAVY, size: 10 }, verticalAlignment: 'center', rowHeight: 24 };
summary.getRange('A4:B8').values = [
  ['Source / label control', 'Recalculated result'],
  ['Source rows', null],
  ['12-MOB label = true', null],
  ['12-MOB label = false', null],
  ['12-MOB label = NULL / not measurable', null],
];
summary.getRange('A4:B4').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF' }, wrapText: true };
const yearRows = Object.entries(report.by_origination_year).map(([issue_year, row]) => ({ issue_year, ...row }));
const lastYearRow = yearRows.length + 1;
summary.getRange('B5:B8').formulas = [
  [`=SUM('By year'!$B$2:$B$${lastYearRow})`],
  [`=SUM('By year'!$C$2:$C$${lastYearRow})`],
  [`=SUM('By year'!$D$2:$D$${lastYearRow})`],
  [`=SUM('By year'!$E$2:$E$${lastYearRow})`],
];
summary.getRange('A5:A8').format = { wrapText: true, verticalAlignment: 'center', rowHeight: 30 };
summary.getRange('B5:B8').format = { font: { bold: true, color: NAVY }, horizontalAlignment: 'center' };
summary.getRange('B5:B8').format.numberFormat = '#,##0';
summary.getRange('A11:D14').values = [
  ['Snapshot maturity diagnostic', 'Loans', '12-MOB NULL', 'Interpretation'],
  ['Mature by file-date proxy', null, null, 'Issue date + 12 calendar months ≤ 2026-08-10'],
  ['Not mature by file-date proxy', null, null, 'NULL is expected under this proxy; do not treat as a negative'],
  ['Proxy-mature NULL with no later action evidence', null, proxyMatureNull,
    `${matureNullDiagnostics.action_observation.missing || 0} have no last-action date; ${matureNullDiagnostics.action_observation.last_action_before_12m_anniversary || 0} have action before 12-month anniversary`],
];
summary.getRange('B12:C13').values = [
  [maturityCounts.mature_by_file_date_proxy_true + maturityCounts.mature_by_file_date_proxy_false + maturityCounts.mature_by_file_date_proxy_null, maturityCounts.mature_by_file_date_proxy_null],
  [maturityCounts.not_mature_by_proxy_null, maturityCounts.not_mature_by_proxy_null],
];
summary.getRange('A11:D11').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 38 };
summary.getRange('A12:D14').format = { wrapText: true, verticalAlignment: 'top', rowHeight: 46 };
summary.getRange('A12:A14').format = { fill: PALE, font: { bold: true, color: NAVY }, wrapText: true };
summary.getRange('B12:C14').format.numberFormat = '#,##0';
summary.getRange('A16:H19').merge();
summary.getRange('A16').values = [[
  'Critical limitation: file Last-Modified is only a cutoff proxy, not proof of per-loan observation through 12 months. Do not replace the 10,860 proxy-mature NULLs with false. They have no recorded action on or after the assumed 12-month anniversary. The source does not establish why these labels remain NULL.'
]];
summary.getRange('A16:H19').format = { fill: AMBER, font: { color: '#664D03' }, wrapText: true, verticalAlignment: 'top' };
summary.getRange('A21:H24').merge();
summary.getRange('A21').values = [[
  'No model, forecast, imputation, PD estimate, calibration or country ranking was produced. Country and year tables describe the downloaded snapshot only; markets and vintage periods have different coverage and label maturity.'
]];
summary.getRange('A21:H24').format = { fill: RED, font: { color: '#7A271A' }, wrapText: true, verticalAlignment: 'top' };
[43, 25, 24, 68, 18, 18, 18, 18].forEach((width, i) => summary.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);
summary.freezePanes.freezeRows(4);

const byYear = workbook.worksheets.add('By year');
byYear.showGridLines = false;
const yearHeaders = ['Origination year', 'Loans', 'Label true', 'Label false', 'Label NULL', 'Known-label coverage'];
const yearValues = yearRows.map((row, i) => [row.issue_year, row.loans, row.target_true, row.target_false, row.target_null, null]);
byYear.getRangeByIndexes(0, 0, yearValues.length + 1, yearHeaders.length).values = [yearHeaders, ...yearValues];
byYear.tables.add(`A1:F${yearValues.length + 1}`, true, 'BondoraByOriginationYear');
for (let i = 0; i < yearValues.length; i++) {
  const r = i + 2;
  byYear.getRange(`F${r}`).formulas = [[`=IFERROR((C${r}+D${r})/B${r},"")`]];
}
byYear.getRange(`A1:F${yearValues.length + 1}`).format = { wrapText: true, verticalAlignment: 'center' };
byYear.getRange('A1:F1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 36 };
byYear.getRange(`F2:F${yearValues.length + 1}`).format.numberFormat = '0.0%';
byYear.getRange(`B2:E${yearValues.length + 1}`).format.numberFormat = '#,##0';
byYear.getRange('A:A').format.columnWidth = 20;
byYear.getRange('B:E').format.columnWidth = 17;
byYear.getRange('F:F').format.columnWidth = 27;
byYear.freezePanes.freezeRows(1);

const byCountry = workbook.worksheets.add('By country');
byCountry.showGridLines = false;
const countryHeaders = ['Country', 'Loans', 'Label true', 'Label false', 'Label NULL', 'Known-label coverage', 'Issue date span', 'Small-cell suppressed'];
const countryValues = Object.entries(report.by_country).map(([country, row]) => {
  const suppressed = row.loans < 50;
  return [country, suppressed ? null : row.loans, suppressed ? null : row.target_true,
    suppressed ? null : row.target_false, suppressed ? null : row.target_null, null,
    row.issue_date_min + ' to ' + row.issue_date_max, suppressed ? 'Yes' : 'No'];
});
byCountry.getRangeByIndexes(0, 0, countryValues.length + 1, countryHeaders.length).values = [countryHeaders, ...countryValues];
byCountry.tables.add(`A1:H${countryValues.length + 1}`, true, 'BondoraCountrySupport');
for (let i = 0; i < countryValues.length; i++) {
  const r = i + 2;
  byCountry.getRange(`F${r}`).formulas = [[`=IFERROR((C${r}+D${r})/B${r},"")`]];
}
byCountry.getRange(`A1:H${countryValues.length + 1}`).format = { wrapText: true, verticalAlignment: 'center' };
byCountry.getRange('A1:H1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 42 };
byCountry.getRange(`F2:F${countryValues.length + 1}`).format.numberFormat = '0.0%';
byCountry.getRange(`B2:E${countryValues.length + 1}`).format.numberFormat = '#,##0';
[18, 16, 16, 16, 16, 24, 30, 24].forEach((width, i) => byCountry.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);
byCountry.freezePanes.freezeRows(1);

const countryYear = workbook.worksheets.add('Country x year');
countryYear.showGridLines = false;
const cyHeaders = ['Country', 'Origination year', 'Loans', 'Label true', 'Label false', 'Label NULL', 'Small-cell suppressed'];
const cyValues = report.by_country_and_year.map(row => [row.country, row.issue_year, row.loans,
  row.target_true, row.target_false, row.target_null, row.small_cell_suppressed ? 'Yes' : 'No']);
countryYear.getRangeByIndexes(0, 0, cyValues.length + 1, cyHeaders.length).values = [cyHeaders, ...cyValues];
countryYear.tables.add(`A1:G${cyValues.length + 1}`, true, 'BondoraCountryYearSupport');
countryYear.getRange(`A1:G${cyValues.length + 1}`).format = { wrapText: true, verticalAlignment: 'center' };
countryYear.getRange('A1:G1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 40 };
countryYear.getRange(`C2:F${cyValues.length + 1}`).format.numberFormat = '#,##0';
[20, 18, 16, 16, 16, 16, 24].forEach((width, i) => countryYear.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);
countryYear.freezePanes.freezeRows(1);

const maturity = workbook.worksheets.add('Maturity diagnostic');
maturity.showGridLines = false;
const maturityRows = [];
for (const row of report.maturity_proxy_diagnostic.by_origination_year) {
  maturityRows.push(['Year', row.issue_year, row.maturity_group, row.loans, row.target_true, row.target_false, row.target_null, '']);
}
for (const row of report.maturity_proxy_diagnostic.by_country) {
  const suppressed = row.loans < 50;
  maturityRows.push(['Country', row.country, row.maturity_group, suppressed ? null : row.loans,
    suppressed ? null : row.target_true, suppressed ? null : row.target_false,
    suppressed ? null : row.target_null, suppressed ? 'Yes' : 'No']);
}
for (const row of report.maturity_proxy_diagnostic.by_country_and_year) {
  maturityRows.push(['Country x year', row.country + ' / ' + row.issue_year, row.maturity_group,
    row.loans, row.target_true, row.target_false, row.target_null, row.small_cell_suppressed ? 'Yes' : 'No']);
}
const maturityHeaders = ['Support grain', 'Country / year', 'File-date maturity proxy', 'Loans', 'Label true', 'Label false', 'Label NULL', 'Suppression'];
maturity.getRangeByIndexes(0, 0, maturityRows.length + 1, maturityHeaders.length).values = [maturityHeaders, ...maturityRows];
maturity.tables.add(`A1:H${maturityRows.length + 1}`, true, 'BondoraMaturityDiagnostics');
maturity.getRange(`A1:H${maturityRows.length + 1}`).format = { wrapText: true, verticalAlignment: 'center' };
maturity.getRange('A1:H1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 40 };
maturity.getRange(`D2:G${maturityRows.length + 1}`).format.numberFormat = '#,##0';
[22, 23, 36, 16, 16, 16, 16, 18].forEach((width, i) => maturity.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);
maturity.freezePanes.freezeRows(1);

const methods = workbook.worksheets.add('Methods and limits');
methods.showGridLines = false;
const methodRows = [
  ['Item', 'Definition / result'],
  ['Publisher public dataset page', 'https://goandgrow.eu/en/public-statistics/'],
  ['2026 transparency report', 'https://goandgrow.eu/en/blog/bondora-loan-portfolio-statistics-2026-a-transparency-report/'],
  ['Local source snapshot', `SHA-256 ${report.source.sha256}; ${report.source.bytes} bytes; 789,144 rows × 31 fields; two sheets.`],
  ['Publisher Last-Modified proxy', '2026-08-10 (verified by HTTP HEAD on 2026-10-17); not a verified per-loan observation cutoff.'],
  ['Publisher 12-month label wording', report.label_definition_from_source_dictionary],
  ['Maturity calculation', 'Proxy only: loan issue date + 12 calendar months, clamping leap-day anniversaries to Feb 28, compared with 2026-08-10. No outcome values are changed.'],
  ['Publisher PD12 observation requirement', 'The 2026 transparency report says PD12 is the share defaulting within 12 months of issuance and notes a full 12-month observation period is required before cohort reporting. It does not establish this dataset export’s per-loan cutoff or historical label build.'],
  ['Publisher default definition', 'The 2026 transparency report describes default as more than 90 days overdue and the customer contract terminated due to arrears. Do not assume this definition is proven identical for every historical row in this export.'],
  ['Feature availability', 'No feature set selected. Dictionary says customer risk rating is at issue, but requested amount, application decision timestamps, and verified point-in-time income source/availability are absent.'],
  ['Excluded post-booking fields', 'Current status/default, repayment and fee totals, outstanding principal, DPD/default months, last action, next payment, early repayment, projected NPV and other servicing fields are outcomes/after-booking.'],
  ['Unresolved maturity evidence', `${proxyMatureNull.toLocaleString('en-US')} labels are NULL although issue+12 months precedes the file-date proxy. Of these, ${(matureNullDiagnostics.action_observation.missing || 0).toLocaleString('en-US')} have no last-action date and ${(matureNullDiagnostics.action_observation.last_action_before_12m_anniversary || 0).toLocaleString('en-US')} have a last action before the 12-month anniversary; ${(matureNullDiagnostics.action_observation.last_action_on_or_after_12m_anniversary || 0).toLocaleString('en-US')} have a recorded action on/after that anniversary.`],
  ['Use limits', 'No model fit, probability estimate, forecast, imputation, calibration, country ranking or country-level PD was produced. Aggregates are descriptive support counts only.'],
  ['Rights / visibility', report.rights_note],
];
methods.getRangeByIndexes(0, 0, methodRows.length, 2).values = methodRows;
methods.getRange('A1:B1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 32 };
methods.getRange(`A2:B${methodRows.length}`).format = { wrapText: true, verticalAlignment: 'top', rowHeight: 64 };
methods.getRange('A:A').format.columnWidth = 36;
methods.getRange('B:B').format.columnWidth = 125;
methods.freezePanes.freezeRows(1);

await workbook.recalculate();
const expected = [report.source.data_rows, report.label_counts.true, report.label_counts.false, report.label_counts.null];
const actual = summary.getRange('B5:B8').values.flat();
if (actual.some((value, i) => value !== expected[i])) {
  throw new Error(`Workbook formula checks failed: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
}
await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range, filename] of [
  ['Summary', 'A1:H24', 'Summary.png'],
  ['By country', 'A1:H10', 'By-country.png'],
  ['By year', `A1:F${yearValues.length + 1}`, 'By-year.png'],
  ['Methods and limits', 'A1:B14', 'Methods-and-limits.png'],
]) {
  const image = await workbook.render({ sheetName, range, scale: 1, format: 'png' });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await image.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ status: 'PASS', sheets: 6, yearRows: yearValues.length, countryRows: countryValues.length,
  countryYearRows: cyValues.length, summaryChecks: actual, outputPath }, null, 2));

function columnName(number) {
  let result = '';
  while (number > 0) {
    const remainder = (number - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    number = Math.floor((number - 1) / 26);
  }
  return result;
}
