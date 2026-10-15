import copy
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from credit_atlas.retail_policy import verify
from credit_atlas.workspace import sha256,write_new
from tests.test_retail_policy import evidence,scores
import scripts.audit_retail_policy as audit

def test_independent_audit_detects_cost_fault_after_primary_replay_bypassed(evidence,monkeypatch):
    root,identifier,_=evidence; folder,receipt,report=verify(root,identifier)
    assessment=root/'artifacts/private/assessment'; assessment.mkdir()
    pq.write_table(pa.Table.from_pylist([{'model':'boosting','target':r['target'],'raw_probability':r['probability']} for r in scores()]),assessment/'private-validation-scores.parquet')
    ledger=root/'artifacts/private/retail-holdout-access.sqlite'; ledger.write_bytes(b'unchanged ledger')
    write_new(root/'artifacts/private/retail-policy-holdout-guard-before-20261010.json',{'retail_holdout_ledger_sha256':sha256(ledger)})
    monkeypatch.setattr(audit,'verify',lambda *args:(folder,receipt,report))
    assert audit.run(root,identifier)['status']=='PASS'
    broken=copy.deepcopy(report); broken['cases'][-1]['expected_declared_cost']['numerator']='999'
    monkeypatch.setattr(audit,'verify',lambda *args:(folder,receipt,broken))
    with pytest.raises(AssertionError,match='arithmetic'): audit.run(root,identifier)
