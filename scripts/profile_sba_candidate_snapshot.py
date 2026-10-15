"""Bounded DuckDB whole-file profiling of separately acquired SBA raw snapshots."""
import argparse,csv,json
from pathlib import Path
from uuid import uuid4
import duckdb
from credit_atlas.workspace import sha256

ROOT=Path.cwd();parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path);args=parser.parse_args();folder=args.folder.resolve()
assert folder.is_relative_to(ROOT/'data/private/business-archive')
receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8-sig'));assert receipt['status']=='RAW_ACQUIRED_NEEDS_PROFILE' and len(receipt['files'])==6
out=ROOT/'artifacts/private'/('sba-candidate-profile-'+uuid4().hex[:12]);out.mkdir()
dictionary=json.loads((ROOT/'artifacts/private/business-sba-21c568f10f7d/dictionary.json').read_text())
profiles=[]
with duckdb.connect() as con:
    con.execute("SET memory_limit='256MB'");con.execute('SET threads=2');con.execute('SET temp_directory=?',[str(out/'spill')])
    for source in receipt['files']:
        path=folder/source['file'];assert sha256(path)==source['sha256']
        program='504' if '_504_' in path.name else '7A'
        with path.open(encoding='utf-8-sig',newline='') as stream:headers=next(csv.reader(stream))
        # Snapshot grain is raw records. Do not infer identity or remove duplicates.
        con.read_csv(str(path),header=True,all_varchar=True,parallel=False,sample_size=-1).create_view('native',replace=True)
        n=con.execute('SELECT COUNT(*) FROM native').fetchone()[0]
        snapshots=[{'raw':r[0],'parsed':str(r[1]) if r[1] else None,'records':r[2]} for r in con.execute("SELECT AsOfDate,COALESCE(TRY_CAST(NULLIF(TRIM(AsOfDate),'') AS DATE),CAST(TRY_STRPTIME(NULLIF(TRIM(AsOfDate),''),'%m/%d/%Y') AS DATE)),COUNT(*) FROM native GROUP BY ALL ORDER BY 1").fetchall()]
        statuses=[{'raw':r[0],'records':r[1]} for r in con.execute('SELECT LoanStatus,COUNT(*) FROM native GROUP BY ALL ORDER BY 1').fetchall()]
        programs=[{'raw':r[0],'records':r[1]} for r in con.execute('SELECT Program,COUNT(*) FROM native GROUP BY ALL ORDER BY 1').fetchall()]
        totals={}
        for field in ['GrossApproval','GrossChargeOffAmount']:
            known,blank,invalid,amount=con.execute(f'''SELECT COUNT(TRY_CAST(NULLIF(TRIM("{field}"),'') AS DECIMAL(38,18))),COUNT(*) FILTER(WHERE NULLIF(TRIM("{field}"),'') IS NULL),COUNT(*) FILTER(WHERE NULLIF(TRIM("{field}"),'') IS NOT NULL AND TRY_CAST("{field}" AS DECIMAL(38,18)) IS NULL),SUM(TRY_CAST(NULLIF(TRIM("{field}"),'') AS DECIMAL(38,18))) FROM native''').fetchone()
            totals[field]={'known_records':known,'blank_records':blank,'unparsed_nonblank_records':invalid,'sum_exact':str(amount) if amount is not None else None}
        profiles.append({'file':source['file'],'sha256':source['sha256'],'program':program,'records':n,'columns':len(headers),'headers':headers,'headers_match_existing_dictionary':headers==[r['field'] for r in dictionary[program]],'actual_snapshot_dates':snapshots,'source_status_counts':statuses,'source_program_counts':programs,'reported_amounts':totals})
        print(json.dumps({'file':source['file'],'records':n,'snapshot_dates':snapshots}),flush=True)
    con.execute('DROP VIEW native')
dates={s['parsed'] for p in profiles for s in p['actual_snapshot_dates']}
result={'status':'PROFILED','source_receipt_sha256':sha256(folder/'receipt.json'),'source_folder':str(folder.relative_to(ROOT)),'profiles':profiles,'total_source_records':sum(p['records'] for p in profiles),'actual_snapshot_dates':sorted(dates,key=lambda x:x or ''),'candidate_filename_date_matches_contents':dates=={'2026-03-31'},'added_to_frozen_business_case':False,'loan_identity_qualified':False,'loan_status_transitions_qualified':False,'fixed_horizon_PD_qualified':False,'publication_time_qualified':False,'method_sha256':sha256(Path(__file__)),'limitations':['Six separate source segments are records,not deduplicated loans/borrowers.','Amounts are source-reported approval/chargeoff scope,not current EAD.','AsOfDate,URL filename,HTTP Last-Modified and retrieval time have separate meanings.','Historical snapshot alone does not qualify loan identity,transitions,survival or PD.']}
(out/'profile.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'output':str(out),'status':'PROFILED','source_records':result['total_source_records'],'dates':result['actual_snapshot_dates']}))
