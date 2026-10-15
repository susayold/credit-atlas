"""Subgroup verification from saved predictions and validation-only demographics."""
import uuid
from pathlib import Path
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from .retail_policy_saved import verify_saved,storage
from .retail_policy_views import lineage_pins,pinned_scores
from .retail_subgroups import FLAGS,ID,calculate,guard,methods,validate
from .workspace import contained,read_json,sha256,timestamp,write_new

# The prior serving adapter used deep inference for verification. Accept that
# exact historical adapter fingerprint only; numerical engines remain pinned,
# and all source rows/report values are still fully replayed below.
LEGACY_POLICY_SERVING_SHA256='7d67bd852493776cfb1e3c758eb6bd0d720bd319b9a7cc07b48f1e25d86a448a'

def supported_methods(value):
    current=methods()
    return value==current or value=={**current,'retail_policy_views':LEGACY_POLICY_SERVING_SHA256}


def source_saved(root,plan,policy_storage=None):
    folder,receipt,report=verify_saved(root,plan['policy_id'],policy_storage)
    if report['freeze_id']!=plan['freeze_id']:raise ValueError('Subgroup frozen-model mismatch')
    case=next((r for r in report['cases'] if r['id']==plan['case_id']),None)
    if case is None:raise ValueError('Policy case unavailable')
    pins=lineage_pins(root,report)
    pins.update({str((folder/n).relative_to(root)):h for n,h in receipt['outputs_sha256'].items()})
    pins[str((folder/'policy-complete.json').relative_to(root))]=sha256(folder/'policy-complete.json')
    scores=pinned_scores(root,report);clients=contained(root,'artifacts/private/'+report['case_id']+'/clients.parquet')
    with duckdb.connect(config={'threads':2,'memory_limit':'256MB'}) as db:
        db.register('validation_scores',pa.Table.from_pylist(scores))
        # Project excluded demographic audit columns only, retaining exactly the
        # saved validation identities. No LIMIT/BILL/PAY predictor columns.
        rows=db.execute('SELECT s.*,c.SEX,c.EDUCATION,c.MARRIAGE,c.AGE FROM validation_scores s JOIN read_parquet(?) c USING(source_client_id) ORDER BY s.source_client_id',[str(clients)]).to_arrow_table().to_pylist()
    if len(rows)!=len(scores) or {(r['source_client_id'],r['target'],r['probability']) for r in rows}!={(r['source_client_id'],r['target'],r['probability']) for r in scores}:raise ValueError('Validation demographic join changed population')
    guard(root,pins);return rows,case['rule'],pins


def verify_saved_subgroups(root,identifier,storage_root=None,policy_storage=None):
    if not isinstance(identifier,str) or not ID.fullmatch(identifier):raise ValueError('Valid subgroup ID required')
    folder=storage(root,storage_root)/identifier;receipt=read_json(folder/'subgroups-complete.json')
    if receipt.get('status')!='RETAIL_VALIDATION_SUBGROUPS_COMPLETE' or receipt.get('schema_version')!=1 or receipt.get('subgroups_id')!=identifier or not supported_methods(receipt.get('methods')) or receipt.get('visibility')!='private' or receipt.get('public_release_approved') is not False or any(receipt.get(k) is not v for k,v in FLAGS.items()):raise ValueError('Subgroup contract changed')
    if set(receipt['outputs_sha256'])!={'assumptions.json','report.json','private-validation-subgroups.parquet'}:raise ValueError('Complete subgroup payload required')
    guard(root,{**receipt['inputs_sha256'],**{str((folder/n).relative_to(root)):h for n,h in receipt['outputs_sha256'].items()}})
    if receipt.get('saved_writer_sha256') is not None and receipt['saved_writer_sha256']!=sha256(Path(__file__)):raise ValueError('Saved subgroup writer changed')
    plan=validate(read_json(folder/'assumptions.json'));rows,rule,pins=source_saved(root,plan,policy_storage)
    if plan['policy_id']!=receipt['policy_id'] or plan['freeze_id']!=receipt['freeze_id'] or pins!=receipt['inputs_sha256']:raise ValueError('Subgroup source binding changed')
    report=read_json(folder/'report.json')
    if pq.read_table(folder/'private-validation-subgroups.parquet').to_pylist()!=rows or report!=calculate(rows,plan,rule):raise ValueError('Subgroups do not replay from selected validation population')
    return folder,receipt,report


def build_saved_subgroups(root,plan,storage_root=None,policy_storage=None):
    if root.resolve().drive.upper()!='D:':raise ValueError('Private D: workspace required')
    writer=sha256(Path(__file__));plan=validate(plan);rows,rule,pins=source_saved(root,plan,policy_storage);method=methods();report=calculate(rows,plan,rule)
    folder=storage(root,storage_root)/('retail-subgroups-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
    write_new(folder/'assumptions.json',plan);write_new(folder/'report.json',report)
    pq.write_table(pa.Table.from_pylist(rows),folder/'private-validation-subgroups.parquet',compression='zstd')
    guard(root,pins)
    if method!=methods() or writer!=sha256(Path(__file__)):raise ValueError('Subgroup method changed')
    write_new(folder/'subgroups-complete.json',{'schema_version':1,'status':'RETAIL_VALIDATION_SUBGROUPS_COMPLETE','subgroups_id':folder.name,'completed_at':timestamp(),'policy_id':plan['policy_id'],'freeze_id':plan['freeze_id'],'methods':method,'inputs_sha256':pins,'outputs_sha256':{n:sha256(folder/n) for n in ['assumptions.json','report.json','private-validation-subgroups.parquet']},'visibility':'private','public_release_approved':False,**FLAGS,'saved_writer_sha256':writer,'actual_model_inference_performed':False})
    return {'subgroups_id':folder.name,'status':'RETAIL_VALIDATION_SUBGROUPS_COMPLETE','records':len(rows)}
