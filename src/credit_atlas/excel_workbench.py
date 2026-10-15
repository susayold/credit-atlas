"""Local XLSX intake and verified native-currency report generation."""
import json
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from .excel_workspace import decode_upload,import_workbook
from .workspace import sha256,write_new,read_json,timestamp


class ExcelWorkbench:
    def __init__(self,service):
        self.service=service; self.root=service.root; self.lock=threading.RLock(); self.cache={}
        self.builder=self.root/'apps/excel/build_workbook.mjs'
        self.node=Path(os.environ.get('CREDIT_ATLAS_NODE',str(Path(sys.base_prefix).parent/'node/bin/node.exe')))
        self.template_file=self.root/'apps/excel/templates/CreditAtlas-Portfolio-Input.xlsx'
        self.methods={str(p):sha256(p) for p in (Path(__file__),Path(__file__).with_name('excel_workspace.py'),self.builder) if p.is_file()}
        self.template_hash=sha256(self.template_file) if self.template_file.exists() else None

    def guard(self):
        if not self.builder.is_file(): raise ValueError('Excel authoring builder unavailable')
        if any(sha256(Path(p))!=h for p,h in self.methods.items()): raise ValueError('Excel methods changed; restart required')

    def template(self):
        self.guard()
        if self.template_hash is None or sha256(self.template_file)!=self.template_hash: raise ValueError('Verified input template unavailable')
        return self.template_file.read_bytes()

    def upload(self,payload):
        self.guard(); result=import_workbook(self.root,decode_upload(payload)); self.guard(); return result

    def payload(self,query):
        inventory=self.service.exposure_views.report(query)
        if len(inventory['currencies'])!=1: raise ValueError('Choose one native currency before exporting an Excel workbook')
        currency=inventory['currencies'][0]['currency']; source=inventory['import_id']; selected={'source_import_id':source,'currency':currency}
        catalogs=[self.service.exposure_scenario_views.catalog(source)['scenario_sets'],self.service.exposure_ecl_views.catalog(source)['ecl_studies'],self.service.exposure_tail_views.catalog(source)['tail_studies']]
        scenario=self.service.exposure_scenario_views.report({**selected,'scenario_id':catalogs[0][0]['scenario_id'],'dimension':'segment'}) if catalogs[0] else None
        ecl=self.service.exposure_ecl_views.report({**selected,'ecl_id':catalogs[1][0]['ecl_id'],'dimension':'stage'}) if catalogs[1] else None
        tail=self.service.exposure_tail_views.report({**selected,'tail_id':catalogs[2][0]['tail_id']}) if catalogs[2] else None
        reviews=self.service.portfolio_reviews.list(source)['packages']
        review=None
        for record in sorted(reviews,key=lambda r:r['updated_at'],reverse=True):
            if not record['evidence_current']: continue
            candidate=self.service.portfolio_reviews.report(source,record['id'])
            if candidate['currency']==currency:
                review=candidate; break
        return {'inventory':inventory,'scenario':scenario,'ecl':ecl,'tail':tail,'review':review}

    def report(self,query):
        self.guard()
        if set(query)-{'import_id','currency','dimension'} or 'import_id' not in query: raise ValueError('Excel report requires import_id and native scope')
        with self.lock:
            data=self.payload(query); key=json.dumps(data,sort_keys=True)
            if key in self.cache:
                path,digest=self.cache[key]
                if sha256(path)!=digest: raise ValueError('Excel export changed')
                return path.read_bytes()
            folder=self.root/'artifacts/private'/('excel-export-'+uuid.uuid4().hex[:12]); folder.mkdir()
            write_new(folder/'input.json',data); path=folder/'portfolio.xlsx'
            if not self.node.exists(): raise ValueError('Bundled Excel authoring runtime unavailable')
            subprocess.run([str(self.node),str(self.builder),'report',str(folder/'input.json'),str(path)],cwd=self.root,
                check=True,capture_output=True,timeout=180)
            self.guard()
            if data!=self.payload(query): raise ValueError('Excel source evidence changed during export')
            digest=sha256(path)
            write_new(folder/'excel-complete.json',{'status':'VERIFIED_PRIVATE_XLSX_EXPORT','import_id':query['import_id'],'filters':data['inventory']['filters'],
                'methods':self.methods,'input_sha256':sha256(folder/'input.json'),'workbook_sha256':digest,'completed_at':timestamp(),
                'visibility':'private','public_release_approved':False})
            self.cache[key]=(path,digest); return path.read_bytes()
