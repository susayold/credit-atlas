"""Independent Python CSV/Decimal replay of full separately acquired snapshot."""
import argparse,csv,json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
from credit_atlas.workspace import sha256

ROOT=Path.cwd();parser=argparse.ArgumentParser();parser.add_argument('profile',type=Path);args=parser.parse_args();profile_path=args.profile.resolve()
profile=json.loads(profile_path.read_text());folder=ROOT/profile['source_folder'];receipt=json.loads((folder/'receipt.json').read_text(encoding='utf-8-sig'))
assert sha256(folder/'receipt.json')==profile['source_receipt_sha256']
out=ROOT/'artifacts/private'/('sba-historical-audit-'+uuid4().hex[:12]);out.mkdir();checked=[]
for p in profile['profiles']:
    path=folder/p['file'];assert sha256(path)==p['sha256']
    n=0;dates=Counter();statuses=Counter();programs=Counter();totals={f:Decimal(0) for f in ['grossapproval','grosschargeoffamount']};known=Counter();blank=Counter()
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.reader(stream);headers=next(reader);positions={h.lower():i for i,h in enumerate(headers)}
        assert len(positions)==len(headers)==p['columns'] and headers==p['headers']
        for row in reader:
            assert len(row)==len(headers);n+=1
            dates[row[positions['asofdate']] or None]+=1;statuses[row[positions['loanstatus']] or None]+=1;programs[row[positions['program']] or None]+=1
            for field in totals:
                value=row[positions[field]].strip()
                if value:totals[field]+=Decimal(value);known[field]+=1
                else:blank[field]+=1
    assert n==p['records'] and dict(statuses)=={r['raw']:r['records'] for r in p['source_status_counts']} and dict(programs)=={r['raw']:r['records'] for r in p['source_program_counts']}
    assert dict(dates)=={r['raw']:r['records'] for r in p['actual_snapshot_dates']} and set(dates)=={'3/31/2026'}
    for field in totals:
        report=p['reported_amounts']['GrossApproval' if field=='grossapproval' else 'GrossChargeOffAmount']
        assert report['known_records']==known[field] and report['blank_records']==blank[field] and report['unparsed_nonblank_records']==0
        assert Decimal(report['sum_exact'])==totals[field]
    checked.append({'file':p['file'],'records':n,'sha256':p['sha256'],'status_buckets':len(statuses),'actual_date':'2026-03-31','numeric_amounts_exact':True})
    print(json.dumps({'file':p['file'],'records':n,'status':'PASS'}),flush=True)
assert sum(p['records'] for p in checked)==2174502 and profile['candidate_filename_date_matches_contents']
(out/'receipt.json').write_text(json.dumps({'status':'PASS','source_profile':str(profile_path.relative_to(ROOT)),'source_profile_sha256':sha256(profile_path),'source_receipt_sha256':profile['source_receipt_sha256'],'files':checked,'source_records':2174502,'snapshot_date':'2026-03-31','schema_columns':{'7A':43,'504':40},'loan_identity_qualified':False,'publication_time_qualified':False,'fixed_horizon_PD_qualified':False,'method_sha256':sha256(Path(__file__))},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','source_records':2174502}))
