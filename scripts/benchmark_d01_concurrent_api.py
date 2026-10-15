"""Bounded read-only concurrency benchmark against one verified D01 run.

This measures a local ThreadingHTTPServer, not production network or model fit.
The receipt contains timings and case lineage only; it does not record loan keys.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import statistics
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from http.server import ThreadingHTTPServer

from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, timestamp, write_new


def run(workers: int = 4, rounds: int = 3, root: Path | None = None) -> dict:
    if not 1 <= workers <= 16 or not 1 <= rounds <= 10:
        raise ValueError("workers must be 1–16 and rounds must be 1–10")

    root = (root or app_root()).resolve()
    output = root / "artifacts/private" / ("d01-api-concurrency-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    started = time.perf_counter()
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    runs = service.runs()["runs"]
    selected = next((item for item in runs
                     if item.get("descriptive_status") == "verified_rebuild"), None)
    if selected is None:
        raise RuntimeError("No verified D01 descriptive rebuild is available")
    case_id = selected["case_id"]
    startup_seconds = time.perf_counter() - started

    loan_rows = service.loans(case_id, {"outcome": "positive", "limit": "4"})["rows"]
    if not loan_rows:
        raise RuntimeError("The verified D01 run has no positive loan for timeline reads")

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(service))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    cases = [
        ("snapshot", "/api/snapshot", {}),
        ("monitoring", "/api/monitoring", {}),
        ("studies", "/api/studies", {}),
        ("episode-followup", "/api/episode-followup", {}),
        ("period-transitions", "/api/period-transitions", {}),
        ("report", "/api/report", {}),
        ("loans", "/api/loans", {"outcome": "positive", "limit": "3"}),
        ("timeline", "/api/timeline", {"loan_key": loan_rows[0]["loan_key"]}),
    ]

    def request(case: tuple[str, str, dict]) -> dict:
        name, route, params = case
        query = urllib.parse.urlencode({"run": case_id, **params})
        started_request = time.perf_counter()
        with urllib.request.urlopen(f"{base}{route}?{query}", timeout=30) as response:
            payload = json.load(response)
            if isinstance(payload, dict) and payload.get("case_id") not in (None, case_id):
                raise RuntimeError("API response mixed D01 case lineage")
        return {"route": name, "seconds": time.perf_counter() - started_request}

    # Warm each route once before measuring steady-state concurrent reads. The
    # cold path is kept separately so expensive cache construction is visible.
    cold_starts = [request(case) for case in cases]

    observations: dict[str, list[float]] = {name: [] for name, _, _ in cases}
    failures: list[dict] = []
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for _ in range(rounds):
                for name, route, params in cases:
                    batch = [(name, route, params)] * workers
                    futures = [pool.submit(request, item) for item in batch]
                    for future in futures:
                        try:
                            result = future.result()
                            observations[result["route"]].append(result["seconds"])
                        except Exception as error:  # retain type/route, never request contents
                            failures.append({"route": name, "exception_type": type(error).__name__})

        summaries = []
        for name, samples in observations.items():
            ordered = sorted(samples)
            p95 = ordered[math.ceil(0.95 * len(ordered)) - 1] if ordered else None
            summaries.append({
                "route": name,
                "successful_requests": len(samples),
                "p50_seconds": statistics.median(samples) if samples else None,
                "p95_seconds": p95,
                "max_seconds": max(samples) if samples else None,
            })
        receipt = {
            "status": "MEASURED" if not failures else "FAILED_REQUESTS",
            "completed_at": timestamp(),
            "case_id": case_id,
            "source_loans": selected.get("loans"),
            "source_loan_months": selected.get("loan_months"),
            "service_startup_seconds": startup_seconds,
            "mode": "read_only_loopback_http",
            "concurrency_workers": workers,
            "rounds_per_route": rounds,
            "expected_requests_per_route": workers * rounds,
            "cold_start_measurements": cold_starts,
            "measurements": summaries,
            "failures": failures,
            "limitations": [
                "One local machine and one verified D01 case; not production traffic.",
                "Loopback HTTP excludes network, authentication and reverse-proxy costs.",
                "Only the listed read-only API routes were exercised; no model training was run.",
                "OS cache, concurrent desktop tasks and other machine load were uncontrolled.",
            ],
            "visibility": "private",
            "public_release_approved": False,
        }
        write_new(output / "receipt.json", receipt)
        print(json.dumps({
            "status": receipt["status"],
            "receipt": str(output / "receipt.json"),
            "workers": workers,
            "rounds": rounds,
            "cold_starts": cold_starts,
            "routes": summaries,
            "failure_count": len(failures),
        }, indent=2))
        if failures:
            raise RuntimeError("Concurrent API requests failed; inspect the private receipt")
        return receipt
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--root", type=Path, default=None,
                        help="Local CreditAtlas workspace; defaults to this checkout")
    args = parser.parse_args()
    run(args.workers, args.rounds, args.root)
