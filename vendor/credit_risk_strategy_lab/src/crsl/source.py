"""Explicit official-source retrieval. No authentication or agreement acceptance."""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import stat
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

PUBLIC_SOURCES = {
    "format-example.zip": "https://www.freddiemac.com/fmac-resources/research/docs/release-47-sample-files.zip",
    "headers.zip": "https://www.freddiemac.com/fmac-resources/research/docs/file_headers_july_2026.zip",
    "layout.xlsx": "https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx",
    "guide.pdf": "https://www.freddiemac.com/fmac-resources/research/pdf/general_user_guide_july_2026.pdf",
    "release-notes.pdf": "https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf",
    "changes.pdf": "https://www.freddiemac.com/fmac-resources/research/pdf/disclosure-changes-summary.pdf",
    "terms.pdf": "https://capitalmarkets.freddiemac.com/crt/docs/pdfs/fre_terms_conditions_sflld.pdf",
}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def write_json_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")

def fetch_public(root: Path) -> list[dict]:
    """Download explicit public files once; refuse mutated cached files."""
    base = root / "data/private/source_documents/release47"
    base.mkdir(parents=True, exist_ok=True)
    receipts = []
    for name, url in PUBLIC_SOURCES.items():
        path = base / name
        receipt_path = base / (name + ".receipt.json")
        if path.exists() or receipt_path.exists():
            if not path.is_file() or not receipt_path.is_file():
                raise ValueError(f"Incomplete cached source: {name}; inspect manually")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt["sha256"] != sha256(path) or receipt["url"] != url:
                raise ValueError(f"Immutable source mismatch: {name}")
            receipts.append(receipt)
            continue
        temporary = base / (name + "." + uuid.uuid4().hex + ".download")
        with urlopen(Request(url, headers={"User-Agent": "CreditRiskResearch/0.1"}), timeout=45) as response:
            with temporary.open("xb") as output:
                size = 0
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    size += len(chunk)
                    if size > 100 * 1024 * 1024:
                        raise ValueError("Unexpectedly large public documentation download")
                    output.write(chunk)
            final_url = response.url
        magic = temporary.read_bytes()[:4]
        if name.endswith(".pdf") and magic != b"%PDF":
            raise ValueError(f"Not a PDF: {name}; download preserved for diagnosis")
        if name.endswith((".zip", ".xlsx")) and magic[:2] != b"PK":
            raise ValueError(f"Not a ZIP container: {name}; download preserved for diagnosis")
        receipt = dict(name=name, url=url, final_url=final_url, fetched_at=utc_now(),
                       bytes=temporary.stat().st_size, sha256=sha256(temporary),
                       release=47, visibility="private", rights="publication_pending")
        temporary.rename(path)
        write_json_new(receipt_path, receipt)
        receipts.append(receipt)
    return receipts

def safe_members(archive: zipfile.ZipFile, max_total: int = 20 * 1024**3) -> list[zipfile.ZipInfo]:
    """Validate *all* members before reading; never extract untrusted paths."""
    names, total, result = set(), 0, []
    for item in archive.infolist():
        name = item.filename
        path = PurePosixPath(name)
        if ("\\" in name or ":" in name or path.is_absolute()
                or ".." in path.parts or "\x00" in name):
            raise ValueError("Unsafe archive member path")
        if stat.S_ISLNK(item.external_attr >> 16):
            raise ValueError("Archive symlinks are not supported")
        if item.flag_bits & 1:
            raise ValueError("Encrypted archives are not supported")
        key = name.casefold()
        if key in names:
            raise ValueError("Duplicate archive member")
        names.add(key)
        total += item.file_size
        if total > max_total:
            raise ValueError("Archive exceeds declared uncompressed budget")
        if not item.is_dir():
            result.append(item)
    return result

def select_pair(archive: zipfile.ZipFile, kind: str) -> tuple[str, str]:
    members = safe_members(archive)
    by_base = {}
    for item in members:
        basename = PurePosixPath(item.filename).name
        if basename in by_base:
            raise ValueError("Ambiguous archive basenames")
        by_base[basename] = item.filename
    if kind == "format_example":
        expected = ("origination_sample_file.txt", "performance_sample_file.txt")
        if not all(name in by_base for name in expected):
            raise ValueError("Official format example members not found")
        return tuple(by_base[name] for name in expected)
    if kind != "annual_sample":
        raise ValueError("Unsupported data kind")
    orig = [name for name in by_base if re.fullmatch(r"sample_orig_\d{4}\.txt", name)]
    if len(orig) != 1:
        raise ValueError("Expected exactly one Release 47 annual origination file")
    year = re.search(r"(\d{4})\.txt$", orig[0]).group(1)
    perf = f"sample_perf_{year}.txt"
    if perf not in by_base:
        raise ValueError("Matching annual performance file missing")
    if len(members) != 2:
        raise ValueError("Annual archive contains unexpected files; review source before ingestion")
    return by_base[orig[0]], by_base[perf]

def copy_annual(root: Path, archive: Path, release: int, confirmed: bool) -> Path:
    if release != 47:
        raise ValueError("Only explicitly mapped Release 47 is supported")
    if not confirmed:
        raise PermissionError("User confirmation of permitted internal research is required")
    with zipfile.ZipFile(archive) as zipped:
        select_pair(zipped, "annual_sample")
    digest = sha256(archive)
    base = root / "data/private/raw"
    base.mkdir(parents=True, exist_ok=True)
    target = base / (digest + ".zip")
    receipt_path = base / (digest + ".receipt.json")
    if target.exists():
        if sha256(target) != digest:
            raise ValueError("Cached annual raw changed")
    else:
        with archive.open("rb") as source, target.open("xb") as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
    if not receipt_path.exists():
        write_json_new(receipt_path, {
            "sha256": digest, "release": release, "data_kind": "annual_sample",
            "research_use_confirmed": True, "received_at": utc_now(),
            "original_filename": archive.name, "visibility": "private",
            "release_confirmation": "user_supplied; not authenticated by file hash registry",
            "public_release_approved": False})
    return target

def verify_official_headers(root: Path) -> dict:
    expected = json.loads((root / "contracts/official-headers-release47.json").read_text(encoding="utf-8"))
    archive_path = root / "data/private/source_documents/release47/headers.zip"
    with zipfile.ZipFile(archive_path) as archive:
        members = safe_members(archive)
        observed = {item.filename: archive.read(item).decode("utf-8-sig").strip().split("|")
                    for item in members}
    if observed != expected:
        raise ValueError("Official headers changed: explicit positional contract review required")
    return {"status": "PASS", "sha256": sha256(archive_path),
            "field_counts": {name: len(fields) for name, fields in observed.items()}}
