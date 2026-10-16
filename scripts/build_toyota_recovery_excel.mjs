import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const [inputPath, outputPath, previewDir] = process.argv.slice(2);
if (!inputPath || !outputPath || !previewDir) {
  throw new Error('usage: node build_toyota_recovery_excel.mjs input.csv output.xlsx preview-dir');
}

const NAVY = '#243B53';
const BLUE = '#486581';
const PALE = '#EAF1F7';
const RED = '#9B1C1C';
const csvText = await fs.readFile(inputPath, 'utf8');
const parsed = parseCsv(csvText);
const headers = parsed[0].map((header, i) => i === 0 ? header.replace(/^\uFEFF/, '') : header);
const sourceRows = parsed.slice(1).filter(row => row.length && row[0]);
const index = Object.fromEntries(headers.map((name, i) => [name, i]));
const get = (row, name) => row[index[name]] ?? '';
const number = (value) => value === '' ? null : Number(value);
if (sourceRows.length !== 80 || sourceRows.some(row => !get(row, 'exception_id'))) {
  throw new Error('Expected 80 ledger rows with nonblank exception IDs');
}

const ledgerHeaders = [
  'Exception ID', 'Deal', 'Report month', 'Report date', 'Collection period start',
  'Collection period end', 'Calendar days', 'Filing date', 'ABS-EE accession',
  '10-D accession', 'ABS-EE recoveredAmount sum (USD)',
  'Certificate net liquidation proceeds (signed USD)',
  'Certificate recoveries on prior liquidations (signed USD)',
  'Certificate aggregate net liquidation proceeds (USD)',
  'Gross principal liquidated (USD)',
  'Repurchased previously charged-off principal (signed USD)',
  'Certificate net credit losses (USD)', 'Certificate recovery bridge check (USD)',
  'Certificate net-loss bridge check (USD)', 'Recovery component identity',
  'Net-loss identity', 'ABS-EE minus certificate (USD)', 'Reconciliation status',
  'Exception note', 'Certificate filing URL', 'Certificate SHA-256',
];

const ledgerRows = sourceRows.map(row => [
  get(row, 'exception_id'), get(row, 'deal'), get(row, 'report_month'), get(row, 'report_date'),
  get(row, 'collection_period_start'), get(row, 'collection_period_end'),
  number(get(row, 'calendar_days_in_collection_period')), get(row, 'filing_date'),
  get(row, 'abs_ee_accession'), get(row, 'ten_d_accession'),
  number(get(row, 'asset_recovered_amount_signed')),
  number(get(row, 'certificate_net_liquidation_proceeds_signed')),
  number(get(row, 'certificate_recoveries_previously_liquidated_signed')),
  number(get(row, 'certificate_aggregate_net_liquidation_proceeds')),
  number(get(row, 'certificate_gross_principal_liquidated')),
  number(get(row, 'certificate_repurchased_previously_charged_off_signed')),
  number(get(row, 'certificate_net_credit_losses')),
  number(get(row, 'certificate_aggregate_formula_delta')),
  number(get(row, 'certificate_net_loss_formula_delta')),
  get(row, 'certificate_component_identity_status'),
  get(row, 'certificate_net_loss_identity_status'),
  number(get(row, 'asset_minus_certificate_recovery_delta')),
  get(row, 'recovery_reconciliation_status'), get(row, 'exception_note'),
  get(row, 'certificate_url'), get(row, 'certificate_sha256'),
]);

const workbook = Workbook.create();
const summary = workbook.worksheets.add('Summary');
summary.showGridLines = false;
summary.getRange('A1:I1').merge();
summary.getRange('A1').values = [['Toyota ABS recovery exception ledger · source-backed public aggregates']];
summary.getRange('A1:I1').format = { fill: NAVY, font: { name: 'Aptos Display', size: 16, bold: true, color: '#FFFFFF' }, verticalAlignment: 'center', rowHeight: 38 };
summary.getRange('A3:B7').values = [
  ['Control', 'Result'],
  ['Periods audited', null],
  ['Tied periods', null],
  ['Unresolved periods', null],
  ['Net signed residual (USD)', null],
];
summary.getRange('A3:B3').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF' }, wrapText: true };
summary.getRange('B4:B7').formulas = [
  ["=COUNTA('Period ledger'!A2:A81)"],
  ["=COUNTIF('Period ledger'!W2:W81,\"TIED\")"],
  ["=COUNTIF('Period ledger'!W2:W81,\"UNRESOLVED\")"],
  ["=SUM('Period ledger'!V2:V81)"],
];
summary.getRange('A9:I9').merge();
summary.getRange('A9').values = [['Deal-level reconciliation']];
summary.getRange('A9:I9').format = { fill: PALE, font: { bold: true, color: NAVY, size: 12 } };
const dealHeaders = ['Deal', 'Periods', 'Tied', 'Unresolved', 'ABS-EE recoveredAmount sum (USD)', 'Certificate aggregate proceeds (USD)', 'Signed residual (USD)', 'Recovery bridge checks passed', 'Net-loss bridge checks passed'];
summary.getRange('A10:I10').values = [dealHeaders];
summary.getRange('A10:I10').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF', size: 10 }, wrapText: true, verticalAlignment: 'center', rowHeight: 42 };
summary.getRange('A11:A12').values = [['2022-B'], ['2024-B']];
summary.getRange('B11:I12').formulas = [11, 12].map(row => [
  `=COUNTIF('Period ledger'!$B$2:$B$81,A${row})`,
  `=COUNTIFS('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$W$2:$W$81,"TIED")`,
  `=COUNTIFS('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$W$2:$W$81,"UNRESOLVED")`,
  `=SUMIF('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$K$2:$K$81)`,
  `=SUMIF('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$N$2:$N$81)`,
  `=SUMIF('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$V$2:$V$81)`,
  `=COUNTIFS('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$T$2:$T$81,"PASS")`,
  `=COUNTIFS('Period ledger'!$B$2:$B$81,A${row},'Period ledger'!$U$2:$U$81,"PASS")`,
]);
summary.getRange('A13').values = [['Total']];
summary.getRange('B13:I13').formulas = [['=SUM(B11:B12)', '=SUM(C11:C12)', '=SUM(D11:D12)', '=SUM(E11:E12)', '=SUM(F11:F12)', '=SUM(G11:G12)', '=SUM(H11:H12)', '=SUM(I11:I12)']];
summary.getRange('A13:I13').format = { fill: PALE, font: { bold: true, color: NAVY } };
summary.getRange('A15:I18').merge();
summary.getRange('A15').values = [[
  'Interpretation: ABS-EE recoveredAmount is compared with the certificate aggregate net liquidation proceeds. Three periods tie exactly; the remaining 77 retain positive residuals totaling USD 3,823,205.14. The cause is not established. This difference is not LGD, loss, forecast, or an adjustment to be forced to zero.'
]];
summary.getRange('A15:I18').format = { fill: '#FFF4DF', font: { color: '#664D03' }, wrapText: true, verticalAlignment: 'top' };
summary.getRange('A20:I22').merge();
summary.getRange('A20').values = [[
  'Period caveat: the first reporting windows for both trusts cover March 1 through April 30 (61 calendar days). A report month label is not proof of a one-calendar-month collection window. See exact start/end dates on Period ledger.'
]];
summary.getRange('A20:I22').format = { fill: PALE, font: { color: NAVY }, wrapText: true, verticalAlignment: 'top' };
summary.getRange('A:A').format.columnWidth = 30;
summary.getRange('B:D').format.columnWidth = 14;
summary.getRange('E:G').format.columnWidth = 27;
summary.getRange('H:I').format.columnWidth = 22;
summary.getRange('B7').format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
summary.getRange('E11:G13').format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
summary.getRange('A3:B7').format.rowHeight = 24;
summary.freezePanes.freezeRows(3);

const ledger = workbook.worksheets.add('Period ledger');
ledger.showGridLines = false;
ledger.getRangeByIndexes(0, 0, ledgerRows.length + 1, ledgerHeaders.length).values = [ledgerHeaders, ...ledgerRows];
const table = ledger.tables.add(`A1:Z${ledgerRows.length + 1}`, true, 'ToyotaRecoveryExceptions');
table.style = 'TableStyleMedium2';
table.showFilterButton = true;
ledger.getRange('A1:Z1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF', size: 10 }, wrapText: true, verticalAlignment: 'center', horizontalAlignment: 'center', rowHeight: 48 };
ledger.getRange(`A2:Z${ledgerRows.length + 1}`).format = { verticalAlignment: 'top', wrapText: true };
const widths = [34, 14, 14, 14, 18, 18, 13, 14, 23, 23, 22, 25, 28, 26, 19, 30, 23, 23, 23, 21, 18, 23, 18, 76, 80, 70];
widths.forEach((width, i) => ledger.getRange(`${columnName(i + 1)}:${columnName(i + 1)}`).format.columnWidth = width);
ledger.getRange(`G2:G${ledgerRows.length + 1}`).format.numberFormat = '0';
ledger.getRange(`K2:S${ledgerRows.length + 1}`).format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
ledger.getRange(`V2:V${ledgerRows.length + 1}`).format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
ledger.freezePanes.freezeRows(1);
ledger.freezePanes.freezeColumns(3);

const definitions = workbook.worksheets.add('Method & sources');
definitions.showGridLines = false;
const notes = [
  ['Topic', 'Definition / evidence'],
  ['Scope', 'Toyota Auto Receivables 2022-B (51 periods) and 2024-B (29 periods), 80 period rows total. Public output contains only monthly aggregates; no contract or asset identifiers.'],
  ['ABS-EE recoveredAmount', 'Monthly sum from the audited ABS-EE EX-102 source. EX-103 defines recoveredAmount as an amount recovered during the period on a defaulted receivable, including repossession proceeds. This measure is not assumed to be a one-to-one certificate row.'],
  ['Certificate aggregate proceeds', 'Negate the sum of the two signed certificate rows: Net Liquidation Proceeds Received During the Collection Period and Recoveries on Previously Liquidated Contracts. Exact identity is checked independently for each period.'],
  ['Certificate net credit losses', 'Gross principal of liquidated receivables + signed principal of previously charged-off repurchased contracts + both signed proceeds rows. Exact identity is checked independently for each period.'],
  ['Cross-source residual', 'ABS-EE recoveredAmount aggregate − certificate Aggregate Net Liquidation Proceeds. A zero is a tie; any nonzero amount stays in its source period and remains unresolved unless evidence establishes the cause.'],
  ['Observed result', '80/80 certificate identities pass; 3/80 ABS-EE-to-certificate recovery amounts tie; 77/80 remain unresolved. Aggregate residual is +USD 3,823,205.14.'],
  ['2022-B subtotal', '51 periods; 2 tied, 49 unresolved; ABS-EE USD 16,414,508.06; certificate USD 14,355,861.00; residual +USD 2,058,647.06.'],
  ['2024-B subtotal', '29 periods; 1 tied, 28 unresolved; ABS-EE USD 13,517,164.16; certificate USD 11,752,606.08; residual +USD 1,764,558.08.'],
  ['First-period duration', 'Both first reporting windows run March 1–April 30, 61 calendar days. Period start/end are carried explicitly; month label alone is insufficient for period alignment.'],
  ['Source: 2022-B initial certificate', 'SEC EX-99.1, collection period and component rows: https://www.sec.gov/Archives/edgar/data/1914281/000095013122002459/d346874dex991.htm'],
  ['Source: 2024-B certificate example', 'SEC EX-99.1 for 2024-B April 2025: https://www.sec.gov/Archives/edgar/data/2012786/000095013125002267/d923232dex991.htm'],
  ['Source: later 2024-B certificate', 'SEC EX-99.1, 2026 report: https://www.sec.gov/Archives/edgar/data/2012786/000119312526240854/d68275dex991.htm'],
  ['Audit lineage', 'The accompanying public CSV and receipt bind both audit outputs and source acquisition receipts by SHA-256. Regenerate with scripts/build_toyota_recovery_components_ledger.py using --workspace-root <private CreditAtlas workspace on D:>.'],
  ['Use limits', 'No residual cause is proven. Do not interpret the residual as LGD, net loss, fraud, data error, or forecast; do not double count repossession proceeds; do not fill missing values or force a tie. The two trusts share an issuer/servicer family and are not independent issuer validation.'],
];
definitions.getRangeByIndexes(0, 0, notes.length, 2).values = notes;
definitions.getRange('A1:B1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 28 };
definitions.getRange(`A2:B${notes.length}`).format = { verticalAlignment: 'top', wrapText: true };
definitions.getRange(`A2:A${notes.length}`).format = { fill: PALE, font: { bold: true, color: NAVY }, verticalAlignment: 'top', wrapText: true };
definitions.getRange('A:A').format.columnWidth = 34;
definitions.getRange('B:B').format.columnWidth = 118;
definitions.getRange(`A2:B${notes.length}`).format.rowHeight = 48;
definitions.getRange(`A2:B${notes.length}`).format.rowHeight = 62;
definitions.freezePanes.freezeRows(1);

await workbook.recalculate();
const metrics = summary.getRange('B4:B7').values.flat();
const checks = summary.getRange('B11:I13').values;
if (metrics[0] !== 80 || metrics[1] !== 3 || metrics[2] !== 77 || Math.abs(metrics[3] - 3823205.14) > 0.01) {
  throw new Error(`Summary formula check failed: ${JSON.stringify(metrics)}`);
}
if (checks[2][0] !== 80 || checks[2][1] !== 3 || checks[2][2] !== 77 || checks[2][6] !== 80 || checks[2][7] !== 80) {
  throw new Error(`Deal summary check failed: ${JSON.stringify(checks)}`);
}
await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range] of [['Summary', 'A1:I22'], ['Period ledger', 'A1:K9'], ['Method & sources', 'A1:B10']]) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: 'png' });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(' ', '-')}.png`), new Uint8Array(await preview.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(JSON.stringify({ status: 'PASS', rows: ledgerRows.length, formulas: metrics, dealChecks: checks, outputPath }, null, 2));

function columnName(index) {
  let result = '';
  while (index > 0) {
    const remainder = (index - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    index = Math.floor((index - 1) / 26);
  }
  return result;
}

function parseCsv(input) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (quoted) {
      if (char === '"' && input[i + 1] === '"') { field += '"'; i++; }
      else if (char === '"') quoted = false;
      else field += char;
    } else if (char === '"') quoted = true;
    else if (char === ',') { row.push(field); field = ''; }
    else if (char === '\n') { row.push(field.replace(/\r$/, '')); rows.push(row); row = []; field = ''; }
    else field += char;
  }
  if (field.length || row.length) { row.push(field.replace(/\r$/, '')); rows.push(row); }
  return rows;
}
