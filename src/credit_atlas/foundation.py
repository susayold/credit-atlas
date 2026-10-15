"""Rebuild D01 from authorized immutable source; no model gate shortcuts."""
from __future__ import annotations

import ctypes
import importlib.util
import shutil
import sys
import time
import uuid
from pathlib import Path

from .workspace import (contained, engine_root, load_engine, read_json,
                        sha256, timestamp, write_new)
from .source_registry import require_technical_profile


def peak_memory_bytes() -> int | None:
    if sys.platform != "win32":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
            "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    counter = Counters()
    counter.cb = ctypes.sizeof(counter)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
    if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counter), counter.cb):
        return counter.PeakWorkingSetSize
    return None


def rebuild(root: Path, asset_index: int = 0) -> Path:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("All new project data and artifacts must remain on D:")
    provenance = load_engine(root)
    from crsl import cli, pipeline, portfolio_profile, segmented_transitions
    from crsl.source import fetch_public, verify_official_headers

    assets = read_json(root / "workspace.local.json")["annual_assets"]
    if not 0 <= asset_index < len(assets):
        raise ValueError("Invalid configured annual asset")
    asset = assets[asset_index]
    archive = contained(root, asset["archive"])
    receipt_path = contained(root, asset["receipt"])
    receipt = read_json(receipt_path)
    if (receipt.get("research_use_confirmed") is not True or
            receipt.get("release") != 47 or receipt.get("data_kind") != "annual_sample" or
            sha256(archive) != receipt.get("sha256") or receipt["sha256"] != asset["sha256"]):
        raise ValueError("Existing source-use confirmation and immutable archive must match")
    if shutil.disk_usage(root).free < 25 * 1024**3:
        raise ValueError("Insufficient storage headroom for a new full-data run")
    output = root / "artifacts/private" / ("d01-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True, exist_ok=False)
    start = {"started_at": timestamp(), "engine_commit": provenance["commit"],
             "raw_sha256": receipt["sha256"], "visibility": "private",
             "public_release_approved": False, "model_training_performed": False}
    write_new(output / "case-start.json", start)
    before = shutil.disk_usage(root).free
    clock = time.perf_counter()
    vendor = engine_root(root)
    try:
        fetch_public(vendor)  # verifies cached official assets; does not accept terms
        verify_official_headers(vendor)
        print("source: re-inspecting authorized annual ZIP", flush=True)
        source, result = cli.inspect_archive(vendor, archive, "annual_sample", release=47)
        require_technical_profile(result)
        print("source: PROFILED; rebuilding foundation", flush=True)
        foundation = pipeline.run(vendor, source)
        manifest = read_json(foundation / "run-complete.json")
        stages = {item["stage"]: vendor / "artifacts/private" / item["output_run"]
                  for item in manifest["stages"]}
        segmented = segmented_transitions.run(vendor, stages["canonical"])
        profile = portfolio_profile.run(vendor, stages["canonical"])
        start.update({"completed_at": timestamp(), "status": "D01_FOUNDATION_REBUILT",
                      "source_run": str(source.relative_to(root)),
                      "source_manifest_sha256": sha256(source / "run-complete.json"),
                      "pipeline_run": str(foundation.relative_to(root)),
                      "pipeline_manifest_sha256": sha256(foundation / "run-complete.json"),
                      "segmented_run": str(segmented.relative_to(root)),
                      "segmented_manifest_sha256": sha256(segmented / "run-complete.json"),
                      "profile_run": str(profile.relative_to(root)),
                      "profile_manifest_sha256": sha256(profile / "run-complete.json"),
                      "source_use_receipt_sha256": sha256(receipt_path),
                      "source_summary": result["summary"],
                      "resource_measurement": {"wall_seconds": round(time.perf_counter() - clock, 3),
                          "peak_working_set_bytes": peak_memory_bytes(), "free_bytes_before": before,
                          "free_bytes_after": shutil.disk_usage(root).free},
                      "research_training_ready": False})
        write_new(output / "foundation-complete.json", start)
        return output
    except Exception as error:
        write_new(output / "case-failed.json", {"failed_at": timestamp(),
                  "exception_type": type(error).__name__, "research_training_ready": False})
        raise


def compare_rebuild(root: Path, case_dir: Path) -> dict:
    """Rerun the same foundation source and verify the complete upstream scope."""
    load_engine(root)
    from crsl.pipeline import run
    vendor = engine_root(root)
    case = read_json(case_dir / "foundation-complete.json")
    source = contained(root, case["source_run"])
    left = contained(root, case["pipeline_run"])
    right = run(vendor, source)
    script = vendor / "scripts/compare_pipeline_runs.py"
    spec = importlib.util.spec_from_file_location("crsl_compare_pipeline_runs", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.compare(vendor, left, right)
    path = write_reproduction_receipt(case_dir, result)
    result["receipt_path"] = str(path.relative_to(root))
    return result


def write_reproduction_receipt(case_dir: Path, result: dict) -> Path:
    """Keep the original proof immutable and store later reproductions by run ID."""
    primary = case_dir / "reproduction.json"
    if not primary.exists():
        write_new(primary, result)
        return primary
    right_pipeline = result.get("right_pipeline")
    if not isinstance(right_pipeline, str) or not right_pipeline.startswith("pipeline-"):
        raise ValueError("A versioned reproduction requires its pipeline run ID")
    versioned = case_dir / f"reproduction-{right_pipeline}.json"
    write_new(versioned, result)
    return versioned
