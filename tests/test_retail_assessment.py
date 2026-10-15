import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.retail import NUMERIC_FEATURES,CATEGORICAL_FEATURES
from credit_atlas.retail_features import RetailEncoder
from credit_atlas.retail_assessment import predict_json,metrics,fit_calibration,run_assessment
from credit_atlas.workspace import read_json,write_new


def test_json_tree_threshold_and_leaf_learning_rate_values():
    model={"kind":"histogram_boosting","feature_dimension":1,"initial_raw_score":0.,"trees":[[
        {"is_leaf":False,"feature":0,"threshold":2.,"left":1,"right":2,"value":0.},
        {"is_leaf":True,"value":-1.}, {"is_leaf":True,"value":1.}]]}
    actual=predict_json(json.loads(json.dumps(model)),[[1.],[2.],[3.]])
    assert np.allclose(actual,[1/(1+np.exp(1)),1/(1+np.exp(1)),1/(1+np.exp(-1))])
    with pytest.raises(ValueError,match="matrix"):
        predict_json(model,[[float("nan")]])


def test_reliability_closed_last_bin_and_constant_calibration():
    result=metrics([0,1,0,1],[0.,1.,.5,.5])
    assert result["reliability_bins"][-1]["loans"]==1
    assert sum(row["loans"] for row in result["reliability_bins"])==4
    labels=np.asarray([0]*50+[1]*50)
    calibration=fit_calibration(np.full(100,.1),labels)
    assert calibration["slope"]==0 and calibration["intercept"]==0
    with pytest.raises(ValueError,match="support"):
        fit_calibration(np.full(100,.1),np.zeros(100))


def synthetic_features(tmp_path,monkeypatch):
    folder=tmp_path/"SYNTHETIC-feature"
    case_folder=tmp_path/"SYNTHETIC-case"
    folder.mkdir();case_folder.mkdir()
    source=[];support={}
    for role,count in [("train",400),("calibration",100),("validation",100)]:
        support[role]={"positive":count//2,"negative":count//2}
        for index in range(count):
            target=index%2
            source.append({"source_client_id":len(source)+1,"target":target,"partition":role,
                           **{name:10+target*10+index%3 for name in NUMERIC_FEATURES},
                           **dict.fromkeys(CATEGORICAL_FEATURES,target)})
    support["final_test"]={"positive":50,"negative":50}
    encoder=RetailEncoder().fit([row for row in source if row["partition"]=="train"])
    ordered=sorted(source,key=lambda row:(row["partition"],row["source_client_id"]))
    matrix=encoder.transform(ordered)
    write_new(folder/"encoder.json",encoder.state)
    development=[{key:row[key] for key in ("source_client_id","partition","target")}|
                 {"features":vector.tolist()} for row,vector in zip(ordered,matrix,strict=True)]
    pq.write_table(pa.Table.from_pylist(development),folder/"development.parquet")
    final=[{"source_client_id":601+i,"target":i%2,"partition":"final_test",
            **dict.fromkeys(NUMERIC_FEATURES,float("nan")),**dict.fromkeys(CATEGORICAL_FEATURES,99)} for i in range(100)]
    pq.write_table(pa.Table.from_pylist(source+final),case_folder/"clients.parquet")
    pq.write_table(pa.Table.from_pylist([{key:row[key] for key in ("source_client_id","target","partition")}
                                       for row in source+final]),case_folder/"partitions.parquet")
    receipt={"case_id":"retail-case-aaaaaaaaaaaa","support":support}
    feature={"case_receipt_sha256":"a"*64}
    monkeypatch.setattr("credit_atlas.retail_assessment.verify_features",lambda *a:(folder,feature,case_folder,receipt,"b"*64))
    return folder


def test_complete_three_model_flow_ignores_poisoned_final_test_and_preserves_score_parity(tmp_path,monkeypatch):
    synthetic_features(tmp_path,monkeypatch)
    result=run_assessment(tmp_path,"retail-features-bbbbbbbbbbbb")
    folder=Path(result["directory"])
    receipt=read_json(folder/"assessment-complete.json")
    assert receipt["model_training_performed"] is True and receipt["final_test_scored"] is False
    assert receipt["champion_selected"] is False and receipt["temporal_out_of_time"] is False
    assert set(result["validation_metrics"])=={"constant","logistic","boosting"}
    assert read_json(folder/"verification.json")["model_parity_rows"]==600
    scores=pq.read_table(folder/"private-validation-scores.parquet").to_pylist()
    assert len(scores)==300 and all(501<=row["source_client_id"]<=600 for row in scores)
    assert all(item["raw"]["loans"]==100 for item in result["validation_metrics"].values())


def test_changed_feature_values_stop_before_fit(tmp_path,monkeypatch):
    folder=synthetic_features(tmp_path,monkeypatch)
    rows=pq.read_table(folder/"development.parquet").to_pylist()
    rows[0]["features"][0]=1000.
    pq.write_table(pa.Table.from_pylist(rows),folder/"development.parquet")
    with pytest.raises(ValueError,match="canonical source"):
        run_assessment(tmp_path,"retail-features-bbbbbbbbbbbb")
    failure=next((tmp_path/"artifacts/private").glob("retail-assessment-*/assessment-failed.json"))
    assert read_json(failure)["fit_started"] is False
