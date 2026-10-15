from concurrent.futures import ThreadPoolExecutor
import threading
import time

import pytest

from credit_atlas.service import ResearchService


@pytest.mark.parametrize(
    ("method_name", "cache_key", "module_name"),
    [
        ("episode_followup", "episode_followup", "credit_atlas.episode_followup"),
        ("period_transitions", "period_transitions", "credit_atlas.period_transitions"),
    ],
)
def test_parallel_supplement_requests_share_one_build(monkeypatch, method_name, cache_key, module_name):
    service = object.__new__(ResearchService)
    case_id = "d01-000000000000"
    case = {"case_id": case_id, "pipeline_run": "run-1"}
    service.root = object()
    service._supplement_locks = {
        "episode_followup": threading.RLock(),
        "period_transitions": threading.RLock(),
    }
    service.case = lambda selected: case

    count_lock = threading.Lock()
    builds = 0

    def build(_root, _case):
        nonlocal builds
        with count_lock:
            builds += 1
        time.sleep(0.03)
        return {"case_id": case_id, "pipeline_run": "run-1", "rows": []}

    module = __import__(module_name, fromlist=["build"])
    monkeypatch.setattr(module, "build", build)
    method = getattr(service, method_name)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: method(case_id), range(16)))

    assert builds == 1
    assert len(results) == 16
    assert all(result["case_id"] == case_id for result in results)
    assert len({id(result) for result in results}) == len(results)

    results[0]["rows"].append({"mutated": True})
    assert results[1]["rows"] == []
