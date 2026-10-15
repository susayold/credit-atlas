"""Check pinned D01 runtime, copied-engine integrity, storage, and package boundaries."""
from __future__ import annotations

import importlib.metadata as md
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from credit_atlas.workspace import sha256, write_new

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor/credit_risk_strategy_lab"
FOUNDATION = ROOT / "artifacts/private/d01-a24484b21a21/foundation-complete.json"
UPSTREAM = VENDOR / "UPSTREAM.json"
LOCK = ROOT / "requirements-lock.txt"
PYPROJECT = ROOT / "pyproject.toml"

lock_entries = {}
for line in LOCK.read_text(encoding="utf-8").splitlines():
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line.strip())
    if match:
        lock_entries[match.group(1).lower().replace("_", "-")] = match.group(2)
runtime = []
version_mismatches = []
license_gaps = []
for normalized_name, version in lock_entries.items():
    try:
        dist = md.distribution(normalized_name)
    except md.PackageNotFoundError:
        version_mismatches.append({"distribution": normalized_name, "locked": version, "installed": None})
        continue
    installed = dist.version
    metadata = dist.metadata
    declared_license = metadata.get("License-Expression") or metadata.get("License")
    if installed != version:
        version_mismatches.append({"distribution": normalized_name, "locked": version, "installed": installed})
    if not declared_license or declared_license.strip().lower() in {"unknown", "none"}:
        license_gaps.append(normalized_name)
    runtime.append({"distribution": normalized_name, "version": installed,
                    "locked_version": version, "license_metadata": declared_license})

upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
upstream_diffs = []
for item in upstream["files"]:
    path = VENDOR / item["path"]
    if not path.is_file():
        upstream_diffs.append({"path": item["path"], "reason": "missing"})
    elif sha256(path) != item["sha256"]:
        upstream_diffs.append({"path": item["path"], "reason": "sha256_mismatch"})

foundation = json.loads(FOUNDATION.read_text(encoding="utf-8"))
storage_paths = [ROOT, VENDOR, ROOT / "data/private", ROOT / "artifacts/private"]
storage = {str(path): str(path.resolve().drive) for path in storage_paths}
if any(drive.upper() != "D:" for drive in storage.values()):
    raise AssertionError(f"User project/source data escaped D: storage: {storage}")

git_result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                            cwd=ROOT, capture_output=True, text=True, check=True)
candidate_paths = [line.replace("\\", "/") for line in git_result.stdout.splitlines()]
private_prefixes = ("data/private/", "artifacts/private/", ".venv/", ".cache/", ".tmp/",
                    "vendor/credit_risk_strategy_lab/data/private/",
                    "vendor/credit_risk_strategy_lab/artifacts/")
private_candidates = [path for path in candidate_paths if path.startswith(private_prefixes)
                      or path in {"workspace.local.json", ".workspace-source.lock"}]

if version_mismatches or upstream_diffs or private_candidates:
    raise AssertionError({"version_mismatches": version_mismatches,
                          "upstream_diffs": upstream_diffs,
                          "private_candidates": private_candidates[:20]})

out = ROOT / "artifacts/private" / f"d01-release-readiness-{uuid4().hex[:12]}"
out.mkdir(parents=True, exist_ok=False)
receipt = {
    "status": "PASS", "scope": "local reproducible D01 release-readiness check; not a publication clearance",
    "python": platform.python_version(), "platform": platform.platform(),
    "root_lock_sha256": sha256(LOCK), "pyproject_sha256": sha256(PYPROJECT),
    "locked_distributions": runtime, "lock_version_mismatches": version_mismatches,
    "packages_without_declared_license_metadata": license_gaps,
    "upstream_repository": upstream["repository"], "upstream_commit": upstream["commit"],
    "upstream_files_pinned": len(upstream["files"]), "upstream_hash_differences": upstream_diffs,
    "storage_drive_by_path": storage, "git_candidate_paths": len(candidate_paths),
    "private_paths_in_git_candidates": len(private_candidates),
    "foundation_resource_measurement": foundation["resource_measurement"],
    "foundation_manifest_sha256": sha256(FOUNDATION), "raw_source_sha256": foundation["raw_sha256"],
    "source_release_authenticated": False, "external_distribution_approved": False,
    "limitations": [
        "Some installed distributions omit SPDX/license metadata; dependency/license compatibility needs a curated notice review before redistribution.",
        "The selectively copied upstream engine has no license file in this workspace; code redistribution rights were not inferred from its GitHub URL.",
        "The raw source receipt is user-supplied and does not authenticate publisher release identity or publication date.",
        "The 812 MB peak and 192-second measurement covers the clean descriptive rebuild only, not concurrent app load or full model training."
    ]
}
write_new(out / "receipt.json", receipt)
print(json.dumps({"status": "PASS", "output": str(out),
                  "locked_distributions": len(runtime), "license_metadata_gaps": len(license_gaps),
                  "upstream_pinned_files": len(upstream["files"]),
                  "private_git_candidates": len(private_candidates),
                  "resource_peak_mib": round(foundation["resource_measurement"]["peak_working_set_bytes"] / 2**20, 1)}, indent=2))
