import json,uuid
from pathlib import Path
from credit_atlas.sovereign_defaults import build,scoped
from credit_atlas.workspace import sha256
root=Path.cwd();doc=build(root);out=root/'artifacts/private'/('sovereign-default-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
p=out/'profile.json';p.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
for year in ['2024','2025']:
    r=scoped(doc,{'year':year});print(year,r['actual_exact'],r['year_change_same_edition_exact'],r['edition_revision_same_year_exact'],r['country_panel'],r['source_summary_comparisons'])
(out/'receipt.json').write_text(json.dumps({'status':'PROFILE_BUILT','rows':sum(len(e['records']) for e in doc['editions']),
    'profile_sha256':sha256(p),'source_receipt_sha256':doc['source_receipt_sha256'],
    'source_summary_mismatches':sum(not x['matches_at_flat_precision'] for e in doc['editions'] for x in e['source_summary_comparisons']),
    'pd_lgd_calibrated':False,'macro_stress_linkage_qualified':False},indent=2),encoding='utf8')
print(out);print(sha256(p))
