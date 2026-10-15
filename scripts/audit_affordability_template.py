import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from credit_atlas.affordability_excel import template_bytes,read_workbook

root=Path(__file__).resolve().parents[1];folder=root/'artifacts/private/affordability-template-roundtrip-20261012'
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
data=template_bytes(root);checks=[]
with zipfile.ZipFile(root/'apps/excel/templates/CreditAtlas-Affordability-Input.xlsx') as z:
    sheets=[ET.fromstring(z.read(n)) for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]
    assert len(sheets)==2
    assert not any(s.findall('.//s:f',ns) for s in sheets)
    assert sum(len(s.findall('.//s:dataValidation',ns)) for s in sheets)==5
    # Check actual blank cells without invoking the importer calculation path.
    controls=next(s for s in sheets if any(c.attrib['r']=='B15' for c in s.findall('.//s:c',ns)))
    for address in ['B'+str(r) for r in range(2,11)]:
        c=next((c for c in controls.findall('.//s:c',ns) if c.attrib['r']==address),None)
        assert c is None or not any((t.text or '').strip() for t in c.iter() if t.tag.endswith('}t') or t.tag.endswith('}v'))
    checks.append('Two sheets,five native validations,no formulas,and blank customer/policy inputs independently checked in saved OOXML')
r=read_workbook((folder/'qa-filled.xlsx').read_bytes())
assert r['assessment']['baseline']['gross_monthly_income']['decimal50']=='5000'
assert r['assessment']['baseline']['monthly_total_debt']['decimal50']=='2000'
assert r['assessment']['baseline']['total_dti_fraction']['decimal50']=='0.4'
assert r['assessment']['baseline']['monthly_residual_after_expenses_and_debt']['decimal50']=='500'
assert len(r['intake']['gross_income'])==1 and r['source']['item_rows']==5
assert r['assessment']['credit_decision'] is None and not r['source_documents_verified']
checks.append('Artifact-tool edited template roundtrip preserves numeric inputs,DTI/residual and unverified evidence state')
(folder/'audit.json').write_text(json.dumps({'status':'PASS','checks':checks,'qa_inputs_only':True,'native_excel_execution_checked':False},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','checks':len(checks),'folder':str(folder)}))
