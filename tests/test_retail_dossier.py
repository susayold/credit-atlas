import copy,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from credit_atlas.retail_dossier import report
from credit_atlas.workspace import sha256

ROOT=Path(__file__).resolve().parents[1];VIEW='suite-view-74e07524f6d0'
@pytest.fixture
def views(tmp_path):
    snap=json.loads((ROOT/f'artifacts/private/{VIEW}/snapshot.json').read_text());r=snap['retail']
    original=json.loads((ROOT/f'artifacts/private/{VIEW}/view-complete.json').read_text())
    # Copy only pinned JSON metadata; predictor/score/model weight files absent.
    paths=[p for p in original['inputs_sha256'] if p.endswith('.json') and not p.endswith('model.json') and not p.endswith('encoder.json') and any(tag in p for tag in ['retail-case-','retail-features-','retail-assessment-','retail-comparison-','retail-freeze-','retail-holdout-','uci-retail-'])]
    pins={}
    for p in paths:
        rel=p.replace('\\','/');target=tmp_path/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/rel).read_bytes());pins[rel]=sha256(target)
    anchor=tmp_path/f'artifacts/private/{VIEW}/view-complete.json';anchor.parent.mkdir(parents=True,exist_ok=True);anchor.write_text(json.dumps({'inputs_sha256':pins}))
    return SimpleNamespace(root=tmp_path,view=lambda _:copy.deepcopy(snap))

def test_metadata_only_dossier_and_real_stage_ids(views):
    r=report(views,{'view_id':VIEW})
    assert len(r['audit_trail'])==6 and r['audit_trail'][4]['artifact_id']==r['freeze_id'] and r['audit_trail'][5]['artifact_id']==r['holdout_id']
    assert r['model']['selected_model']=='boosting' and r['model']['selected_variant']=='raw'
    assert r['governance']['review_owner'] is None and r['governance']['authenticated_sign_off'] is False
    assert not r['governance']['opening_page_refits_or_rescores'] and not r['governance']['qualified_for_production']
    assert not list(views.root.rglob('*.parquet')) and not list(views.root.rglob('*.csv'))
    assert str(views.root) not in json.dumps(r)

def mutate(views,name,edit):
    candidates=list(views.root.rglob(name))
    p=next(p for p in candidates if 'retail-holdout-' in p.parent.name) if name=='access-start.json' else candidates[0]
    d=json.loads(p.read_text());edit(d);p.write_text(json.dumps(d));anchor=next(views.root.rglob('view-complete.json'));a=json.loads(anchor.read_text());a['inputs_sha256'][p.relative_to(views.root).as_posix()]=sha256(p);anchor.write_text(json.dumps(a))

def test_explicit_production_claim_rejected(views):
    mutate(views,'evaluation-complete.json',lambda d:d.update(qualified_for_production=True))
    with pytest.raises(ValueError,match='qualification'):report(views,{'view_id':VIEW})

def test_final_evaluation_before_freeze_rejected(views):
    mutate(views,'access-start.json',lambda d:d.update(started_at='2020-01-01T00:00:00+00:00'))
    with pytest.raises(ValueError,match='chronology'):report(views,{'view_id':VIEW})

def test_metrics_changed_without_new_suite_projection_rejected(views):
    mutate(views,'holdout-metrics.json',lambda d:d.update(roc_auc=.99))
    with pytest.raises(ValueError,match='metrics'):report(views,{'view_id':VIEW})

@pytest.mark.parametrize('query',[{}, {'view_id':VIEW,'client_id':'1'},{'view_id':VIEW,'rescore':'true'}])
def test_bounded_aggregate_query(views,query):
    with pytest.raises(ValueError):report(views,query)
