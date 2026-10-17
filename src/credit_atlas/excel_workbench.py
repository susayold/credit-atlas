"""Local XLSX intake and verified native-currency report generation."""
import json
import os
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from .excel_workspace import decode_upload,import_workbook
from .workspace import sha256,write_new,read_json,timestamp,contained


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
        source_provenance=self.source_provenance(source,inventory,query)
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
        return {'inventory':inventory,'source_provenance':source_provenance,'scenario':scenario,'ecl':ecl,'tail':tail,'review':review}

    def source_provenance(self,source,inventory,query):
        receipt,verified_report,receipt_digest=self.service.exposure_views.evidence(source)
        folder=contained(self.root,'artifacts/private/'+source)
        metadata_path=folder/'metadata.json'
        metadata=read_json(metadata_path)
        outputs=receipt.get('outputs_sha256',{})
        required={'source.csv','metadata.json','positions.parquet','report.json'}
        if (receipt.get('import_id')!=source or receipt.get('visibility')!='private'
                or receipt.get('public_release_approved') is not False or set(outputs)!=required
                or sha256(metadata_path)!=outputs.get('metadata.json')
                or sha256(folder/'import-complete.json')!=receipt_digest
                or metadata.get('source_namespace')!=inventory.get('source_namespace')
                or metadata.get('dataset_kind')!=inventory.get('dataset_kind')
                or metadata.get('amount_kind')!=inventory.get('amount_kind')):
            raise ValueError('Excel provenance does not match verified exposure source')
        lineage=[]
        for row in metadata.get('source_lineage',[]):
            path=row.get('path'); digest=row.get('sha256')
            if not isinstance(path,str) or not isinstance(digest,str): raise ValueError('Invalid source lineage for Excel provenance')
            normalized=path.replace('\\','/')
            if normalized.startswith('/') or ':' in normalized.split('/')[0] or '..' in normalized.split('/'):
                raise ValueError('Absolute or escaping lineage path cannot be exported')
            lineage.append({'path':normalized,'sha256':digest})
        lineage.sort(key=lambda row:row['path'])
        is_freddie='freddie' in metadata['source_namespace'].casefold() and '2012' in metadata['source_namespace']
        source_observation=metadata['dataset_kind']=='source_observation'
        if is_freddie:
            warning=('Freddie Mac 2012 annual sample: reported raw UPB is descriptive sample data. It does not prove assets owned by a lender, borrower-level portfolio exposure, EAD, empirical expected loss, or a securitization-pool relationship. Freddie publication authenticity, applicable terms, and use rights remain separate qualifications.')
        elif source_observation:
            warning=('Source-observation amounts describe the selected source records. They do not by themselves prove ownership, borrower linkage, EAD, or empirical expected loss.')
        else:
            warning=('Declared portfolio data are user-supplied inputs; the import does not independently authenticate ownership, borrower linkage, EAD, or accounting treatment.')
        return {'import_id':source,'receipt_sha256':receipt_digest,'completed_at':receipt.get('completed_at'),
            'metadata_sha256':outputs['metadata.json'],'source_csv_sha256':outputs['source.csv'],
            'positions_sha256':outputs['positions.parquet'],'import_report_sha256':outputs['report.json'],
            'dataset_kind':metadata['dataset_kind'],'amount_kind':metadata['amount_kind'],
            'source_namespace':metadata['source_namespace'],'source_description':metadata['source_description'],
            'as_of':metadata['as_of'],'date_grain':metadata['date_grain'],'currency_scope':query.get('currency','all'),
            'dimension':query.get('dimension','region'),'record_count':inventory['records'],
            'all_currency_record_count':verified_report['records'],
            'risk_contract':metadata['risk_contract'],'ownership_certified':verified_report['contract']['ownership_certified'],
            'amount_is_ead':verified_report['contract']['amount_is_ead'],'visibility':'private',
            'public_release_approved':False,'scope_warning':warning,'source_lineage':lineage}

    def export_provenance(self,report):
        if not isinstance(report,dict): raise ValueError('P4 report payload required for provenance')
        if report.get('opening_import_id') and report.get('closing_import_id'):
            roles={'opening':report['opening_import_id'],'closing':report['closing_import_id']}
        else:
            source=report.get('source_import_id') or report.get('import_id')
            if not isinstance(source,str): raise ValueError('P4 report is missing a bound source import')
            roles={'primary':source}
        sources=[]
        for role,identifier in roles.items():
            inventory=self.service.exposure_views.report({'import_id':identifier})
            sources.append({'role':role,**self.source_provenance(identifier,inventory,{})})

        artifacts=[]
        receipt_specs=(('scenario_id','scenario','scenario-complete.json'),('ecl_id','ecl','ecl-complete.json'),
            ('tail_id','tail','tail-complete.json'),('convergence_id','convergence','convergence-complete.json'),
            ('movement_id','movement','movement-complete.json'))
        for key,kind,receipt_name in receipt_specs:
            identifier=report.get(key)
            if not isinstance(identifier,str): continue
            receipt_path=contained(self.root,'artifacts/private/'+identifier+'/'+receipt_name)
            receipt=read_json(receipt_path)
            if (receipt.get(key)!=identifier or receipt.get('visibility')!='private'
                    or receipt.get('public_release_approved') is not False):
                raise ValueError('P4 derived export receipt is not private/source-bound')
            bound=[receipt[k] for k in ('opening_import_id','closing_import_id') if k in receipt]
            if not bound and isinstance(receipt.get('source_import_id'),str): bound=[receipt['source_import_id']]
            if not bound and kind=='convergence' and isinstance(report.get('source_import_id'),str):
                bound=[report['source_import_id']]
            if sorted(bound)!=sorted(roles.values()): raise ValueError('P4 derived export inputs differ from source provenance')
            artifacts.append({'artifact_type':kind,'artifact_id':identifier,'receipt_file':receipt_name,
                'receipt_sha256':sha256(receipt_path),'source_import_ids':bound,'status':receipt.get('status')})
        if isinstance(report.get('id'),str) and report['id'].startswith('portfolio-review-'):
            artifacts.append({'artifact_type':'portfolio_review','artifact_id':report['id'],
                'revision':report.get('revision'),'receipt_sha256':None,
                'evidence_snapshot_count':len(report.get('snapshots',{}))})
        return {'schema_version':1,'generated_at':timestamp(),'visibility':'private','public_release_approved':False,
            'report_filters':report.get('filters',{}) or ({'currency':report['currency']} if isinstance(report.get('currency'),str) else {}),
            'source_scope_note':'Source imports describe the full verified input; report_filters records the downloaded subset when the report is filtered.',
            'source_imports':sources,'derived_artifacts':artifacts,
            'portability_note':'Relative paths and SHA-256 hashes are private-workspace lineage references; they do not authenticate publisher identity, ownership or usage rights.'}

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
