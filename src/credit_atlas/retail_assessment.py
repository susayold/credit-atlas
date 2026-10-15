"""Fixed-settings retail development benchmark with JSON-only model persistence."""
from __future__ import annotations

import re
import warnings
import uuid
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.special import expit
from sklearn import __version__ as sklearn_version
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss
from threadpoolctl import threadpool_limits

from .retail import NUMERIC_FEATURES,CATEGORICAL_FEATURES
from .retail_features import RetailEncoder,verify_case,DEVELOPMENT_ROLES
from .workspace import contained,read_json,sha256,timestamp,write_new

FEATURE_ID=re.compile(r"retail-features-[0-9a-f]{12}\Z")
SETTINGS={"version":"uci350-fixed-development-comparison-v1","logistic_C":1.0,
          "logistic_max_iter":2000,"logistic_tol":1e-8,"calibration_C":1.0,
          "calibration_logit_clip":1e-12,"reliability_bin_edges":[i/10 for i in range(11)],
          "boosting":{"learning_rate":.05,"max_iter":120,"max_leaf_nodes":15,
                      "min_samples_leaf":50,"l2_regularization":1.0,"random_state":71},
          "selection_uses_final_test":False,"hyperparameter_search":False}


def verify_features(root,feature_id):
    if not isinstance(feature_id,str) or not FEATURE_ID.fullmatch(feature_id):
        raise ValueError("Valid retail feature ID required")
    folder=contained(root,"artifacts/private/"+feature_id)
    receipt=read_json(folder/"features-complete.json")
    if (receipt.get("schema_version")!=1 or receipt.get("feature_id")!=feature_id
            or receipt.get("status")!="RETAIL_DEVELOPMENT_FEATURES_PREPARED"
            or receipt.get("method_source_sha256")!=sha256(Path(__file__).with_name("retail_features.py"))
            or receipt.get("visibility")!="private" or any(receipt.get(key) is not False for key in
                ("model_training_performed","final_test_predictors_materialized","final_test_scored","public_release_approved"))):
        raise ValueError("Retail feature contract changed")
    case_folder,case,case_digest=verify_case(root,receipt["case_id"])
    if case_digest!=receipt["case_receipt_sha256"]:
        raise ValueError("Retail feature case changed")
    if set(receipt["outputs_sha256"])!={"access-start.json","encoder.json","coverage.json","development.parquet"}:
        raise ValueError("Complete development artifacts required")
    for name,digest in receipt["outputs_sha256"].items():
        if sha256(contained(root,str((folder/name).relative_to(root))))!=digest:
            raise ValueError("Retail feature evidence changed")
    return folder,receipt,case_folder,case,sha256(folder/"features-complete.json")


def predict_json(model,matrix):
    matrix=np.asarray(matrix,dtype=np.float64)
    if matrix.ndim!=2 or not np.isfinite(matrix).all() or matrix.shape[1]!=model["feature_dimension"]:
        raise ValueError("Invalid retail prediction matrix")
    kind=model["kind"]
    if kind=="constant":
        result=np.full(len(matrix),model["prevalence"])
    elif kind=="logistic":
        result=expit(matrix@np.asarray(model["coefficients"])+model["intercept"])
    elif kind=="histogram_boosting":
        raw=np.full(len(matrix),model["initial_raw_score"])
        for tree in model["trees"]:
            leaves=np.asarray([node["is_leaf"] for node in tree],dtype=bool)
            indices=np.zeros(len(matrix),dtype=np.int64)
            for _ in range(len(tree)):
                active=np.flatnonzero(~leaves[indices])
                if not len(active):
                    break
                for node_index in np.unique(indices[active]):
                    node=tree[int(node_index)]
                    selected=active[indices[active]==node_index]
                    indices[selected]=np.where(matrix[selected,node["feature"]]<=node["threshold"],node["left"],node["right"])
            if not leaves[indices].all():
                raise ValueError("Invalid persisted tree graph")
            raw+=np.asarray([node["value"] for node in tree])[indices]
        result=expit(raw)
    else:
        raise ValueError("Unsupported retail model")
    if not np.isfinite(result).all() or np.any((result<0)|(result>1)):
        raise ValueError("Invalid retail probability")
    return result


def logit(probabilities):
    p=np.asarray(probabilities,dtype=np.float64)
    if not np.isfinite(p).all() or np.any((p<0)|(p>1)):
        raise ValueError("Invalid calibration probability")
    p=np.clip(p,SETTINGS["calibration_logit_clip"],1-SETTINGS["calibration_logit_clip"])
    return np.log(p)-np.log1p(-p)


def fit_calibration(probabilities,targets):
    values=logit(probabilities)
    if len(set(targets))!=2 or min(np.sum(targets==1),np.sum(targets==0))<50:
        raise ValueError("Insufficient calibration class support")
    if np.ptp(values)==0:
        state={"slope":0.,"intercept":float(logit([np.mean(targets)])[0]),"fit_case":"constant_input_intercept_only"}
    else:
        fitted=LogisticRegression(C=SETTINGS["calibration_C"],max_iter=2000,tol=1e-8).fit(values.reshape(-1,1),targets)
        state={"slope":float(fitted.coef_[0,0]),"intercept":float(fitted.intercept_[0]),"fit_case":"varying_scores"}
    if state["slope"]<0 or not np.isfinite([state["slope"],state["intercept"]]).all():
        raise ValueError("Negative or invalid calibration slope; investigate ranking")
    return {**state,"method":"regularized_sigmoid_on_logit","C":SETTINGS["calibration_C"],
            "logit_clip":SETTINGS["calibration_logit_clip"],"fit_partition":"calibration",
            "fit_rows":len(targets),"events":int(np.sum(targets))}


def metrics(targets,probabilities):
    targets=np.asarray(targets)
    p=np.asarray(probabilities)
    bins=[]
    edges=SETTINGS["reliability_bin_edges"]
    for i,(lower,upper) in enumerate(zip(edges,edges[1:])):
        mask=(p>=lower)&((p<upper) if i<len(edges)-2 else (p<=upper))
        n=int(np.sum(mask))
        bins.append({"lower":lower,"upper":upper,"loans":n,"events":int(np.sum(targets[mask])),
                     "mean_probability":float(np.mean(p[mask])) if n else None,
                     "observed_rate":float(np.mean(targets[mask])) if n else None})
    if sum(row["loans"] for row in bins)!=len(targets):
        raise ValueError("Reliability bins do not reconcile")
    return {"loans":len(targets),"events":int(np.sum(targets)),"roc_auc":float(roc_auc_score(targets,p)),
            "average_precision":float(average_precision_score(targets,p)),"brier_score":float(brier_score_loss(targets,p)),
            "log_loss":float(log_loss(targets,p,labels=[0,1])),"reliability_bins":bins,
            "average_precision_definition":"not_trapezoidal_PR_AUC"}


def run_assessment(root:Path,feature_id:str):
    root=root.resolve()
    if root.drive.upper()!="D:":
        raise ValueError("Private D: workspace required")
    folder,feature,case_folder,case,digest=verify_features(root,feature_id)
    output=contained(root,"artifacts/private/retail-assessment-"+uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    provenance={"schema_version":1,"assessment_id":output.name,"feature_id":feature_id,"feature_receipt_sha256":digest,
                "case_id":case["case_id"],"case_receipt_sha256":feature["case_receipt_sha256"],
                "method_source_sha256":sha256(Path(__file__)),"visibility":"private","public_release_approved":False,
                "final_test_scored":False,"champion_selected":False,"temporal_out_of_time":False,
                "qualified_for_production":False}
    write_new(output/"access-start.json",{**provenance,"started_at":timestamp(),"purpose":"retail_fixed_development_comparison",
              "final_test_predictors_materialized":False,"permitted_predictor_partitions":list(DEVELOPMENT_ROLES)})
    try:
        development=pq.read_table(folder/"development.parquet").to_pylist()
        with duckdb.connect() as db:
            db.read_parquet(str(case_folder/"clients.parquet")).create_view("clients")
            db.read_parquet(str(case_folder/"partitions.parquet")).create_view("partitions")
            columns=",".join('c."'+name+'"' for name in NUMERIC_FEATURES+CATEGORICAL_FEATURES)
            source=db.sql("SELECT c.source_client_id,c.target,p.partition,"+columns+
                          " FROM clients c JOIN partitions p USING(source_client_id) "
                          "WHERE p.partition IN ('train','calibration','validation') ORDER BY p.partition,c.source_client_id").arrow().read_all().to_pylist()
        if [(r["source_client_id"],r["target"],r["partition"]) for r in source]!=[
                (r["source_client_id"],r["target"],r["partition"]) for r in development]:
            raise ValueError("Development identities/labels differ from frozen case")
        encoder=RetailEncoder.restore(read_json(folder/"encoder.json"))
        if RetailEncoder().fit([r for r in source if r["partition"]=="train"]).state!=encoder.state:
            raise ValueError("Encoder differs from exact training cohort")
        matrix=np.asarray([r["features"] for r in development])
        if not np.array_equal(matrix,encoder.transform(source)):
            raise ValueError("Development features differ from canonical source")
        roles=np.asarray([r["partition"] for r in development])
        targets=np.asarray([r["target"] for r in development],dtype=np.int8)
        masks={role:roles==role for role in DEVELOPMENT_ROLES}
        for role,mask in masks.items():
            if int(np.sum(mask))!=sum(case["support"][role].values()) or int(np.sum(targets[mask]))!=case["support"][role]["positive"]:
                raise ValueError("Development class support mismatch")
            if min(int(np.sum(targets[mask]==0)),int(np.sum(targets[mask]==1)))<(200 if role=="train" else 50):
                raise ValueError("Insufficient development support")
        if sklearn_version!="1.8.0":
            raise ValueError("Reviewed tree JSON exporter requires sklearn 1.8.0")
        write_new(output/"settings.json",SETTINGS)
        write_new(output/"fit-start.json",{**provenance,"started_at":timestamp(),"model_training_requested":True,
                  "settings_sha256":sha256(output/"settings.json"),"sklearn_version":sklearn_version})
        train=masks["train"]
        models={"constant":{"kind":"constant","prevalence":float(np.mean(targets[train])),"feature_dimension":matrix.shape[1]}}
        native={"constant":np.full(len(matrix),models["constant"]["prevalence"])}
        with threadpool_limits(limits=1),warnings.catch_warnings():
            warnings.simplefilter("error",ConvergenceWarning)
            logistic=LogisticRegression(C=SETTINGS["logistic_C"],max_iter=SETTINGS["logistic_max_iter"],
                                        tol=SETTINGS["logistic_tol"]).fit(matrix[train],targets[train])
            models["logistic"]={"kind":"logistic","feature_dimension":matrix.shape[1],
                                "coefficients":logistic.coef_[0].tolist(),"intercept":float(logistic.intercept_[0])}
            native["logistic"]=logistic.predict_proba(matrix)[:,1]
            boosting=HistGradientBoostingClassifier(**SETTINGS["boosting"],early_stopping=False,
                        validation_fraction=None,categorical_features=None,class_weight=None,warm_start=False).fit(matrix[train],targets[train])
            if boosting.do_early_stopping_ or len(boosting.validation_score_) or boosting.n_iter_!=SETTINGS["boosting"]["max_iter"]:
                raise ValueError("Unexpected internal validation or boosting fit")
            trees=[]
            for iteration in boosting._predictors:
                if len(iteration)!=1 or any(node["is_categorical"] for node in iteration[0].nodes):
                    raise ValueError("Unsupported tree export")
                trees.append([{"value":float(node["value"]),"feature":int(node["feature_idx"]),
                               "threshold":float(node["num_threshold"]),"left":int(node["left"]),
                               "right":int(node["right"]),"is_leaf":bool(node["is_leaf"])} for node in iteration[0].nodes])
            models["boosting"]={"kind":"histogram_boosting","feature_dimension":matrix.shape[1],
                                 "initial_raw_score":float(boosting._baseline_prediction[0,0]),"trees":trees}
            native["boosting"]=boosting.predict_proba(matrix)[:,1]
            evaluations,score_rows={},[]
            for name,model in models.items():
                write_new(output/(name+"-model.json"),model)
                saved=predict_json(read_json(output/(name+"-model.json")),matrix)
                if not np.allclose(saved,native[name],rtol=0,atol=1e-12):
                    raise ValueError("Persisted retail model scoring parity failed")
                calibration=fit_calibration(saved[masks["calibration"]],targets[masks["calibration"]])
                write_new(output/(name+"-calibration.json"),calibration)
                loaded=read_json(output/(name+"-calibration.json"))
                adjusted=expit(loaded["slope"]*logit(saved)+loaded["intercept"])
                validation=masks["validation"]
                evaluations[name]={"raw":metrics(targets[validation],saved[validation]),
                                   "calibrated":metrics(targets[validation],adjusted[validation])}
                for row,raw,calibrated in zip([r for r in development if r["partition"]=="validation"],
                                              saved[validation],adjusted[validation],strict=True):
                    score_rows.append({"source_client_id":row["source_client_id"],"target":row["target"],"model":name,
                                       "raw_probability":float(raw),"calibrated_probability":float(calibrated)})
        pq.write_table(pa.Table.from_pylist(score_rows),output/"private-validation-scores.parquet",compression="zstd")
        # Recompute all displayed metrics from the saved private score artifact.
        persisted=pq.read_table(output/"private-validation-scores.parquet").to_pylist()
        for name in models:
            selected=[r for r in persisted if r["model"]==name]
            for variant,column in (("raw","raw_probability"),("calibrated","calibrated_probability")):
                if metrics([r["target"] for r in selected],[r[column] for r in selected])!=evaluations[name][variant]:
                    raise ValueError("Saved validation metrics failed reconciliation")
        write_new(output/"validation-metrics.json",evaluations)
        write_new(output/"verification.json",{"status":"PASS","model_parity_rows":len(matrix),"models_checked":3,
                  "validation_score_sets_recomputed":6,"final_test_scored":False})
        *_,current=verify_features(root,feature_id)
        if current!=digest:
            raise ValueError("Retail features changed during assessment")
        write_new(output/"assessment-complete.json",{**provenance,"status":"RETAIL_DEVELOPMENT_ASSESSMENT_VERIFIED",
                  "completed_at":timestamp(),"model_training_performed":True,"support":case["support"],
                  "final_test_predictors_materialized":False,
                  "outputs_sha256":{p.name:sha256(p) for p in output.iterdir() if p.is_file()}})
        return {"directory":str(output),"status":"RETAIL_DEVELOPMENT_ASSESSMENT_VERIFIED",
                "validation_metrics":{name:{variant:{key:value for key,value in item.items() if key!="reliability_bins"}
                                             for variant,item in variants.items()} for name,variants in evaluations.items()},
                "final_test_scored":False,"champion_selected":False}
    except Exception as error:
        write_new(output/"assessment-failed.json",{**provenance,"status":"FAIL","failed_at":timestamp(),
                  "exception_type":type(error).__name__,"fit_started":(output/"fit-start.json").exists()})
        raise
