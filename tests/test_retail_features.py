import copy
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.retail import NUMERIC_FEATURES,CATEGORICAL_FEATURES,assign_partitions
from credit_atlas.retail_features import RetailEncoder,prepare_features
from credit_atlas.workspace import read_json


def record(partition="train",value=10,category=0):
    return {"partition":partition,**dict.fromkeys(NUMERIC_FEATURES,value),
            **dict.fromkeys(CATEGORICAL_FEATURES,category)}


def test_train_scaling_saved_state_and_unseen_category_do_not_learn_validation():
    encoder=RetailEncoder().fit([record(value=10),record(value=30,category=-2)])
    assert encoder.state["numeric"]["LIMIT_BAL"]=={"mean":20.,"scale":10.}
    before=copy.deepcopy(encoder.state)
    validation=[record("validation",1000,9)]
    native=encoder.transform(validation)
    restored=RetailEncoder.restore(json.loads(json.dumps(before)))
    assert np.array_equal(native,restored.transform(validation))
    assert encoder.state==before and native[0,0]==98
    assert native[0,len(NUMERIC_FEATURES)]==1 # explicit unseen bucket
    assert native.shape[1]==len(NUMERIC_FEATURES)+6*3


@pytest.mark.parametrize("role",["calibration","validation","final_test"])
def test_encoder_cannot_fit_other_partitions(role):
    with pytest.raises(ValueError,match="training"):
        RetailEncoder().fit([record(role)])


def test_final_test_transform_is_refused_and_nonfinite_fit_rejected():
    encoder=RetailEncoder().fit([record()])
    with pytest.raises(ValueError,match="final-test"):
        encoder.transform([record("final_test")])
    with pytest.raises(ValueError):
        RetailEncoder().fit([record(value=float("nan"))])
    with pytest.raises(ValueError):
        RetailEncoder().fit([record(value=True)])


def test_altered_encoder_schema_is_rejected():
    state=copy.deepcopy(RetailEncoder().fit([record()]).state)
    state["feature_names"][0]="source_client_id"
    with pytest.raises(ValueError,match="schema"):
        RetailEncoder.restore(state)
    state=copy.deepcopy(RetailEncoder().fit([record()]).state)
    state["numeric"]["LIMIT_BAL"]["scale"]=0
    with pytest.raises(ValueError,match="scaling"):
        RetailEncoder.restore(state)


def test_development_join_never_reads_poisoned_final_test_predictors(tmp_path,monkeypatch):
    folder=tmp_path/"SYNTHETIC-retail-case"
    folder.mkdir()
    labels=[{"source_client_id":i+1,"target":i%2} for i in range(200)]
    assignments=assign_partitions(labels)
    roles={row["source_client_id"]:row["partition"] for row in assignments}
    clients=[{**label,**record(value=float("nan") if roles[label["source_client_id"]]=="final_test" else 10),
              "SEX":"SYNTHETIC_EXCLUDED_DEMOGRAPHIC"} for label in labels]
    pq.write_table(pa.Table.from_pylist(clients),folder/"clients.parquet")
    pq.write_table(pa.Table.from_pylist(assignments),folder/"partitions.parquet")
    support={role:{"positive":sum(row["target"] for row in assignments if row["partition"]==role),
                   "negative":sum(1-row["target"] for row in assignments if row["partition"]==role)}
             for role in ("train","calibration","validation","final_test")}
    monkeypatch.setattr("credit_atlas.retail_features.verify_case",lambda *args:(folder,{"support":support},"a"*64))
    result=prepare_features(tmp_path,"retail-case-aaaaaaaaaaaa")
    output=Path(result["directory"])
    prepared=pq.read_table(output/"development.parquet").to_pylist()
    assert len(prepared)==180
    assert not {row["source_client_id"] for row in prepared} & {key for key,role in roles.items() if role=="final_test"}
    assert "SEX" not in read_json(output/"encoder.json")["feature_names"]
    assert "SYNTHETIC_EXCLUDED_DEMOGRAPHIC" not in (output/"encoder.json").read_text()
    assert read_json(output/"features-complete.json")["final_test_scored"] is False
    assert read_json(output/"access-start.json")["all_label_ids_read_for_split_verification"] is True
