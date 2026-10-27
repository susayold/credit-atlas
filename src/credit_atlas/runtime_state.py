"""SQLite handle for persistent local state or process-memory-only serving state."""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path


class SQLiteRuntimeState:
    """Keep the existing review schemas without creating a local DB in read-only mode."""

    def __init__(self, path: Path | None, namespace: str):
        self.ephemeral = path is None
        self.uri = self.ephemeral
        if self.ephemeral:
            self.path = f"file:credit-atlas-{namespace}-{uuid.uuid4().hex}?mode=memory&cache=shared"
            self._keeper = sqlite3.connect(self.path, uri=True, check_same_thread=False)
        else:
            self.path = Path(path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._keeper = None

    def connect(self, timeout: int = 10):
        return sqlite3.connect(str(self.path), timeout=timeout, uri=self.uri, check_same_thread=False)
