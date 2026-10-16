import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const [inputPath, outputPath, previewDir] = process.argv.slice(2);
if (!inputPath || !outputPath || !previewDir) {
  throw new Error('usage: node build_nissan_exception_ledger.mjs input.csv output.xlsx preview-dir');
}

const NAVY = '#17324D';
const BLUE = '#315E7D';
const PALE = '#E9F1F6';
const AMBER = '#FFF2D8';
const RED = '#FCE8E6';
const rows = parseCsv(await fs.readFile(inputPath, 'utf8'));
const headers = rows[0].map((value, i) => i === 0 ? value.replace(/^\uFEFF/, '') : value);
const rawRows = rows.slice(1).filter(row => row.length && row[0]);
const index = Object.fromEntries(headers.map((name, i) => [name, i]));
const field = (row, name) => row[index[name]] ?? '';
const column = (name) => columnName(index[name] + 1);
if (rawRows.length !== 23 || headers.length < 60) throw new Error('Expected the complete 23-period Nissan ledger');

const ledgerRows = rawRows.map(row => row.map((value, i) => typedValue(headers[i], value)));
const lastRow = ledgerRows.length + 1;
const monthRange = `'Period ledger'!$${column('report_month')}$2:$${column('report_month')}$${lastRow}`;
const summary = Workbook.create();
const overview = summary.worksheets.add('Summary');
overview.showGridLines = false;
overview.getRange('A1:D1').merge();
overview.getRange('A1').values = [['Nissan 2024-B · event, DPD & recovery reconciliation']];
overview.getRange('A1:D1').format = { fill: NAVY, font: { name: 'Aptos Display', size: 16, bold: true, color: '#FFFFFF' }, verticalAlignment: 'center', rowHeight: 40 };
overview.getRange('A2:D2').merge();
overview.getRange('A2').values = [['23 source periods · monthly aggregates · source signs retained · unresolved items stay visible']];
overview.getRange('A2:D2').format = { fill: PALE, font: { color: NAVY, size: 10 }, verticalAlignment: 'center', rowHeight: 24 };

const metrics = [
  ['Control', 'Recalculated result', 'Interpretation'],
  ['Reporting periods', null, 'Audited periods in the public aggregate ledger.'],
  ['Pool balance exact periods', null, 'ABS-EE ending pool balance equals certificate pool balance.'],
  ['Positive balance / contract count exact', null, 'Positive asset ending-balance count equals certificate contract count.'],
  ['Positive charge-off count exact', null, 'A separate event candidate; not a universal default-event definition.'],
  ['Positive charge-off amount exact', null, 'Amount comparison retains source signs and field meaning.'],
  ['Recovery exact periods', null, 'ABS-EE recoveredAmount equals certificate recoveries.'],
  ['Recovery exception periods', null, 'Non-zero ABS-EE minus certificate residuals remain unresolved.'],
  ['Recovery residual total (USD)', null, 'Signed aggregate residual across six exception periods. Not LGD or net loss.'],
  ['DPD literal exact fields', null, 'Literal source bucket checks across all four buckets.'],
  ['DPD shifted exact fields · diagnostic only', null, 'Candidate boundary performs worse on full panel; not adopted.'],
  ['July 2025 ABS-EE charge-off amount (USD)', null, '36 positive event rows; do not equate directly with certificate principal.'],
  ['July 2025 certificate gross defaulted principal · signed USD', null, 'Source-reported signed principal amount.'],
  ['June 2025 DPD literal exact fields', null, 'Monthly certificate comparison, 8 bucket count/balance checks.'],
  ['June 2025 shifted exact fields · diagnostic only', null, 'Matches this month only; rejected as a system-wide rule.'],
];
overview.getRange('A4:C18').values = metrics;
overview.getRange('A4:C4').format = { fill: BLUE, font: { bold: true, color: '#FFFFFF' }, wrapText: true, verticalAlignment: 'center', rowHeight: 32 };
const formulas = [
  `=COUNTA('Period ledger'!$${column('report_month')}$2:$${column('report_month')}$${lastRow})`,
  countTrueFormula('pool_balance_tie'),
  countTrueFormula('positive_balance_count_tie'),
  countTrueFormula('chargeoff_count_tie'),
  countTrueFormula('chargeoff_amount_tie'),
  countTrueFormula('recovery_current_amount_tie'),
  `=COUNTIF('Period ledger'!$${column('asset_minus_certificate_recovery_usd')}$2:$${column('asset_minus_certificate_recovery_usd')}$${lastRow},"<>0")`,
  `=SUM('Period ledger'!$${column('asset_minus_certificate_recovery_usd')}$2:$${column('asset_minus_certificate_recovery_usd')}$${lastRow})`,
  `=SUM('Period ledger'!$${column('dpd_literal_exact_fields')}$2:$${column('dpd_literal_exact_fields')}$${lastRow})`,
  `=SUM('Period ledger'!$${column('dpd_shifted_exact_fields_diagnostic_only')}$2:$${column('dpd_shifted_exact_fields_diagnostic_only')}$${lastRow})`,
  `=SUMIF(${monthRange},"2025-07",'Period ledger'!$${column('asset_chargeoff_amount_positive_usd')}$2:$${column('asset_chargeoff_amount_positive_usd')}$${lastRow})`,
  `=SUMIF(${monthRange},"2025-07",'Period ledger'!$${column('certificate_gross_defaulted_principal_signed_usd')}$2:$${column('certificate_gross_defaulted_principal_signed_usd')}$${lastRow})`,
  `=SUMIF(${monthRange},"2025-06",'Period ledger'!$${column('dpd_literal_exact_fields')}$2:$${column('dpd_literal_exact_fields')}$${lastRow})`,
  `=SUMIF(${monthRange},"2025-06",'Period ledger'!$${column('dpd_shifted_exact_fields_diagnostic_only')}$2:$${column('dpd_shifted_exact_fields_diagnostic_only')}$${lastRow})`,
];
overview.getRange('B5:B18').formulas = formulas.map(formula => [formula]);
overview.getRange('A5:C18').format = { verticalAlignment: 'center', wrapText: true, rowHeight: 33 };
overview.getRange('A5:A18').format = { fill: PALE, font: { bold: true, color: NAVY }, wrapText: true, verticalAlignment: 'center' };
overview.getRange('B5:B18').format = { font: { bold: true, color: NAVY, size: 11 }, horizontalAlignment: 'right', verticalAlignment: 'center' };
overview.getRange('B12').format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
overview.getRange('B15:B16').format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
overview.getRange('A20:D23').merge();
overview.getRange('A20').values = [[
  'Decision: do not force one event rule to fit every month. July 2025 charge-off, June 2025 DPD boundary and six recovery residuals remain exceptions for further source/servicer investigation. Candidate shifted DPD is diagnostic only; it reduces full-panel exact checks from 178/184 to 86/184.'
]];
overview.getRange('A20:D23').format = { fill: AMBER, font: { color: '#664D03' }, wrapText: true, verticalAlignment: 'top' };
overview.getRange('A25:D27').merge();
overview.getRange('A25').values = [['Use limits: the ledger is source/parser reconciliation, not external model validation, event-label sign-off, LGD, PD, loss forecast, fraud indicator, or accounting estimate. No raw asset identifiers are published.']];
overview.getRange('A25:D27').format = { fill: RED, font: { color: '#7A271A' }, wrapText: true, verticalAlignment: 'top' };
overview.getRange('A:A').format.columnWidth = 42;
overview.getRange('B:B').format.columnWidth = 23;
overview.getRange('C:C').format.columnWidth = 72;
overview.getRange('D:D').format.columnWidth = 18;
overview.freezePanes.freezeRows(4);

const ledger = summary.worksheets.add('Period ledger');
ledger.showGridLines = false;
ledger.getRangeByIndexes(0, 0, ledgerRows.length + 1, headers.length).values = [headers, ...ledgerRows];
const lastColumn = columnName(headers.length);
const table = ledger.tables.add(`A1:${lastColumn}${lastRow}`, true, 'Nissan2024BPeriodLedger');
table.style = 'TableStyleMedium2';
table.showFilterButton = true;
ledger.getRange(`A1:${lastColumn}1`).format = { fill: NAVY, font: { bold: true, color: '#FFFFFF', size: 9 }, wrapText: true, verticalAlignment: 'center', horizontalAlignment: 'center', rowHeight: 54 };
ledger.getRange(`A2:${lastColumn}${lastRow}`).format = { verticalAlignment: 'top', wrapText: true, rowHeight: 24 };
headers.forEach((header, i) => {
  const col = columnName(i + 1);
  let width = 16;
  if (header.includes('_url')) width = 74;
  else if (header.includes('accession')) width = 25;
  else if (header.includes('usd')) width = 21;
  else if (header.includes('tie') || header.includes('exact') || header.includes('present')) width = 16;
  else if (header.includes('date') || header.includes('period')) width = 17;
  ledger.getRange(`${col}:${col}`).format.columnWidth = width;
});
for (const name of headers.filter(value => value.endsWith('_usd'))) {
  const col = column(name);
  ledger.getRange(`${col}2:${col}${lastRow}`).format.numberFormat = '$#,##0.00;[Red]($#,##0.00);–';
}
for (const name of headers.filter(value => value.endsWith('_count') || value.endsWith('_count_delta') || value.includes('exact_fields') || value.includes('calendar_days'))) {
  const col = column(name);
  ledger.getRange(`${col}2:${col}${lastRow}`).format.numberFormat = '#,##0;[Red](#,##0);–';
}
ledger.freezePanes.freezeRows(1);
ledger.freezePanes.freezeColumns(2);

const method = summary.worksheets.add('Method & sources');
method.showGridLines = false;
const notes = [
  ['Topic', 'Definition / evidence'],
  ['Scope', 'Nissan Auto Receivables 2024-B Owner Trust; 23 monthly periods (2024-10 to 2026-08); 1,154,259 asset-month rows and 63,688 asset keys in the private audited panel. Public workbook includes monthly aggregates only.'],
  ['Source grain', 'One row per report date. Collection-period start/end, filing accessions, public URLs, source values, exactness flags and aggregate deltas remain visible on Period ledger.'],
  ['Pool tie', 'Ending pool balance and positive ending-balance count are compared independently with the certificate pool balance and contract count.'],
  ['Charge-off candidates', 'Positive charge-off rows, first zeroBalanceCode=4 rows and positive first-code-4 amount are separate candidate definitions. No single candidate matches all periods.'],
  ['July 2025 event', 'ABS-EE: 36 positive charge-off rows / USD 655,185.56; first code 4: 33 / USD 577,420.34; three repeated rows: USD 77,765.22. Certificate: one defaulted receivable and signed gross principal −USD 59,000.49. No transaction-level crosswalk proves these are the same measure.'],
  ['DPD literal', 'Monthly ABS-EE bucket counts and balances are compared literally with four certificate buckets. June 2025: 2/8 exact; total count and balance residuals are zero after offsetting bucket differences.'],
  ['DPD shifted diagnostic', 'Moving each candidate boundary one day earlier yields 8/8 June checks but only 86/184 full-panel exact fields vs 178/184 literal. Kept as a diagnostic; not adopted as a rule.'],
  ['Recovery residual', 'ABS-EE recoveredAmount minus certificate Recoveries of Defaulted Receivables. Six periods differ by +USD 8,859.23 total. It is not a recovery-rate estimate, LGD, loss or forecast.'],
  ['Nissan EX-103', 'Recovered amount applies to receivables previously charged off. Repossessed sale proceeds are in repossessedProceedsAmount if sold in the repossession period; sale proceeds in a later period are included in recoveredAmount. Keep fields separate to avoid double count.'],
  ['Amendment check', 'SEC submissions census checked 2026-10-17: no ABS-EE/A or 10-D/A for 2025-07-31 appeared in the 57 recent rows; this does not rule out servicer-side changes not filed as an amendment.'],
  ['Sources: SEC July 2025 certificate', 'https://www.sec.gov/Archives/edgar/data/2035264/000119312525187356/d930039dex991.htm'],
  ['Sources: SEC July 2025 ABS-EE', 'https://www.sec.gov/Archives/edgar/data/2035264/000095013125003344/0000950131-25-003344-index.html'],
  ['Source: SEC June 2025 certificate', 'https://www.sec.gov/Archives/edgar/data/2035264/000119312525166251/d44534dex991.htm'],
  ['Source: issuer field definitions, EX-103', 'https://www.sec.gov/Archives/edgar/data/1129068/000119312526231956/0001193125-26-231956-index.htm'],
  ['Source: SEC submissions API', 'https://data.sec.gov/submissions/CIK0002035264.json'],
  ['Calculation precision', 'Public CSV builder uses Python Decimal for amount deltas and checks private audit receipt hashes/status. Workbook formulas independently recalculate counts, deltas and summary totals from the public CSV; source amounts keep reported signs.'],
  ['Missingness and estimation', 'No missing-to-zero fill, forecast, interpolation or imputation is used. Blank focus-audit fields mean not in the four-month event detail, not a measured zero.'],
  ['Release boundary', 'No asset identifiers, borrower rows, credentials or private audit payloads are published. CSV and receipt contain aggregate values, source URLs and SHA-256 lineage.'],
  ['Primary research note', 'docs/NISSAN_2024B_EXCEPTION_LEDGER_VI.md'],
];
method.getRangeByIndexes(0, 0, notes.length, 2).values = notes;
method.getRange('A1:B1').format = { fill: NAVY, font: { bold: true, color: '#FFFFFF' }, wrapText: true, rowHeight: 30 };
method.tables.add(`A1:B${notes.length}`, true, 'NissanMethodSources');
method.getRange(`A2:B${notes.length}`).format = { verticalAlignment: 'top', wrapText: true, rowHeight: 48 };
method.getRange(`A2:A${notes.length}`).format = { fill: PALE, font: { bold: true, color: NAVY }, verticalAlignment: 'top', wrapText: true };
method.getRange('A:A').format.columnWidth = 35;
method.getRange('B:B').format.columnWidth = 118;
method.freezePanes.freezeRows(1);

await summary.recalculate();
const calculated = overview.getRange('B5:B18').values.flat();
const expected = [23, 23, 23, 20, 21, 17, 6, 8859.23, 178, 86, 655185.56, -59000.49, 2, 8];
for (let i = 0; i < expected.length; i++) {
  if (typeof calculated[i] === 'number' ? Math.abs(calculated[i] - expected[i]) > 0.01 : calculated[i] !== expected[i]) {
    throw new Error(`Summary check failed at row ${i + 5}: ${JSON.stringify(calculated[i])} != ${expected[i]}`);
  }
}

await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range, filename] of [
  ['Summary', 'A1:D27', 'Summary.png'],
  ['Period ledger', 'A1:L9', 'Period-ledger.png'],
  ['Method & sources', 'A1:B11', 'Method-sources.png'],
]) {
  const image = await summary.render({ sheetName, range, scale: 1, format: 'png' });
  await fs.writeFile(path.join(previewDir, filename), new Uint8Array(await image.arrayBuffer()));
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const file = await SpreadsheetFile.exportXlsx(summary);
await file.save(outputPath);
console.log(JSON.stringify({ status: 'PASS', periods: ledgerRows.length, columns: headers.length, summaryChecks: calculated, outputPath }, null, 2));

function countTrueFormula(name) {
  const col = column(name);
  return `=COUNTIF('Period ledger'!$${col}$2:$${col}$${lastRow},"TIED")`;
}

function typedValue(header, value) {
  if (value === '') return null;
  if ((header.endsWith('_tie') || header.endsWith('_exact')) && value === 'True') return 'TIED';
  if ((header.endsWith('_tie') || header.endsWith('_exact')) && value === 'False') return 'MISMATCH';
  if (value === 'True') return true;
  if (value === 'False') return false;
  if (header === 'report_date' || header.startsWith('collection_period_') || header === 'report_month') return value;
  if (header.endsWith('_usd') || header.endsWith('_pct') || header.includes('count') || header.endsWith('_delta') || header.includes('exact_fields') || header.endsWith('_days') || header.includes('row_months')) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : value;
  }
  return value;
}

function columnName(n) {
  let result = '';
  while (n > 0) {
    const remainder = (n - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    n = Math.floor((n - 1) / 26);
  }
  return result;
}

function parseCsv(text) {
  const result = [];
  let row = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (char === '"') quoted = false;
      else cell += char;
    } else if (char === '"') quoted = true;
    else if (char === ',') { row.push(cell); cell = ''; }
    else if (char === '\n') { row.push(cell.replace(/\r$/, '')); result.push(row); row = []; cell = ''; }
    else cell += char;
  }
  if (cell.length || row.length) { row.push(cell.replace(/\r$/, '')); result.push(row); }
  return result;
}
