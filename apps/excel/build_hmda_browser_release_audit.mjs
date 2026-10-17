import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const [jsonArg, outputArg, dimensionAuditArg] = process.argv.slice(2);
if (!jsonArg || !outputArg) throw new Error('usage: build_hmda_browser_release_audit.mjs <audit.json> <output.xlsx>');
const input = path.resolve(jsonArg);
const output = path.resolve(outputArg);
const audit = JSON.parse(await fs.readFile(input, 'utf8'));
if (audit.evidence_type !== 'hmda_browser_selected_release_action_counts_2018_2025'
    || audit.status !== 'PASS' || audit.years?.length !== 8) {
  throw new Error('Expected the verified eight-year HMDA Browser action-count audit');
}
const dimensionAudit = dimensionAuditArg ? JSON.parse(await fs.readFile(path.resolve(dimensionAuditArg), 'utf8')) : null;
if (dimensionAudit && (dimensionAudit.evidence_type !== 'hmda_browser_2025_snapshot_dimension_api_parity'
    || dimensionAudit.status !== 'PASS' || dimensionAudit.results?.length !== 5
    || dimensionAudit.results.some((item) => !item.all_action_counts_match
      || !item.official_api_parameter_echo_matches || item.official_api_http_status !== 200
      || !(item.app_marginal_summary_match === true || item.app_intersection_summary_match === true)))) {
  throw new Error('Expected five verified filtered-API dimensions for the 2025 Snapshot');
}

const wb = Workbook.create();
const browser = wb.worksheets.add('Browser selected');
const archives = wb.worksheets.add('App One-Year');
const deltas = wb.worksheets.add('Vintage deltas');
const dimensions = dimensionAudit ? wb.worksheets.add('Dimension parity') : null;
const lineage = wb.worksheets.add('Lineage');
const method = wb.worksheets.add('Method & sources');

const navy = '#17365D';
const blue = '#D9EAF7';
const light = '#F3F6FA';
const teal = '#DDEBF7';
const grey = '#5B6573';
const actions = ['1', '2', '3', '4', '5', '6', '7', '8'];
const actionLabels = {
  '1': 'Loan originated',
  '2': 'Approved, not accepted',
  '3': 'Application denied',
  '4': 'Withdrawn',
  '5': 'Closed for incompleteness',
  '6': 'Purchased loan',
  '7': 'Preapproval denied',
  '8': 'Preapproval approved, not accepted',
};

function styleBase(sheet, lastColumn, lastRow = 30) {
  sheet.showGridLines = false;
  sheet.getRange(`A1:${lastColumn}${lastRow}`).format.font = { name: 'Arial', size: 10, color: '#1F2937' };
  sheet.getRange(`A1:${lastColumn}${lastRow}`).format.verticalAlignment = 'center';
}
function title(sheet, range, text) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(':')[0]).values = [[text]];
  sheet.getRange(range).format = {
    fill: navy,
    font: { name: 'Arial', size: 15, bold: true, color: '#FFFFFF' },
    rowHeight: 34,
    verticalAlignment: 'center',
  };
}
function subtitle(sheet, range, text, height = 36) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(':')[0]).values = [[text]];
  sheet.getRange(range).format = {
    fill: light,
    font: { name: 'Arial', size: 10, italic: true, color: grey },
    wrapText: true,
    rowHeight: height,
    verticalAlignment: 'center',
  };
}
function header(sheet, range) {
  sheet.getRange(range).format = {
    fill: navy,
    font: { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' },
    wrapText: true,
    horizontalAlignment: 'center',
    verticalAlignment: 'center',
    rowHeight: 38,
  };
}
function columnWidths(sheet, widths) {
  for (const [column, width] of Object.entries(widths)) {
    sheet.getRange(`${column}:${column}`).format.columnWidth = width;
  }
}

const allYears = audit.years;
const appYears = allYears.filter((item) => item.activity_year >= 2019 && item.activity_year <= 2024);
const crossVintageYears = allYears.filter((item) => !item.local_archive_comparison.same_vintage_as_browser);
if (crossVintageYears.map((x) => x.activity_year).join(',') !== '2019,2020,2021,2022') {
  throw new Error('Expected 2019–2022 to be the only cross-vintage comparisons');
}

// Official Data Browser selected releases: source action counts are values; summary KPIs are formulas.
styleBase(browser, 'O', 20);
columnWidths(browser, { A: 11, B: 17, C: 15, D: 14, E: 14, F: 14, G: 14, H: 14, I: 14, J: 14, K: 14, L: 17, M: 17, N: 17, O: 17 });
title(browser, 'A1:O1', 'CreditAtlas · HMDA Browser-selected releases 2018–2025');
subtitle(browser, 'A2:O2', 'Official nationwide API action counts by activity year. Denied share is an application-disposition measure, not repayment/default PD. One row per annual release; do not sum years as unique applications.', 42);
browser.getRange('A4:O4').values = [[
  'Activity year', 'Browser release', 'Freeze date', 'Action 1', 'Action 2', 'Action 3', 'Action 4', 'Action 5', 'Action 6', 'Action 7', 'Action 8',
  'Total actions 1–8', 'Decisions 1+2+3', 'Denied · 3', 'Denied share',
]];
header(browser, 'A4:O4');
const browserRows = allYears.map((item) => [
  item.activity_year, item.browser_selected_release, item.browser_freeze_date,
  ...actions.map((code) => item.browser_actions_1_to_8[code]), null, null, null, null,
]);
browser.getRange('A5:O12').values = browserRows;
browser.getRange('L5:O12').formulas = allYears.map((_, index) => {
  const r = index + 5;
  return [`=SUM(D${r}:K${r})`, `=SUM(D${r}:F${r})`, `=F${r}`, `=IFERROR(N${r}/M${r},0)`];
});
browser.getRange('A5:O12').format.rowHeight = 27;
browser.getRange('D5:N12').format.numberFormat = '#,##0;(#,##0);-';
browser.getRange('O5:O12').format.numberFormat = '0.0000%';
browser.tables.add('A4:O12', true, 'HmdaBrowserSelectedReleaseCounts');
browser.freezePanes.freezeRows(4);
subtitle(browser, 'A15:O16', 'Observed time series across years still mixes Three-Year, One-Year and Snapshot release windows, with changing coverage and product/geography mix. Use release labels and freeze dates in every comparison; do not treat rate movement as causal or as borrower performance.', 52);

// Receipt-bound One-Year archives loaded by the application, including years whose Browser vintage is Three-Year.
styleBase(archives, 'O', 20);
columnWidths(archives, { A: 11, B: 17, C: 15, D: 14, E: 14, F: 14, G: 14, H: 14, I: 14, J: 14, K: 14, L: 17, M: 17, N: 17, O: 17 });
title(archives, 'A1:O1', 'CreditAtlas · Stored One-Year archives 2019–2024');
subtitle(archives, 'A2:O2', 'Counts are read from verified private acquisition receipt profiles. Raw LAR files remain on D:. 2019 has the publisher caveat that its One-Year vintage includes more than 12 months of updates.', 42);
archives.getRange('A4:O4').values = [[
  'Activity year', 'App archive', 'Freeze date', 'Action 1', 'Action 2', 'Action 3', 'Action 4', 'Action 5', 'Action 6', 'Action 7', 'Action 8',
  'Total actions 1–8', 'Decisions 1+2+3', 'Denied · 3', 'Denied share',
]];
header(archives, 'A4:O4');
const archiveRows = appYears.map((item) => {
  const local = item.local_archive_comparison;
  return [
    item.activity_year, local.local_release_vintage, local.local_freeze_date,
    ...actions.map((code) => local.local_actions_1_to_8[code]), null, null, null, null,
  ];
});
archives.getRange('A5:O10').values = archiveRows;
archives.getRange('L5:O10').formulas = appYears.map((_, index) => {
  const r = index + 5;
  return [`=SUM(D${r}:K${r})`, `=SUM(D${r}:F${r})`, `=F${r}`, `=IFERROR(N${r}/M${r},0)`];
});
archives.getRange('A5:O10').format.rowHeight = 27;
archives.getRange('D5:N10').format.numberFormat = '#,##0;(#,##0);-';
archives.getRange('O5:O10').format.numberFormat = '0.0000%';
archives.tables.add('A4:O10', true, 'HmdaAppOneYearArchiveCounts');
archives.freezePanes.freezeRows(4);
subtitle(archives, 'A13:O14', '2019–2022 app archives are intentionally not substituted for the current Browser-selected Three-Year releases. 2023–2024 One-Year archives match the Browser product/freeze and their action profiles reconcile exactly.', 48);

// Formula-linked vintage deltas: Browser-selected Three-Year minus app One-Year archive.
styleBase(deltas, 'O', 24);
columnWidths(deltas, { A: 11, B: 18, C: 18, D: 13, E: 13, F: 13, G: 13, H: 13, I: 13, J: 13, K: 13, L: 16, M: 16, N: 16, O: 17 });
title(deltas, 'A1:O1', 'Vintage sensitivity · Browser Three-Year minus stored One-Year');
subtitle(deltas, 'A2:O2', '2019–2022 only. Positive/negative deltas show changes between aggregate release-state profiles; they are not matched applications or a count of new unique rows.', 38);
deltas.getRange('A4:O4').values = [[
  'Year', 'Browser release', 'App archive', 'Δ action 1', 'Δ action 2', 'Δ action 3', 'Δ action 4', 'Δ action 5', 'Δ action 6', 'Δ action 7', 'Δ action 8',
  'Δ total actions', 'Δ decisions 1–3', 'Δ denied · 3', 'Δ denied share · pp',
]];
header(deltas, 'A4:O4');
const deltaValues = crossVintageYears.map((item) => [item.activity_year, 'Three-Year', 'One-Year', ...Array(12).fill(null)]);
deltas.getRange('A5:O8').values = deltaValues;
const deltaFormulas = crossVintageYears.map((item, index) => {
  const row = index + 5;
  const browserRow = item.activity_year - 2013; // 2018 is row 5; 2019 is row 6.
  const archiveRow = item.activity_year - 2014; // 2019 is row 5.
  const actionDeltaFormulas = actions.map((_, actionIndex) => {
    const col = String.fromCharCode('D'.charCodeAt(0) + actionIndex);
    return `='Browser selected'!${col}${browserRow}-'App One-Year'!${col}${archiveRow}`;
  });
  const totalCol = 'L';
  const decisionsCol = 'M';
  const deniedCol = 'N';
  const rateCol = 'O';
  return [
    ...actionDeltaFormulas,
    `=SUM(D${row}:K${row})`,
    `=SUM(D${row}:F${row})`,
    `=F${row}`,
    `=('Browser selected'!${rateCol}${browserRow}-'App One-Year'!${rateCol}${archiveRow})*100`,
  ];
});
deltas.getRange('D5:O8').formulas = deltaFormulas;
deltas.getRange('A5:O8').format.rowHeight = 29;
deltas.getRange('D5:N8').format.numberFormat = '#,##0;(#,##0);-';
deltas.getRange('O5:O8').format.numberFormat = '0.00000000;(0.00000000);-';
deltas.tables.add('A4:O8', true, 'HmdaCrossVintageDeltaSummary');
deltas.freezePanes.freezeRows(4);
subtitle(deltas, 'A11:O12', 'Action 4–8 deltas matter: for example, 2020 has fewer action-4 rows but more action-2 rows in the Browser Three-Year vintage. The total delta is not “late rows added”; resubmissions/reclassifications can move action counts in both directions.', 48);

if (dimensionAudit && dimensions) {
  const scopeLabels = {
    state_ca: ['California state', 'state=CA'],
    county_los_angeles: ['Los Angeles County', 'county=06037'],
    state_ca_conventional: ['California × conventional', 'state=CA; loan_type=1'],
    largest_reporter_lei: ['Largest reporting institution (LEI)', 'one LEI selected by largest local 2025 action-1–8 count'],
    nationwide_conventional: ['Nationwide conventional loans', 'loan_type=1'],
  };
  styleBase(dimensions, 'O', 20);
  columnWidths(dimensions, { A: 28, B: 52, C: 15, D: 15, E: 15, F: 15, G: 15, H: 15, I: 17, J: 17, K: 17, L: 18, M: 14, N: 17, O: 14 });
  title(dimensions, 'A1:O1', 'Filtered dimension parity · official 2025 Snapshot API vs local source');
  subtitle(dimensions, 'A2:O2', 'Five spot-check scopes compared on action codes 1–8. Four app marginal buckets and the California × conventional intersection match the receipt-verified app report. Share columns are Excel formulas.', 54);
  dimensions.getRange('A4:O4').values = [[
    'Scope', 'Official filter', 'API rows 1–8', 'Local rows 1–8', 'API decisions 1+2+3', 'Local decisions 1+2+3',
    'API denied · 3', 'Local denied · 3', 'API denied share', 'Local denied share', 'Δ share · pp',
    'Local raw match', 'API filter echo', 'App match', 'Check',
  ]];
  header(dimensions, 'A4:O4');
  const dimensionRows = dimensionAudit.results.map((item) => {
    const [label, filter] = scopeLabels[item.scope] ?? [item.scope, 'See private receipt'];
    const appMatch = item.app_intersection_summary_match ?? item.app_marginal_summary_match;
    return [label, filter, item.api_summary.action_1_to_8_records, item.local_snapshot_summary.action_1_to_8_records,
      item.api_summary.decision_denominator_1_2_3, item.local_snapshot_summary.decision_denominator_1_2_3,
      item.api_summary.denied_numerator_action_3, item.local_snapshot_summary.denied_numerator_action_3,
      null, null, null, item.all_action_counts_match ? 'PASS' : 'FAIL',
      item.official_api_parameter_echo_matches ? 'PASS' : 'FAIL',
      appMatch === null ? 'N/A' : appMatch ? 'PASS' : 'FAIL', null];
  });
  const dimensionEndRow = 4 + dimensionAudit.results.length;
  dimensions.getRange(`A5:O${dimensionEndRow}`).values = dimensionRows;
  dimensions.getRange(`I5:K${dimensionEndRow}`).formulas = dimensionAudit.results.map((_, index) => {
    const row = index + 5;
    return [`=IFERROR(G${row}/E${row},0)`, `=IFERROR(H${row}/F${row},0)`, `=(I${row}-J${row})*100`];
  });
  dimensions.getRange(`O5:O${dimensionEndRow}`).formulas = dimensionAudit.results.map((_, index) => {
    const row = index + 5;
    return [`=IF(AND(C${row}=D${row},E${row}=F${row},G${row}=H${row},L${row}="PASS",M${row}="PASS",OR(N${row}="PASS",N${row}="N/A")),"PASS","CHECK")`];
  });
  dimensions.getRange(`A5:O${dimensionEndRow}`).format.rowHeight = 34;
  dimensions.getRange(`C5:H${dimensionEndRow}`).format.numberFormat = '#,##0;(#,##0);-';
  dimensions.getRange(`I5:J${dimensionEndRow}`).format.numberFormat = '0.0000%';
  dimensions.getRange(`K5:K${dimensionEndRow}`).format.numberFormat = '0.00000000;(0.00000000);-';
  dimensions.tables.add(`A4:O${dimensionEndRow}`, true, 'HmdaFilteredDimensionApiParity');
  dimensions.freezePanes.freezeRows(4);
  subtitle(dimensions, 'A11:O12', 'Public sheet intentionally omits raw LAR rows, local paths, exact LEI and full action-level query responses. Exact query, LEI, action profiles, API payloads and receipt hashes are retained in the private D: receipt; only aggregate summaries are published.', 52);
}

// Hashes and source IDs, without private paths or any loan-level data.
styleBase(lineage, 'G', 18);
columnWidths(lineage, { A: 12, B: 18, C: 16, D: 22, E: 48, F: 66, G: 23 });
title(lineage, 'A1:G1', 'Release/API lineage and receipt references');
subtitle(lineage, 'A2:G2', 'Public release/source identifiers and SHA-256 hashes only. Private receipts, raw files and local paths remain on D:.', 34);
lineage.getRange('A4:G4').values = [[
  'Activity year', 'Browser product', 'Freeze', 'App source ID', 'Local source receipt SHA-256', 'Official API request', 'API response SHA-256',
]];
header(lineage, 'A4:G4');
const lineageRows = allYears.map((item) => [
  item.activity_year,
  item.browser_selected_release,
  item.browser_freeze_date,
  item.local_archive_comparison.local_source_id,
  item.local_archive_comparison.local_source_receipt_sha256,
  item.official_api_url,
  item.api_response_sha256,
]);
lineage.getRange('A5:G12').values = lineageRows;
lineage.getRange('A5:G12').format.wrapText = true;
lineage.getRange('A5:G12').format.rowHeight = 50;
lineage.tables.add('A4:G12', true, 'HmdaReleaseApiLineage');
lineage.freezePanes.freezeRows(4);

styleBase(method, 'D', 28);
columnWidths(method, { A: 30, B: 72, C: 64, D: 24 });
title(method, 'A1:D1', 'Method, definitions and source limits');
method.getRange('A3:D3').values = [['Item', 'Definition / value', 'Official source / evidence', 'Status']];
header(method, 'A3:D3');
const methodRows = [
  ['Release selection', 'Use the latest available static release selected by the FFIEC/CFPB Data Browser for each activity year.', audit.source_release_mapping, 'Official FAQ'],
  ['API function', 'Nationwide aggregations API powers the Data Browser; one request per year, action filter 1–8.', audit.source_documentation, 'Official API docs'],
  ['Decision denominator', 'Count(action_taken in 1,2,3): originated + approved/not accepted + denied.', 'CreditAtlas-derived descriptive denominator', 'Not PD/default'],
  ['Denied numerator', 'Count(action_taken == 3).', 'Official public action code 3', 'Not default'],
  ['Denied share', 'Denied action 3 / actions 1+2+3; Excel formula shown in Browser selected and App One-Year sheets.', 'Recomputed from official action counts', 'Descriptive'],
  ['2018 source boundary', '1,961 local raw rows have action=-1 and are quarantined; API/report profile covers actions 1–8.', '2018 private acquisition and audit receipt', 'Excluded from KPI'],
  ['2019–2022 vintage comparison', 'App archives are One-Year; the current Browser selects Three-Year. Compare totals by action only; no row-level match.', 'See Vintage deltas and JSON audit', 'Cross-vintage diagnostic'],
  ['2023–2025 matching releases', '2023/2024 One-Year and 2025 Snapshot app receipts match all Browser-selected action counts.', 'Private receipts crosswalked in JSON output', 'Exact action-count match'],
  ['2025 filtered API dimension check', dimensionAudit ? `${dimensionAudit.results.length} Snapshot scopes reconciled; four app marginal buckets and the California × conventional intersection match.` : 'No filtered dimension audit supplied to this workbook build.', 'See Dimension parity and sanitized API audit JSON', dimensionAudit?.status ?? 'Not included'],
  ['2025 Dynamic', 'Dynamic is a separate weekly release state; not the Browser-selected static Snapshot.', '2025 Snapshot/Dynamic comparison report', 'Separate source ID'],
  ['Release-state limits', 'Release differences can include late submissions/resubmissions and reclassifications; action deltas can have either sign.', 'No row matching performed', 'Do not call new unique rows'],
  ['Trend limits', 'Across-year levels also reflect coverage, reporting thresholds, product mix and geography mix.', 'Additional harmonization needed', 'Not causal'],
  ['Data handling', 'This workbook has action-count aggregates, no raw LAR records. Raw CSV/ZIP and full source receipts remain private.', 'Project rights review', 'No row-level data'],
  ['Rights status', 'Reviewed pages support analysis/privacy-modified use but did not specify raw rehosting/redistribution terms.', 'HMDA rights review', 'Raw remains private'],
  ['Forecast/model', 'No forecast, imputation, PD, default or risk model was created by this audit.', 'Audit scope', 'None'],
];
method.getRange(`A4:D${3 + methodRows.length}`).values = methodRows;
method.getRange(`A4:D${3 + methodRows.length}`).format.wrapText = true;
method.getRange(`A4:D${3 + methodRows.length}`).format.rowHeight = 52;
method.tables.add(`A3:D${3 + methodRows.length}`, true, 'HmdaAuditMethodNotes');
method.freezePanes.freezeRows(3);

wb.recalculate();
for (const [sheet, range, expectedRows] of [
  ['Browser selected', 'L5:O12', allYears],
  ['App One-Year', 'L5:O10', appYears],
]) {
  const values = wb.worksheets.getItem(sheet).getRange(range).values;
  if (values.length !== expectedRows.length) throw new Error(`${sheet}: unexpected output row count`);
  expectedRows.forEach((item, i) => {
    const summary = sheet === 'Browser selected'
      ? item.browser_summary
      : item.local_archive_comparison.local_summary;
    const row = values[i];
    if (Number(row[0]) !== summary.action_1_to_8_records
        || Number(row[1]) !== summary.decision_denominator_actions_1_2_3
        || Number(row[2]) !== summary.denied_numerator_action_3
        || Math.abs(Number(row[3]) - Number(summary.descriptive_denied_share)) > 1e-12) {
      throw new Error(`${sheet}: calculated summary does not match audit JSON for ${item.activity_year}`);
    }
  });
}
if (dimensionAudit && dimensions) {
  const dimensionEndRow = 4 + dimensionAudit.results.length;
  const values = dimensions.getRange(`C5:O${dimensionEndRow}`).values;
  dimensionAudit.results.forEach((item, i) => {
    const row = values[i];
    if (Number(row[0]) !== item.api_summary.action_1_to_8_records
        || Number(row[1]) !== item.local_snapshot_summary.action_1_to_8_records
        || Number(row[2]) !== item.api_summary.decision_denominator_1_2_3
        || Number(row[3]) !== item.local_snapshot_summary.decision_denominator_1_2_3
        || Number(row[4]) !== item.api_summary.denied_numerator_action_3
        || Number(row[5]) !== item.local_snapshot_summary.denied_numerator_action_3
        || Math.abs(Number(row[6]) - Number(item.api_summary.descriptive_denied_share)) > 1e-12
        || Math.abs(Number(row[7]) - Number(item.local_snapshot_summary.descriptive_denied_share)) > 1e-12
        || Math.abs(Number(row[8]) - Number(item.descriptive_denied_share_delta)) > 1e-8
        || row[9] !== 'PASS' || row[10] !== 'PASS'
        || row[11] !== ((item.app_intersection_summary_match ?? item.app_marginal_summary_match) === null
          ? 'N/A' : (item.app_intersection_summary_match ?? item.app_marginal_summary_match) ? 'PASS' : 'FAIL')
        || row[12] !== 'PASS') {
      throw new Error(`Filtered dimension parity formula/source mismatch for ${item.scope}: ${JSON.stringify(row)}`);
    }
  });
}
const deltaValuesCalculated = deltas.getRange('D5:O8').values;
crossVintageYears.forEach((item, i) => {
  const expected = item.local_archive_comparison.browser_minus_local_archive;
  const row = deltaValuesCalculated[i];
  const actualActions = row.slice(0, 8).map(Number);
  for (let j = 0; j < actions.length; j++) {
    if (actualActions[j] !== expected.actions_1_to_8[actions[j]]) {
      throw new Error(`Vintage delta mismatch for ${item.activity_year} action ${actions[j]}`);
    }
  }
  if (Number(row[8]) !== expected.action_1_to_8_records
      || Number(row[9]) !== expected.decision_denominator_actions_1_2_3
      || Number(row[10]) !== expected.denied_numerator_action_3
      || Math.abs(Number(row[11]) - Number(expected.descriptive_denied_share_percentage_points)) > 1e-8) {
    throw new Error(`Vintage summary mismatch for ${item.activity_year}`);
  }
});

const errorScan = await wb.inspect({
  kind: 'match',
  searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',
  options: { useRegex: true, maxResults: 100 },
  maxChars: 3000,
});
if (!errorScan.ndjson.includes('matched 0 entries')) throw new Error(`Formula error scan failed: ${errorScan.ndjson}`);
const outputDir = path.dirname(output);
await fs.mkdir(outputDir, { recursive: true });
const qa = {
  status: 'PASS',
  evidence_type: audit.evidence_type,
  input_json_sha256: (await import('node:crypto')).createHash('sha256').update(await fs.readFile(input)).digest('hex'),
  dimension_audit_input_json_sha256: dimensionAudit
    ? (await import('node:crypto')).createHash('sha256').update(await fs.readFile(path.resolve(dimensionAuditArg))).digest('hex')
    : null,
  years: allYears.length,
  same_vintage_exact_matches: 4,
  cross_vintage_diagnostics: 4,
  formula_error_scan: errorScan.ndjson,
  ledger_impact: 'None; project capability ledger remains 26/50.',
  dimension_parity_scopes: dimensionAudit ? dimensionAudit.results.length : 0,
  dimension_parity_status: dimensionAudit?.status ?? 'Not included',
  raw_rows_in_workbook: false,
};
await fs.writeFile(`${output}.qa.json`, JSON.stringify(qa, null, 2));
for (const sheet of wb.worksheets.items) {
  const rangeBySheet = {
    'Browser selected': 'A1:O16',
    'App One-Year': 'A1:O14',
    'Vintage deltas': 'A1:O12',
    'Dimension parity': 'A1:O12',
    Lineage: 'A1:G12',
    'Method & sources': 'A1:D18',
  };
  const preview = await wb.render({ sheetName: sheet.name, range: rangeBySheet[sheet.name], scale: 1, format: 'png' });
  await fs.writeFile(`${output}.${sheet.name.replaceAll(' ', '_')}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const exported = await SpreadsheetFile.exportXlsx(wb);
await exported.save(output);
const roundTrip = await SpreadsheetFile.importXlsx(await FileBlob.load(output));
const browserLedger = roundTrip.worksheets.getItem('Browser selected').getRange('A5:O12').values;
if (browserLedger.length !== 8) throw new Error('XLSX round-trip lost Browser release rows');
console.log(JSON.stringify({ status: 'PASS', output, years: allYears.length, appArchives: appYears.length,
  crossVintageComparisons: crossVintageYears.length, formulaErrors: errorScan.ndjson, qaPath: `${output}.qa.json` }));
