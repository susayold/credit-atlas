import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('validation_audit',Path(__file__).resolve().parents[1]/'scripts/audit_retail_validation_acceptance.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def test_ties_and_constant_no_ranking_advantage():
    values=audit.weighted_metrics(audit.prepare([1,0],[.5,.5]))
    assert values==pytest.approx([.5,.5,.25,np.log(2)])

def test_pairwise_auc_and_weighted_duplicate_rows():
    y=np.array([0,1,0,1]);p=np.array([.1,.8,.8,.9]);weights=np.array([2,1,3,2])
    yy=np.repeat(y,weights);pp=np.repeat(p,weights)
    positives=pp[yy==1];negatives=pp[yy==0]
    expected=sum((a>b)+.5*(a==b) for a in positives for b in negatives)/(len(positives)*len(negatives))
    got=audit.weighted_metrics(audit.prepare(y,p),weights)
    assert got[0]==pytest.approx(expected)
    assert got==pytest.approx(audit.weighted_metrics(audit.prepare(yy,pp)))

def test_zero_weights_are_absent_observations():
    assert audit.weighted_metrics(audit.prepare([1,0,1],[.7,.2,.99]),[1,1,0])==pytest.approx(audit.weighted_metrics(audit.prepare([1,0],[.7,.2])))

def test_average_precision_uses_whole_tied_threshold_group():
    assert audit.weighted_metrics(audit.prepare([1,0,1],[.9,.8,.8]))[1]==pytest.approx(5/6)

def test_probability_edges_finite_log_loss():
    got=audit.weighted_metrics(audit.prepare([0,1],[0,1]));assert np.isfinite(got).all() and got[0]==1 and got[1]==1 and got[2]==0

@pytest.mark.parametrize('y,p',[([0,0],[.1,.2]),([0,1],[.1,float('nan')]),([0,1],[-.1,.2]),([0,1],[.1])])
def test_bad_probability_contract(y,p):
    with pytest.raises(ValueError):audit.prepare(y,p)
