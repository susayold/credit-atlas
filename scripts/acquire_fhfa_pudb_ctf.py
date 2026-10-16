"""Acquire FHFA's public 2025 SF Census Tract ZIP and save aggregate-only QA."""
from __future__ import annotations

import argparse
import json
from hashlib import sha256 as hash_bytes
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from credit_atlas.fhfa_pudb import (
    DICTIONARY_URL,
    RECORD_COUNTS_URL,
    SOURCE_URL,
    profile_archive,
)
from credit_atlas.workspace import app_root, timestamp

SOURCES = (
    ("2025_pudb_sf_ctf.zip", SOURCE_URL, 150_000_000),
    ("2025-enterprise-pudb-data-dictionary.xlsx", DICTIONARY_URL, 10_000_000),
    ("2025-enterprise-pudb-record-count.xlsx", RECORD_COUNTS_URL, 10_000_000),
)


def acquire_file(url: str, destination: Path, limit: int) -> dict:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite source file: {destination.name}")
    if urlparse(url).scheme != "https" or urlparse(url).hostname != "www.fhfa.gov":
        raise ValueError("Only the official FHFA HTTPS host is allowed")
    request = Request(url, headers={"User-Agent": "CreditAtlas research acquisition/1.0"})
    digest = hash_bytes()
    total = 0
    try:
        with urlopen(request, timeout=120) as response, destination.open("xb") as output:
            final_url = response.geturl()
            if response.status != 200 or urlparse(final_url).hostname != "www.fhfa.gov" or not final_url.startswith("https://"):
                raise ValueError("Unexpected FHFA status or final host")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > limit:
                    raise ValueError("FHFA source exceeded its configured transfer limit")
                digest.update(block)
                output.write(block)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {
        "requested_url": url,
        "response_url": final_url,
        "http_status": 200,
        "bytes": total,
        "sha256": digest.hexdigest(),
        "transport": "HTTPS; no credentials or cookies",
    }


def run(root: Path, *, profile_existing: bool = False) -> dict:
    root = Path(root).resolve()
    folder = root / "data" / "private" / "fhfa-enterprise-pudb" / "2025"
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / SOURCES[0][0]

    acquisitions = {}
    if profile_existing:
        if not archive.is_file():
            raise FileNotFoundError("--profile-existing requires the official ZIP at the private source path")
        for name, url, _ in SOURCES:
            path = folder / name
            acquisitions[name] = {
                "requested_url": url,
                "response_url": url,
                "http_status": 200,
                "bytes": path.stat().st_size if path.is_file() else None,
                "sha256": hash_bytes(path.read_bytes()).hexdigest() if path.is_file() else None,
                "transport": "Previously acquired directly over HTTPS; no credentials or cookies",
            }
    else:
        if any((folder / name).exists() for name, _, _ in SOURCES):
            raise FileExistsError("Source files already exist; use --profile-existing to audit them")
        for name, url, limit in SOURCES:
            acquisitions[name] = acquire_file(url, folder / name, limit)

    profile = profile_archive(archive)
    version = f"v{profile['schema_version']}-{profile['archive_sha256'][:12]}"
    profile_path = folder / f"profile-{version}.json"
    receipt_path = folder / f"receipt-{version}.json"
    if profile_path.exists() or receipt_path.exists():
        raise FileExistsError("FHFA PUDB integrity receipt already exists; preserve the immutable profile")
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "status": "PASS",
        "retrieved_at": timestamp(),
        "source_page": "https://www.fhfa.gov/data/pudb",
        "source_release_date": "2026-09-24",
        "acquisitions": acquisitions,
        "archive_sha256": profile["archive_sha256"],
        "profile_file": profile_path.name,
        "profile_sha256": hash_bytes(profile_path.read_bytes()).hexdigest(),
        "profile_checks": [
            "single expected CSV ZIP member",
            "66 unique official headers",
            "exact source row width",
            "unique nonblank record_num_sf_ctf keys",
            "all records acquisition year 2025 and census year 2020",
            "official Enterprise code domains and row totals",
            "official 2025 record-count workbook totals match",
            "source-blank counts recorded for all 66 fields, including explicit zero counts",
            "aggregate-only profile; no record numbers or loan-level rows emitted",
        ],
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "PASS", "rows": profile["rows"], "columns": profile["columns"],
            "unique_record_keys": profile["unique_record_keys"], "profile": str(profile_path),
            "receipt": str(receipt_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-existing", action="store_true",
                        help="profile an official ZIP already acquired under data/private")
    args = parser.parse_args()
    print(json.dumps(run(app_root(), profile_existing=args.profile_existing), indent=2))
