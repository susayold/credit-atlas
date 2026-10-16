"""Bounded acquisition of official U.S. Treasury HAMP performance ZIPs."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


SOURCE_PAGE = "https://home.treasury.gov/data/troubled-assets-relief-program/reports/mha-public-file"
DATASETS = {
    "2009-2017": {
        "file": "HMP_Govt_Agency_Perf_Data_20090101_20171201.zip",
        "url": "https://mhadatafile.treasury.gov/Prod/reports/HMP_Govt_Agency_Perf_Data_20090101_20171201.zip",
    },
    "2018-2023": {
        "file": "HMP_Govt_Agency_Perf_Data.zip",
        "url": "https://home.treasury.gov/system/files/256/HMP_Govt_Agency_Perf_Data.zip",
    },
}
ALLOWED_HOSTS = {"home.treasury.gov", "mhadatafile.treasury.gov"}
MAX_BYTES = 3 * 1024**3
MIN_FREE_BYTES = 1024**3


class AcquisitionError(ValueError):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urlsplit(new_url)
        if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.fragment):
            raise AcquisitionError("Treasury data redirected outside the official HTTPS hosts")
        return super().redirect_request(request, response, code, message, headers, new_url)


def acquire(root: Path, release: str) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise AcquisitionError("Treasury source files and receipts must stay on D:")
    try:
        metadata = DATASETS[release]
    except KeyError as exc:
        raise AcquisitionError("Select a listed HAMP performance release") from exc
    parsed = urlsplit(metadata["url"])
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise AcquisitionError("Unapproved Treasury source URL")

    opener = urllib.request.build_opener(OfficialRedirects())
    head = urllib.request.Request(metadata["url"], method="HEAD",
                                  headers={"User-Agent": "CreditAtlas official data audit/1.0"})
    try:
        with opener.open(head, timeout=60) as response:
            size = int(response.headers.get("Content-Length", "0"))
            modified = response.headers.get("Last-Modified")
            content_type = response.headers.get_content_type().casefold()
            final_url = response.geturl()
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as exc:
        raise AcquisitionError("Treasury file metadata request failed") from exc
    if (size <= 0 or size > MAX_BYTES or content_type not in {"application/zip", "application/octet-stream"}
            or urlsplit(final_url).hostname not in ALLOWED_HOSTS):
        raise AcquisitionError("Treasury response is not a bounded ZIP with valid metadata")
    if shutil.disk_usage(root).free < size + MIN_FREE_BYTES:
        raise AcquisitionError("Insufficient free space on D: for the Treasury ZIP and safety margin")

    data_dir = root / "data/private/mortgage/treasury-hamp" / release
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / metadata["file"]
    partial = data_dir / (metadata["file"] + ".partial")
    if target.exists() or partial.exists():
        raise AcquisitionError("Treasury ZIP or partial download already exists; preserve and inspect it first")
    request = urllib.request.Request(metadata["url"], headers={
        "User-Agent": "CreditAtlas official data audit/1.0",
        "Accept": "application/zip,application/octet-stream",
    })
    digest = hashlib.sha256()
    received = 0
    try:
        with opener.open(request, timeout=60) as response:
            actual_type = response.headers.get_content_type().casefold()
            actual_size = int(response.headers.get("Content-Length", "0"))
            if (response.status != 200 or actual_type not in {"application/zip", "application/octet-stream"}
                    or actual_size != size):
                raise AcquisitionError("Treasury download headers differ from the validated metadata")
            with partial.open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    received += len(chunk)
                    if received > size or received > MAX_BYTES:
                        raise AcquisitionError("Treasury download exceeded the bounded Content-Length")
                    digest.update(chunk)
                    stream.write(chunk)
        if received != size or not zipfile.is_zipfile(partial):
            raise AcquisitionError("Treasury download is incomplete or is not a ZIP archive")
        with zipfile.ZipFile(partial) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if not members or any(item.flag_bits & 1 for item in members):
                raise AcquisitionError("Treasury ZIP has no data members or contains encrypted members")
            corrupt_member = archive.testzip()
            if corrupt_member:
                raise AcquisitionError("Treasury ZIP CRC validation failed")
            member_summary = [{"name": item.filename, "bytes": item.file_size, "crc32": f"{item.CRC:08x}"}
                              for item in members]
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    audit_id = "treasury-hamp-acq-" + uuid.uuid4().hex[:12]
    receipt = {
        "schema_version": 1,
        "status": "DOWNLOADED_PENDING_SOURCE_AUDIT",
        "audit_id": audit_id,
        "release": release,
        "source_page": SOURCE_PAGE,
        "source_url": metadata["url"],
        "final_url": final_url,
        "file_name": metadata["file"],
        "last_modified": modified,
        "content_type": content_type,
        "bytes": received,
        "sha256": digest.hexdigest(),
        "downloaded_at_utc": timestamp(),
        "members": member_summary,
        "private_path": str(target),
        "visibility": "private",
        "loan_rows_emitted": False,
        "public_release_approved": False,
    }
    receipt_dir = root / "artifacts/private" / audit_id
    receipt_dir.mkdir(parents=True, exist_ok=False)
    with (receipt_dir / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return {key: receipt[key] for key in (
        "status", "audit_id", "release", "file_name", "last_modified", "bytes", "sha256", "members")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    parser.add_argument("--release", choices=sorted(DATASETS), required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(acquire(args.root, args.release), indent=2, ensure_ascii=False))
    except (OSError, AcquisitionError, urllib.error.URLError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
