import base64
import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import pytest
from credit_atlas.excel_workspace import NS,read_inputs,import_workbook,decode_upload
from credit_atlas.exposure_imports import verify_import

TEMPLATE=Path(__file__).parents[1]/'apps/excel/templates/CreditAtlas-Portfolio-Input.xlsx'


def mutated(address,change):
    output=io.BytesIO()
    with zipfile.ZipFile(TEMPLATE) as source,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as dest:
        for name in source.namelist():
            content=source.read(name)
            if name=='xl/worksheets/sheet1.xml':
                tree=ET.fromstring(content); cell=tree.find('.//s:c[@r="'+address+'"]',NS); assert cell is not None
                change(cell); content=ET.tostring(tree,encoding='utf-8',xml_declaration=True)
            dest.writestr(name,content)
    return output.getvalue()


def test_real_authored_template_roundtrip_and_currency_zero_semantics(tmp_path):
    result=import_workbook(tmp_path,TEMPLATE.read_bytes()); _,_,report=verify_import(tmp_path,result['import_id'])
    assert result['rows']==3 and report['global_cross_currency_total'] is None
    currencies={r['currency']:r for r in report['currencies']}
    assert currencies['USD']['reported_amount_major_exact']=='250000' and currencies['USD']['zero_amount_records']==1
    assert currencies['VND']['reported_amount_major_exact']=='1000000' and currencies['USD']['research_el_major_exact'] is None
    source=next((tmp_path/'artifacts/private').glob('excel-intake-*/source.xlsx'))
    source.write_bytes(source.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='lineage'): verify_import(tmp_path,result['import_id'])


def test_formula_cache_is_never_used():
    def change(cell): ET.SubElement(cell,'{'+NS['s']+'}f').text='1+1'
    with pytest.raises(ValueError,match='formulas'): read_inputs(mutated('G2',change))


@pytest.mark.parametrize('value',['1234567890123456','1e100000000','NaN',
    '100000000000000.000000000000001','100000000000000.000000000000009',
    '99999999999999.999999999999999999'])
def test_numeric_excel_precision_and_expansion_bounds(value):
    def change(cell): cell.find('s:v',NS).text=value
    with pytest.raises(ValueError): read_inputs(mutated('G2',change))


@pytest.mark.parametrize('value,expected',[
    ('123456789012345','123456789012345'),
    ('100000000000000.000000000000000','100000000000000.000000000000000'),
    ('0.000000000000000001','0.000000000000000001'),
    ('123456789012345000000000','123456789012345000000000'),
    ('0.000000000000000000','0.000000000000000000')])
def test_exact_numeric_digit_boundary_and_trailing_zeros(value,expected):
    def change(cell): cell.find('s:v',NS).text=value
    rows,_=read_inputs(mutated('G2',change))
    assert rows[0][6]==expected


def test_precision_check_independent_of_ambient_decimal_context():
    from decimal import localcontext
    def change(cell): cell.find('s:v',NS).text='1234567890123456'
    with localcontext() as context:
        context.prec=3
        with pytest.raises(ValueError,match='15 significant'):read_inputs(mutated('G2',change))


def test_xlsx_file_size_bound_checked_before_parsing():
    from credit_atlas.excel_workspace import MAX_FILE
    with pytest.raises(ValueError,match='20MB'):read_inputs(b'x'*(MAX_FILE+1))


def test_position_row_limit_exact_boundary():
    # Minimal populated rows isolate the header-versus-position off-by-one gate.
    # Full row semantics/uniqueness are separately enforced by normalize().
    def payload(count):
        output=io.BytesIO()
        with zipfile.ZipFile(TEMPLATE) as source,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as dest:
            for name in source.namelist():
                data=source.read(name)
                if name=='xl/worksheets/sheet1.xml':
                    tree=ET.fromstring(data);sheet=tree.find('s:sheetData',NS)
                    header=ET.tostring(sheet[0],encoding='unicode')
                    body=''.join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>P{i}</t></is></c></row>' for i in range(2,count+2))
                    data=('<worksheet xmlns="'+NS['s']+'"><sheetData>'+header+body+'</sheetData></worksheet>').encode()
                dest.writestr(name,data)
        return output.getvalue()
    rows,_=read_inputs(payload(50000));assert len(rows)==50000
    with pytest.raises(ValueError,match='row bound'):read_inputs(payload(50001))


def test_duplicate_position_and_missing_amount_rejected(tmp_path):
    def change(cell):
        cell.attrib['t']='inlineStr'; cell.clear(); cell.attrib.update(r='A3',t='inlineStr')
        inline=ET.SubElement(cell,'{'+NS['s']+'}is'); ET.SubElement(inline,'{'+NS['s']+'}t').text='EXAMPLE-001'
    with pytest.raises(ValueError,match='duplicate'): import_workbook(tmp_path,mutated('A3',change))
    def missing(cell):
        cell.find('s:v',NS).text=''
    with pytest.raises(ValueError,match='decimal'): import_workbook(tmp_path,mutated('G2',missing))


def test_malformed_upload_and_unsupported_macro():
    with pytest.raises(ValueError): read_inputs(b'not a workbook')
    with pytest.raises(ValueError): decode_upload({'filename':'file.xlsm','content_base64':'AA=='})
    payload={'filename':'portfolio.xlsx','content_base64':base64.b64encode(TEMPLATE.read_bytes()).decode()}
    assert decode_upload(payload)==TEMPLATE.read_bytes()
    output=io.BytesIO()
    with zipfile.ZipFile(TEMPLATE) as source,zipfile.ZipFile(output,'w') as dest:
        for name in source.namelist(): dest.writestr(name,source.read(name))
        dest.writestr('xl/vbaProject.bin',b'unsupported')
    with pytest.raises(ValueError,match='Macros'): read_inputs(output.getvalue())
