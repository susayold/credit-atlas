import io
import json
import subprocess
from unittest.mock import patch

import pytest

from credit_atlas.drive_storage import DriveStorageError, RcloneDriveRoot
from credit_atlas.runtime_state import SQLiteRuntimeState


ROOT_ID = "1YCHLG7p7AMCF8hpWOvP4_iYzpqQ92h7H"


def _config_result(scope="drive.readonly", root_id=ROOT_ID):
    payload = f"[creditatlas]\ntype = drive\nscope = {scope}\nroot_folder_id = {root_id}\n".encode()
    return subprocess.CompletedProcess(["rclone"], 0, stdout=payload, stderr=b"")


def _root():
    with patch("credit_atlas.drive_storage.subprocess.run", return_value=_config_result()):
        return RcloneDriveRoot("creditatlas:", executable="rclone")


def test_drive_root_requires_read_only_scope_and_project_root():
    with patch("credit_atlas.drive_storage.subprocess.run", return_value=_config_result(scope="drive")):
        with pytest.raises(DriveStorageError, match="scope drive.readonly"):
            RcloneDriveRoot("creditatlas:", executable="rclone")
    with patch("credit_atlas.drive_storage.subprocess.run", return_value=_config_result(root_id="wrong")):
        with pytest.raises(DriveStorageError, match="verified Credit Atlas root"):
            RcloneDriveRoot("creditatlas:", executable="rclone")


def test_drive_paths_reject_traversal_and_writes():
    root = _root()
    with pytest.raises(ValueError, match="escapes"):
        root / "data/../outside.json"
    with pytest.raises(ValueError, match="ending in"):
        RcloneDriveRoot("creditatlas:data", executable="rclone")
    with pytest.raises(PermissionError, match="read-only"):
        (root / "receipt.json").open("wb")


def test_drive_file_metadata_and_content_are_streamed_through_rclone():
    root = _root()
    metadata = {"Name": "receipt.json", "Size": 8, "ModTime": "2026-10-28T00:00:00Z", "IsDir": False}
    stat_result = subprocess.CompletedProcess(["rclone"], 0, stdout=json.dumps(metadata).encode(), stderr=b"")
    with patch("credit_atlas.drive_storage.subprocess.run", return_value=stat_result) as run:
        info = (root / "artifacts/private/receipt.json").stat()
    assert info.st_size == 8
    assert info.st_mtime_ns > 0
    run.assert_called_once_with(
        ["rclone", "lsjson", "--stat", "creditatlas:artifacts/private/receipt.json"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    class Process:
        def __init__(self):
            self.stdout = io.BytesIO(b"receipt")

        def wait(self):
            return 0

    with patch("credit_atlas.drive_storage.subprocess.Popen", return_value=Process()) as popen:
        with (root / "artifacts/private/receipt.json").open("rb") as stream:
            assert stream.read() == b"receipt"
    popen.assert_called_once_with(
        ["rclone", "cat", "creditatlas:artifacts/private/receipt.json"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )


def test_ephemeral_runtime_state_uses_shared_memory_database():
    state = SQLiteRuntimeState(None, "test")
    assert state.ephemeral is True
    assert str(state.path).startswith("file:credit-atlas-test-")
    with state.connect() as db:
        db.execute("CREATE TABLE marker (value TEXT)")
        db.execute("INSERT INTO marker VALUES ('memory-only')")
    with state.connect() as db:
        assert db.execute("SELECT value FROM marker").fetchone()[0] == "memory-only"
