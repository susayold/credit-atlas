import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas.retail_comparison import paired_bootstrap,verify_assessment
from credit_atlas.retail_assessment import run_assessment
from credit_atlas.workspace import read_json,sha256
from .test_retail_assessment import synthetic_features


def test_shared_resampling_gives_zero_difference_for_identical_scores_and_repeatable_intervals():
    targets=np.asarray([0,1]*20)
    probabilities=np.linspace(.1,.9,40)
    scores={"logistic/raw":probabilities,"boosting/raw":probabilities.copy()}
    result=paired_bootstrap(targets,scores,replicates=100,seed=5)
    assert result==paired_bootstrap(targets,scores,replicates=100,seed=5)
    assert result["paired_improvements"][0]["metrics"]=={
        name:{"point":0.,"lower":0.,"upper":0.} for name in ("roc_auc","average_precision","brier_score","log_loss")}


def test_metric_directions_and_class_conditioned_baseline_interval():
    y=np.asarray([0,1]*20)
    scores={"logistic/raw":np.full(40,.5),"boosting/raw":np.where(y==1,.9,.1)}
    result=paired_bootstrap(y,scores,replicates=100,seed=8)
    for metric,item in result["paired_improvements"][0]["metrics"].items():
        assert item["point"]>0 and item["lower"]>0
    baseline=result["absolute_intervals"]["logistic/raw"]["brier_score"]
    assert baseline=={"point":.25,"lower":.25,"upper":.25}


@pytest.mark.parametrize("scores",[{"x":[.1]}, {"x":[float("nan")]*4},{"x":[1.1]*4}])
def test_wrong_grain_nonfinite_or_out_of_range_probabilities_are_rejected(scores):
    with pytest.raises(ValueError,match="Paired"):
        paired_bootstrap([0,1,0,1],scores,replicates=100)


def test_score_order_tamper_is_rejected_even_if_artifact_digest_is_updated(tmp_path,monkeypatch):
    synthetic_features(tmp_path,monkeypatch)
    import credit_atlas.retail_assessment as assessment_module
    monkeypatch.setattr("credit_atlas.retail_comparison.verify_features",assessment_module.verify_features)
    result=run_assessment(tmp_path,"retail-features-bbbbbbbbbbbb")
    folder=Path(result["directory"])
    *_,labels,probabilities=verify_assessment(tmp_path,folder.name)
    assert len(labels)==100 and len(probabilities)==6
    path=folder/"private-validation-scores.parquet"
    rows=pq.read_table(path).to_pylist()
    rows[0],rows[1]=rows[1],rows[0]
    pq.write_table(pa.Table.from_pylist(rows),path)
    receipt=read_json(folder/"assessment-complete.json")
    receipt["outputs_sha256"][path.name]=sha256(path)
    (folder/"assessment-complete.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError,match="ordered validation"):
        verify_assessment(tmp_path,folder.name)
