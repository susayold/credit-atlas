"""Acquire World Omni 2025-A closing agreements and the filed 2026 amendment from SEC EDGAR."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
CIK_PATH = "2046523"
UA = "OpenAI Codex Credit Atlas research (https://openai.com)"
SEC = "https://www.sec.gov/Archives/edgar/data/2046523"
FILES = [
    {
        "accession": "000110465925007200",
        "form": "8-K",
        "file": "tm252785d11_8k.htm",
        "role": "2025-01-29 closing filing",
        "expected": "WORLD OMNI AUTO RECEIVABLES TRUST 2025-A",
    },
    {
        "accession": "000110465925007200",
        "form": "EX-4.1",
        "file": "tm252785d11_ex4-1.htm",
        "role": "executed Sale and Servicing Agreement",
        "expected": "SALE AND SERVICING AGREEMENT",
    },
    {
        "accession": "000110465925007200",
        "form": "EX-4.2",
        "file": "tm252785d11_ex4-2.htm",
        "role": "executed Indenture",
        "expected": "INDENTURE",
    },
    {
        "accession": "000110465925007200",
        "form": "EX-4.3",
        "file": "tm252785d11_ex4-3.htm",
        "role": "executed Trust Agreement",
        "expected": "TRUST AGREEMENT",
    },
    {
        "accession": "000110465925007200",
        "form": "EX-99.1",
        "file": "tm252785d11_ex99-1.htm",
        "role": "executed Receivables Purchase Agreement",
        "expected": "RECEIVABLES PURCHASE AGREEMENT",
    },
    {
        "accession": "000110465925007200",
        "form": "EX-99.2",
        "file": "tm252785d11_ex99-2.htm",
        "role": "executed Administration Agreement",
        "expected": "ADMINISTRATION AGREEMENT",
    },
    {
        "accession": "000110465925007200",
        "form": "EX-99.3",
        "file": "tm252785d11_ex99-3.htm",
        "role": "executed Asset Representations Review Agreement",
        "expected": "ASSET REPRESENTATIONS REVIEW AGREEMENT",
    },
    {
        "accession": "000110465926005075",
        "form": "8-K",
        "file": "tm263585d12_8k.htm",
        "role": "2026-01-13 Omnibus Amendment filing",
        "expected": "WORLD OMNI AUTO RECEIVABLES TRUST 2025-A",
    },
    {
        "accession": "000110465926005075",
        "form": "EX-4.1",
        "file": "tm263585d12_ex4-1.htm",
        "role": "executed Omnibus Amendment to Sale and Servicing Agreement",
        "expected": "OMNIBUS AMENDMENT TO SALE AND SERVICING AGREEMENT",
    },
]


def fetch(url: str, destination: Path, limit: int = 8 * 1024 * 1024) -> dict:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "www.sec.gov":
        raise ValueError(f"Unexpected SEC URL: {url}")
    time.sleep(0.25)
    request = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json"})
    size = 0
    partial = destination.with_suffix(destination.suffix + ".partial")
    try:
        with urlopen(request, timeout=60) as response:
            if response.status != 200 or urlsplit(response.geturl()).hostname != "www.sec.gov":
                raise ValueError(f"Unexpected response: {response.status} {response.geturl()}")
            with partial.open("xb") as stream:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    size += len(block)
                    if size > limit:
                        raise ValueError(f"SEC document exceeds size bound: {destination.name}")
                    stream.write(block)
            if not size:
                raise ValueError(f"Empty SEC response: {url}")
            partial.replace(destination)
            return {
                "url": url,
                "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
                "bytes": size,
                "sha256": sha256(destination),
                "retrieved_at": timestamp(),
            }
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def main() -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    folder = ROOT / "data/private/structured" / f"woart-legal-source-{uuid.uuid4().hex[:12]}"
    folder.mkdir(parents=True, exist_ok=False)
    write_new(folder / "acquisition-start.json", {
        "status": "STARTED",
        "deal": "World Omni Auto Receivables Trust 2025-A",
        "cik": CIK_PATH,
        "source": "SEC EDGAR Archives",
        "user_agent": UA,
        "started_at": timestamp(),
    })
    downloaded = []
    try:
        accessions = sorted({entry["accession"] for entry in FILES})
        for accession in accessions:
            url = f"{SEC}/{accession}/index.json"
            name = f"{accession}_index.json"
            meta = fetch(url, folder / name, 2 * 1024 * 1024)
            index_data = json.loads((folder / name).read_text(encoding="utf-8"))
            listed = {item["name"] for item in index_data["directory"]["item"]}
            required = [entry["file"] for entry in FILES if entry["accession"] == accession]
            missing = sorted(set(required) - listed)
            if missing:
                raise ValueError(f"SEC filing index omits expected files {accession}: {missing}")
            downloaded.append({"accession": accession, "form": "index.json", "file": name, **meta})
        for entry in FILES:
            url = f"{SEC}/{entry['accession']}/{entry['file']}"
            path = folder / entry["file"]
            meta = fetch(url, path)
            content = path.read_text(encoding="utf-8", errors="replace").upper()
            if entry["expected"] not in content:
                raise ValueError(f"Downloaded filing title check failed: {entry['file']}")
            if "WORLD OMNI AUTO RECEIVABLES TRUST 2025-A" not in content:
                raise ValueError(f"Deal identity not present in {entry['file']}")
            downloaded.append({**entry, **meta})
            print(entry["file"], meta["bytes"], meta["sha256"], flush=True)
        receipt = {
            "status": "SEC_CLOSING_AGREEMENTS_AND_AMENDMENT_ACQUIRED",
            "source_id": folder.name,
            "deal": "World Omni Auto Receivables Trust 2025-A",
            "cik": CIK_PATH,
            "completed_at": timestamp(),
            "filings": downloaded,
            "script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
            "script_sha256": sha256(Path(__file__)),
            "amendment_scope": "Omnibus SSA Amendment filed Jan 20 2026, dated/effective Jan 13 2026 subject to stated conditions; Conversion Date is not specified in the amendment.",
            "visibility": "private",
            "public_release_approved": False,
            "limitations": [
                "This acquisition collects filings and agreement text; it is not legal advice or complete executed-document counsel review.",
                "No Conversion Date, Rating Agency Condition package, or legal opinion delivery evidence was independently acquired.",
                "No asset-level receivables schedule or current contractual waterfall qualification is implied.",
            ],
        }
        write_new(folder / "acquisition-complete.json", receipt)
        print(folder, flush=True)
        return folder
    except Exception as error:
        write_new(folder / "acquisition-failed.json", {
            "status": "INCOMPLETE",
            "error_type": type(error).__name__,
            "http_status": error.code if isinstance(error, HTTPError) else None,
            "files_downloaded": downloaded,
            "failed_at": timestamp(),
        })
        raise


if __name__ == "__main__":
    main()
