"""Synthetic OOXML fixtures exercise import boundaries, not authored deliverables."""
import base64
import io
import zipfile
from xml.sax.saxutils import escape
import pytest
from credit_atlas.affordability_excel import read_workbook, import_upload, GROUPS, HEADERS


def fixture_workbook(missing=False, zero=False, expired=False, formula=False, duplicate=False, external=False, numeric=None, coverage=True):
    controls = [('case_ref','qa-case'),('as_of','2026-10-12'),('currency','USD'),('scope','individual'),('scope_ref','qa-person'),('members','1'),('policy_ref','qa-policy'),('max_total_dti_fraction','0.4'),('min_monthly_residual','500')]
    controls += [('coverage_'+g, 'true' if coverage else 'false') for g in GROUPS]
    amounts = ['60000','4000','1500','1500','500']
    if missing: amounts[-1]=''
    if zero: amounts[0]='0'
    items = [HEADERS] + [[g, 'qa-'+g, a, 'annual' if g=='gross_income' else 'monthly', '', '2026-10-11' if expired and g=='net_income' else ''] for g,a in zip(GROUPS,amounts)]
    def xml(rows, which):
        output=[]
        for ri,row in enumerate(rows,1):
            cells=[]
            for ci,value in enumerate(row):
                addr=chr(65+ci)+str(ri)
                if which=='items' and addr=='C2' and numeric is not None:
                    cells.append(f'<c r="{addr}"><v>{escape(numeric)}</v></c>')
                else:
                    f='<f>1+1</f>' if formula and which=='items' and addr=='C2' else ''
                    cells.append(f'<c r="{addr}" t="inlineStr">{f}<is><t>{escape(value)}</t></is></c>')
            if duplicate and which=='items' and ri==2: cells.append(cells[0])
            output.append(f'<row r="{ri}">'+''.join(cells)+'</row>')
        return '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'+''.join(output)+'</sheetData></worksheet>'
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="AffordabilityControl" r:id="r1"/><sheet name="AffordabilityItems" r:id="r2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/s1.xml"/><Relationship Id="r2" Target="worksheets/s2.xml"/></Relationships>')
        z.writestr('xl/worksheets/s1.xml',xml([['key','value']]+controls,'controls'))
        z.writestr('xl/worksheets/s2.xml',xml(items,'items'))
        if external: z.writestr('xl/_rels/external.rels','<Relationships><Relationship Id="x" Target="https://example.com" TargetMode="External"/></Relationships>')
    return buffer.getvalue()


def test_source_cell_lineage_exact_assessment_and_upload_parity():
    data=fixture_workbook(); r=read_workbook(data)
    assert r['assessment']['baseline']['total_dti_fraction']['decimal50']=='0.4'
    assert r['assessment']['baseline']['monthly_residual_after_expenses_and_debt']['decimal50']=='500'
    assert r['source']['item_rows']==5 and len(r['source']['sha256'])==64
    assert next(x for x in r['source']['cell_lineage'] if x.get('group')=='gross_income' and x['field']=='amount')['cell']=='C2'
    assert not r['source_documents_verified'] and r['assessment']['credit_decision'] is None
    assert import_upload({'filename':'qa.xlsx','content_base64':base64.b64encode(data).decode()})==r


@pytest.mark.parametrize('flags,field',[(dict(missing=True),'monthly_total_debt'),(dict(expired=True),'monthly_residual_after_expenses_and_debt'),(dict(coverage=False),'total_dti_fraction')])
def test_missing_expired_and_unattested_keep_dependencies_unavailable(flags,field):
    assert read_workbook(fixture_workbook(**flags))['assessment']['baseline'][field] is None


def test_real_zero_is_preserved_and_numeric_scientific_xml_normalizes():
    r=read_workbook(fixture_workbook(zero=True))['assessment']['baseline']
    assert r['gross_monthly_income']['decimal50']=='0' and r['dti_unavailable_reason']=='zero_gross_income'
    assert read_workbook(fixture_workbook(numeric='6E4'))['intake']['gross_income'][0]['amount']=='60000'


@pytest.mark.parametrize('flags',[dict(formula=True),dict(duplicate=True),dict(external=True),dict(numeric='1234567890123456'),dict(numeric='NaN')])
def test_unsupported_or_ambiguous_values_rejected(flags):
    with pytest.raises(ValueError): read_workbook(fixture_workbook(**flags))


@pytest.mark.parametrize('data',[b'not zip',b'',b'PK',b'x'*(2*1024**2+1)], ids=['not-zip','empty','truncated-zip','oversize'])
def test_malformed_and_oversize(data):
    with pytest.raises(ValueError): read_workbook(data)


def test_xml_entity_and_duplicate_control_rejected():
    data=fixture_workbook()
    for replacement in ['<!DOCTYPE foo [<!ENTITY x "hello">]>', '']:
        b=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as old,zipfile.ZipFile(b,'w') as new:
            for name in old.namelist():
                content=old.read(name)
                if name=='xl/worksheets/s1.xml':
                    if replacement: content=replacement.encode()+content
                    else: content=content.replace(b'policy_ref', b'case_ref')
                new.writestr(name,content)
        with pytest.raises(ValueError):read_workbook(b.getvalue())


def test_blank_deliverable_template_and_tamper_guard(tmp_path):
    from pathlib import Path
    from credit_atlas.affordability_excel import template_bytes
    root=Path(__file__).resolve().parents[1]
    data=template_bytes(root)
    with pytest.raises(ValueError,match='Integer member count'): read_workbook(data)
    dest=tmp_path/'apps/excel/templates';dest.mkdir(parents=True)
    (dest/'CreditAtlas-Affordability-Input.xlsx').write_bytes(data+b'changed')
    with pytest.raises(ValueError,match='evidence changed'):template_bytes(tmp_path)


def test_guidance_column_is_labelled_and_not_financial_input():
    data=fixture_workbook()
    for header in ['Guidance','Unlabelled']:
        b=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(data)) as old,zipfile.ZipFile(b,'w') as new:
            for name in old.namelist():
                content=old.read(name)
                if name=='xl/worksheets/s1.xml':
                    content=content.replace(b'<row r="1">',f'<row r="1"><c r="D1" t="inlineStr"><is><t>{header}</t></is></c>'.encode())
                    content=content.replace(b'<row r="2">',b'<row r="2"><c r="D2" t="inlineStr"><is><t>999999</t></is></c>')
                new.writestr(name,content)
        if header=='Guidance': assert read_workbook(b.getvalue())['intake']['case_ref']=='qa-case'
        else:
            with pytest.raises(ValueError,match='explicitly labelled'):read_workbook(b.getvalue())
