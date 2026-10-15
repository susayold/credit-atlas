"""Entry-selection diagnostics, using only pre-outcome eligibility grouping."""
import argparse
import json
import uuid
from pathlib import Path
import duckdb
from .source import sha256,utc_now,write_json_new
from .cli import code_fingerprint

def create_attrition(db,sql_dir):
    n=db.execute('SELECT COUNT(*),COUNT(DISTINCT loan_id) FROM labels').fetchone()
    if n[0]!=n[1]: raise ValueError('Label keys not unique')
    d=db.execute('SELECT COUNT(*),COUNT(DISTINCT loan_id) FROM dim_loan').fetchone()
    if d[0]!=d[1] or d[0]!=n[0]: raise ValueError('Origination keys do not reconcile')
    if db.execute('SELECT COUNT(*) FROM labels ANTI JOIN dim_loan USING(loan_id)').fetchone()[0]:
        raise ValueError('Unmatched label loan')
    db.execute('CREATE TEMP TABLE attrition_features AS '+(sql_dir/'attrition_features.sql').read_text())
    totals=db.execute('SELECT feature,SUM(loans),SUM(observed_values+missing_values) FROM attrition_features GROUP BY 1').fetchall()
    if any(total!=n[0] or counts!=n[0] for _,total,counts in totals):
        raise ValueError('Feature denominators fail reconciliation')

def run(root,label_run):
    lm=json.loads((label_run/'run-complete.json').read_text())
    if lm.get('status')!='LABELS_DEVELOPMENT_COMPLETE': raise ValueError('Completed labels required')
    canonical=root/'artifacts/private'/lm['canonical_run']
    cm=json.loads((canonical/'run-complete.json').read_text())
    inputs={'labels':(label_run/'labels.parquet',lm),'dim_loan':(canonical/'dim_loan.parquet',cm)}
    destination=root/'artifacts/private'/('attrition-'+uuid.uuid4().hex[:12]);destination.mkdir()
    with duckdb.connect() as db:
        for name,(path,manifest) in inputs.items():
            if sha256(path)!=manifest['outputs_sha256'][path.name]: raise ValueError('Input changed')
            db.read_parquet(str(path)).create_view(name)
        create_attrition(db,root/'sql')
        db.table('attrition_features').write_parquet(str(destination/'feature_distributions.parquet'),compression='zstd')
        check=db.execute('SELECT feature,SUM(loans),SUM(missing_values) FROM attrition_features GROUP BY 1 ORDER BY 1').fetchall()
    write_json_new(destination/'run-complete.json',{'status':'ATTRITION_COMPLETE','completed_at':utc_now(),
        'label_run':label_run.name,'code_sha256':code_fingerprint(root),'visibility':'private',
        'public_release_approved':False,'grouping':'entry_eligibility_not_future_label_availability',
        'denominators':[{'feature':f,'loans':n,'missing':m} for f,n,m in check],
        'outputs_sha256':{'feature_distributions.parquet':sha256(destination/'feature_distributions.parquet')}})
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--label-run',type=Path,required=True)
    args=parser.parse_args();print(run(Path(__file__).resolve().parents[2],args.label_run.resolve()))
