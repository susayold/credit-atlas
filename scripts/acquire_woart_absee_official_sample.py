"""Acquire one current World Omni ABS-EE asset XML directly from SEC EDGAR."""
from __future__ import annotations

import gzip
import hashlib
import json
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
CIK = "2046523"
ACCESSION = "000110465926111552"
REPORT_DATE = "2026-08-31"
ATTACHMENT = "woart2025aex102aug26.xml"
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"
MAX_BYTES = 256 * 1024**2


def fetch(url: str, limit: int) -> tuple[bytes, dict]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=90) as response:
        if response.status != 200 or response.url != url:
            raise ValueError("Unexpected SEC response status or redirect")
        payload = response.read(limit + 1)
        if not payload or len(payload) > limit:
            raise ValueError("Empty or oversized SEC response")
        return payload, {
            "url": response.url,
            "http_status": response.status,
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }


def acquire() -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    folder = ROOT / "data/private/structured" / ("woart-absee-official-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    index_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/index.json"
    index_bytes, index_meta = fetch(index_url, 2 * 1024**2)
    index = json.loads(index_bytes)
    entries = {item["name"]: item for item in index["directory"]["item"]}
    if ATTACHMENT not in entries or int(entries[ATTACHMENT]["size"]) > MAX_BYTES:
        raise ValueError("Expected bounded asset-level XML attachment absent from official filing index")
    attachment_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/{ATTACHMENT}"
    request = Request(attachment_url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    archive_path = folder / (ATTACHMENT + ".gz")
    raw_digest = hashlib.sha256()
    raw_size = 0
    prefix = bytearray()
    with urlopen(request, timeout=90) as response:
        if response.status != 200 or response.url != attachment_url:
            raise ValueError("Unexpected SEC response status or redirect")
        xml_meta = {
            "url": response.url,
            "http_status": response.status,
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }
        if xml_meta["content_type"] != "text/xml":
            raise ValueError("SEC attachment is not text/xml")
        with archive_path.open("xb") as target:
            with gzip.GzipFile(filename=ATTACHMENT, mode="wb", fileobj=target, mtime=0) as zipped:
                while True:
                    chunk = response.read(1024**2)
                    if not chunk:
                        break
                    raw_size += len(chunk)
                    if raw_size > MAX_BYTES:
                        raise ValueError("SEC XML exceeded the download size limit")
                    raw_digest.update(chunk)
                    if len(prefix) < 4096:
                        prefix.extend(chunk[:4096 - len(prefix)])
                    zipped.write(chunk)
    if not bytes(prefix).lstrip().startswith(b"<assetData ") or b"<reportingPeriodEndingDate>08-31-2026</reportingPeriodEndingDate>" not in bytes(prefix):
        raise ValueError("Downloaded attachment is not the expected WOART ABS-EE XML")
    index_path = folder / "filing-index.json"
    index_path.write_bytes(index_bytes)
    raw_hash = raw_digest.hexdigest()
    receipt = {
        "source_id": folder.name,
        "status": "SEC_OFFICIAL_ABSEE_XML_ACQUIRED",
        "issuer": "World Omni Auto Receivables Trust 2025-A",
        "cik": CIK,
        "form": "ABS-EE",
        "accession": ACCESSION,
        "report_date": REPORT_DATE,
        "attachment": ATTACHMENT,
        "official_xml_uncompressed_bytes": raw_size,
        "official_xml_sha256": raw_hash,
        "compressed_archive": archive_path.name,
        "compressed_bytes": archive_path.stat().st_size,
        "compressed_sha256": sha256(archive_path),
        "index": {
            **index_meta,
            "file": index_path.name,
            "bytes": len(index_bytes),
            "sha256": sha256(index_path),
        },
        "xml_source": {
            **xml_meta,
            "file": archive_path.name,
            "indexed_bytes": int(entries[ATTACHMENT]["size"]),
            "uncompressed_sha256": raw_hash,
            "compressed_sha256": sha256(archive_path),
        },
        "acquired_at": timestamp(),
        "script": "scripts/acquire_woart_absee_official_sample.py",
        "script_sha256": sha256(Path(__file__)),
        "visibility": "private",
        "public_release_approved": False,
        "limitations": [
            "One official monthly ABS-EE snapshot only; it is not a loan-level time series.",
            "No Conversion Date or legal effectiveness package is implied by this asset data file.",
            "ABS-EE values require a separate field-level mapping and reconciliation before modeling.",
        ],
    }
    write_new(folder / "acquisition-complete.json", receipt)
    print(folder)
    print(json.dumps({"status": receipt["status"], "report_date": REPORT_DATE,
            "uncompressed_bytes": raw_size, "compressed_bytes": receipt["compressed_bytes"]}))
    return folder


if __name__ == "__main__":
    acquire()
