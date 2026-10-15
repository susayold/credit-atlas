"""Read-only legacy XLS inventory and independent pool roll-forward checks.

Run with bundled Python; xlrd 2.0.2 is installed only in the D: legacy-reader target.
Does not recalculate or edit the issuer workbooks.
"""
import hashlib
import json
import sys
import uuid
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.cache/xls-reader'))
import xlrd


def inspect(source_id):
    if not __import__('re').fullmatch(r'abs-source-[0-9a-f]{12}', source_id):
        raise ValueError('Invalid source identifier')
    source = ROOT / 'data/private/structured' / source_id
    receipt = json.loads((source / 'acquisition-complete.json').read_text())
    if receipt['status'] != 'ABS_ISSUER_SOURCE_COMPLETE':
        raise ValueError('Incomplete source')
    for item in receipt['files']:
        if hashlib.sha256((source / item['file']).read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Source digest mismatch')
    cells, periods, checks = [], [], []
    for item in receipt['files']:
        if not item['file'].endswith('.xls'):
            continue
        book = xlrd.open_workbook(source / item['file'], formatting_info=True)
        for sheet in book.sheets():
            if sheet.cell_value(0, 0) != receipt['deal'] or sheet.cell_value(1, 0) != 'Monthly Servicer Certificate':
                raise ValueError('Unexpected issuer/certificate schema')
            for row in range(sheet.nrows):
                for col in range(sheet.ncols):
                    cell = sheet.cell(row, col)
                    if cell.ctype == xlrd.XL_CELL_EMPTY:
                        continue
                    xf = book.xf_list[cell.xf_index]
                    cells.append({'file': item['file'], 'sheet': sheet.name, 'row': row + 1, 'column': col + 1,
                                  'cell_type': cell.ctype, 'value': cell.value,
                                  'number_format': book.format_map[xf.format_key].format_str})
            def number(row, col=1):
                cell = sheet.cell(row - 1, col)
                if cell.ctype != xlrd.XL_CELL_NUMBER:
                    raise ValueError('Expected numeric pool source cell')
                return Decimal(str(cell.value))
            required = {16: 'Principal Payments', 17: 'Defaulted Receivables', 18: 'Repurchased Accounts'}
            for row, label in required.items():
                if sheet.cell_value(row - 1, 0).strip() != label:
                    raise ValueError('Pool layout drift')
            if 'Yield Supplement Overcollateralization Amount' not in sheet.cell_value(18, 0) or 'Pool Balance at' not in sheet.cell_value(19, 0):
                raise ValueError('Ending pool layout drift')
            delta = number(15) - number(16) - number(17) - number(18) - number(19) - number(20)
            count_delta = number(15, 2) - number(16, 2) - number(17, 2) - number(18, 2) - number(20, 2)
            dates = sheet.cell_value(5, 1)
            payment = xlrd.xldate_as_datetime(sheet.cell_value(9, 1), book.datemode).date().isoformat()
            periods.append({'file': item['file'], 'sheet': sheet.name, 'collection_period_source': dates,
                            'distribution_date': payment, 'rows': sheet.nrows, 'columns': sheet.ncols,
                            'ending_pool_balance_source': str(number(20)), 'ending_accounts': str(number(20, 2))})
            checks.append({'file': item['file'], 'sheet': sheet.name,
                           'check': 'receivables less principal/default/repurchase equals pool plus yield supplement',
                           'money_delta_usd': str(delta), 'money_tolerance_usd': '0.01',
                           'account_delta': str(count_delta), 'pass': abs(delta) <= Decimal('.01') and count_delta == 0})
    if len({p['collection_period_source'] for p in periods}) != len(periods):
        raise ValueError('Duplicate collection periods')
    output = ROOT / 'artifacts/private' / ('abs-inventory-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    (output / 'source-cells.json').write_text(json.dumps(cells, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    summary = {'source_id': source_id, 'inventory_id': output.name,
               'status': 'PASS' if all(c['pass'] for c in checks) else 'SOURCE_RECONCILIATION_FAILED',
               'reader': 'xlrd ' + xlrd.__version__, 'stored_cells': len(cells),
               'nonempty_cells': sum(c['cell_type'] not in (xlrd.XL_CELL_BLANK, xlrd.XL_CELL_EMPTY)
                                     and not (c['cell_type'] == xlrd.XL_CELL_TEXT and c['value'] == '') for c in cells),
               'styled_blank_cells': sum(c['cell_type'] == xlrd.XL_CELL_BLANK for c in cells),
               'empty_text_cells': sum(c['cell_type'] == xlrd.XL_CELL_TEXT and c['value'] == '' for c in cells),
               'periods': periods, 'checks': checks,
               'limitations': ['Cached numeric cells retain binary floating point source values and formats',
                               'No formula recalculation or extracted formula lineage',
                               'Pool plus yield supplement is receivables balance, not note balance',
                               'Payment date differs from collection period',
                               'Pool checks do not certify deal waterfall or prospectus terms'],
               'source_receipt_sha256': hashlib.sha256((source / 'acquisition-complete.json').read_bytes()).hexdigest(),
               'inspector_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output / 'inventory.json').write_text(json.dumps(summary, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'inventory_id': output.name, 'status': summary['status'], 'periods': len(periods),
                      'stored_cells': len(cells), 'nonempty_cells': summary['nonempty_cells'],
                      'failed_checks': sum(not c['pass'] for c in checks)}))
    return summary


if __name__ == '__main__':
    inspect(sys.argv[1])
