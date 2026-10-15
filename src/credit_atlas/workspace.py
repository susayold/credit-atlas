"""Workspace boundaries, immutable engine verification and safe JSON IO."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def contained(base: Path, name: str) -> Path:
    """Resolve a project-relative path and refuse traversal/symlink escapes."""
    candidate = (base / name).resolve()
    if not candidate.is_relative_to(base.resolve()):
        raise ValueError("Path is outside the configured workspace")
    return candidate


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def engine_root(root: Path) -> Path:
    return root / "vendor/credit_risk_strategy_lab"


def load_engine(root: Path) -> dict:
    vendor = engine_root(root)
    provenance = read_json(vendor / "UPSTREAM.json")
    for item in provenance["files"]:
        if sha256(contained(vendor, item["path"])) != item["sha256"]:
            raise ValueError(f"Pinned upstream engine changed: {item['path']}")
    source = str(vendor / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    return provenance


def completed_cases(root: Path) -> list[tuple[Path, dict]]:
    cases = []
    for path in sorted((root / "artifacts/private").glob("d01-*/case-complete.json")):
        case = read_json(path)
        if case.get("status") == "D01_DESCRIPTIVE_COMPLETE":
            cases.append((path.parent, case))
    return sorted(cases, key=lambda item: item[1]["completed_at"], reverse=True)
