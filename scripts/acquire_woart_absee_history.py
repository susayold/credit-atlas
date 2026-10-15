"""Acquire contiguous official monthly World Omni ABS-EE XML snapshots from SEC."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import uuid
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
CIK = "2046523"
ISSUER = "World Omni Auto Receivables Trust 2025-A"
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"
MAX_XML_BYTES = 256 * 1024**2
PERIODS = [date(y, m, 1).replace(day=__import__("calendar").monthrange(y, m)[1])
           for y, m in [(y, m) for y in (2025, 2026) for m in range(1, 13)]
           if date(y, m, 1) >= date(2025, 1, 1) and date(y, m, 1) <= date(2026, 8, 1)]


def get(url: str, limit: int) -> tuple[bytes, dict]:
    time.sleep(0.25)
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


def acquire_xml(folder: Path, accession: str, filename: str, report_date: date) -> dict:
    url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}/{filename}"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    path = folder / (report_date.strftime("%Y-%m") + ".xml.gz")
    digest = hashlib.sha256()
    size = 0
    prefix = bytearray()
    time.sleep(0.25)
    with urlopen(request, timeout=120) as response:
        if response.status != 200 or response.url != url or response.headers.get("Content-Type") != "text/xml":
            raise ValueError("Unexpected SEC XML response")
        meta = {"url": response.url, "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag")}
        with path.open("xb") as target:
            with gzip.GzipFile(filename=filename, mode="wb", fileobj=target, mtime=0) as zipped:
                while True:
                    chunk = response.read(1024**2)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_XML_BYTES:
                        raise ValueError("ABS-EE XML exceeded the per-file bound")
                    digest.update(chunk)
                    if len(prefix) < 4096:
                        prefix.extend(chunk[:4096 - len(prefix)])
                    zipped.write(chunk)
    expected = report_date.strftime("%m-%d-%Y").encode()
    if not bytes(prefix).lstrip().startswith(b"<assetData ") or b"<reportingPeriodEndingDate>" + expected + b"</reportingPeriodEndingDate>" not in prefix:
        raise ValueError(f"XML root/reporting date mismatch for {report_date}")
    return {**meta, "file": path.name, "attachment": filename, "accession": accession,
            "report_date": report_date.isoformat(), "uncompressed_bytes": size,
            "uncompressed_sha256": digest.hexdigest(), "compressed_bytes": path.stat().st_size,
            "compressed_sha256": sha256(path)}


def acquire() -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    folder = ROOT / "data/private/structured" / ("woart-absee-history-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    submissions_url = f"https://data.sec.gov/submissions/CIK{CIK.zfill(10)}.json"
    submissions_bytes, submissions_meta = get(submissions_url, 4 * 1024**2)
    submissions_path = folder / "sec-submissions.json"
    submissions_path.write_bytes(submissions_bytes)
    submissions = json.loads(submissions_bytes)
    if str(submissions.get("cik", "")).zfill(10) != CIK.zfill(10) or submissions.get("name") != ISSUER:
        raise ValueError("SEC submissions identity mismatch")
    recent = submissions["filings"]["recent"]
    selected = {}
    for i, form in enumerate(recent["form"]):
        if form != "ABS-EE" or not recent["reportDate"][i]:
            continue
        report_date = date.fromisoformat(recent["reportDate"][i])
        if report_date in PERIODS:
            accession = recent["accessionNumber"][i].replace("-", "")
            if report_date in selected:
                raise ValueError("Duplicate official ABS-EE report period")
            selected[report_date] = {
                "accession": accession,
                "filing_date": recent["filingDate"][i],
                "primary_document": recent["primaryDocument"][i],
            }
    if sorted(selected) != PERIODS:
        raise ValueError("SEC submissions do not contain every requested monthly period")

    records = []
    for report_date in PERIODS:
        filing = selected[report_date]
        accession = filing["accession"]
        index_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}/index.json"
        index_bytes, index_meta = get(index_url, 2 * 1024**2)
        index = json.loads(index_bytes)
        index_name = report_date.strftime("%Y-%m") + "-index.json"
        index_path = folder / index_name
        index_path.write_bytes(index_bytes)
        candidates = [item for item in index["directory"]["item"]
                      if re.fullmatch(r"woart2025aex102[a-z]{3}\d{2}\.xml", item["name"])]
        if len(candidates) != 1:
            raise ValueError(f"Expected one official asset-data XML attachment for {report_date}")
        if int(candidates[0]["size"]) > MAX_XML_BYTES:
            raise ValueError("Official SEC filing index advertises oversized XML")
        xml = acquire_xml(folder, accession, candidates[0]["name"], report_date)
        records.append({
            "report_date": report_date.isoformat(),
            "filing_date": filing["filing_date"],
            "primary_document": filing["primary_document"],
            "index": {**index_meta, "file": index_name, "bytes": len(index_bytes),
                      "sha256": sha256(index_path)},
            "xml": xml,
        })
        print(f"{report_date.isoformat()} {xml['uncompressed_bytes']} {xml['compressed_bytes']}", flush=True)

    receipt = {
        "source_id": folder.name,
        "status": "SEC_OFFICIAL_ABSEE_HISTORY_ACQUIRED",
        "issuer": ISSUER,
        "cik": CIK,
        "form": "ABS-EE",
        "period_count": len(records),
        "report_start": PERIODS[0].isoformat(),
        "report_end": PERIODS[-1].isoformat(),
        "submissions": {**submissions_meta, "file": submissions_path.name,
                         "bytes": len(submissions_bytes), "sha256": sha256(submissions_path)},
        "reports": records,
        "acquired_at": timestamp(),
        "script": "scripts/acquire_woart_absee_history.py",
        "script_sha256": sha256(Path(__file__)),
        "visibility": "private",
        "public_release_approved": False,
        "limitations": [
            "Official asset-level snapshots, not a stable loan-level panel until asset-key continuity is validated.",
            "No PD, default, recovery or exit labels are derived in the acquisition step.",
            "No Conversion Date or legal effectiveness package is implied by the ABS-EE data.",
            "XML is gzip-compressed losslessly; raw bytes are recoverable and hash-verified.",
        ],
    }
    write_new(folder / "acquisition-complete.json", receipt)
    print(folder)
    print(json.dumps({"periods": len(records),
                      "uncompressed_bytes": sum(x["xml"]["uncompressed_bytes"] for x in records),
                      "compressed_bytes": sum(x["xml"]["compressed_bytes"] for x in records)}))
    return folder


if __name__ == "__main__":
    acquire()
