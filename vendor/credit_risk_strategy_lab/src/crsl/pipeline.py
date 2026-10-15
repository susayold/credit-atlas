"""One-command development foundation. Success never implies full research release."""
import argparse
import json
import uuid
from pathlib import Path
from . import canonical,labels,audit,portfolio,splits,attrition,metrics,vintage,verify_vintage
from .source import utc_now,write_json_new,sha256
from .cli import code_fingerprint

def verified_vintage(root,canonical_run):
    path=vintage.run(root,canonical_run)
    verification=verify_vintage.verify(root,path)
    if verification.get('status')!='PASS':
        raise ValueError('Vintage independent verification failed')
    write_json_new(path/'verification.json',verification)
    return path


STAGES=(('canonical',canonical.run,'source'),('labels',labels.run,'canonical'),
        ('audit',audit.run,'canonical'),('portfolio',portfolio.run,'canonical'),
        ('splits',splits.run,'labels'),('attrition',attrition.run,'labels'),
        ('metrics',metrics.run,'portfolio'),('vintage',verified_vintage,'canonical'))

def run(root,source_run,stages=None):
    root=root.resolve();source_run=source_run.resolve()
    manifest=json.loads((source_run/'run-complete.json').read_text())
    if manifest.get('data_kind')!='annual_sample' or manifest.get('result_status')!='PROFILED':
        raise ValueError('Completed annual source inspection required')
    output=root/'artifacts/private'/('pipeline-'+uuid.uuid4().hex[:12]);output.mkdir(parents=True)
    start={'started_at':utc_now(),'source_run':str(source_run),
           'source_manifest_sha256':sha256(source_run/'run-complete.json'),
           'code_sha256':code_fingerprint(root),'visibility':'private','research_ready':False,
           'public_release_approved':False}
    write_json_new(output/'run-start.json',start)
    paths={'source':source_run};receipts=[]
    for name,operation,dependency in STAGES if stages is None else stages:
        try:
            path=operation(root,paths[dependency])
            paths[name]=path
            receipt={'stage':name,'status':'PASS','output_run':path.name,'completed_at':utc_now()}
            if name=='vintage':
                receipt['verification_sha256']=sha256(path/'verification.json')
                receipt['output_manifest_sha256']=sha256(path/'run-complete.json')
            receipts.append(receipt)
            write_json_new(output/(name+'.json'),receipt)
            print(f'{name}: PASS ({path.name})',flush=True)
        except Exception as error:
            write_json_new(output/'run-failed.json',{'failed_at':utc_now(),'failed_stage':name,
              'exception_type':type(error).__name__,'completed_stages':receipts,'research_ready':False})
            raise
    start.update(completed_at=utc_now(),status='DEVELOPMENT_PIPELINE_COMPLETE',stages=receipts,
      note='Ingestion was an input; multi-vintage/model/website/workbook gates are not completed by this command.')
    write_json_new(output/'run-complete.json',start)
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-run',type=Path,required=True)
    args=parser.parse_args();print(run(Path(__file__).resolve().parents[2],args.source_run))
