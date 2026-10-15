"""Real Parquet queries on synthetic cases check cross-run identity boundaries."""
from datetime import date
import json
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from credit_atlas import service
from credit_atlas.server import handler_for
from credit_atlas.snapshot import TARGET
from credit_atlas.workspace import sha256, write_new


@pytest.fixture
def two_cases(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "load_engine", lambda root: {"commit": "SYNTHETIC-QA"})
    ids = ["d01-111111111111", "d01-222222222222"]
    tokens = ["a" * 24, "b" * 24]
    for identifier, token in zip(ids, tokens):
        case = tmp_path / "artifacts/private" / identifier
        stage = tmp_path / "artifacts/private" / ("SYNTHETIC-stage-" + identifier)
        case.mkdir(parents=True)
        stage.mkdir()
        raw_id = "SYNTHETIC-source-id-" + identifier
        dim = {"loan_id": raw_id, "origination_year": 2020, "classic_fico": 700,
               "original_dti": 30, "original_ltv": 80, "original_cltv": 80,
               "original_upb": 100000., "original_term": 360, "original_interest_rate": 3.,
               "occupancy": "P", "loan_purpose": "P", "property_type": "SF",
               "first_payment_date": date(2020, 1, 1), "is_relief_refinance": False, "is_harp_subset": False}
        label = {"loan_id": raw_id, "origination_year": 2020, "landmark": date(2020, 1, 1), "horizon_end": date(2021, 1, 1),
                 "eligibility_reason": "eligible", "outcome": "d3_event", "target": 1,
                 "label_known_month": date(2020, 2, 1)}
        fact = {"loan_id": raw_id, "period": date(2020, 2, 1), "delinquency_state": "D3PLUS",
                "terminal_type": None, "current_upb": 99000., "current_rate": 3.,
                "loan_age": 2, "modification": None, "assistance": None, "payment_deferral": None}
        episode = {"loan_id": raw_id, "confirmation_month": date(2020, 2, 1), "event_type": "FIRST_OBSERVED_D3"}
        for name, record in [("dim_loan", dim), ("labels", label), ("fact_loan_month", fact), ("episodes", episode)]:
            pq.write_table(pa.Table.from_pylist([record]), stage / (name + ".parquet"))
        index = {"loan_key": token, "loan_id": raw_id, "origination_year": 2020,
                 "segment": "non_relief", "classic_fico": 700, "original_ltv": 80,
                 "outcome": "d3_event", "target": 1}
        pq.write_table(pa.Table.from_pylist([index]), case / "loan-index.parquet")
        pipeline = "SYNTHETIC-pipeline-" + identifier
        write_new(case / "snapshot.json", {"case_id": identifier, "pipeline_run": pipeline,
                                         "target": TARGET, "visibility": "private",
                                         "source_years": [2020], "source_release": 47})
        write_new(case / "report.json", {"pipeline_run": pipeline, "tables": []})
        write_new(case / "foundation-complete.json", {"source_kind": "SYNTHETIC-QA"})
        write_new(case / "case-complete.json", {
            "case_id": identifier, "pipeline_run": pipeline, "status": "D01_DESCRIPTIVE_COMPLETE",
            "visibility": "private", "public_release_approved": False,
            "engine_commit": "SYNTHETIC-QA", "target_version": TARGET["version"],
            "canonical_run": str(stage.relative_to(tmp_path)), "label_run": str(stage.relative_to(tmp_path)),
            "portfolio_run": str(stage.relative_to(tmp_path)),
            "verified_inputs": [{"path": str(p.relative_to(tmp_path)), "sha256": sha256(p)} for p in stage.glob("*.parquet")],
            "outputs_sha256": {name: sha256(case / name) for name in
                               ["snapshot.json", "report.json", "loan-index.parquet", "foundation-complete.json"]}})
    return service.ResearchService(tmp_path), ids, tokens


def test_private_queries_never_return_source_id_and_reject_foreign_run_token(two_cases):
    api, ids, tokens = two_cases
    listed = api.loans(ids[0], {"outcome": "positive"})
    assert listed["total_matching"] == 1
    assert listed["rows"][0]["loan_key"] == tokens[0]
    timeline = api.timeline(ids[0], tokens[0])
    assert timeline["case_id"] == ids[0]
    assert timeline["months"][0]["delinquency_state"] == "D3PLUS"
    assert "SYNTHETIC-source-id" not in json.dumps([listed, timeline])
    assert "loan_id" not in json.dumps([listed, timeline])
    assert api.loans(ids[1], {"q": tokens[0]})["total_matching"] == 0
    with pytest.raises(KeyError):
        api.timeline(ids[1], tokens[0])


def test_foreign_loan_context_cannot_be_saved_as_finding(two_cases):
    api, ids, tokens = two_cases
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(api))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:" + str(server.server_port)
    payload = {"case_id": ids[1], "title": "SYNTHETIC-QA", "body": "synthetic note",
               "view": "lifecycle", "filters": {"loan_key": tokens[0]}, "evidence_refs": ["loan_timeline"]}
    headers = {"Origin": base, "X-CreditAtlas-Client": "local", "Content-Type": "application/json"}
    try:
        request = urllib.request.Request(base + "/api/findings", data=json.dumps(payload).encode(), headers=headers)
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=5)
        assert error.value.code == 404
        assert api.reviews.list(ids[1]) == []
        payload["filters"]["loan_key"] = tokens[1]
        with urllib.request.urlopen(urllib.request.Request(
                base + "/api/findings", data=json.dumps(payload).encode(), headers=headers), timeout=5) as response:
            assert response.status == 201
            assert json.load(response)["filters"]["loan_key"] == tokens[1]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
