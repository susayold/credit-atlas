"""Runtime acceptance for the public-safe project-register API and static UI assets."""
from __future__ import annotations

import hashlib
import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from credit_atlas.server import LocalResearchServer, handler_for  # noqa: E402

RECEIPT = ROOT / "docs/data/project-register-api-runtime-qa-2026-10-18.json"


class EmptyRunCatalogService:
    """Small service stub; the register route does not depend on research runs."""

    root = ROOT
    sec_views = None

    def runs(self):
        return {"runs": []}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get(base_url: str, path: str) -> tuple[int, bytes]:
    try:
        with urlopen(base_url + path, timeout=15) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def main() -> int:
    with patch("credit_atlas.server.MonitorReviews", return_value=SimpleNamespace()), patch(
        "credit_atlas.server.CorporateMemos", return_value=SimpleNamespace()
    ):
        server = LocalResearchServer(
            ("127.0.0.1", 0), handler_for(EmptyRunCatalogService(), web_root=ROOT / "apps/web")
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            checks: list[str] = []
            for path in ("/?view=register", "/app.js", "/project-register.js", "/style.css"):
                status, body = get(base_url, path)
                assert status == 200 and body, (path, status, len(body))
                checks.append(f"GET {path}: 200, {len(body)} bytes")

            status, run_body = get(base_url, "/api/runs")
            assert status == 200 and json.loads(run_body) == {"runs": []}
            checks.append("GET /api/runs: 200, empty verified-run catalog")

            status, payload = get(base_url, "/api/project-register")
            assert status == 200
            data = json.loads(payload)
            assert len(data["datasets"]) == 29
            assert len(data["source_records"]) == 125
            assert len(data["method_cards"]) == 15
            assert len(data["capabilities"]) == 50
            method_by_id = {row["id"]: row for row in data["method_cards"]}
            source_by_id = {row["source_id"]: row for row in data["source_records"]}
            macro_group = next(row for row in data["datasets"]
                               if row["id"] == "fred-alfred-macro-market-context")
            assert len(macro_group["source_release_record_ids"]) == 11
            assert all(source_by_id[source_id]["registry_group_id"] == macro_group["id"]
                       for source_id in macro_group["source_release_record_ids"])
            direct_unrate = source_by_id["bls-unrate-direct-2026-09"]
            assert direct_unrate["source_series_id"] == "LNS14000000"
            assert direct_unrate["native_row_count"] == 945
            assert direct_unrate["model_qualified_in_receipt"] is False
            fhfa_group = next(row for row in data["datasets"]
                              if row["id"] == "fhfa-hpi-geographic-context")
            assert len(fhfa_group["source_release_record_ids"]) == 2
            assert all(source_by_id[source_id]["registry_group_id"] == fhfa_group["id"]
                       for source_id in fhfa_group["source_release_record_ids"])
            direct_hpi = source_by_id["fhfa-us-census-all-transactions-hpi-2026q2"]
            assert direct_hpi["native_row_count"] == 2060
            assert direct_hpi["model_qualified_in_receipt"] is False
            assert all(row["source_release_record_ids"] for row in method_by_id.values())
            assert sum(len(row["source_release_record_ids"]) for row in method_by_id.values()) == 50
            assert sum(bool(row["method_card_ids"]) for row in source_by_id.values()) == 33
            for method in method_by_id.values():
                assert method["evidence_refs"]
                for source_id in method["source_release_record_ids"]:
                    assert method["id"] in source_by_id[source_id]["method_card_ids"]
            for source in source_by_id.values():
                for method_id in source["method_card_ids"]:
                    assert source["source_id"] in method_by_id[method_id]["source_release_record_ids"]
            lendingclub = method_by_id["lendingclub-source-population-and-label-readiness"]
            assert lendingclub["evidence_refs"] == [
                "docs/LENDINGCLUB_FULL_SOURCE_VI.md",
                "docs/LENDINGCLUB_SOURCE_PROFILE_VI.md",
                "docs/LENDINGCLUB_DICTIONARY_REVIEW_VI.md",
            ]
            assert "World Omni" in method_by_id["structured-abs-surveillance"]["source_linkage_note"]
            progress = data["progress"]
            assert (progress["completed"], progress["requirements"], progress["fraction"]) == (26, 50, 0.52)
            domain_counts = {row["id"]: f"{row['completed']}/{row['requirements']}" for row in progress["domains"]}
            assert domain_counts == {"P1": "6/10", "P2": "9/10", "P3": "8/10", "P4": "3/10", "P5": "0/10"}
            gates = [[row["id"], row["status"]] for row in progress["d01_release_gates"]]
            assert gates == [["R0", "Partial"], ["R1", "Accepted with scope"], ["R2", "Open"], ["R3", "Open"], ["R4", "Partial"]]
            checks.extend((
                "GET /api/project-register: 200; 29 dataset groups, 125 source records, 15 method cards, 50 capabilities; 10 FRED/ALFRED + direct BLS UNRATE and 2 FHFA HPI records bound to source groups",
                "All 15 method cards have repository evidence paths; source-to-method lineage is reciprocal across 50 links and 33 source rows",
                "LendingClub card exposes three existing evidence documents; structured ABS scope excludes World Omni from the 103-period finding",
                "Progress reconciles to authoritative ledger: 26/50 (52%); P1 6/10, P2 9/10, P3 8/10, P4 3/10, P5 0/10",
                "D01 R0-R4 statuses match the project register",
            ))

            status, error_body = get(base_url, "/api/project-register?unexpected=1")
            assert status == 400 and json.loads(error_body).get("error")
            checks.append("GET /api/project-register with unsupported filter: 400")

            app_js = (ROOT / "apps/web/app.js").read_text(encoding="utf-8")
            assert app_js.count('"monitor","suite","register","retail"') >= 2
            checks.append("Frontend init includes register in both no-run and run-error fallbacks")

            inputs = (
                "apps/web/app.js",
                "apps/web/project-register.js",
                "src/credit_atlas/project_register.py",
                "src/credit_atlas/server.py",
                "docs/COMPLETION_REQUIREMENTS_50.json",
                "docs/data/creditatlas-project-register-2026-10-17.json",
                "docs/data/creditatlas-source-release-register-2026-10-17.json",
                "docs/data/n02-source-to-kpi-map-2026-10-17.json",
                "docs/N02_SOURCE_TO_KPI_TRACEABILITY_2026-10-17_VI.md",
                "docs/PROJECT_REVIEW_RESEARCH_ADDENDUM_2026-10-18_VI.md",
                "docs/PROJECT_REVIEW_AND_NEXT_PLAN_2026-10-16_VI.md",
                "docs/BLS_UNRATE_DIRECT_SOURCE_REVIEW_VI.md",
                "docs/FHFA_US_CENSUS_HPI_DIRECT_SOURCE_REVIEW_VI.md",
                "docs/PUBLIC_MORTGAGE_CONTEXT.md",
                "scripts/acquire_bls_unrate.py",
                "scripts/acquire_public_mortgage_context.py",
                "scripts/compare_fhfa_us_hpi_to_fred.py",
                "src/credit_atlas/fhfa_hpi.py",
                "src/credit_atlas/mortgage_macro_context.py",
                "src/credit_atlas/server.py",
                "tests/test_project_register.py",
                "tests/test_bls_unrate.py",
                "tests/test_mortgage_macro_context.py",
            )
            receipt = {
                "evidence_type": "project_register_api_runtime_acceptance",
                "status": "PASS",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "Actual server handler, project-register API, reciprocal method/source lineage, evidence paths, and served static assets with an empty mortgage-run catalog. Browser visual/render acceptance is not claimed.",
                "checks": len(checks),
                "check_details": checks,
                "api_summary": {"datasets": 29, "source_records": 125, "method_cards": 15, "method_cards_with_source_lineage": 15, "method_source_links": 50, "source_records_with_method_links": 33, "capabilities": 50, "completed": 26, "requirements": 50, "fraction": 0.52, "domain_counts": domain_counts, "d01_gates": gates},
                "empty_run_catalog": True,
                "private_data_loaded": False,
                "raw_rows_or_credentials_in_receipt": False,
                "source_sha256": {relative: sha256(ROOT / relative) for relative in inputs},
            }
            RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
            print(json.dumps({"status": "PASS", "checks": len(checks), "receipt": str(RECEIPT)}, ensure_ascii=False))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
