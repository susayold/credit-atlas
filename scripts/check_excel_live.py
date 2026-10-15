"""Verify the running local app's private XLSX downloads against saved controls."""
import hashlib
import io
import json
import uuid
import zipfile
from decimal import Decimal
from urllib.request import urlopen
from xml.etree import ElementTree as ET
from credit_atlas.workspace import app_root,sha256,timestamp,write_new

if __name__=='__main__':
    root=app_root(); base='http://127.0.0.1:8770'; source='exposure-import-57b88e00bedb'
    template=root/'apps/excel/templates/CreditAtlas-Portfolio-Input.xlsx'
    with urlopen(base+'/api/exposure-excel-template',timeout=180) as response:
        assert response.status==200 and 'no-store' in response.headers['Cache-Control']
        assert hashlib.sha256(response.read()).hexdigest()==sha256(template)
    with urlopen(base+'/api/exposure-excel-report?import_id='+source+'&currency=USD&dimension=region',timeout=240) as response:
        assert response.status==200 and 'spreadsheetml.sheet' in response.headers['Content-Type']
        assert 'no-store' in response.headers['Cache-Control']; workbook=response.read()
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
        manifest=ET.fromstring(archive.read('xl/workbook.xml'))
        assert len(manifest.findall('s:sheets/s:sheet',ns))==6
        summary=ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
        model=ET.fromstring(archive.read('xl/worksheets/sheet2.xml'))
        amount=Decimal(summary.find('.//s:c[@r="B7"]/s:v',ns).text)
        loss=Decimal(model.find('.//s:c[@r="G20"]/s:v',ns).text)
        assert amount==Decimal('915208989.12')
        assert abs(loss-Decimal('17313511.79897183'))<Decimal('.01')
        assert model.find('.//s:c[@r="G20"]/s:f',ns) is not None
    with urlopen(base+'/api/portfolio-reviews?source_import_id='+source,timeout=180) as response:
        records=json.load(response)['packages']
        assert any(r['id']=='portfolio-review-d865f99b6cf8' and r['evidence_current'] and r['status']=='draft' for r in records)
    receipt={'status':'PASS','completed_at':timestamp(),'source_import_id':source,
        'template_sha256':sha256(template),'workbook_sha256':hashlib.sha256(workbook).hexdigest(),
        'reported_amount_usd':str(amount),'adverse_research_el_usd':str(loss),
        'checks':['Live template byte parity','Private XLSX MIME/no-store','Six saved sheets',
            'Native source total','Adverse formula/cached result parity','Actual draft review remains current'],
        'visibility':'private','public_release_approved':False}
    output=root/'artifacts/private'/('excel-live-'+uuid.uuid4().hex[:12]+'.json'); write_new(output,receipt)
    print(json.dumps({'status':'PASS','receipt':str(output)},indent=2))
