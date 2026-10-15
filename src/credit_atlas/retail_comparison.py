"""Paired validation uncertainty; no model selection or final-test access."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from scipy.special import expit
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss

from .retail_assessment import SETTINGS,verify_features,predict_json,logit,metrics
from .workspace import contained,read_json,sha256,timestamp,write_new

ASSESSMENT_ID=re.compile(r"retail-assessment-[0-9a-f]{12}\Z")
MODEL_NAMES=("constant","logistic","boosting")
METRICS=("roc_auc","average_precision","brier_score","log_loss")
BOOTSTRAP={"version":"retail-paired-validation-bootstrap-v1","replicates":1000,"seed":676,
           "confidence_level":.95,"method":"class_stratified_paired_client_percentile",
           "intervals":"unadjusted_exploratory","conditioning":"fixed_fitted_models_and_observed_class_counts",
           "champion_selection_performed":False,"final_test_scored":False}


def verify_assessment(root,assessment_id):
    if not isinstance(assessment_id,str) or not ASSESSMENT_ID.fullmatch(assessment_id):
        raise ValueError("Valid retail assessment ID required")
    folder=contained(root,"artifacts/private/"+assessment_id)
    receipt=read_json(folder/"assessment-complete.json")
    if (receipt.get("assessment_id")!=assessment_id or receipt.get("schema_version")!=1
            or receipt.get("status")!="RETAIL_DEVELOPMENT_ASSESSMENT_VERIFIED"
            or receipt.get("method_source_sha256")!=sha256(Path(__file__).with_name("retail_assessment.py"))
            or receipt.get("visibility")!="private" or receipt.get("model_training_performed") is not True
            or any(receipt.get(key) is not False for key in ("public_release_approved","final_test_scored",
                  "champion_selected","temporal_out_of_time","qualified_for_production","final_test_predictors_materialized"))):
        raise ValueError("Retail assessment contract changed")
    feature_folder,feature,_,case,feature_digest=verify_features(root,receipt["feature_id"])
    if (feature_digest!=receipt["feature_receipt_sha256"] or receipt["case_id"]!=case["case_id"]
            or receipt["case_receipt_sha256"]!=feature["case_receipt_sha256"] or receipt["support"]!=case["support"]):
        raise ValueError("Retail assessment input lineage changed")
    expected={"access-start.json","settings.json","fit-start.json","private-validation-scores.parquet",
              "validation-metrics.json","verification.json"}|{
              name+suffix for name in MODEL_NAMES for suffix in ("-model.json","-calibration.json")}
    if set(receipt["outputs_sha256"])!=expected:
        raise ValueError("Complete assessment artifact set required")
    for name,digest in receipt["outputs_sha256"].items():
        if sha256(contained(root,str((folder/name).relative_to(root))))!=digest:
            raise ValueError("Assessment artifact changed")
    if read_json(folder/"settings.json")!=SETTINGS:
        raise ValueError("Reviewed assessment settings changed")
    validation=[row for row in pq.read_table(feature_folder/"development.parquet").to_pylist() if row["partition"]=="validation"]
    count=sum(case["support"]["validation"].values())
    if len(validation)!=count or len({row["source_client_id"] for row in validation})!=count:
        raise ValueError("Validation source population changed")
    targets=np.asarray([row["target"] for row in validation],dtype=np.int8)
    matrix=np.asarray([row["features"] for row in validation],dtype=np.float64)
    scores=pq.read_table(folder/"private-validation-scores.parquet").to_pylist()
    if len(scores)!=3*count or {row["model"] for row in scores}!=set(MODEL_NAMES):
        raise ValueError("Saved validation model/cohort coverage changed")
    saved_metrics=read_json(folder/"validation-metrics.json")
    probabilities={}
    for name in MODEL_NAMES:
        selected=[row for row in scores if row["model"]==name]
        if [(row["source_client_id"],row["target"]) for row in selected]!=[
                (row["source_client_id"],row["target"]) for row in validation]:
            raise ValueError("Models must share identical ordered validation clients and outcomes")
        native=predict_json(read_json(folder/(name+"-model.json")),matrix)
        calibration=read_json(folder/(name+"-calibration.json"))
        adjusted=expit(calibration["slope"]*logit(native)+calibration["intercept"])
        for variant,column,expected_predictions in (("raw","raw_probability",native),
                ("calibrated","calibrated_probability",adjusted)):
            p=np.asarray([row[column] for row in selected],dtype=np.float64)
            if not np.allclose(p,expected_predictions,rtol=0,atol=1e-12):
                raise ValueError("Validation scores differ from persisted model/calibration")
            if metrics(targets,p)!=saved_metrics[name][variant]:
                raise ValueError("Validation metrics differ from saved score outcomes")
            probabilities[name+"/"+variant]=p
    return folder,receipt,sha256(folder/"assessment-complete.json"),targets,probabilities


def point_metrics(targets,probabilities):
    return np.asarray([roc_auc_score(targets,probabilities),average_precision_score(targets,probabilities),
                       brier_score_loss(targets,probabilities),log_loss(targets,probabilities,labels=[0,1])],dtype=float)


def paired_bootstrap(targets,probabilities,*,replicates=1000,seed=676):
    """Resample each class once per replicate, then reuse client indices across all score variants."""
    y=np.asarray(targets)
    if (y.ndim!=1 or len(y)==0 or set(y.tolist())!={0,1}
            or type(replicates) is not int or not 100<=replicates<=5000
            or type(seed) is not int or not 0<=seed<2**32 or not probabilities):
        raise ValueError("Binary validation labels and bounded bootstrap settings required")
    names=list(probabilities)
    arrays={name:np.asarray(p,dtype=float) for name,p in probabilities.items()}
    if any(p.shape!=y.shape or not np.isfinite(p).all() or np.any((p<0)|(p>1)) for p in arrays.values()):
        raise ValueError("Paired finite probabilities on one validation cohort required")
    rng=np.random.default_rng(seed)
    classes=[np.flatnonzero(y==target) for target in (0,1)]
    draws={name:np.empty((replicates,4),dtype=float) for name in names}
    points={name:point_metrics(y,p) for name,p in arrays.items()}
    for i in range(replicates):
        indices=np.concatenate([rng.choice(group,size=len(group),replace=True) for group in classes])
        for name,p in arrays.items():
            draws[name][i]=point_metrics(y[indices],p[indices])
    def interval(samples,point):
        lower,upper=np.percentile(samples,[2.5,97.5],axis=0)
        return {metric:{"point":float(value),"lower":float(lo),"upper":float(hi)}
                for metric,value,lo,hi in zip(METRICS,point,lower,upper,strict=True)}
    absolute={name:interval(draws[name],points[name]) for name in names}
    differences=[]
    orientation=np.asarray([1,1,-1,-1])
    pairs=[("logistic/"+v,"boosting/"+v) for v in ("raw","calibrated")]+[
           (name+"/raw",name+"/calibrated") for name in MODEL_NAMES]
    for reference,candidate in pairs:
        if reference in draws and candidate in draws:
            differences.append({"reference":reference,"candidate":candidate,
                "definition":"positive_is_candidate_improvement_for_each_metric",
                "metrics":interval((draws[candidate]-draws[reference])*orientation,
                                   (points[candidate]-points[reference])*orientation)})
    return {"rows":len(y),"events":int(np.sum(y)),"replicates":replicates,"seed":seed,
            "absolute_intervals":absolute,"paired_improvements":differences,
            "class_counts_preserved_per_replicate":True,"client_indices_shared_across_models":True}


def run_comparison(root:Path,assessment_id:str):
    root=root.resolve()
    if root.drive.upper()!="D:":
        raise ValueError("Private D: workspace required")
    output=contained(root,"artifacts/private/retail-comparison-"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output/"access-start.json",{"started_at":timestamp(),"assessment_id":assessment_id,
              "purpose":"paired_validation_uncertainty","final_test_scored":False,
              "final_test_predictors_materialized":False,"model_training_performed":False})
    try:
        folder,assessment,digest,targets,probabilities=verify_assessment(root,assessment_id)
        write_new(output/"bootstrap-config.json",BOOTSTRAP)
        result=paired_bootstrap(targets,probabilities,replicates=BOOTSTRAP["replicates"],seed=BOOTSTRAP["seed"])
        write_new(output/"comparison.json",{**result,"limitations":[
            "Exploratory unadjusted percentile intervals; not a preregistered winner-selection test.",
            "Fixed-model, class-conditioned uncertainty omits training/refitting and prevalence uncertainty.",
            "Source clients are resampling units; unknown household clustering cannot be adjusted.",
            "One random historical cohort; no evidence of future temporal or geographic transportability.",
            "No final-test predictions, champion or operational threshold selected."]})
        *_,current_targets,current_probabilities=verify_assessment(root,assessment_id)
        if sha256(folder/"assessment-complete.json")!=digest or not np.array_equal(targets,current_targets) or any(
                not np.array_equal(p,current_probabilities[name]) for name,p in probabilities.items()):
            raise ValueError("Assessment changed during paired comparison")
        write_new(output/"comparison-complete.json",{"schema_version":1,"status":"RETAIL_PAIRED_VALIDATION_COMPARISON_COMPLETE",
                  "comparison_id":output.name,"completed_at":timestamp(),"assessment_id":assessment_id,
                  "assessment_receipt_sha256":digest,"case_id":assessment["case_id"],
                  "method_source_sha256":sha256(Path(__file__)),"visibility":"private","public_release_approved":False,
                  "model_training_performed":False,"champion_selected":False,"final_test_scored":False,
                  "final_test_predictors_materialized":False,
                  "outputs_sha256":{p.name:sha256(p) for p in output.iterdir() if p.is_file()}})
        return {"directory":str(output),"status":"RETAIL_PAIRED_VALIDATION_COMPARISON_COMPLETE",
                "rows":result["rows"],"replicates":result["replicates"],"paired_improvements":result["paired_improvements"],
                "champion_selected":False,"final_test_scored":False}
    except Exception as error:
        write_new(output/"comparison-failed.json",{"status":"FAIL","exception_type":type(error).__name__,"failed_at":timestamp()})
        raise
