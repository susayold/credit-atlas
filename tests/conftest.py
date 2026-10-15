"""Skip only tests that require deliberately omitted local research payloads."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def pytest_collection_modifyitems(config, items):
    root = Path(config.rootpath)
    if (root / "data/private").exists() and (root / "artifacts/private").exists():
        return
    manifest = root / "tests/public_private_data_skiplist.json"
    if not manifest.is_file():
        return
    requirements = json.loads(manifest.read_text(encoding="utf-8"))
    skipped_nodes = set(requirements["test_nodes"])
    marker = pytest.mark.skip(reason=requirements["reason"])
    for item in items:
        stable_node = item.nodeid.split("[", 1)[0]
        if stable_node in skipped_nodes:
            item.add_marker(marker)
