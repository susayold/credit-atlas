import copy,json
from pathlib import Path
from types import SimpleNamespace
import pytest
from credit_atlas.retail_data_contract import report
from credit_atlas.workspace import sha256

ROOT=Path(__file__).resolve().parents[1];VIEW='suite-view-74e07524f6d0'

@pytest.fixture
def views(tmp_path):
    snapshot=json.loads((ROOT/f'artifacts/private/{VIEW}/snapshot.json').read_text())
    paths=[f'artifacts/private/{snapshot["retail"]["case_id"]}/{n}' for n in ['case-complete.json','quality.json','protocol.json','reconciliation.json']]+[f'data/private/public-suite/{snapshot["suite_id"]}/{n}' for n in ['uci-retail-receipt.json','uci-retail-metadata.json']]
    pins={}
    for p in paths:
        target=tmp_path/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes());pins[p]=sha256(target)
    anchor=tmp_path/f'artifacts/private/{VIEW}/view-complete.json';anchor.parent.mkdir(parents=True,exist_ok=True);anchor.write_text(json.dumps({'inputs_sha256':pins}))
    return SimpleNamespace(root=tmp_path,view=lambda _:copy.deepcopy(snapshot))

def test_aggregate_only_month_target_predictor_contract(views):
    r=report(views,{'view_id':VIEW})
    assert r['clients']==30000 and r['history_rows']==180000
    assert [m['reference_month'] for m in r['history_mapping']]==['2005-09','2005-08','2005-07','2005-06','2005-05','2005-04']
    assert r['history_mapping'][0]['status_field']=='PAY_0' and r['history_mapping'][1]['status_field']=='PAY_2'
    assert sum(f['predictor'] for f in r['feature_mapping'])==19
    assert r['target_counts']=={'0':23364,'1':6636}
    assert r['temporal_out_of_time'] is False and r['qualified_for_production'] is False
    assert not list(views.root.rglob('*.parquet')) and not list(views.root.rglob('*.csv'))
    unknown=[c for c in r['source_category_counts'] if c['field'].startswith('PAY_') and c['code'] in {'-2','0'}]
    assert len(unknown)==12 and not any(c['dictionary_qualified'] for c in unknown)
    assert r['negative_statement_cells_retained']==3932

def change(views,name,edit,pin=True):
    p=next(views.root.rglob(name));data=json.loads(p.read_text());edit(data);p.write_text(json.dumps(data))
    if pin:
        a=next(views.root.rglob('view-complete.json'));anchor=json.loads(a.read_text());anchor['inputs_sha256'][p.relative_to(views.root).as_posix()]=sha256(p);a.write_text(json.dumps(anchor))

@pytest.mark.parametrize('name,edit,match',[
 ('quality.json',lambda d:d.update(history_rows=179999),'population mismatch'),
 ('quality.json',lambda d:d['target_counts'].update({'1':6635}),'Target aggregate'),
 ('reconciliation.json',lambda d:d['differing_rows'].update(clients=1),'reconciliation'),
 ('protocol.json',lambda d:d['excluded_predictors'].remove('source_client_id'),'must not'),
 ('quality.json',lambda d:d['source_category_counts']['PAY_0'].update({'-2':0}),'category population')])
def test_inconsistent_aggregate_rejected(views,name,edit,match):
    change(views,name,edit)
    with pytest.raises(ValueError,match=match):report(views,{'view_id':VIEW})

def test_changed_receipt_not_reinterpreted(views):
    change(views,'quality.json',lambda d:d.update(clients=1),pin=False)
    with pytest.raises(ValueError,match='not pinned'):report(views,{'view_id':VIEW})

@pytest.mark.parametrize('query',[{}, {'view_id':VIEW,'partition':'final_test'},{'view_id':VIEW,'client_id':'1'}])
def test_no_client_or_partition_reads(views,query):
    with pytest.raises(ValueError):report(views,query)
