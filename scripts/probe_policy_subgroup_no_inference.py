"""Real browser policy/subgroup workflow under explicit inference tripwires."""
import importlib.util,json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import credit_atlas.retail_assessment as assessment
import credit_atlas.retail_comparison as comparison
import credit_atlas.retail_freeze as freeze
import credit_atlas.retail_policy as policy
import credit_atlas.retail_subgroups as groups
from credit_atlas.retail_subgroup_views import RetailSubgroupViews
from credit_atlas.workspace import sha256

ROOT=Path.cwd();calls=[]
def forbidden(*args,**kwargs):
    calls.append('forbidden_inference_or_deep_verifier')
    raise AssertionError('Inference/refit/deep model verifier called by serving workflow')
with ExitStack() as stack:
    for module,name in [(assessment,'predict_json'),(assessment,'run_assessment'),(comparison,'predict_json'),(comparison,'verify_assessment'),(freeze,'verify_assessment'),(freeze,'verify_freeze'),(freeze,'verify_comparison'),(policy,'verify_freeze'),(groups,'verify_policy')]:
        stack.enter_context(patch.object(module,name,forbidden))
    views=RetailSubgroupViews(ROOT)
    scope={'policy_id':'retail-policy-bd4b8623de28','freeze_id':'retail-freeze-3dc86f5afe01'}
    catalog=views.catalog(scope);assert any(s['subgroups_id']=='retail-subgroups-3cf671cf3152' for s in catalog['studies'])
    for dimension in ['sex','education','marriage','age_band']:
        report=views.report({**scope,'subgroups_id':'retail-subgroups-3cf671cf3152','dimension':dimension})
        assert sum(r['records'] for r in report['groups'])==4499 and sum(r['events'] for r in report['groups'])==995
    spec=importlib.util.spec_from_file_location('qa_policy_browser',ROOT/'scripts/browser_retail_policy_qa.py');qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
    result=qa.run(ROOT)
assert not calls
out=Path(result['directory']);receipt=json.loads((out/'receipt.json').read_text())
receipt.update({'entire_policy_subgroup_inference_tripwires':True,'forbidden_calls':0,'real_subgroup_dimensions_checked':4,'saved_subgroups_helper_sha256':sha256(ROOT/'src/credit_atlas/retail_subgroups_saved.py'),'saved_policy_helper_sha256':sha256(ROOT/'src/credit_atlas/retail_policy_saved.py'),'subgroup_serving_sha256':sha256(ROOT/'src/credit_atlas/retail_subgroup_views.py'),'policy_serving_sha256':sha256(ROOT/'src/credit_atlas/retail_policy_views.py'),'probe_sha256':sha256(Path(__file__)),'app_js_sha256':sha256(ROOT/'apps/web/app.js'),'server_sha256':sha256(ROOT/'src/credit_atlas/server.py')})
(out/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','output':str(out),'forbidden_calls':0,'browser_checks':result['checks']}))
