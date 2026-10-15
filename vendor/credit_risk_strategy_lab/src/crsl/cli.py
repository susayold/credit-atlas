"""CLI intentionally stops at source qualification; no model shortcuts."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from . import __version__
from .contracts import SCHEMA_VERSION
from .ingest import stage_member
from .qualification import profile, qualify
from .source import fetch_public, copy_annual, select_pair, sha256, utc_now, write_json_new, verify_official_headers

def default_root() -> Path:
    return Path(__file__).resolve().parents[2]

def code_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for base, pattern in ((root/"src/crsl", "*.py"), (root/"sql", "*.sql"),
                          (root/"contracts", "*.json"), (root/"configs", "*.json")):
        for path in sorted(base.rglob(pattern)):
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()

def git_state(root: Path) -> dict:
    def command(*args):
        # Trust only this explicitly selected local project for this invocation;
        # do not alter global Git safe.directory settings.
        out = subprocess.run(["git", "-c", f"safe.directory={root.resolve().as_posix()}",
                              "-C", str(root), *args], capture_output=True, text=True)
        return out.stdout.strip() if out.returncode == 0 else None
    status = command("status", "--porcelain")
    return {"commit": command("rev-parse", "--verify", "HEAD"),
            "dirty": None if status is None else bool(status),
            "status_available": status is not None}

def inspect_archive(root: Path, path: Path, kind: str, release: int = 47,
                    batch_size: int = 10000) -> tuple[Path, dict]:
    if release != 47:
        raise ValueError("Unsupported release; cannot infer positional mapping from vintage")
    with zipfile.ZipFile(path) as archive:
        pair = select_pair(archive, kind)
    archive_hash = sha256(path)
    implementation_hash = code_fingerprint(root)
    fingerprint = hashlib.sha256(
        (archive_hash + implementation_hash + SCHEMA_VERSION + kind).encode()).hexdigest()
    run_id = fingerprint[:12] + "-" + uuid.uuid4().hex[:8]
    run_dir = root / "artifacts/private" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {
        "run_id": run_id, "input_fingerprint": fingerprint,
        "started_at": utc_now(), "source_sha256": archive_hash,
        "code_sha256": implementation_hash, "schema_version": SCHEMA_VERSION,
        "release": release, "data_kind": kind, "visibility": "private",
        "public_release_approved": False, "python": platform.python_version(),
        "package_version": __version__, "git": git_state(root),
    }
    write_json_new(run_dir / "run-start.json", manifest)
    try:
        staged = [stage_member(path, member, table, run_dir/table, batch_size,
                               format_example=(kind == "format_example"))
                  for table, member in zip(("origination", "performance"), pair)]
        if any(item["status"] != "PASS" for item in staged):
            result = {"run_id": run_id, "status": "FAIL", "ingestion": staged,
                      "research_ready": False, "reason": "Parsing failed; no research profile released"}
        else:
            measured = profile(run_dir/"origination/staging.parquet",
                               run_dir/"performance/staging.parquet", root/"sql")
            result = {"run_id": run_id, "status": "PROFILED", "ingestion": staged,
                      **measured, **qualify(kind, staged, measured)}
        manifest.update({"completed_at": utc_now(), "result_status": result["status"],
                         "research_ready": result["research_ready"]})
        write_json_new(run_dir/"result.json", result)
        write_json_new(run_dir/"run-complete.json", manifest)
        return run_dir, result
    except Exception as error:
        # Preserve evidence and partial attempt. Do not publish it as successful.
        write_json_new(run_dir/"run-failed.json", {
            "run_id": run_id, "failed_at": utc_now(), "exception_type": type(error).__name__,
            "research_ready": False})
        raise

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("source-fetch")
    commands.add_parser("inspect-public-example")
    annual = commands.add_parser("inspect-annual")
    annual.add_argument("--archive", type=Path, required=True)
    annual.add_argument("--release", type=int, required=True)
    annual.add_argument("--research-use-confirmed", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "source-fetch":
            receipts = fetch_public(root)
            verify_official_headers(root)
            print(json.dumps({"downloaded_or_verified": len(receipts),
                              "visibility": "private", "annual_access": "user_required"}, indent=2))
            return 0
        if args.command == "inspect-public-example":
            # Also verifies cache hashes; no unverified source passed downstream.
            fetch_public(root)
            verify_official_headers(root)
            path = root/"data/private/source_documents/release47/format-example.zip"
            kind = "format_example"
        else:
            fetch_public(root)
            verify_official_headers(root)
            path = copy_annual(root, args.archive.resolve(), args.release, args.research_use_confirmed)
            kind = "annual_sample"
        run_dir, result = inspect_archive(root, path, kind)
        print(json.dumps({"run_dir": str(run_dir), "status": result["status"],
                          "summary": result.get("summary"),
                          "gates": result.get("gates"), "reason": result.get("reason"),
                          "research_ready": result["research_ready"]}, indent=2, allow_nan=False))
        # 2 = expected research gate blocked; 1 = operational/parse failure.
        return 1 if result["status"] == "FAIL" else (0 if result["research_ready"] else 2)
    except (OSError, ValueError, PermissionError, zipfile.BadZipFile) as error:
        print(f"Source operation blocked: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
