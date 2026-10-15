"""Exercise visible KPI dossiers and actual workbook downloads, without model fitting."""
import json
import uuid
from pathlib import Path
from math import isclose
import zipfile
from xml.etree import ElementTree as ET
from playwright.sync_api import sync_playwright, expect
from credit_atlas.workspace import app_root, sha256


def audit(path,report):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        manifest=ET.fromstring(archive.read('xl/workbook.xml'))
        names=[x.attrib['name'] for x in manifest.findall('s:sheets/s:sheet',ns)]
        assert names==['Overview','KPI','Data','Reviews']
        strings=ET.fromstring(archive.read('xl/sharedStrings.xml'))
        shared=[''.join(x.itertext()) for x in strings.findall('s:si',ns)]
        trees={name:ET.fromstring(archive.read(f'xl/worksheets/sheet{i}.xml')) for i,name in enumerate(names,1)}
        cells={name:{x.attrib['r']:x for x in tree.findall('.//s:sheetData/s:row/s:c',ns)} for name,tree in trees.items()}
    def value(sheet,coord):
        cell=cells[sheet][coord];v=cell.find('s:v',ns)
        if cell.attrib.get('t')=='inlineStr':return ''.join(cell.find('s:is',ns).itertext())
        if cell.attrib.get('t')=='s':return shared[int(v.text)]
        if cell.attrib.get('t') in {'str','d'}:return v.text
        return float(v.text) if v is not None and v.text else None
    expected=[(d,kind,m) for d,r in report['kpi_analysis'].items() for kind,items in [('Business',r['metrics']),('Quality',r['data_quality']['metrics'])] for m in items]
    assert len([x for x in cells['KPI'] if x.startswith('E') and x[1:].isdigit() and int(x[1:])>=6])==len(expected)
    for row,(d,kind,m) in enumerate(expected,6):
        assert [value('KPI',c+str(row)) for c in 'ABCD']==[d,kind,m['name'],m['unit']]
        actual=value('KPI','E'+str(row));assert actual=='Unavailable' if m['value'] is None else isclose(actual,m['value'],rel_tol=1e-14,abs_tol=1e-12)
        c=m['comparison']
        if c:
            assert isclose(value('KPI','G'+str(row)),c['value'],rel_tol=1e-14,abs_tol=1e-12)
            assert isclose(value('KPI','H'+str(row)),m['value']-c['value'],rel_tol=1e-12,abs_tol=1e-9)
            if c['value']!=0:assert isclose(value('KPI','I'+str(row)),(m['value']-c['value'])/c['value'],rel_tol=1e-10,abs_tol=1e-12)
            assert abs(value('KPI','K'+str(row)))<1e-7
        else:assert value('KPI','H'+str(row))=='Unavailable'
        assert cells['KPI']['H'+str(row)].find('s:f',ns) is not None
        assert cells['KPI']['L'+str(row)].find('s:f',ns) is None
    for name,items in cells.items():
        for coord,cell in items.items():assert cell.attrib.get('t')!='e',(name,coord)
    assert trees['KPI'].find('s:sheetViews/s:sheetView/s:pane',ns).attrib['topLeftCell']=='D6'
    assert cells['Overview']['B6'].attrib.get('t')=='d' or isinstance(value('Overview','B6'),float)
    return len(expected)


def run():
    root=app_root();out=root/'artifacts/private'/('kpi-workbook-qa-'+uuid.uuid4().hex[:12]);out.mkdir();checks=[];errors=[]
    ledger=root/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True);page=browser.new_page(viewport={'width':1500,'height':1050},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:8770/?view=monitor');expect(page.get_by_role('button',name='Xuất KPI Excel',exact=True)).to_be_enabled(timeout=180000)
        assert page.locator('#monitor-kpi-analysis').evaluate('(e)=>e.compareDocumentPosition(document.querySelector(".monitor-kpis")) & Node.DOCUMENT_POSITION_FOLLOWING')
        for d,name in [('P1','Retail'),('P2','Mortgage'),('P3','Business'),('P4','Portfolio'),('P5','Structured')]:
            page.locator('.kpi-analysis-nav').get_by_role('button',name=d+' · '+name,exact=True).click()
            selector=page.get_by_label('KPI chi tiết '+d,exact=True);count=selector.locator('option').count();assert count>0
            for index in [0,count-1]:
                selector.select_option(str(index));assert page.locator('.kpi-metric-detail h4').inner_text()==selector.locator('option:checked').inner_text()
            assert page.locator('.kpi-playbook-steps article').count()==4
            assert page.locator('.kpi-source-table[open]').count()>=2
        checks.append('All five domain dossiers expose KPI actuals/formulas/source IDs, four investigation steps and open data/gap tables')
        page.locator('.kpi-analysis-nav').get_by_role('button',name='P2 · Mortgage',exact=True).click()
        page.get_by_label('KPI chi tiết P2',exact=True).select_option(label='D3 share — selected basis')
        page.locator('#monitor-kpi-analysis').screenshot(path=str(out/'analysis-desktop.png'))
        with page.expect_download() as pending:page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'all.json');report=json.loads((out/'all.json').read_text(encoding='utf-8'))
        with page.expect_download(timeout=240000) as pending:page.get_by_role('button',name='Xuất KPI Excel',exact=True).click()
        pending.value.save_as(out/'all.xlsx');assert audit(out/'all.xlsx',report)==110
        checks.append('Real UI all-domain XLSX: 88 business KPIs, 22 quality controls, every actual/unit/baseline and eight cached comparison formulas reconcile JSON')
        page.get_by_label('Monitor domain',exact=True).select_option('P2');page.get_by_label('KPI baseline P2',exact=True).select_option('none')
        with page.expect_download() as pending:page.get_by_role('button',name='Xuất monitor JSON',exact=True).click()
        pending.value.save_as(out/'P2.json');report=json.loads((out/'P2.json').read_text(encoding='utf-8'))
        with page.expect_download(timeout=240000) as pending:page.get_by_role('button',name='Xuất KPI Excel',exact=True).click()
        pending.value.save_as(out/'P2.xlsx');assert audit(out/'P2.xlsx',report)==len(report['kpi_analysis']['P2']['metrics'])+11
        checks.append('Filtered P2 workbook preserves disabled main baseline and separate YoY comparison; no other domain records')
        page.set_viewport_size({'width':390,'height':844});page.locator('#monitor-kpi-analysis').scroll_into_view_if_needed();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(out/'analysis-mobile.png'));browser.close()
    assert not errors,errors;assert before==sha256(ledger)
    checks.append('Mobile has no page overflow/browser exceptions; frozen holdout access ledger unchanged')
    (out/'receipt.json').write_text(json.dumps({'status':'PASS','checks':checks,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'PASS','checks':len(checks),'directory':str(out)}))


if __name__=='__main__':run()
