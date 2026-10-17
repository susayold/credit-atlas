"""Browser acceptance for the public national-only FHFA NMDB fallback."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from playwright.sync_api import sync_playwright

from credit_atlas import nmdb_aggregate
from credit_atlas.server import handler_for
from credit_atlas.service import ResearchService


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", required=True, type=Path,
                        help="Private local checkout containing the frozen D01 run.")
    parser.add_argument("--run", default="d01-a24484b21a21")
    parser.add_argument("--receipt", required=True, type=Path,
                        help="QA receipt path under workspace data/private/receipts.")
    args = parser.parse_args()
    workspace_root = args.workspace_root.resolve()
    receipt_path = args.receipt.resolve()
    private_receipts = (workspace_root / "data" / "private" / "receipts").resolve()
    if not receipt_path.is_relative_to(private_receipts):
        raise ValueError("QA receipt must remain under workspace data/private/receipts")
    if not args.run.startswith("d01-"):
        raise ValueError("Expected a verified D01 frozen run id")

    review_path = workspace_root / "artifacts" / "private" / "nmdb-public-fallback-browser-qa-review.sqlite3"
    service = ResearchService(workspace_root, review_path=review_path)
    original_read = nmdb_aggregate.read
    nmdb_aggregate.read = lambda _root: original_read(PROJECT_ROOT)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        handler_for(service, web_root=PROJECT_ROOT / "apps" / "web"),
    )
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    checks: list[str] = []
    page_errors: list[str] = []
    api_statuses: list[dict[str, object]] = []
    export_path = receipt_path.with_name("fhfa-nmdb-public-fallback-browser-export.json")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page(accept_downloads=True)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("response", lambda response: api_statuses.append(
                {"status": response.status, "path": "/" + response.url.split("/", 3)[-1].split("?", 1)[0]}
            ) if "/api/fhfa-nmdb-performance" in response.url else None)
            response = page.goto(
                f"http://127.0.0.1:{server.server_port}/?view=sources&run={args.run}",
                wait_until="networkidle", timeout=90_000,
            )
            if response is None or response.status != 200:
                raise RuntimeError("D01 source view did not return HTTP 200")
            panel = page.locator("#fhfa-nmdb-performance")
            panel.wait_for(state="visible", timeout=60_000)
            panel.get_by_text("National All Mortgages series observations", exact=False).wait_for(timeout=30_000)
            content = panel.inner_text()
            required = (
                "2002Q1", "2026Q2", "392",
                "does not expose or count the all-geography archive",
            )
            missing = [value for value in required if value not in content]
            if missing:
                raise AssertionError(f"Public fallback panel is missing expected scope/coverage text: {missing}")
            if panel.locator("svg").count() < 2:
                raise AssertionError("Public fallback did not render both trend charts")
            if "Aggregate source rows" in content or "Suppressed rows · all geographies" in content:
                raise AssertionError("National fallback is mislabeled as all-geography coverage")
            checks.append(
                "D01 source view renders two trends, 98 quarters and 392 national observations with national-only labels"
            )

            with page.expect_download() as download_info:
                panel.get_by_role("button", name="Xuất FHFA NMDB aggregate JSON").click()
            download = download_info.value
            download.save_as(export_path)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            if exported.get("source_package_scope") != "National / Census Areas package · National rows only":
                raise AssertionError("JSON export does not identify its national-only source package")
            if exported.get("quality", {}).get("all_geography_rows") is not None:
                raise AssertionError("JSON export claims an all-geography row count for the national fallback")
            if len(exported.get("rows", [])) != 98 or exported["quality"].get("coverage_observations") != 392:
                raise AssertionError("JSON export period/series coverage does not reconcile")
            checks.append("JSON export preserves package provenance, national coverage and null all-geography count")
            if page_errors:
                raise AssertionError(f"Browser page errors: {page_errors}")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
        nmdb_aggregate.read = original_read

    expected_paths = {"/api/fhfa-nmdb-performance", "/api/fhfa-nmdb-performance-report"}
    observed_paths = {str(item["path"]) for item in api_statuses}
    if observed_paths != expected_paths or any(item["status"] != 200 for item in api_statuses):
        raise AssertionError(f"Unexpected NMDB API statuses: {api_statuses}")
    receipt = {
        "schema_version": "fhfa-nmdb-public-fallback-browser-qa-v1",
        "status": "PASS",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkout": "public UI and API code; National/Census Areas package with verified National slice",
        "ui_route": f"/?view=sources&run={args.run}",
        "api_statuses": api_statuses,
        "coverage": {"first_period": "2002Q1", "last_period": "2026Q2", "periods": 98,
                     "national_all_mortgages_series_observations": 392, "all_geography_rows": None},
        "checks": checks,
        "page_errors": page_errors,
        "export": {"file": export_path.name, "bytes": export_path.stat().st_size,
                   "sha256": sha256(export_path)},
        "privacy": "No screenshots or borrower/loan-level records captured; export contains public FHFA aggregates only.",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
