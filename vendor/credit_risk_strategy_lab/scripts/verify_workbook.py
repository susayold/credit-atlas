"""Read-only XLSX/preview QA with the bundled Python runtime (openpyxl)."""
import datetime
import hashlib
import json
import math
import re
import sys
import zipfile
from pathlib import Path

import openpyxl

directory = Path(sys.argv[1]).resolve()
registry = json.loads((directory / 'registry.json').read_text())
file = directory / registry['filename']
check = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if check(file) != registry['sha256'] or check(directory / 'preview.json') != registry['preview_sha256']:
    raise ValueError('Workbook / preview hash mismatch')
preview = json.loads((directory / 'preview.json').read_text())
values = openpyxl.load_workbook(file, data_only=True)
formulas = openpyxl.load_workbook(file, data_only=False)
if values.sheetnames != [s['name'] for s in preview['sheets']]:
    raise ValueError('Sheet order differs from preview')
if len(values.sheetnames) != 15:
    raise ValueError('Sheet inventory differs from plan')

def equal(a, b):
    if isinstance(a, datetime.datetime):
        return a.isoformat(timespec='milliseconds') + 'Z' == b
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)
    return a == b

cells_checked = 0
for sheet in preview['sheets']:
    ws = values[sheet['name']]
    if ws.sheet_state != 'visible' or ws.sheet_view.showGridLines is not False:
        raise ValueError('Hidden sheet or unexpected gridlines')
    for table in [sheet, *sheet.get('extraTables', [])]:
        for i, row in enumerate(table['rows'], table['startRow']):
            for j, expected in enumerate(row, 1):
                actual = ws.cell(i, j).value
                if not equal(actual, expected):
                    raise ValueError(f'Preview mismatch {ws.title}!{ws.cell(i,j).coordinate}: {actual} vs {expected}')
                cells_checked += 1
    for row in ws:
        for cell in row:
            if cell.data_type == 'e':
                raise ValueError(f'Formula error {ws.title}!{cell.coordinate}')
    for row in formulas[ws.title]:
        for cell in row:
            if cell.comment:
                raise ValueError('Unexpected cell comment')
            if isinstance(cell.value, str) and re.search(r'[A-Z]:[\\/]|S\d{2}[Q0-9]{1}\d{8}', cell.value):
                raise ValueError('Potential private path or source identifier')
            if cell.data_type == 'f' and "'13_Checks'!" in cell.value:
                raise ValueError('Business output depends on terminal checks')
for r in range(7, 12):
    if values['13_Checks'].cell(r, 4).value != 'PASS':
        raise ValueError('Reconciliation not PASS')
for name in ['03_Portfolio', '05_Transitions']:
    if formulas[name].freeze_panes != 'A7':
        raise ValueError('Missing expected freeze pane')
if formulas.defined_names:
    raise ValueError('Unexpected defined names')
with zipfile.ZipFile(file) as archive:
    if any('externalLinks/' in name or 'vbaProject' in name or 'comments' in name.lower() for name in archive.namelist()):
        raise ValueError('Unexpected external link, macro or comment')
report = dict(status='PASS', cells_checked=cells_checked, sheets_checked=len(values.sheetnames),
              preview_matches_xlsx=True, formula_errors=0, hidden_sheets=0,
              native_excel_recalculation_verified=False, sha256=registry['sha256'])
(directory / 'qa.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
