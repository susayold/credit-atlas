from pathlib import Path
import uuid,json
from credit_atlas.absee_profile import report
from credit_atlas.workspace import sha256
root=Path.cwd();r=report(root)
out=root/'artifacts/private'/('absee-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
(out/'profile.json').write_text(json.dumps(r,indent=2),encoding='utf8')
checks={'row_counts':all(p['rows']==p['parquet_declared_rows'] for p in r['periods']),
        'nonempty_keys':all(p['unique_keys']>0 for p in r['periods']),
        'no_duplicate_keys':all(p['duplicate_key_rows']==0 for p in r['periods']),
        'dates_numeric_valid':all(not p['invalid_by_field'] for p in r['periods'])}
(out/'receipt.json').write_text(json.dumps({'status':'PASS' if all(checks.values()) else 'ISSUES_FOUND',
    'checks':checks,'profile_sha256':sha256(out/'profile.json'),'rows':r['total_rows'],'periods':r['selected_periods'],
    'source_fidelity_verified':False,'model_ready':False},indent=2),encoding='utf8')
print(out);print(json.dumps(checks));print(r['total_rows'])
