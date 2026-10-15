"""Policy serving/persistence from verified saved scores, with no model inference."""
import hashlib
import re
import uuid
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from .retail_policy import FLAGS,calculate,methods,validate
from .workspace import contained,read_json,sha256,timestamp,write_new


def storage(root,folder=None):
    folder=(folder or root/'artifacts/private').resolve()
    if not folder.is_relative_to((root/'artifacts/private').resolve()):raise ValueError('Policy storage must remain in private workspace')
    return folder


def saved_source(root,freeze_id):
    if not isinstance(freeze_id,str) or not re.fullmatch(r'retail-freeze-[0-9a-f]{12}',freeze_id):raise ValueError('Valid frozen model required')
    folder=contained(root,'artifacts/private/'+freeze_id);frozen=read_json(folder/'freeze-complete.json');digest=sha256(folder/'freeze-complete.json')
    if frozen.get('status')!='RETAIL_BENCHMARK_MODEL_FROZEN' or frozen.get('freeze_id')!=freeze_id or frozen.get('champion_selected') is not True or frozen.get('champion_scope')!='research_random_cohort_benchmark':raise ValueError('Frozen benchmark contract changed')
    if frozen.get('visibility')!='private' or any(frozen.get(k) is not False for k in ['final_test_scored','model_training_performed','qualified_for_production','public_release_approved']):raise ValueError('Frozen benchmark gates changed')
    assessment=contained(root,'artifacts/private/'+frozen['assessment_id']);receipt=read_json(assessment/'assessment-complete.json')
    score_path=assessment/'private-validation-scores.parquet';raw=score_path.read_bytes();score_digest=hashlib.sha256(raw).hexdigest()
    if receipt['outputs_sha256'][score_path.name]!=score_digest:raise ValueError('Saved validation scores changed')
    lineage={'freeze_id':freeze_id,'case_id':frozen['case_id'],'assessment_id':frozen['assessment_id'],'selected_model':frozen['selected_model'],'selected_variant':frozen['selected_variant'],'inputs_sha256':{str((folder/'freeze-complete.json').relative_to(root)):digest,str(score_path.relative_to(root)):score_digest}}
    from .retail_policy_views import lineage_pins
    # Byte-check the complete freeze graph, including method versions and raw
    # acquisition bytes. This does not deserialize predictors or invoke scorers.
    pins=lineage_pins(root,lineage)
    selection=read_json(folder/'selection.json')
    if selection['model']!=frozen['selected_model'] or selection['variant']!=frozen['selected_variant'] or selection['selection_partition']!='validation' or selection['qualified_for_production'] is not False:raise ValueError('Frozen selection changed')
    feature=contained(root,'artifacts/private/'+frozen['feature_id']);case=contained(root,'artifacts/private/'+frozen['case_id'])
    if sha256(folder/'model.json')!=sha256(assessment/(frozen['selected_model']+'-model.json')) or sha256(folder/'encoder.json')!=sha256(feature/'encoder.json') or sha256(folder/'settings.json')!=sha256(assessment/'settings.json'):raise ValueError('Frozen bundle differs from selected saved artifacts')
    if frozen['selected_variant']=='calibrated' and sha256(folder/'calibration.json')!=sha256(assessment/(frozen['selected_model']+'-calibration.json')):raise ValueError('Frozen calibrator changed')
    if frozen['selected_model'] not in {'constant','logistic','boosting'} or frozen['selected_variant'] not in {'raw','calibrated'}:raise ValueError('Unsupported saved model/variant')
    column=frozen['selected_variant']+'_probability'
    scores=[{'source_client_id':r['source_client_id'],'target':r['target'],'probability':r[column]} for r in pq.read_table(pa.BufferReader(raw)).to_pylist() if r['model']==frozen['selected_model']]
    labels=pq.read_table(case/'partitions.parquet',columns=['source_client_id','target'],filters=[('partition','=','validation')]).to_pylist();expected={r['source_client_id']:r['target'] for r in labels}
    if len(scores)!=len(expected) or len({r['source_client_id'] for r in scores})!=len(scores) or any(expected.get(r['source_client_id'])!=r['target'] for r in scores):raise ValueError('Saved validation cohort mismatch')
    if any(sha256(contained(root,p))!=h for p,h in pins.items()):raise ValueError('Policy lineage changed during saved-score read')
    return scores,lineage


def verify_saved(root,identifier,storage_root=None):
    if not isinstance(identifier,str) or not re.fullmatch(r'retail-policy-[0-9a-f]{12}',identifier):raise ValueError('Valid retail policy ID required')
    folder=storage(root,storage_root)/identifier;receipt=read_json(folder/'policy-complete.json')
    if receipt.get('schema_version')!=1 or receipt.get('policy_id')!=identifier or receipt.get('status')!='RETAIL_DECLARED_POLICY_COMPLETE' or receipt.get('methods')!=methods() or receipt.get('visibility')!='private' or receipt.get('public_release_approved') is not False or any(receipt.get(k) is not v for k,v in FLAGS.items()):raise ValueError('Policy contract changed')
    if set(receipt['outputs_sha256'])!={'assumptions.json','report.json'}:raise ValueError('Complete policy outputs required')
    for name,digest in receipt['outputs_sha256'].items():
        if sha256(folder/name)!=digest:raise ValueError('Policy payload changed')
    if receipt.get('saved_writer_sha256') is not None and receipt['saved_writer_sha256']!=sha256(Path(__file__)):raise ValueError('Saved policy writer changed')
    plan=validate(read_json(folder/'assumptions.json'))
    if plan['freeze_id']!=receipt['freeze_id']:raise ValueError('Policy freeze binding changed')
    scores,lineage=saved_source(root,plan['freeze_id'])
    if lineage['inputs_sha256']!=receipt['inputs_sha256']:raise ValueError('Policy input lineage changed')
    report=read_json(folder/'report.json')
    if report!=calculate(scores,plan)|lineage:raise ValueError('Policy does not replay from saved validation scores')
    return folder,receipt,report


def build_saved(root,plan,storage_root=None):
    if root.resolve().drive.upper()!='D:':raise ValueError('Private D: workspace required')
    writer=sha256(Path(__file__));method=methods()
    plan=validate(plan);scores,lineage=saved_source(root,plan['freeze_id']);report=calculate(scores,plan)|lineage
    folder=storage(root,storage_root)/('retail-policy-'+uuid.uuid4().hex[:12]);folder.mkdir(parents=True)
    write_new(folder/'assumptions.json',plan);write_new(folder/'report.json',report)
    current_scores,current_lineage=saved_source(root,plan['freeze_id'])
    if current_lineage!=lineage or current_scores!=scores or method!=methods() or writer!=sha256(Path(__file__)):raise ValueError('Policy source/method changed before completion')
    receipt={'schema_version':1,'policy_id':folder.name,'status':'RETAIL_DECLARED_POLICY_COMPLETE','completed_at':timestamp(),'freeze_id':plan['freeze_id'],'methods':methods(),'inputs_sha256':lineage['inputs_sha256'],'outputs_sha256':{n:sha256(folder/n) for n in ['assumptions.json','report.json']},'visibility':'private','public_release_approved':False,**FLAGS,'saved_writer_sha256':sha256(Path(__file__)),'actual_model_inference_performed':False}
    write_new(folder/'policy-complete.json',receipt)
    return {'policy_id':folder.name,'status':receipt['status'],'records':report['records']}
