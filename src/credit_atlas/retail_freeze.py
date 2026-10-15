"""Validation-only selection and immutable retail benchmark model bundle."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from .retail_comparison import BOOTSTRAP,verify_assessment
from .retail_assessment import verify_features
from .workspace import contained,read_json,sha256,timestamp,write_new

COMPARISON_ID=re.compile(r"retail-comparison-[0-9a-f]{12}\Z")
FREEZE_ID=re.compile(r"retail-freeze-[0-9a-f]{12}\Z")
RUBRIC={"version":"retail-development-proper-score-rubric-v1",
        "established_after_development_inspection":True,"confirmatory_preregistered_test":False,
        "primary_metric":"brier_score","minimum_boosting_brier_improvement":.001,
        "required_brier_and_log_loss_bootstrap_lower":0.,"maximum_auc_point_degradation":.005,
        "minimum_calibration_brier_improvement":.0001,
        "fallback":"logistic/raw if it improves constant Brier and log loss, else constant/raw",
        "scope":"historical random-cohort research benchmark, not production approval"}


def choose_model(validation,comparison):
    selected="constant";variant="raw";reasons=[]
    if all(validation["logistic"]["raw"][key]<validation["constant"]["raw"][key] for key in ("brier_score","log_loss")):
        selected="logistic";reasons.append("logistic_improves_constant_brier_and_log_loss")
        pair=next(row["metrics"] for row in comparison["paired_improvements"]
                  if row["reference"]=="logistic/raw" and row["candidate"]=="boosting/raw")
        if (pair["brier_score"]["point"]>=RUBRIC["minimum_boosting_brier_improvement"]
                and pair["brier_score"]["lower"]>0 and pair["log_loss"]["lower"]>0
                and pair["roc_auc"]["point"]>=-RUBRIC["maximum_auc_point_degradation"]):
            selected="boosting";reasons.append("boosting_meets_development_proper_score_rule")
    if selected!="constant":
        pair=next(row["metrics"] for row in comparison["paired_improvements"]
                  if row["reference"]==selected+"/raw" and row["candidate"]==selected+"/calibrated")
        if (pair["brier_score"]["point"]>=RUBRIC["minimum_calibration_brier_improvement"]
                and pair["brier_score"]["lower"]>0 and pair["log_loss"]["lower"]>0):
            variant="calibrated";reasons.append("calibration_meets_development_incremental_rule")
        else:
            reasons.append("raw_variant_retained_without_clear_calibration_benefit")
    return {"model":selected,"variant":variant,"reason_codes":reasons,
            "selection_partition":"validation","qualified_for_production":False}


def verify_comparison(root,comparison_id):
    if not isinstance(comparison_id,str) or not COMPARISON_ID.fullmatch(comparison_id):
        raise ValueError("Valid comparison ID required")
    folder=contained(root,"artifacts/private/"+comparison_id)
    receipt=read_json(folder/"comparison-complete.json")
    if (receipt.get("schema_version")!=1 or receipt.get("comparison_id")!=comparison_id
            or receipt.get("status")!="RETAIL_PAIRED_VALIDATION_COMPARISON_COMPLETE"
            or receipt.get("method_source_sha256")!=sha256(Path(__file__).with_name("retail_comparison.py"))
            or receipt.get("visibility")!="private" or any(receipt.get(key) is not False for key in
                ("public_release_approved","model_training_performed","champion_selected","final_test_scored","final_test_predictors_materialized"))):
        raise ValueError("Comparison contract changed")
    assessment_folder,assessment,digest,targets,_=verify_assessment(root,receipt["assessment_id"])
    if digest!=receipt["assessment_receipt_sha256"] or assessment["case_id"]!=receipt["case_id"]:
        raise ValueError("Comparison assessment lineage changed")
    if set(receipt["outputs_sha256"])!={"access-start.json","bootstrap-config.json","comparison.json"}:
        raise ValueError("Complete comparison evidence required")
    for name,expected in receipt["outputs_sha256"].items():
        if sha256(folder/name)!=expected:
            raise ValueError("Comparison evidence changed")
    result=read_json(folder/"comparison.json")
    if (read_json(folder/"bootstrap-config.json")!=BOOTSTRAP or result["rows"]!=len(targets)
            or result["replicates"]!=BOOTSTRAP["replicates"] or result["seed"]!=BOOTSTRAP["seed"]):
        raise ValueError("Comparison configuration/population changed")
    return folder,receipt,assessment_folder,assessment,result,sha256(folder/"comparison-complete.json")


def freeze_model(root:Path,comparison_id:str):
    root=root.resolve()
    if root.drive.upper()!="D:":
        raise ValueError("Private D: workspace required")
    comparison_folder,comparison,assessment_folder,assessment,result,digest=verify_comparison(root,comparison_id)
    feature_folder,_,_,_,_=verify_features(root,assessment["feature_id"])
    choice=choose_model(read_json(assessment_folder/"validation-metrics.json"),result)
    output=contained(root,"artifacts/private/retail-freeze-"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    write_new(output/"rubric.json",RUBRIC)
    write_new(output/"selection.json",{**choice,"decided_at":timestamp(),"comparison_id":comparison_id,
              "rationale":"Development-only benchmark decision; proper scoring rules primary, ranking/support and simplicity considered. Rubric established after viewing development results; holdout has not been read for selection."})
    sources={"encoder.json":feature_folder/"encoder.json","model.json":assessment_folder/(choice["model"]+"-model.json"),
             "settings.json":assessment_folder/"settings.json"}
    if choice["variant"]=="calibrated":
        sources["calibration.json"]=assessment_folder/(choice["model"]+"-calibration.json")
    for name,path in sources.items():
        with (output/name).open("xb") as stream:
            stream.write(path.read_bytes())
    verify_comparison(root,comparison_id)
    if sha256(comparison_folder/"comparison-complete.json")!=digest:
        raise ValueError("Comparison changed during freeze")
    write_new(output/"freeze-complete.json",{"schema_version":1,"status":"RETAIL_BENCHMARK_MODEL_FROZEN",
              "freeze_id":output.name,"frozen_at":timestamp(),"comparison_id":comparison_id,
              "comparison_receipt_sha256":digest,"assessment_id":assessment["assessment_id"],
              "assessment_receipt_sha256":comparison["assessment_receipt_sha256"],
              "case_id":assessment["case_id"],"case_receipt_sha256":assessment["case_receipt_sha256"],
              "feature_id":assessment["feature_id"],"feature_receipt_sha256":assessment["feature_receipt_sha256"],
              "selected_model":choice["model"],"selected_variant":choice["variant"],
              "method_source_sha256":sha256(Path(__file__)),"champion_scope":"research_random_cohort_benchmark",
              "champion_selected":True,"final_test_scored":False,"model_training_performed":False,
              "qualified_for_production":False,"visibility":"private","public_release_approved":False,
              "outputs_sha256":{p.name:sha256(p) for p in output.iterdir() if p.is_file()}})
    return {"directory":str(output),"status":"RETAIL_BENCHMARK_MODEL_FROZEN",**choice,"final_test_scored":False}


def verify_freeze(root,freeze_id):
    if not isinstance(freeze_id,str) or not FREEZE_ID.fullmatch(freeze_id):
        raise ValueError("Valid freeze ID required")
    folder=contained(root,"artifacts/private/"+freeze_id)
    receipt=read_json(folder/"freeze-complete.json")
    if (receipt.get("freeze_id")!=freeze_id or receipt.get("schema_version")!=1
            or receipt.get("status")!="RETAIL_BENCHMARK_MODEL_FROZEN"
            or receipt.get("method_source_sha256")!=sha256(Path(__file__))
            or receipt.get("champion_selected") is not True or receipt.get("visibility")!="private"
            or receipt.get("champion_scope")!="research_random_cohort_benchmark"
            or any(receipt.get(key) is not False for key in ("final_test_scored","model_training_performed","qualified_for_production","public_release_approved"))):
        raise ValueError("Frozen benchmark contract changed")
    *_,comparison_digest=verify_comparison(root,receipt["comparison_id"])
    if comparison_digest!=receipt["comparison_receipt_sha256"]:
        raise ValueError("Frozen comparison changed")
    assessment_folder,assessment,assessment_digest,*_=verify_assessment(root,receipt["assessment_id"])
    feature_folder,_,case_folder,case,feature_digest=verify_features(root,receipt["feature_id"])
    if (assessment_digest!=receipt["assessment_receipt_sha256"] or feature_digest!=receipt["feature_receipt_sha256"]
            or case["case_id"]!=receipt["case_id"] or assessment["case_receipt_sha256"]!=receipt["case_receipt_sha256"]):
        raise ValueError("Frozen case/feature/assessment changed")
    choice=choose_model(read_json(assessment_folder/"validation-metrics.json"),
                        read_json(contained(root,"artifacts/private/"+receipt["comparison_id"])/"comparison.json"))
    selection=read_json(folder/"selection.json")
    if (read_json(folder/"rubric.json")!=RUBRIC or any(selection[key]!=value for key,value in choice.items())
            or receipt["selected_model"]!=choice["model"] or receipt["selected_variant"]!=choice["variant"]):
        raise ValueError("Frozen choice does not reproduce from development evidence")
    expected={"rubric.json","selection.json","encoder.json","model.json","settings.json"}
    if choice["variant"]=="calibrated":
        expected.add("calibration.json")
    if set(receipt["outputs_sha256"])!=expected:
        raise ValueError("Complete frozen bundle required")
    for name,digest in receipt["outputs_sha256"].items():
        if sha256(folder/name)!=digest:
            raise ValueError("Frozen model artifact changed")
    if (sha256(folder/"encoder.json")!=sha256(feature_folder/"encoder.json")
            or sha256(folder/"model.json")!=sha256(assessment_folder/(choice["model"]+"-model.json"))
            or sha256(folder/"settings.json")!=sha256(assessment_folder/"settings.json")):
        raise ValueError("Frozen bundle differs from selected development artifacts")
    if choice["variant"]=="calibrated" and sha256(folder/"calibration.json")!=sha256(assessment_folder/(choice["model"]+"-calibration.json")):
        raise ValueError("Frozen calibration differs from selected artifact")
    return folder,receipt,sha256(folder/"freeze-complete.json"),case_folder,case
