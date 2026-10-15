"""Register authorized annual archives without approving cohorts or models."""
from __future__ import annotations

import os
import re
import shutil
import uuid
import zipfile
from pathlib import Path

from .acquisition import MAX_ZIP, verify_annual_zip
from .workspace import contained, engine_root, load_engine, read_json, sha256, timestamp, write_new


def require_technical_profile(result: dict):
    expected = {"format_parse": "PASS", "referential_integrity": "PASS",
                "research_sample_identity": "PASS_USER_ATTESTED", "history_presence_screen": "PASS",
                "source_qualification": "CANDIDATE_FOR_COHORT_REVIEW"}
    if result.get("status") != "PROFILED" or any(result.get("gates", {}).get(k) != v for k, v in expected.items()):
        raise ValueError("Annual technical source gates must pass before foundation analytics")


def validate_import(archive: Path, release: int, confirmed: bool, expected_sha256: str):
    if release != 47:
        raise ValueError("Release 47 must be explicitly identified")
    if confirmed is not True:
        raise PermissionError("Permitted internal research use must be confirmed for this archive")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("An expected lowercase SHA-256 digest is required")
    if not archive.is_file() or archive.stat().st_size > MAX_ZIP:
        raise ValueError("A bounded local annual ZIP is required")
    observed = sha256(archive)
    if observed != expected_sha256:
        raise ValueError("Archive does not match the expected source digest")
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
    origin = [name for name in names if re.fullmatch(r"sample_orig_\d{4}\.txt", name)]
    if len(origin) != 1:
        raise ValueError("Expected a Release 47 annual sample, not a format example")
    year = int(re.search(r"(\d{4})\.txt$", origin[0]).group(1))
    if not 1999 <= year <= 2026:
        raise ValueError("Unsupported annual vintage")
    verify_annual_zip(archive, year)
    return year, observed


def register_asset(root: Path, asset: dict):
    """Atomic config replacement under a single-writer lock; preserve before/after evidence."""
    archive, receipt_path = contained(root, asset["archive"]), contained(root, asset["receipt"])
    receipt = read_json(receipt_path)
    if (sha256(archive) != asset["sha256"] or receipt.get("sha256") != asset["sha256"] or
            receipt.get("research_use_confirmed") is not True or receipt.get("release") != 47 or
            receipt.get("data_kind") != "annual_sample" or receipt.get("public_release_approved") is not False):
        raise ValueError("Registered source receipt, rights and immutable archive must agree")
    config_path = root / "workspace.local.json"
    lock = root / ".workspace-source.lock"
    attempt = root / "artifacts/private" / ("source-register-" + uuid.uuid4().hex[:12])
    attempt.mkdir(parents=True)
    try:
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
            previous = read_json(config_path) if config_path.exists() else {"annual_assets": []}
            write_new(attempt / "workspace-before.json", previous)
            assets = previous.get("annual_assets")
            if not isinstance(assets, list):
                raise ValueError("Workspace annual source registry must be a list")
            for index, existing in enumerate(assets):
                if existing["sha256"] == asset["sha256"]:
                    # Existing registry entry must be identical; do not silently repair it.
                    if existing != asset:
                        raise ValueError("Existing digest has a different registry reference")
                    write_new(attempt / "receipt.json", {"status": "ALREADY_REGISTERED", "asset_index": index,
                                                       "source_sha256": asset["sha256"], "completed_at": timestamp()})
                    return index
            index = len(assets)
            updated = {**previous, "annual_assets": assets + [asset]}
            candidate = attempt / "workspace-next.json"
            write_new(candidate, updated)
            os.replace(candidate, config_path)
            write_new(attempt / "receipt.json", {"status": "REGISTERED_NOT_MODEL_QUALIFIED", "asset_index": index,
                                               "source_sha256": asset["sha256"], "completed_at": timestamp(),
                                               "workspace_sha256": sha256(config_path)})
            return index
    finally:
        # Only release a lock this attempt created.
        if "stream" in locals():
            lock.unlink(missing_ok=True)


def import_annual(root: Path, archive: Path, release: int, confirmed: bool, expected_sha256: str):
    root, archive = root.resolve(), archive.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("New private source storage must remain on D:")
    year, digest = validate_import(archive, release, confirmed, expected_sha256)
    if shutil.disk_usage(root).free < 25 * 1024**3 + archive.stat().st_size:
        raise ValueError("Insufficient source-storage headroom")
    load_engine(root)
    from crsl.source import copy_annual
    destination = copy_annual(engine_root(root), archive, release, confirmed)
    asset = {"archive": str(destination.relative_to(root)),
             "receipt": str(destination.with_suffix(".receipt.json").relative_to(root)), "sha256": digest}
    index = register_asset(root, asset)
    return {"status": "REGISTERED_NOT_MODEL_QUALIFIED", "asset_index": index, "origination_year": year,
            "sha256": digest, "research_training_ready": False,
            "next_command": "rebuild --asset-index " + str(index)}
