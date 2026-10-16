from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "acquire_hmda_national_snapshot.py"
SPEC = importlib.util.spec_from_file_location("acquire_hmda_national_snapshot", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def make_zip(path: Path, members: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return path


def test_extract_accepts_ffiec_macos_sidecar_but_extracts_only_csv(tmp_path: Path) -> None:
    archive = make_zip(tmp_path / "source.zip", {
        "2025_public_ts_csv.csv": b"activity_year,lei\n2025,example\n",
        "__MACOSX/._2025_public_ts_csv.csv": b"resource fork metadata",
    })

    result = MODULE.extract_single_csv(archive, tmp_path / "out", max_uncompressed=1024)

    assert result["member"] == "2025_public_ts_csv.csv"
    assert Path(result["path"]).read_bytes() == b"activity_year,lei\n2025,example\n"
    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["2025_public_ts_csv.csv"]


def test_extract_rejects_unexpected_archive_member(tmp_path: Path) -> None:
    archive = make_zip(tmp_path / "source.zip", {
        "data.csv": b"a\n1\n",
        "readme.txt": b"unexpected",
    })

    with pytest.raises(MODULE.AcquisitionError, match="Unexpected non-CSV"):
        MODULE.extract_single_csv(archive, tmp_path / "out", max_uncompressed=1024)


def test_extract_rejects_traversal_csv_member(tmp_path: Path) -> None:
    archive = make_zip(tmp_path / "source.zip", {"../data.csv": b"a\n1\n"})

    with pytest.raises(MODULE.AcquisitionError, match="Unsafe CSV member"):
        MODULE.extract_single_csv(archive, tmp_path / "out", max_uncompressed=1024)
