"""Value-only XLSX affordability intake with bounded parsing and cell lineage."""
import base64
import hashlib
import io
import json
import posixpath
import re
import zipfile
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from .affordability import GROUPS, assess

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RID = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
HEADERS = ['group', 'ref', 'amount', 'period', 'evidence_ref', 'valid_through']
CONTROL_KEYS = {'case_ref', 'as_of', 'currency', 'scope', 'scope_ref', 'members',
                'policy_ref', 'max_total_dti_fraction', 'min_monthly_residual'} | {'coverage_' + g for g in GROUPS}
STRESS_KEYS = {'gross_income_reduction_fraction', 'net_income_reduction_fraction', 'extra_monthly_expense'}
MAX_BYTES = 2 * 1024**2
TEMPLATE_SHA256 = '5c88cf6a9685db9bef9defd7c6f0d6e31352e499ec8d8fb3d76cb8224a64b979'


def template_bytes(root):
    path = root / 'apps/excel/templates/CreditAtlas-Affordability-Input.xlsx'
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != TEMPLATE_SHA256:
        raise ValueError('Affordability template evidence changed')
    return data


def _xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('XML declarations are unsupported')
    return ET.fromstring(data)


def _parse(data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise ValueError('Affordability XLSX must be at most 2MB')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if len(names) > 100 or len(names) != len(set(names)) or sum(x.file_size for x in z.infolist()) > 10 * 1024**2:
            raise ValueError('Workbook expanded size or entry bound exceeded')
        if any(n.startswith('/') or '\\' in n or '..' in n.split('/') or any(t in n.lower() for t in ('vbaproject', 'externallinks', 'connections.xml', 'embeddings/')) for n in names):
            raise ValueError('Macros, external data and embedded files are unsupported')
        # Never follow external relationships, including external sheet targets.
        for name in names:
            if name.endswith('.rels'):
                if any(r.attrib.get('TargetMode') == 'External' for r in _xml(z.read(name))):
                    raise ValueError('External relationships are unsupported')
        strings = []
        if 'xl/sharedStrings.xml' in names:
            strings = [''.join(t.text or '' for t in n.findall('.//s:t', NS)) for n in _xml(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
        rels = _xml(z.read('xl/_rels/workbook.xml.rels'))
        targets = {}
        for r in rels:
            target = r.attrib['Target']
            path = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
            if not path.startswith('xl/') or path not in names or r.attrib['Id'] in targets:
                raise ValueError('Invalid workbook relationship')
            targets[r.attrib['Id']] = path
        sheets = {}
        for sheet in _xml(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS):
            name = sheet.attrib['name']
            if name in sheets:
                raise ValueError('Duplicate worksheet name')
            sheets[name] = targets[sheet.attrib[RID]]
        if set(sheets) != {'AffordabilityControl', 'AffordabilityItems'} or len(set(sheets.values())) != 2:
            raise ValueError('Exactly AffordabilityControl and AffordabilityItems sheets required')

        def rows(sheet, width, limit):
            out = []; seen = set(); seen_rows = set(); guidance_column = width + 2; guidance_seen = False; guidance_header = False
            for row in _xml(z.read(sheets[sheet])).findall('s:sheetData/s:row', NS):
                rowno = int(row.attrib['r'])
                if not 1 <= rowno <= limit or rowno in seen_rows or len(seen_rows) >= limit:
                    raise ValueError('Invalid or duplicate input row')
                seen_rows.add(rowno)
                values = [''] * width
                for cell in row.findall('s:c', NS):
                    address = cell.attrib['r']
                    match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', address)
                    if not match or int(match[2]) != rowno or address in seen:
                        raise ValueError('Invalid or duplicate input cell')
                    seen.add(address)
                    column = 0
                    for char in match[1]: column = column * 26 + ord(char) - 64
                    if cell.find('s:f', NS) is not None:
                        raise ValueError('Replace input formulas with explicit values')
                    kind = cell.attrib.get('t', 'n'); v = cell.find('s:v', NS)
                    value = v.text or '' if v is not None else ''
                    if kind == 's':
                        if not value.isdigit() or int(value) >= len(strings): raise ValueError('Invalid shared string')
                        value = strings[int(value)]
                    elif kind == 'inlineStr': value = ''.join(t.text or '' for t in cell.findall('s:is//s:t', NS))
                    elif kind == 'b':
                        if value not in {'0', '1'}: raise ValueError('Invalid Excel boolean')
                        value = 'true' if value == '1' else 'false'
                    elif kind == 'n' and value:
                        number = Decimal(value)
                        if not number.is_finite() or len(''.join(map(str, number.as_tuple().digits)).rstrip('0')) > 15 or number.adjusted() > 18 or number.as_tuple().exponent < -6:
                            raise ValueError('Numeric input exceeds exact supported Excel precision')
                        value = format(number, 'f')
                    elif kind not in {'n', 'str'}: raise ValueError('Unsupported Excel cell type')
                    if len(value) > 256: raise ValueError('Input text is too long')
                    if column > width and column != guidance_column:
                        if value: raise ValueError('Unexpected input column')
                        continue
                    if column == guidance_column:
                        if value:
                            guidance_seen = True
                            if rowno == 1 and value == 'Guidance': guidance_header = True
                    else: values[column - 1] = value
                if any(values): out.append((rowno, values))
            if guidance_seen and not guidance_header: raise ValueError('Guidance column must be explicitly labelled')
            out.sort()
            return out

        controls = rows('AffordabilityControl', 2, 40)
        items = rows('AffordabilityItems', 6, 2501)
        if not controls or controls.pop(0) != (1, ['key', 'value']): raise ValueError('Exact control header required at row 1')
        if not items or items.pop(0) != (1, HEADERS): raise ValueError('Exact item header required at row 1')
        control = {}; lineage = []
        for rowno, (key, value) in controls:
            if key in control: raise ValueError('Duplicate control key')
            control[key] = value
            lineage.append({'field': key, 'sheet': 'AffordabilityControl', 'cell': f'B{rowno}', 'source_value': value})
        if set(control) not in (CONTROL_KEYS, CONTROL_KEYS | STRESS_KEYS): raise ValueError('Exact controls and complete optional stress required')
        if not re.fullmatch(r'[1-9][0-9]*', control['members']): raise ValueError('Integer member count required')
        payload = {k: control[k] for k in ['case_ref', 'as_of', 'currency', 'scope', 'scope_ref']}
        payload['members'] = int(control['members'])
        payload['coverage'] = {}
        for group in GROUPS:
            value = control['coverage_' + group]
            if value not in {'true', 'false'}: raise ValueError('Explicit true/false coverage required')
            payload['coverage'][group] = value == 'true'; payload[group] = []
        payload['policy'] = {k: control[k] or None for k in ['policy_ref', 'max_total_dti_fraction', 'min_monthly_residual']}
        if STRESS_KEYS <= set(control): payload['stress'] = {k: control[k] for k in STRESS_KEYS}
        for rowno, values in items:
            group, ref, amount, period, evidence, validity = values
            if group not in GROUPS: raise ValueError('Unknown affordability input group')
            payload[group].append({'ref': ref, 'amount': amount or None, 'period': period, 'evidence_ref': evidence or None, 'valid_through': validity or None})
            for column, value, field in zip('ABCDEF', values, HEADERS):
                lineage.append({'group': group, 'ref': ref, 'field': field, 'sheet': 'AffordabilityItems', 'cell': f'{column}{rowno}', 'source_value': value})
        result = assess(payload)
        return {'intake': payload, 'assessment': result, 'source': {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'item_rows': len(items), 'cell_lineage': lineage},
                'status': 'VALUE_ONLY_XLSX_PARSED', 'visibility': 'private', 'source_documents_verified': False, 'public_release_approved': False}


def read_workbook(data):
    try: return _parse(data)
    except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, InvalidOperation, OverflowError, NotImplementedError, RuntimeError) as error:
        raise ValueError('Malformed or unsupported affordability XLSX') from error


def import_upload(payload):
    if not isinstance(payload, dict) or set(payload) != {'filename', 'content_base64'} or not isinstance(payload['filename'], str) or not payload['filename'].lower().endswith('.xlsx'):
        raise ValueError('Named XLSX upload required')
    encoded = payload['content_base64']
    if not isinstance(encoded, str) or len(encoded) > (MAX_BYTES + 2) // 3 * 4:
        raise ValueError('Workbook upload too large')
    return read_workbook(base64.b64decode(encoded, validate=True))


def main():
    import argparse
    from pathlib import Path
    from uuid import uuid4
    parser = argparse.ArgumentParser()
    parser.add_argument('workbook', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    if args.workbook.stat().st_size > MAX_BYTES: raise ValueError('Affordability XLSX must be at most 2MB')
    data = args.workbook.read_bytes(); result = read_workbook(data)
    folder = args.root / 'artifacts/private' / ('affordability-excel-intake-' + uuid4().hex[:12])
    folder.mkdir(parents=True)
    (folder / 'source.xlsx').write_bytes(data)
    (folder / 'intake-assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(folder), 'status': result['status'], 'source_sha256': result['source']['sha256'], 'item_rows': result['source']['item_rows']}))


if __name__ == '__main__': main()
