"""Bounded XLSX intake into the existing typed private exposure contract."""
import base64
import csv
import io
import json
import posixpath
import re
import uuid
import zipfile
from decimal import Decimal,InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET
from .exposure_imports import FIELDS,META_KEYS,import_exposures,normalize,validate_metadata
from .workspace import contained,sha256,timestamp,write_new

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
REL='http://schemas.openxmlformats.org/package/2006/relationships'
MAX_FILE=20*1024**2


def _read_inputs(data):
    if not isinstance(data,bytes) or not 0<len(data)<=MAX_FILE: raise ValueError('XLSX file must be at most 20MB')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist()
        if len(names)>1000 or len(names)!=len(set(names)) or sum(n.file_size for n in z.infolist())>100*1024**2:
            raise ValueError('Workbook expanded size/entry bound exceeded')
        if any('..' in n.split('/') or n.startswith('/') or '\\' in n or any(t in n.lower() for t in ('vbaproject','externallinks','connections.xml')) for n in names):
            raise ValueError('Macros/external data links are unsupported')
        strings=[]
        if 'xl/sharedStrings.xml' in names:
            strings=[''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        relationships=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        targets={r.attrib['Id']:posixpath.normpath(posixpath.join('xl',r.attrib['Target'])) if not r.attrib['Target'].startswith('/') else r.attrib['Target'].lstrip('/') for r in relationships}
        workbook=ET.fromstring(z.read('xl/workbook.xml')); sheets={n.attrib['name']:targets[n.attrib['{'+NS['r']+'}id']] for n in workbook.findall('s:sheets/s:sheet',NS)}
        if not {'InputPositions','InputControl'}<=set(sheets): raise ValueError('Use InputPositions and InputControl sheets from the template')
        def rows(sheet,columns,max_rows):
            result=[]
            for row in ET.fromstring(z.read(sheets[sheet])).findall('s:sheetData/s:row',NS):
                values=['']*columns
                seen_cells=set()
                if len(result)>=max_rows: raise ValueError('Input row bound exceeded')
                for cell in row.findall('s:c',NS):
                    if cell.find('s:f',NS) is not None: raise ValueError('Input formulas must be replaced with explicit values; cached formula values are not trusted')
                    match=re.fullmatch(r'([A-Z]+)([1-9][0-9]*)',cell.attrib['r'])
                    if not match: raise ValueError('Invalid cell address')
                    if cell.attrib['r'] in seen_cells: raise ValueError('Duplicate input cell')
                    seen_cells.add(cell.attrib['r'])
                    column=0
                    for char in match[1]: column=column*26+ord(char)-64
                    v=cell.find('s:v',NS); value=v.text if v is not None and v.text else ''
                    kind=cell.attrib.get('t','n')
                    if kind=='s': value=strings[int(value)]
                    elif kind=='inlineStr': value=''.join(t.text or '' for t in cell.findall('s:is//s:t',NS))
                    elif kind=='b': value='true' if value=='1' else 'false'
                    elif kind=='e': raise ValueError('Input contains Excel error')
                    elif kind=='n' and value:
                        number=Decimal(value)
                        # normalize() rounds under the ambient Decimal context before counting.
                        # Inspect the exact constructor digits and remove only trailing zeros.
                        significant_digits=len(''.join(map(str,number.as_tuple().digits)).rstrip('0'))
                        if not number.is_finite() or number.adjusted()>23 or number.as_tuple().exponent < -18 or significant_digits>15:
                            raise ValueError('Numeric Excel cells support up to 15 significant digits; use text for exact larger amounts/IDs')
                        value=format(number,'f')
                    if column>columns:
                        if sheet=='InputControl' and column>=4: continue
                        if value: raise ValueError('Unexpected populated input column')
                    else: values[column-1]=value
                if any(values): result.append(values)
            return result
        positions=rows('InputPositions',len(FIELDS),50001); controls=rows('InputControl',2,30)
        if not positions or positions.pop(0)!=list(FIELDS) or not positions: raise ValueError('Exact position headers and at least one position required')
        if not controls or controls.pop(0)!=['key','value']: raise ValueError('Exact control headers required')
        metadata={}
        for key,value in controls:
            if key in metadata: raise ValueError('Duplicate metadata field')
            metadata[key]=value
        if set(metadata)!=META_KEYS: raise ValueError('Exact metadata fields required')
        for key in ('schema_version','risk_contract','source_lineage','public_release_approved'):
            metadata[key]=json.loads(metadata[key])
        if metadata['source_lineage']!=[]: raise ValueError('Workbook lineage is generated by the importer; leave it []')
        validate_metadata(metadata)
        return positions,metadata


def read_inputs(data):
    try: return _read_inputs(data)
    except (zipfile.BadZipFile,ET.ParseError,KeyError,IndexError,InvalidOperation,NotImplementedError) as error:
        raise ValueError('Malformed or unsupported XLSX input') from error


def import_workbook(root,data):
    rows,metadata=read_inputs(data)
    folder=contained(root,'artifacts/private/excel-intake-'+uuid.uuid4().hex[:12]); folder.mkdir(parents=True)
    (folder/'source.xlsx').write_bytes(data)
    metadata['source_lineage']=[{'path':str((folder/'source.xlsx').relative_to(root)),'sha256':sha256(folder/'source.xlsx')}]
    with (folder/'positions.csv').open('x',encoding='utf-8',newline='') as file:
        writer=csv.writer(file); writer.writerow(FIELDS); writer.writerows(rows)
    write_new(folder/'metadata.json',metadata)
    normalized=normalize(folder/'positions.csv',metadata)
    receipt=import_exposures(root,str((folder/'positions.csv').relative_to(root)),str((folder/'metadata.json').relative_to(root)))
    write_new(folder/'intake-complete.json',{'status':'VERIFIED_XLSX_TYPED_EXPOSURE_INTAKE','import_id':receipt['import_id'],
        'rows':len(normalized),'input_sha256':sha256(folder/'source.xlsx'),'adapter_sha256':sha256(Path(__file__)),
        'completed_at':timestamp(),'visibility':'private','public_release_approved':False})
    return {'import_id':receipt['import_id'],'rows':len(normalized),'status':'verified','visibility':'private','public_release_approved':False}


def decode_upload(payload):
    if not isinstance(payload,dict) or set(payload)!={'filename','content_base64'} or not isinstance(payload['filename'],str) or not payload['filename'].lower().endswith('.xlsx'):
        raise ValueError('Named XLSX upload required')
    if not isinstance(payload['content_base64'],str) or len(payload['content_base64'])>MAX_FILE*4//3+4: raise ValueError('Workbook upload too large')
    return base64.b64decode(payload['content_base64'],validate=True)
