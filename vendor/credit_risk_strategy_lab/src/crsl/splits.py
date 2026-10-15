"""Fail-closed development partition audit; cannot approve missing future vintages."""
from datetime import date
from collections import Counter

ROLES=('train','calibration','validation','test')

def split_records(records,config):
    years={role:set(config[role+'_years']) for role in ROLES}
    all_years=[y for role in ROLES for y in years[role]]
    if len(set(all_years))!=len(all_years): raise ValueError('Overlapping origination years')
    if any(not years[r] for r in ROLES): raise ValueError('Each role requires vintage years')
    for earlier,later in zip(ROLES,ROLES[1:]):
        if max(years[earlier])>=min(years[later]): raise ValueError('Partitions must be chronological')
    cutoffs={'train':date.fromisoformat(config['train_fit_month']),
             'calibration':date.fromisoformat(config['calibration_fit_month']),
             'validation':date.fromisoformat(config['selection_freeze_month'])}
    if not cutoffs['train']<cutoffs['calibration']<cutoffs['validation']:
        raise ValueError('Fitting/selection dates must be chronological')
    seen=set(); output=[]; counts=Counter(); exclusions=Counter(); observed_years=set()
    for row in records:
        identity=row['loan_id']
        if identity in seen: raise ValueError('Loan appears more than once in origination partitions')
        seen.add(identity); observed_years.add(row['origination_year'])
        role=next((r for r in ROLES if row['origination_year'] in years[r]),'unused')
        reason='included'
        target=row['target']
        if role=='unused': reason='unused_vintage'
        elif target not in (0,1) or target is None: reason='unavailable_label'
        elif row['label_known_month'] is None: reason='missing_label_time'
        elif role in cutoffs and row['label_known_month']>=cutoffs[role]: reason='label_not_mature_before_fit'
        elif role!='train':
            scoring_cutoff={'calibration':cutoffs['train'],'validation':cutoffs['calibration'],'test':cutoffs['validation']}[role]
            if row['landmark']<scoring_cutoff: reason='scoring_before_upstream_fit'
        output.append({'loan_id':identity,'partition':role,'reason':reason,
                       'included':reason=='included','test_locked':role=='test'})
        if reason=='included': counts[(role,int(target))]+=1
        else: exclusions[(role,reason)]+=1
    missing=sorted(set(all_years)-observed_years)
    support={r:{'positive':counts[(r,1)],'negative':counts[(r,0)]} for r in ROLES}
    failures=[]
    if missing: failures.append('missing_required_vintages')
    if any(s['positive']<config['minimum_positive_per_partition'] or
           s['negative']<config['minimum_negative_per_partition'] for s in support.values()):
        failures.append('insufficient_class_support')
    if config.get('status')!='approved': failures.append('protocol_not_approved')
    if config.get('claim')!='retrospective_temporal_not_strict_pit':
        raise ValueError('Latest-release pipeline cannot certify strict historical PIT')
    return output,{'support':support,'missing_years':missing,'blocking_reasons':failures,
                   'training_ready':not failures,'excluded':[{'partition':r,'reason':s,'loans':n} for (r,s),n in sorted(exclusions.items())]}

def run(root,label_run):
    import json
    import uuid
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq
    from .source import sha256,utc_now,write_json_new
    from .cli import code_fingerprint
    source=json.loads((label_run/'run-complete.json').read_text())
    if source.get('status')!='LABELS_DEVELOPMENT_COMPLETE': raise ValueError('Completed label run required')
    path=label_run/'labels.parquet'
    if sha256(path)!=source['outputs_sha256'][path.name]: raise ValueError('Label file changed')
    config=json.loads((root/'configs/split.json').read_text())
    with duckdb.connect() as db:
        records=db.read_parquet(str(path)).project('loan_id,origination_year,target,label_known_month,landmark').arrow().read_all().to_pylist()
    assignments,audit=split_records(records,config)
    destination=root/'artifacts/private'/('splits-'+uuid.uuid4().hex[:12]);destination.mkdir()
    pq.write_table(pa.Table.from_pylist(assignments),destination/'split_manifest.parquet',compression='zstd')
    write_json_new(destination/'audit.json',audit)
    write_json_new(destination/'run-complete.json',{
      'completed_at':utc_now(),'status':'SPLIT_AUDIT_COMPLETE','label_run':label_run.name,
      'code_sha256':code_fingerprint(root),'labels_sha256':sha256(path),'config':config,
      'visibility':'private','public_release_approved':False,'training_ready':audit['training_ready'],
      'outputs_sha256':{p.name:sha256(p) for p in destination.iterdir()}})
    return destination

if __name__=='__main__':
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-run',type=Path,required=True)
    args=parser.parse_args()
    print(run(Path(__file__).resolve().parents[2],args.label_run.resolve()))
