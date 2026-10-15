"""Measure actual local frozen API requests; write private receipt, no model claims."""
import json
import math
import statistics
import threading
import time
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new


def run(root):
    output = root / "artifacts/private" / ("api-benchmark-" + uuid.uuid4().hex[:12])
    output.mkdir()
    started = time.perf_counter()
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    cases = service.runs()["runs"]
    selected = next(c for c in cases if c["descriptive_status"] == "verified_rebuild")
    case_id = selected["case_id"]
    startup = time.perf_counter() - started
    loans = service.loans(case_id, {"outcome": "positive", "limit": "3"})["rows"]
    if len(loans) != 3:
        raise ValueError("Three actual loans are required for the timeline benchmark")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = "http://127.0.0.1:" + str(server.server_port)

    def request(route, **query):
        before = time.perf_counter()
        with urllib.request.urlopen(base + route + "?" + urlencode({"run": case_id, **query}), timeout=20) as response:
            data = json.load(response)
            if "case_id" in data and data["case_id"] != case_id:
                raise ValueError("Benchmark response mixed case lineage")
        return time.perf_counter() - before

    try:
        measurements = []
        for route in ["/api/snapshot", "/api/monitoring", "/api/studies", "/api/episode-followup", "/api/period-transitions", "/api/report", "/api/loans", "/api/timeline"]:
            query = {"loan_key": loans[0]["loan_key"]} if route.endswith("timeline") else {}
            first = request(route, **query)
            samples = [request(route, **({"loan_key": loans[i % 3]["loan_key"]} if route.endswith("timeline") else {}))
                       for i in range(12)]
            ordered = sorted(samples)
            p95 = ordered[math.ceil(.95 * len(ordered)) - 1]
            budget = 3 if route.endswith("timeline") else 2
            measurements.append({"route": route, "first_request_seconds": first, "samples_seconds": samples,
                                 "warm_p50_seconds": statistics.median(samples), "warm_p95_seconds": p95,
                                 "warm_max_seconds": max(samples), "planning_budget_seconds": budget,
                                 "planning_budget_met": p95 <= budget})
        receipt = {"status": "MEASURED", "completed_at": timestamp(), "case_id": case_id,
                   "source_loans": selected["loans"], "source_loan_months": selected["loan_months"],
                   "startup_verification_seconds": startup, "requests_per_route": 13,
                   "mode": "sequential_loopback_HTTP_on_current_machine", "measurements": measurements,
                   "limitations": ["Small engineering sample; not a production load test.",
                                   "Filesystem caches and concurrent desktop work are uncontrolled.",
                                   "First request may reuse process/OS work from prior routes.",
                                   "Timeline samples rotate three actual positive loans; no claim over every loan."],
                   "visibility": "private", "public_release_approved": False}
        write_new(output / "receipt.json", receipt)
        print(json.dumps({"output": str(output), "measurements": [
            {"route": m["route"], "warm_p95_seconds": round(m["warm_p95_seconds"], 4),
             "budget_met": m["planning_budget_met"]} for m in measurements]}, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    run(app_root())
