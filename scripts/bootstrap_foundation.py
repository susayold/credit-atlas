"""Pin a clean local mortgage engine and reuse existing authorized source assets.

This does not download annual data, accept source terms or copy old derived runs.
It preserves the existing research-use receipt for the same immutable raw ZIP.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True).stdout


def pin(root: Path, repo: Path) -> dict:
    if root.resolve().drive.upper() != "D:" or repo.resolve().drive.upper() != "D:":
        raise ValueError("Project and source workspace must be on D:")
    if git(repo, "status", "--porcelain").strip():
        raise ValueError("Inspect existing local changes before pinning the engine")
    commit = git(repo, "rev-parse", "HEAD").decode().strip()
    vendor = root / "vendor/credit_risk_strategy_lab"
    if vendor.exists():
        raise FileExistsError("Engine already pinned; inspect its receipt instead of overwriting")
    prefixes = ("src/", "sql/", "contracts/", "configs/", "tests/", "scripts/", "docs/")
    names = git(repo, "ls-files").decode().splitlines()
    selected = [n for n in names if n.startswith(prefixes) or n in
                {"pyproject.toml", "requirements-dev.lock", "requirements-models.lock"}]
    receipt_files = []
    for name in selected:
        target = vendor / name
        target.parent.mkdir(parents=True, exist_ok=True)
        content = git(repo, "show", f"{commit}:{name}")
        target.write_bytes(content)
        receipt_files.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
    receipt = {"repository": "https://github.com/susayold/credit-risk-strategy-lab",
               "commit": commit, "pinned_at": datetime.now(timezone.utc).isoformat(),
               "method": "selective_git_blob_copy", "raw_data_included": False,
               "old_derived_runs_included": False, "files": receipt_files}
    (vendor / "UPSTREAM.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for name in ("source_documents/release47", "raw"):
        source_dir = repo / "data/private" / name
        target_dir = vendor / "data/private" / name
        target_dir.mkdir(parents=True, exist_ok=True)
        for source in source_dir.iterdir():
            if source.is_file():
                shutil.copyfile(source, target_dir / source.name)
    raw_receipts = list((vendor / "data/private/raw").glob("*.receipt.json"))
    annual = []
    for path in raw_receipts:
        source_receipt = json.loads(path.read_text(encoding="utf-8"))
        archive = path.with_name(source_receipt["sha256"] + ".zip")
        if (source_receipt.get("research_use_confirmed") is not True or
                source_receipt.get("data_kind") != "annual_sample" or
                source_receipt.get("release") != 47 or digest(archive) != source_receipt["sha256"]):
            raise ValueError("Existing annual research-use/source receipt is not valid")
        annual.append({"archive": str(archive.relative_to(root)),
                       "receipt": str(path.relative_to(root)), "sha256": digest(archive)})
    if not annual:
        raise ValueError("No verified authorized annual source was found")
    private = root / "artifacts/private"
    private.mkdir(parents=True, exist_ok=True)
    inventory = {"created_at": datetime.now(timezone.utc).isoformat(),
                 "engine_commit": commit, "engine_files": len(selected),
                 "source_repo": str(repo), "authorized_annual_assets": annual,
                 "old_artifacts_reused": False, "model_training_ready": False}
    (private / "bootstrap-inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (root / "workspace.local.json").write_text(json.dumps({"annual_assets": annual}, indent=2) + "\n", encoding="utf-8")
    return {"engine_commit": commit, "engine_files": len(selected), "annual_assets": len(annual)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repo", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(pin(Path(__file__).resolve().parents[1], args.source_repo.resolve()), indent=2))
