import json
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import credit_atlas.retail_explanations as base
import credit_atlas.retail_cohort_explanations as cohort
import credit_atlas.retail_comparison as comparison
import credit_atlas.retail_freeze as freeze
from credit_atlas.retail_explanation_views import RetailExplanationViews
from credit_atlas.retail_cohort_explanation_views import RetailCohortExplanationViews
from credit_atlas.workspace import sha256

ROOT=Path.cwd();out=ROOT/'artifacts/private'/('explanations-saved-probe-'+uuid4().hex[:12]);out.mkdir()
ledger=ROOT/'artifacts/private/retail-holdout-access.sqlite';before=sha256(ledger);calls=[]
def forbidden(*a,**kw):calls.append('forbidden');raise AssertionError('Actual inference/deep replay attempted')
scope={'freeze_id':'retail-freeze-3dc86f5afe01','explanations_id':'retail-explanations-84b3ac3bab6e'}
with ExitStack() as stack:
    for module,name in [(base,'predict_json'),(base,'verify'),(base,'calculate'),(cohort,'verify'),(cohort,'calculate'),(comparison,'verify_assessment'),(freeze,'verify_freeze')]:stack.enter_context(patch.object(module,name,forbidden))
    view=RetailExplanationViews(ROOT);report=view.report(scope)
    assert report['local_case_count']==12
    clients=RetailCohortExplanationViews(ROOT);q={**scope,'cohort_id':'retail-cohort-explanations-02487bb9d1a2'}
    seen=set();pages=0
    for offset in range(0,4499,50):
        r=clients.clients({**q,'offset':str(offset),'limit':'50'});pages+=1
        assert r['total']==4499 and not seen&{c['client_token'] for c in r['clients']}
        seen.update(c['client_token'] for c in r['clients'])
    assert len(seen)==4499
    token=next(iter(seen));r=clients.report({**q,'client_token':token});assert len(r['client']['contributions'])==4
    assert clients.clients({**q,'q':token})['total']==1
assert not calls and sha256(ledger)==before
(out/'receipt.json').write_text(json.dumps({'status':'PASS','forbidden_calls':0,'clients':4499,'pages':pages,'local_cases':12,'exact_token_search':True,'ledger_unchanged':True,'saved_verifier_sha256':sha256(ROOT/'src/credit_atlas/retail_explanations_saved.py'),'base_serving_sha256':sha256(ROOT/'src/credit_atlas/retail_explanation_views.py'),'cohort_serving_sha256':sha256(ROOT/'src/credit_atlas/retail_cohort_explanation_views.py'),'script_sha256':sha256(Path(__file__))},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','output':str(out),'clients':4499,'forbidden_calls':0}))
