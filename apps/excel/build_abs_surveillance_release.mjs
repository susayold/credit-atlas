import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const [csvPath, contractsPath, receiptPath, outputPath, previewDir] = process.argv.slice(2);
if (!csvPath || !contractsPath || !receiptPath || !outputPath || !previewDir) {
  throw new Error('usage: node build_abs_surveillance_release.mjs ledger.csv contracts.json receipt.json output.xlsx preview-dir');
}

const NAVY = '#17324D';
const BLUE = '#315E7D';
const PALE = '#E9F1F6';
const AMBER = '#FFF2D8';
const RED = '#FCE8E6';
const data = parseCsv(await fs.readFile(csvPath, 'utf8'));
const headers = data[0].map((value, i) => i === 0 ? value.replace(/^\uFEFF/, '') : value);
const sourceRows = data.slice(1).filter(row => row.length && row[0]);
const index = Object.fromEntries(headers.map((name, i) => [name, i]));
const contracts = JSON.parse(await fs.readFile(contractsPath, 'utf8'));
const receipt = JSON.parse(await fs.readFile(receiptPath, 'utf8'));
if (sourceRows.length !== 103 || receipt.period_count !== 103 || contracts.contracts.length !== 3) {
  throw new Error('Expected three deal contracts and 103 aggregate periods');
}
if (receipt.cross_deal_recovery_residual_total !== null) {
  throw new Error('Do not aggregate recovery residual dollars across deal contracts');
}
const get = (row, name) => row[index[name]] ?? '';
const toValue = (header, value) => {
  if (value === '') return null;
  if (header.endsWith('_usd') || header.endsWith('_count') || header.endsWith('_fields') || header.endsWith('_days')) {
    const n = Number(value);
    return Number.isFinite(n) ? n : value;
  }
  return value;
};
const ledgerRows = sourceRows.map(row => row.map((value, i) => toValue(headers[i], value)));
const lastRow = ledgerRows.length + 1;
const contractCol = column('deal_id');
const recoveryStatusCol = column('recovery_tie_status');
const recoveryDeltaCol = column('recovery_delta_asset_minus_certificate_usd');
const exceptionStatusCol = column('exception_status');
const dpdExactCol = column('dpd_literal_exact_fields');
const dpdTotalCol = column('dpd_total_field_checks');
const workbook = Workbook.create();

const summary = workbook.worksheets.add('Summary');
summary.showGridLines = false;
summary.getRange('A1:J1').merge();
summary.getRange('A1').values = [['Structured ABS surveillance · contract-aware release']];
summary.getRange('A1:J1').format = { fill: NAVY, font: { name: 'Aptos Display', size: 16, bold: true, color: '#FFFFFF' }, verticalAlignment: 'center', rowHeight: 40 };
summary.getRange('A2:J2').merge();
summary.getRange('A2').values = [['Toyota 2022-B, Toyota 2024-B and Nissan 2024-B · 103 deal-period rows · source comparators remain contract-specific']];
summary.getRange('A2:J2').format = { fill: PALE, font: { color: NAVY, size: 10 }, verticalAlignment: 'center', rowHeight: 24 };
summary.getRange('A4:B8').values = [
  ['Release control', 'Recalculated result'],
  ['Deal-period rows', null],
  ['Deal contracts', null],
  ['Periods with any reconciliation exception', null],
  ['Non-zero recovery comparator periods', null],
];
summary.getRange('A4:B4').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF' }, wrapText: true };
summary.getRange('A5:A8').format = { wrapText: true, verticalAlignment: 'center', rowHeight: 34 };
summary.getRange('B5:B8').format = { font: { bold: true, color: NAVY }, horizontalAlignment: 'center', verticalAlignment: 'center' };
summary.getRange('B5:B8').formulas = [
  [`=COUNTA('Period ledger'!$A$2:$A$${lastRow})`],
  ['=COUNTA(A12:A14)'],
  [`=COUNTIF('Period ledger'!$${exceptionStatusCol}$2:$${exceptionStatusCol}$${lastRow},"UNRESOLVED")`],
  [`=COUNTIF('Period ledger'!$${recoveryStatusCol}$2:$${recoveryStatusCol}$${lastRow},"UNRESOLVED")`],
];

const summaryHeaders = [
  'Deal', 'Contract ID', 'Periods', 'Certificate recovery comparator',
  'Tied periods', 'Recovery exceptions', 'Recovery delta total · within contract only USD',
  'Periods with any exception', 'Native DPD exact fields', 'Native DPD fields checked',
];
summary.getRange('A11:J14').values = [
  summaryHeaders,
  ...contracts.contracts.map(contract => [contract.deal_id, contract.contract_id, null, contract.certificate_recovery_comparator_label, null, null, null, null, null, 'Contract-specific; no cross-deal aggregation']),
];
summary.getRange('A11:J11').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF', size: 9 }, wrapText: true, verticalAlignment: 'center', rowHeight: 44 };
const dealRange = `'Period ledger'!$${contractCol}$2:$${contractCol}$${lastRow}`;
const recoveryStatusRange = `'Period ledger'!$${recoveryStatusCol}$2:$${recoveryStatusCol}$${lastRow}`;
const deltaRange = `'Period ledger'!$${recoveryDeltaCol}$2:$${recoveryDeltaCol}$${lastRow}`;
const exceptionRange = `'Period ledger'!$${exceptionStatusCol}$2:$${exceptionStatusCol}$${lastRow}`;
const dpdExactRange = `'Period ledger'!$${dpdExactCol}$2:$${dpdExactCol}$${lastRow}`;
const dpdTotalRange = `'Period ledger'!$${dpdTotalCol}$2:$${dpdTotalCol}$${lastRow}`;
for (let i = 0; i < contracts.contracts.length; i++) {
  const row = 12 + i;
  summary.getRange(`C${row}`).formulas = [[`=COUNTIF(${dealRange},A${row})`]];
  summary.getRange(`E${row}:H${row}`).formulas = [[
    `=COUNTIFS(${dealRange},A${row},${recoveryStatusRange},"TIED")`,
    `=COUNTIFS(${dealRange},A${row},${recoveryStatusRange},"UNRESOLVED")`,
    `=SUMIF(${dealRange},A${row},${deltaRange})`,
    `=COUNTIFS(${dealRange},A${row},${exceptionRange},"UNRESOLVED")`,
  ]];
  summary.getRange(`D${row}`).values = [[contracts.contracts[i].certificate_recovery_comparator_label]];
  if (contracts.contracts[i].deal_id === 'NISSAN-2024-B') {
    summary.getRange(`I${row}:J${row}`).formulas = [[`=SUMIF(${dealRange},A${row},${dpdExactRange})`, `=SUMIF(${dealRange},A${row},${dpdTotalRange})`]];
  } else {
    summary.getRange(`I${row}:J${row}`).values = [['Not included in this ledger', 'Not included in this ledger']];
  }
}
summary.getRange('A12:J14').format = { wrapText: true, verticalAlignment: 'top', rowHeight: 48 };
summary.getRange('A12:B14').format = { fill: PALE, font: { color: NAVY, bold: true } };
summary.getRange('C12:C14').format.numberFormat = '#,##0';
summary.getRange('E12:F14').format.numberFormat = '#,##0';
summary.getRange('G12:G14').format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
summary.getRange('A16:J19').merge();
summary.getRange('A16').values = [[
  'Analyst readout: 83 recovery-comparator period residuals remain non-zero across the three contracts. Toyota compares ABS-EE recoveredAmount with aggregate net liquidation proceeds; Nissan compares with current Recoveries of Defaulted Receivables. Keep residuals and tie counts within each contract. Do not calculate a pooled recovery delta, tie rate, LGD or loss estimate.'
]];
summary.getRange('A16:J19').format = { fill: AMBER, font: { color: '#664D03' }, wrapText: true, verticalAlignment: 'top' };
summary.getRange('A21:J24').merge();
summary.getRange('A21').values = [[
  'Nissan adds nine exception periods beyond recovery (charge-off count/amount, first-code-4 count/amount and June 2025 literal DPD). The one-day-earlier DPD candidate matches June only and worsens full-panel checks from 178/184 to 86/184; it is diagnostic and not adopted. Root causes remain unresolved.'
]];
summary.getRange('A21:J24').format = { fill: RED, font: { color: '#7A271A' }, wrapText: true, verticalAlignment: 'top' };
[38, 36, 14, 42, 14, 18, 34, 20, 26, 34].forEach((width, i) => summary.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);
summary.freezePanes.freezeRows(11);

const ledger = workbook.worksheets.add('Period ledger');
ledger.showGridLines = false;
ledger.getRangeByIndexes(0, 0, ledgerRows.length + 1, headers.length).values = [headers, ...ledgerRows];
const lastColumn = columnName(headers.length);
const table = ledger.tables.add(`A1:${lastColumn}${lastRow}`, true, 'ABSSurveillancePeriods');
table.style = 'TableStyleMedium2';
table.showFilterButton = true;
ledger.getRange(`A1:${lastColumn}1`).format = { fill: NAVY, font: { bold: true, color: '#FFFFFF', size: 9 }, wrapText: true, verticalAlignment: 'center', horizontalAlignment: 'center', rowHeight: 54 };
ledger.getRange(`A2:${lastColumn}${lastRow}`).format = { wrapText: true, verticalAlignment: 'top', rowHeight: 32 };
headers.forEach((header, i) => {
  const col = columnName(i + 1);
  let width = 18;
  if (header.endsWith('_url')) width = 72;
  else if (header.includes('accession')) width = 24;
  else if (header.endsWith('_usd')) width = 23;
  else if (header.includes('status') || header.includes('categories')) width = 26;
  else if (header.includes('definition')) width = 31;
  else if (header.endsWith('_count') || header.endsWith('_fields') || header.endsWith('_days')) width = 15;
  ledger.getRange(`${col}:${col}`).format.columnWidth = width;
});
for (const header of headers.filter(item => item.endsWith('_usd'))) {
  const col = column(header);
  ledger.getRange(`${col}2:${col}${lastRow}`).format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
}
for (const header of headers.filter(item => item.endsWith('_count') || item.endsWith('_fields') || item.endsWith('_days'))) {
  const col = column(header);
  ledger.getRange(`${col}2:${col}${lastRow}`).format.numberFormat = '#,##0;[Red](#,##0);–';
}
ledger.freezePanes.freezeRows(1);
ledger.freezePanes.freezeColumns(5);

const definitions = workbook.worksheets.add('Data contracts');
definitions.showGridLines = false;
const contractRows = contracts.contracts.map(contract => [
  contract.deal_id,
  contract.contract_id,
  contract.trust_name,
  contract.issuer_family,
  contract.expected_period_count,
  contract.expected_report_start + ' to ' + contract.expected_report_end,
  contract.certificate_recovery_comparator_label,
  contract.certificate_recovery_definition,
  contract.native_dpd_definition_id,
  contract.native_dpd_definition,
  contract.evidence_note,
]);
const definitionHeaders = ['Deal', 'Contract ID', 'Trust', 'Issuer family', 'Expected periods', 'Report window', 'Recovery comparator', 'Certificate recovery definition', 'Native DPD definition ID', 'Native DPD definition', 'Research evidence'];
definitions.getRangeByIndexes(0, 0, contractRows.length + 1, definitionHeaders.length).values = [definitionHeaders, ...contractRows];
definitions.tables.add(`A1:K${contractRows.length + 1}`, true, 'ABSDealDataContracts');
definitions.getRange('A1:K1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 42 };
definitions.getRange(`A2:K${contractRows.length + 1}`).format = { fill: PALE, wrapText: true, verticalAlignment: 'top', rowHeight: 92 };
definitions.getRange('A:A').format.columnWidth = 22;
definitions.getRange('B:B').format.columnWidth = 36;
definitions.getRange('C:C').format.columnWidth = 48;
definitions.getRange('D:D').format.columnWidth = 30;
definitions.getRange('E:F').format.columnWidth = 20;
definitions.getRange('G:G').format.columnWidth = 38;
definitions.getRange('H:H').format.columnWidth = 90;
definitions.getRange('I:I').format.columnWidth = 42;
definitions.getRange('J:J').format.columnWidth = 72;
definitions.getRange('K:K').format.columnWidth = 56;
definitions.freezePanes.freezeRows(1);

const finding = workbook.worksheets.add('Analyst finding');
finding.showGridLines = false;
finding.getRange('A1:B1').merge();
finding.getRange('A1').values = [[contracts.analyst_finding.finding_id + ' · ' + contracts.analyst_finding.title]];
finding.getRange('A1:B1').format = { fill: NAVY, font: { name: 'Aptos Display', size: 15, bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 58, verticalAlignment: 'center' };
const findingRows = [
  ['Classification', contracts.analyst_finding.classification],
  ['Status', contracts.analyst_finding.status],
  ['Observation', contracts.analyst_finding.statement],
  ['Required action', contracts.analyst_finding.required_action],
  ['Use limit', contracts.analyst_finding.use_limit],
  ['Release / evidence', contracts.release_id + ' · ' + receipt.period_count + ' aggregate deal-period rows · contract and source hashes are in the release receipt.'],
  ['Calculation rules', 'Each period residual is asset recoveredAmount minus its own certificate comparator. Exact tie only at zero. No missing-to-zero, interpolation, forecast, imputation, cross-deal recovery sum, or asset identifiers.'],
  ['Source: Toyota recovery-component research', 'docs/TOYOTA_RECOVERY_COMPONENT_EXCEPTION_LEDGER_VI.md'],
  ['Source: Nissan event / DPD / recovery research', 'docs/NISSAN_2024B_EXCEPTION_LEDGER_VI.md'],
  ['SEC public filings', 'Open report-period filings from the Period ledger: ABS-EE and certificate accessions are separately linked on every row.'],
];
finding.getRangeByIndexes(3, 0, findingRows.length, 2).values = findingRows;
finding.getRange('A4:A13').format = { fill: PALE, font: { bold: true, color: NAVY }, verticalAlignment: 'top', wrapText: true };
finding.getRange('A4:B13').format = { verticalAlignment: 'top', wrapText: true, rowHeight: 58 };
finding.getRange('B:B').format.columnWidth = 120;
finding.getRange('A:A').format.columnWidth = 38;
finding.freezePanes.freezeRows(3);

await workbook.recalculate();
const controls = summary.getRange('B5:B8').values.flat();
if (controls[0] !== 103 || controls[1] !== 3 || controls[2] !== 86 || controls[3] !== 83) {
  throw new Error(`Release KPI formula check failed: ${JSON.stringify(controls)}`);
}
const dealResults = summary.getRange('C12:J14').values;
const expectedDeals = [
  [51, 2, 49, 2058647.06, 49],
  [29, 1, 28, 1764558.08, 28],
  [23, 17, 6, 8859.23, 9],
];
for (let i = 0; i < expectedDeals.length; i++) {
  const actual = dealResults[i];
  const expected = expectedDeals[i];
  for (const [index, expectedValue] of [[0, expected[0]], [2, expected[1]], [3, expected[2]], [4, expected[3]], [5, expected[4]]]) {
    if (typeof actual[index] !== 'number' || Math.abs(actual[index] - expectedValue) > 0.01) {
      throw new Error(`Deal formula check failed at row ${12 + i}, column index ${index}: ${JSON.stringify(actual[index])} != ${expectedValue}`);
    }
  }
}
if (dealResults[2][6] !== 178 || dealResults[2][7] !== 184 || dealResults[0][6] !== 'Not included in this ledger' || dealResults[1][6] !== 'Not included in this ledger') {
  throw new Error(`Deal DPD availability labels changed: ${JSON.stringify(dealResults.map(row => row.slice(6)))}`);
}

await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range, filename] of [
  ['Summary', 'A1:J24', 'Summary.png'],
  ['Period ledger', 'A1:M9', 'Period-ledger.png'],
  ['Data contracts', 'A1:K4', 'Data-contracts.png'],
  ['Analyst finding', 'A1:B13', 'Analyst-finding.png'],
]) {
  const image = await workbook.render({ sheetName, range, scale: 1, format: 'png' });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await image.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ status: 'PASS', rows: ledgerRows.length, columns: headers.length, releaseChecks: controls, dealFormulaChecks: dealResults, outputPath }, null, 2));

function column(headerName) {
  let result = '';
  let number = index[headerName] + 1;
  while (number > 0) {
    const remainder = (number - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    number = Math.floor((number - 1) / 26);
  }
  return result;
}

function columnName(number) {
  let result = '';
  while (number > 0) {
    const remainder = (number - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    number = Math.floor((number - 1) / 26);
  }
  return result;
}

function parseCsv(text) {
  const output = [];
  let row = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (char === '"') quoted = false;
      else cell += char;
    } else if (char === '"') quoted = true;
    else if (char === ',') { row.push(cell); cell = ''; }
    else if (char === '\n') { row.push(cell.replace(/\r$/, '')); output.push(row); row = []; cell = ''; }
    else cell += char;
  }
  if (cell.length || row.length) { row.push(cell.replace(/\r$/, '')); output.push(row); }
  return output;
}
