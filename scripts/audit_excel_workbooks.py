"""Read saved XLSX XML independently; never modify workbooks."""
import json
import zipfile
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.workspace import app_root,sha256,timestamp,write_new
from credit_atlas.excel_workspace import read_inputs

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def inspect(path):
    with zipfile.ZipFile(path) as archive:
        workbook=ET.fromstring(archive.read('xl/workbook.xml'))
        sheets=[r.attrib['name'] for r in workbook.findall('s:sheets/s:sheet',NS)]
        result={}
        for index,name in enumerate(sheets,1):
            tree=ET.fromstring(archive.read(f'xl/worksheets/sheet{index}.xml'))
            cells={cell.attrib['r']:cell for cell in tree.findall('.//s:sheetData/s:row/s:c',NS)}
            assert not [c for c in cells.values() if c.attrib.get('t')=='e'],name
            result[name]=cells
        return result

def numeric(cells,address):
    return Decimal(cells[address].find('s:v',NS).text)

def run(root):
    directory=root/'outputs/01a119ef-c68b-7292-b81e-8192458d08f8'
    template=directory/'CreditAtlas-Portfolio-Input.xlsx'; report=directory/'CreditAtlas-Portfolio-Review.xlsx'
    inputs=inspect(template); results=inspect(report)
    assert list(inputs)==['InputPositions','InputControl']
    assert list(results)==['Summary','ScenarioModel','ResearchResults','Inventory','Review','Audit']
    rows,metadata=read_inputs(template.read_bytes())
    assert len(rows)==3 and metadata['risk_contract'] is None
    assert numeric(inputs['InputPositions'],'G3')==0
    assert numeric(results['Summary'],'B6')==9698
    assert numeric(results['Summary'],'B7')==Decimal('915208989.12')
    assert numeric(results['Audit'],'D6')==0 and numeric(results['Audit'],'D7')==0
    assert abs(numeric(results['ScenarioModel'],'G20')-Decimal('17313511.79897183'))<Decimal('.01')
    assert results['ScenarioModel']['G20'].find('s:f',NS) is not None
    assert results['Summary']['B14'].find('s:f',NS) is not None
    assert sha256(template)==sha256(root/'apps/excel/templates/CreditAtlas-Portfolio-Input.xlsx')
    receipt={'status':'PASS','completed_at':timestamp(),'workbooks':{str(p):sha256(p) for p in (template,report)},
        'builder_sha256':sha256(root/'apps/excel/build_workbook.mjs'),
        'source_payload_sha256':sha256(root/'artifacts/private/excel-workbook-input-20261009.json'),
        'checks':['2 input sheets, 6 report sheets','No saved Excel error cells','Zero and missing risk inputs retained',
            '9698 observations and USD 915208989.12 source control','Count and cent-level amount reconciliation',
            'Saved adverse EL agrees within one cent','Formula cells and cached results present','Packaged template matches deliverable'],
        'desktop_excel_execution_tested':False,'visibility':'private','public_release_approved':False}
    output=root/'artifacts/private'/('excel-workbook-audit-'+timestamp().replace(':','').replace('-','').replace('.','')+'.json')
    write_new(output,receipt)
    return {'status':'PASS','receipt':str(output)}

if __name__=='__main__': print(json.dumps(run(app_root()),indent=2))
