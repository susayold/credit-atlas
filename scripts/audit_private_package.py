"""Check the served bundle and Git candidate exclusions against the actual case."""
import json
import re
import subprocess
import uuid

import duckdb

from credit_atlas.server import STATIC
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root, sha256, timestamp, write_new


def run(root):
    output = root / "artifacts/private" / ("package-audit-" + uuid.uuid4().hex[:12])
    output.mkdir()
    service = ResearchService(root, review_path=output / "qa-reviews.sqlite3")
    selected = next(case for case in service.runs()["runs"] if case["descriptive_status"] == "verified_rebuild")
    case = service.case(selected["case_id"])
    with duckdb.connect() as db:
        identities = [row[0] for row in db.read_parquet(str(case["path"] / "loan-index.parquet"))
                      .project("loan_id").fetchall()]
    pattern = re.compile("|".join(re.escape(identifier) for identifier in identities).encode("ascii"))
    web = root / "apps/web"
    allowed = set(STATIC.values())
    actual = {path.relative_to(web).as_posix() for path in web.rglob("*") if path.is_file()}
    if actual != allowed:
        raise ValueError("The static directory must match the explicit served-asset allowlist")
    inventory = []
    for name in sorted(allowed):
        file = web / name
        if not file.resolve().is_relative_to(web.resolve()):
            raise ValueError("Static asset escapes the served directory")
        # Assets include binary PNG backgrounds; inspect bytes so the privacy
        # scan covers every served asset without assuming a text encoding.
        if pattern.search(file.read_bytes()):
            raise ValueError("Actual source identity found in a static asset")
        inventory.append({"asset": name, "bytes": file.stat().st_size, "sha256": sha256(file)})
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=root, capture_output=True, text=True, check=True)
    candidates = [name.replace("\\", "/") for name in result.stdout.splitlines()]
    forbidden = ("data/private/", "artifacts/private/", ".venv/", ".cache/", ".tmp/",
                 "vendor/credit_risk_strategy_lab/data/private/", "vendor/credit_risk_strategy_lab/artifacts/")
    if any(path == "workspace.local.json" or path == ".workspace-source.lock" or path.startswith(forbidden)
           for path in candidates):
        raise ValueError("Private workspace material is included in Git candidates")
    receipt = {"status": "PASS", "completed_at": timestamp(), "case_id": selected["case_id"],
               "source_identifiers_checked": len(identities), "static_assets": inventory,
               "git_candidate_files": len(candidates), "private_paths_in_git_candidates": 0,
               "scope": "explicit served static bundle plus Git private-path exclusions",
               "limitations": ["Not an authorization to publish source-derived data.",
                               "Free-text future edits and external deployment need a fresh check.",
                               "Identifier scan applies to the static bundle, not every documentation example."],
               "visibility": "private", "public_release_approved": False}
    write_new(output / "receipt.json", receipt)
    print(json.dumps({"status": "PASS", "output": str(output),
                      "static_assets": len(inventory), "source_identifiers_checked": len(identities)}, indent=2))


if __name__ == "__main__":
    run(app_root())
