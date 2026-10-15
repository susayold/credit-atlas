"""Inspectable source/engine evidence; no automatic research readiness."""
import shutil
from .workspace import load_engine, read_json, contained, sha256


def inventory(root):
    upstream = load_engine(root)
    assets = read_json(root / "workspace.local.json")["annual_assets"]
    sources = []
    for asset in assets:
        archive = contained(root, asset["archive"])
        receipt = read_json(contained(root, asset["receipt"]))
        sources.append({"sha256_matches": sha256(archive) == asset["sha256"] == receipt["sha256"],
                        "bytes": archive.stat().st_size,
                        "original_filename": receipt["original_filename"],
                        "release": receipt["release"],
                        "research_use_confirmed": receipt["research_use_confirmed"],
                        "public_release_approved": receipt["public_release_approved"]})
    return {"module": "P2", "case": "D01", "engine_commit": upstream["commit"],
            "engine_files_verified": len(upstream["files"]), "sources": sources,
            "free_bytes": shutil.disk_usage(root).free,
            "model_training_ready": False, "inventory_is_rebuild_evidence": False}
