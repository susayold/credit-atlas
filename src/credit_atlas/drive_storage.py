"""Read-only, streaming access to a workspace rooted in a configured rclone remote.

The remote must use a read-only provider scope. File contents are read with
``rclone cat`` and flow through process pipes; this module never downloads them
to a local workspace or cache directory.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from typing import BinaryIO, TextIO

_CREDIT_ATLAS_DRIVE_ROOT_ID = "1YCHLG7p7AMCF8hpWOvP4_iYzpqQ92h7H"


class DriveStorageError(OSError):
    """The configured read-only Drive remote could not serve a workspace file."""


@dataclass(frozen=True)
class RemoteStat:
    st_size: int
    st_mtime_ns: int

    @property
    def st_mtime(self) -> float:
        return self.st_mtime_ns / 1_000_000_000


class RcloneDriveRoot:
    """A virtual workspace root backed by a named rclone remote (for example ``creditatlas:``)."""

    def __init__(self, remote: str, *, executable: str | None = None):
        if not isinstance(remote, str) or not re.fullmatch(r"[A-Za-z0-9._-]+:", remote):
            raise ValueError("Drive remote must be a configured rclone remote name ending in ':'")
        self.remote = remote
        self.executable = executable or shutil.which("rclone")
        if not self.executable:
            raise DriveStorageError("rclone is required for the configured Drive-backed workspace")
        self._verify_remote_configuration()

    def _verify_remote_configuration(self) -> None:
        result = subprocess.run(
            [self.executable, "config", "redacted", self.remote[:-1]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise DriveStorageError("The rclone remote is not configured; use a project-rooted read-only Drive remote")
        try:
            lines = result.stdout.decode("utf-8").splitlines()
        except UnicodeDecodeError as error:
            raise DriveStorageError("The rclone remote configuration could not be verified") from error
        config = {}
        for line in lines:
            key, separator, value = line.partition("=")
            if separator:
                config[key.strip()] = value.strip()
        if (config.get("type") != "drive" or config.get("scope") != "drive.readonly"
                or config.get("root_folder_id") != _CREDIT_ATLAS_DRIVE_ROOT_ID):
            raise DriveStorageError(
                "Configure the Drive remote with scope drive.readonly and the verified Credit Atlas root folder"
            )

    def resolve(self) -> "RcloneDriveRoot":
        return self

    def __truediv__(self, relative: str) -> "RcloneDrivePath":
        return RcloneDrivePath(self, relative)


class RcloneDrivePath:
    """Path-like, read-only view used by the existing verified receipt readers."""

    def __init__(self, root: RcloneDriveRoot, relative: str = ""):
        if not isinstance(relative, str) or "\\" in relative or ":" in relative:
            raise ValueError("Drive workspace paths must be project-relative POSIX paths")
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            if relative != "":
                raise ValueError("Drive workspace path escapes the configured project root")
        self.root = root
        self.relative = "" if relative == "" else path.as_posix()

    def resolve(self) -> "RcloneDrivePath":
        return self

    @property
    def name(self) -> str:
        return PurePosixPath(self.relative).name

    def is_relative_to(self, other: object) -> bool:
        if isinstance(other, RcloneDriveRoot):
            return self.root is other
        if isinstance(other, RcloneDrivePath):
            if self.root is not other.root:
                return False
            return self.relative == other.relative or self.relative.startswith(other.relative.rstrip("/") + "/")
        return False

    def __truediv__(self, relative: str) -> "RcloneDrivePath":
        suffix = str(relative)
        combined = f"{self.relative}/{suffix}" if self.relative else suffix
        return RcloneDrivePath(self.root, combined)

    def _remote_path(self) -> str:
        return self.root.remote + self.relative

    def _run_json_stat(self) -> dict:
        result = subprocess.run(
            [self.root.executable, "lsjson", "--stat", self._remote_path()],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise DriveStorageError("Drive file metadata is unavailable; check the configured read-only rclone remote")
        try:
            value = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DriveStorageError("Drive returned invalid file metadata") from error
        if not isinstance(value, dict):
            raise DriveStorageError("Drive returned invalid file metadata")
        return value

    def is_file(self) -> bool:
        return not bool(self._run_json_stat().get("IsDir"))

    def is_dir(self) -> bool:
        return bool(self._run_json_stat().get("IsDir"))

    def stat(self) -> RemoteStat:
        value = self._run_json_stat()
        raw_time = value.get("ModTime")
        mtime_ns = 0
        if isinstance(raw_time, str) and raw_time:
            try:
                parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                mtime_ns = int(parsed.timestamp() * 1_000_000_000)
            except ValueError:
                mtime_ns = 0
        try:
            size = 0 if value.get("IsDir") else int(value["Size"])
        except (KeyError, TypeError, ValueError) as error:
            raise DriveStorageError("Drive file metadata omitted its byte size") from error
        return RemoteStat(st_size=size, st_mtime_ns=mtime_ns)

    def glob(self, pattern: str) -> list["RcloneDrivePath"]:
        """List matching direct children without recursively scanning the project."""
        if (not isinstance(pattern, str) or not pattern or "/" in pattern or "\\" in pattern
                or pattern in {".", ".."}):
            raise ValueError("Drive glob patterns must match direct child names only")
        result = subprocess.run(
            [self.root.executable, "lsjson", self._remote_path()],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            raise DriveStorageError("Drive directory listing failed; check the configured read-only remote")
        try:
            entries = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DriveStorageError("Drive returned an invalid directory listing") from error
        if not isinstance(entries, list):
            raise DriveStorageError("Drive returned an unexpected directory listing")
        import fnmatch

        paths = []
        for entry in entries:
            name = entry.get("Name") if isinstance(entry, dict) else None
            if (not isinstance(name, str) or not name or name in {".", ".."}
                    or "/" in name or "\\" in name):
                continue
            if fnmatch.fnmatchcase(name, pattern):
                paths.append(self / name)
        return paths

    def open(self, mode: str = "r", *, encoding: str | None = None, errors: str | None = None,
             newline: str | None = None):
        if mode not in {"r", "rt", "rb"}:
            raise PermissionError("Drive-backed workspace is read-only")
        process = subprocess.Popen(
            [self.root.executable, "cat", self._remote_path()],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        if process.stdout is None:
            process.kill()
            raise DriveStorageError("Could not open a Drive content stream")
        stream: BinaryIO | TextIO
        stream = process.stdout if mode == "rb" else io.TextIOWrapper(
            process.stdout, encoding=encoding or "utf-8", errors=errors, newline=newline
        )
        return _CheckedRcloneStream(process, stream)

    def read_bytes(self) -> bytes:
        with self.open("rb") as stream:
            return stream.read()

    def read_text(self, encoding: str = "utf-8", errors: str | None = None) -> str:
        with self.open("r", encoding=encoding, errors=errors) as stream:
            return stream.read()

    def open_seekable(self) -> "_RcloneRangeReader":
        """Open a bounded, in-memory-block-cached range reader for ZIP metadata access."""
        return _RcloneRangeReader(self)


class _RcloneRangeReader(io.RawIOBase):
    """Seekable remote reader using bounded rclone range requests, never local files."""

    _BLOCK_SIZE = 1024 * 1024
    _MAX_CACHED_BLOCKS = 4

    def __init__(self, path: RcloneDrivePath):
        super().__init__()
        self.path = path
        self.size = path.stat().st_size
        self.position = 0
        self.blocks: OrderedDict[int, bytes] = OrderedDict()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def tell(self) -> int:
        self._checkClosed()
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        self._checkClosed()
        if whence == io.SEEK_SET:
            target = offset
        elif whence == io.SEEK_CUR:
            target = self.position + offset
        elif whence == io.SEEK_END:
            target = self.size + offset
        else:
            raise ValueError("Invalid seek mode")
        if target < 0:
            raise ValueError("Negative seek position")
        self.position = target
        return target

    def readinto(self, buffer) -> int:
        self._checkClosed()
        view = memoryview(buffer).cast("B")
        if not view:
            return 0
        remaining = min(len(view), max(0, self.size - self.position))
        copied = 0
        while copied < remaining:
            block_number = self.position // self._BLOCK_SIZE
            block_offset = self.position % self._BLOCK_SIZE
            block = self._read_block(block_number)
            count = min(remaining - copied, len(block) - block_offset)
            if count <= 0:
                raise DriveStorageError("Drive range response ended before the declared file size")
            view[copied:copied + count] = block[block_offset:block_offset + count]
            copied += count
            self.position += count
        return copied

    def _read_block(self, block_number: int) -> bytes:
        cached = self.blocks.get(block_number)
        if cached is not None:
            self.blocks.move_to_end(block_number)
            return cached
        offset = block_number * self._BLOCK_SIZE
        count = min(self._BLOCK_SIZE, self.size - offset)
        result = subprocess.run(
            [self.path.root.executable, "cat", "--offset", str(offset), "--count", str(count),
             self.path._remote_path()],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0 or len(result.stdout) != count:
            raise DriveStorageError("Drive range read failed or returned incomplete bytes")
        self.blocks[block_number] = result.stdout
        self.blocks.move_to_end(block_number)
        while len(self.blocks) > self._MAX_CACHED_BLOCKS:
            self.blocks.popitem(last=False)
        return result.stdout

    def close(self) -> None:
        self.blocks.clear()
        super().close()


class _CheckedRcloneStream:
    def __init__(self, process: subprocess.Popen, stream: BinaryIO | TextIO):
        self.process = process
        self.stream = stream

    def __enter__(self):
        return self.stream

    def __exit__(self, exc_type, exc_value, traceback):
        self.stream.close()
        return_code = self.process.wait()
        if exc_type is None and return_code != 0:
            raise DriveStorageError("Drive content stream failed; check remote access and network status")
        return False
