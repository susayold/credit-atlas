"""Aggregate-only model dossier from pinned research evidence, without scoring."""
from datetime import datetime
from pathlib import Path
from .retail_data_contract import report as source_contract
from .workspace import contained,read_json,sha256

METHOD_SHA=sha256(Path(__file__))

def report(views,query):
    if set(query)!={'view_id'}:raise ValueError('Retail dossier requires view_id only')
    if sha256(Path(__file__))!=METHOD_SHA:raise ValueError('Dossier method changed;restart required')
    identifier=query['view_id'];view=views.view(identifier);r=view['retail'];root=views.root
    anchor=read_json(contained(root,'artifacts/private/'+identifier+'/view-complete.json'))
    pins={k.replace('\\','/'):h for k,h in anchor['inputs_sha256'].items()};used={}
    def saved(relative):
        path=contained(root,relative)
        if relative not in pins or sha256(path)!=pins[relative]:raise ValueError('Dossier artifact missing or changed')
        used[relative]=pins[relative];return read_json(path)
    casebase='artifacts/private/'+r['case_id']+'/'
    freezebase='artifacts/private/'+r['freeze_id']+'/'
    holdoutbase='artifacts/private/'+r['holdout_id']+'/'
    case=saved(casebase+'case-complete.json');frozen=saved(freezebase+'freeze-complete.json')
    selection=saved(freezebase+'selection.json');rubric=saved(freezebase+'rubric.json')
    held=saved(holdoutbase+'evaluation-complete.json');access=saved(holdoutbase+'access-start.json')
    metrics=saved(holdoutbase+'holdout-metrics.json');verification=saved(holdoutbase+'verification.json')
    assessmentbase='artifacts/private/'+frozen['assessment_id']+'/'
    comparisonbase='artifacts/private/'+frozen['comparison_id']+'/'
    featurebase='artifacts/private/'+frozen['feature_id']+'/'
    assessment=saved(assessmentbase+'assessment-complete.json');comparison=saved(comparisonbase+'comparison-complete.json');feature=saved(featurebase+'features-complete.json')
    if frozen['case_id']!=case['case_id'] or held['case_id']!=case['case_id'] or held['freeze_id']!=frozen['freeze_id']:raise ValueError('Dossier case/freeze/holdout mismatch')
    if held['freeze_receipt_sha256']!=pins[freezebase+'freeze-complete.json'] or access['freeze_receipt_sha256']!=held['freeze_receipt_sha256']:raise ValueError('Dossier freeze receipt mismatch')
    if frozen['assessment_receipt_sha256']!=pins[assessmentbase+'assessment-complete.json'] or frozen['comparison_receipt_sha256']!=pins[comparisonbase+'comparison-complete.json'] or frozen['feature_receipt_sha256']!=pins[featurebase+'features-complete.json']:raise ValueError('Dossier development lineage mismatch')
    if selection!=r['selection'] or rubric!=r['rubric'] or selection['model']!=r['selected_model'] or selection['variant']!=r['selected_variant']:raise ValueError('Dossier selection differs from suite projection')
    if any(r['holdout'][key]!=metrics[key] for key in r['holdout']):raise ValueError('Saved final metrics differ from suite projection')
    if access['model_selection_performed'] is not False or access['model_training_performed'] is not False or held['qualified_for_production'] is not False or r['qualified_for_production'] is not False:raise ValueError('Dossier qualification contract changed')
    if not datetime.fromisoformat(selection['decided_at'])<=datetime.fromisoformat(frozen['frozen_at'])<datetime.fromisoformat(access['started_at'])<datetime.fromisoformat(held['completed_at']):raise ValueError('Dossier decision/freeze/evaluation chronology changed')
    contract=source_contract(views,query)
    trail=[{'stage':name,'artifact_id':item[key],'recorded_at':item.get('completed_at',item.get('frozen_at'))} for name,item,key in [('Source canonical',case,'case_id'),('Train-only feature preparation',feature,'feature_id'),('Development assessment',assessment,'assessment_id'),('Paired validation comparison',comparison,'comparison_id'),('Model freeze',frozen,'freeze_id'),('Saved final evaluation',held,'evaluation_id')]]
    return {'schema_version':'retail-model-dossier-v1','view_id':identifier,'suite_id':view['suite_id'],'case_id':r['case_id'],'freeze_id':r['freeze_id'],'holdout_id':r['holdout_id'],
        'intended_use':'Historical Taiwan booked-card behavioral benchmark;research interpretation of source next-month payment target',
        'prohibited_claims':['Vietnam production PD','Application approval-time underwriting','PD12/regulatory default','Authenticated bank credit approval'],
        'source_contract':contract,'model':{'selected_model':r['selected_model'],'selected_variant':r['selected_variant'],'feature_dimension':r['feature_dimension'],'selection':selection,'rubric':rubric},
        'validation_metrics':r['validation'],'paired_validation_uncertainty':r['paired_improvements'],'saved_final_test':r['holdout'],
        'audit_trail':trail,'evidence_hashes':used,'method_sha256':METHOD_SHA,
        'governance':{'review_owner':None,'authenticated_sign_off':False,'intended_use_approved_for_production':False,'temporal_out_of_time':False,'qualified_for_production':False,'final_test_confidence_intervals_available':False,'opening_page_refits_or_rescores':False},
        'limitations':list(dict.fromkeys(r['limits']+verification['caveats']+['App resolves saved aggregate artifacts;does not reread final-test predictors or run model inference.','Saved chronology is local research evidence;not independently authenticated organizational sign-off.','Source labels/raw cohort existed before freeze;holdout was reserved in the model pipeline,not unseen at organizational level.','Model-review ownership,monitoring protocol and deployment intended-use approval remain unprovided.'])),
        'visibility':'private','public_release_approved':False}
