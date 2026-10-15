"""Rebuild the public release inventory from Git-visible, nonignored files."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "PUBLIC_FILE_MANIFEST.json"


def main() -> None:
    paths = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    ).decode("utf-8").split("\0")
    files: dict[str, str] = {}
    total_bytes = 0
    for name in sorted(path for path in paths if path and path != MANIFEST):
        content = (ROOT / name).read_bytes()
        if b"\0" not in content:
            content = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        files[name] = hashlib.sha256(content).hexdigest()
        total_bytes += len(content)
    manifest = {
        "files": len(files),
        "bytes": total_bytes,
        "hash_basis": "SHA-256 of Git-normalized LF text; binary files hashed as-is",
        "excluded_private_data": True,
        "sha256": files,
    }
    (ROOT / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(files), "bytes": total_bytes, "manifest": MANIFEST}))


if __name__ == "__main__":
    main()
