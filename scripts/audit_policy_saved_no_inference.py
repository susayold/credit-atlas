import json,shutil
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from credit_atlas.workspace import sha256
from credit_atlas.retail_policy_views import RetailPolicyViews
import credit_atlas.retail_comparison as comparison
import credit_atlas.retail_assessment as assessment
import credit_atlas.retail_freeze as freeze
import credit_atlas.retail_policy as legacy

ROOT=Path.cwd();out=ROOT/'artifacts/private'/('policy-saved-no-inference-'+uuid4().hex[:12]);out.mkdir();store=out/'policies';store.mkdir()
ID='retail-policy-bd4b8623de28';FREEZE='retail-freeze-3dc86f5afe01'
source=ROOT/'artifacts/private'/ID;before={p.name:sha256(p) for p in source.iterdir() if p.is_file()}
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';ledger_before=sha256(ledger)
shutil.copytree(source,store/ID)
def forbidden(*args,**kwargs):raise AssertionError('Actual model inference/refit verifier was called')
with patch.object(comparison,'predict_json',forbidden),patch.object(assessment,'predict_json',forbidden),patch.object(assessment,'run_assessment',forbidden),patch.object(freeze,'verify_freeze',forbidden),patch.object(legacy,'verify_freeze',forbidden):
    views=RetailPolicyViews(ROOT,storage_root=store);r=views.report({'policy_id':ID,'freeze_id':FREEZE})
    assert {k:v for k,v in r.items() if k not in ['policy_id','visibility','public_release_approved']}==json.loads((source/'report.json').read_text())
    plan=r['assumptions'];query={'policy_id':ID,'freeze_id':FREEZE,'lower_threshold':'0.1','upper_threshold':'0.3','review_capacity':'3000',**{a+'_'+key:value for a,row in plan['cost_matrix'].items() for key,value in row.items()}}
    preview=views.preview(query);case=preview['cases'][-1]
    assert case['review_records']==2277 and case['review_capacity_exceeded'] is False and case['review_overflow_records']==0
    saved=views.save(preview['assumptions']);assert saved['policy_id']!=ID
    reopened=RetailPolicyViews(ROOT,storage_root=store).report({'policy_id':saved['policy_id'],'freeze_id':FREEZE})
    assert reopened['assumptions']==preview['assumptions'] and reopened['cases']==preview['cases']
    assert {p['policy_id'] for p in views.catalog(FREEZE)['policies']}=={ID,saved['policy_id']}
    receipt=json.loads((store/saved['policy_id']/'policy-complete.json').read_text());assert receipt['actual_model_inference_performed'] is False
assert sha256(ledger)==ledger_before
assert before=={p.name:sha256(p) for p in source.iterdir() if p.is_file()}
(out/'receipt.json').write_text(json.dumps({'status':'PASS','original_policy':ID,'qa_saved_policy':saved['policy_id'],'qa_storage':str(store.relative_to(ROOT)),'report_preview_save_reopen_catalog':True,'forbidden_inference_refit_verifiers_blocked':True,'original_policy_unchanged':True,'ledger_unchanged':True,'saved_helper_sha256':sha256(ROOT/'src/credit_atlas/retail_policy_saved.py'),'serving_sha256':sha256(ROOT/'src/credit_atlas/retail_policy_views.py'),'method_sha256':sha256(Path(__file__))},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'status':'PASS','actual_inference_calls':0}))
