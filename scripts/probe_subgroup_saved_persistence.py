import json
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from credit_atlas.workspace import sha256
from credit_atlas.retail_subgroup_views import RetailSubgroupViews
import credit_atlas.retail_assessment as assessment
import credit_atlas.retail_comparison as comparison
import credit_atlas.retail_freeze as freeze
import credit_atlas.retail_policy as policy
import credit_atlas.retail_subgroups as legacy

ROOT=Path.cwd();out=ROOT/'artifacts/private'/('subgroup-saved-persistence-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger)
source=ROOT/'artifacts/private/retail-subgroups-3cf671cf3152';source_hashes={p.name:sha256(p) for p in source.iterdir() if p.is_file()}
plan=json.loads((source/'assumptions.json').read_text());expected=json.loads((source/'report.json').read_text());calls=[]
def forbidden(*args,**kwargs):calls.append('forbidden');raise AssertionError('Inference/refit attempted')
with ExitStack() as stack:
    for module,name in [(assessment,'predict_json'),(assessment,'run_assessment'),(comparison,'predict_json'),(comparison,'verify_assessment'),(freeze,'verify_assessment'),(freeze,'verify_freeze'),(freeze,'verify_comparison'),(policy,'verify_freeze'),(legacy,'verify_policy')]:stack.enter_context(patch.object(module,name,forbidden))
    view=RetailSubgroupViews(ROOT,storage_root=out/'qa-subgroups');created=view.save(plan)
    reopened=RetailSubgroupViews(ROOT,storage_root=out/'qa-subgroups')
    _,_,actual=__import__('credit_atlas.retail_subgroups_saved',fromlist=['verify_saved_subgroups']).verify_saved_subgroups(ROOT,created['subgroups_id'],out/'qa-subgroups')
    assert actual==expected
    catalog=reopened.catalog({k:plan[k] for k in ['policy_id','freeze_id']});assert len(catalog['studies'])==1
    for dimension in plan['dimensions']:
        result=reopened.report({'policy_id':plan['policy_id'],'freeze_id':plan['freeze_id'],'subgroups_id':created['subgroups_id'],'dimension':dimension})
        assert result['groups']==[r for r in expected['groups'] if r['dimension']==dimension]
assert not calls and sha256(ledger)==before
assert source_hashes=={p.name:sha256(p) for p in source.iterdir() if p.is_file()}
(out/'receipt.json').write_text(json.dumps({'status':'PASS','source_study_unchanged':True,'qa_storage_only':True,'save_reopen_catalog_dimensions':4,'full_report_equal':True,'forbidden_calls':0,'ledger_unchanged':True,'saved_helper_sha256':sha256(ROOT/'src/credit_atlas/retail_subgroups_saved.py'),'serving_sha256':sha256(ROOT/'src/credit_atlas/retail_subgroup_views.py'),'script_sha256':sha256(Path(__file__))},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','output':str(out),'forbidden_calls':0}))
