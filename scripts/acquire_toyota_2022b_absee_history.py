"""Acquire the contiguous official Toyota 2022-B monthly ABS-EE loan snapshots."""
from __future__ import annotations

import calendar
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
CIK = "1914281"
ISSUER = "Toyota Auto Receivables 2022-B Owner Trust"
START = date(2022, 4, 1)
END = date(2026, 6, 1)
MAX_XML_BYTES = 512 * 1024**2
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"


def expected_periods() -> list[date]:
    periods = []
    year, month = START.year, START.month
    while (year, month) <= (END.year, END.month):
        periods.append(date(year, month, calendar.monthrange(year, month)[1]))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return periods


def get(url: str, limit: int) -> tuple[bytes, dict]:
    time.sleep(0.25)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}), timeout=90) as response:
        if response.status != 200 or response.url != url:
            raise ValueError("Unexpected SEC response status or redirect")
        payload = response.read(limit + 1)
        if not payload or len(payload) > limit:
            raise ValueError("Empty or oversized SEC response")
        return payload, {"url": response.url, "http_status": response.status,
                         "content_type": response.headers.get("Content-Type"),
                         "last_modified": response.headers.get("Last-Modified"),
                         "etag": response.headers.get("ETag")}


def acquire_xml(folder: Path, accession: str, filename: str, report_date: date, advertised_bytes: int) -> dict:
    accession_path = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession_path}/{filename}"
    path = folder / (report_date.strftime("%Y-%m") + ".xml.gz")
    digest = hashlib.sha256()
    size = 0
    prefix = bytearray()
    time.sleep(0.25)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}), timeout=120) as response:
        if response.status != 200 or response.url != url or response.headers.get("Content-Type") != "text/xml":
            raise ValueError("Unexpected SEC XML response")
        meta = {"url": response.url, "http_status": response.status,
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag")}
        with path.open("xb") as target:
            with gzip.GzipFile(filename=filename, mode="wb", fileobj=target, mtime=0) as zipped:
                while chunk := response.read(1024**2):
                    size += len(chunk)
                    if size > MAX_XML_BYTES:
                        raise ValueError("Toyota 2022-B ABS-EE XML exceeded the per-file bound")
                    digest.update(chunk)
                    if len(prefix) < 8192:
                        prefix.extend(chunk[:8192 - len(prefix)])
                    zipped.write(chunk)
    expected = report_date.strftime("%m-%d-%Y").encode()
    text = bytes(prefix)
    if not re.sub(br"^\s*<\?xml[^>]*\?>\s*", b"", text, count=1).startswith(b"<assetData "):
        raise ValueError(f"XML root mismatch for {report_date}")
    if b"<reportingPeriodEndingDate>" + expected + b"</reportingPeriodEndingDate>" not in text:
        raise ValueError(f"XML reporting date mismatch for {report_date}")
    if size != advertised_bytes:
        raise ValueError(f"Downloaded XML size differs from SEC index for {report_date}")
    return {**meta, "file": path.name, "attachment": filename, "accession": accession,
            "report_date": report_date.isoformat(), "uncompressed_bytes": size,
            "uncompressed_sha256": digest.hexdigest(), "compressed_bytes": path.stat().st_size,
            "compressed_sha256": sha256(path)}


def acquire() -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    out = ROOT / "data/private/structured" / ("toyota-2022b-absee-history-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    submissions_url = f"https://data.sec.gov/submissions/CIK{CIK.zfill(10)}.json"
    submission_bytes, submission_meta = get(submissions_url, 8 * 1024**2)
    submission_path = out / "sec-submissions.json"
    submission_path.write_bytes(submission_bytes)
    submission = json.loads(submission_bytes)
    if str(submission.get("cik", "")).zfill(10) != CIK.zfill(10) or submission.get("name") != ISSUER:
        raise ValueError("SEC submissions identity mismatch")

    recent = submission["filings"]["recent"]
    selected = {}
    for i, form in enumerate(recent["form"]):
        if form != "ABS-EE" or not recent["reportDate"][i]:
            continue
        period = date.fromisoformat(recent["reportDate"][i])
        if period < START or period > date(END.year, END.month, calendar.monthrange(END.year, END.month)[1]):
            continue
        accession = recent["accessionNumber"][i]
        if period in selected:
            raise ValueError(f"Duplicate ABS-EE filing for {period}: {selected[period]['accession']} and {accession}")
        selected[period] = {"accession": accession, "filing_date": recent["filingDate"][i],
                            "primary_document": recent["primaryDocument"][i]}
    periods = expected_periods()
    missing = sorted(set(periods) - set(selected))
    unexpected = sorted(set(selected) - set(periods))
    if missing or unexpected or sorted(selected) != periods:
        raise ValueError(f"Non-contiguous SEC report periods; missing={missing}, unexpected={unexpected}")

    records = []
    for report_date in periods:
        filing = selected[report_date]
        accession = filing["accession"].replace("-", "")
        index_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}/index.json"
        index_bytes, index_meta = get(index_url, 2 * 1024**2)
        index = json.loads(index_bytes)
        candidates = [item for item in index["directory"]["item"]
                      if re.fullmatch(r"taot22bex102[^/]*\.xml", item.get("name", ""), flags=re.IGNORECASE)]
        if len(candidates) != 1:
            raise ValueError(f"Expected one Toyota 2022-B EX-102 for {report_date}, found {len(candidates)}")
        advertised = int(candidates[0].get("size", 0))
        if advertised <= 0 or advertised > MAX_XML_BYTES:
            raise ValueError(f"SEC index advertises invalid/oversized XML for {report_date}")
        index_path = out / (report_date.strftime("%Y-%m") + "-index.json")
        index_path.write_bytes(index_bytes)
        xml = acquire_xml(out, filing["accession"], candidates[0]["name"], report_date, advertised)
        records.append({"report_date": report_date.isoformat(), "filing_date": filing["filing_date"],
                        "primary_document": filing["primary_document"],
                        "index": {**index_meta, "file": index_path.name, "bytes": len(index_bytes),
                                  "sha256": sha256(index_path)}, "xml": xml})
        print(f"{report_date.isoformat()} {xml['uncompressed_bytes']} {xml['compressed_bytes']}", flush=True)

    receipt = {
        "source_id": out.name,
        "status": "SEC_OFFICIAL_TOYOTA_2022B_ABSEE_HISTORY_ACQUIRED",
        "issuer": ISSUER, "cik": CIK, "form": "ABS-EE", "period_count": len(records),
        "report_start": periods[0].isoformat(), "report_end": periods[-1].isoformat(),
        "submissions": {**submission_meta, "file": submission_path.name, "bytes": len(submission_bytes),
                        "sha256": sha256(submission_path)},
        "reports": records, "acquired_at": timestamp(),
        "script": "scripts/acquire_toyota_2022b_absee_history.py", "script_sha256": sha256(Path(__file__)),
        "visibility": "private", "public_release_approved": False,
        "limitations": [
            "Monthly snapshots from one Toyota trust; not a representative auto-loan population.",
            "No PD/default/recovery label is derived at acquisition; disappearance or zero balance is not automatically an exit cause.",
            "Source values remain raw XML; exact definitions, amendment context, and loan-key persistence still require profiling.",
        ],
    }
    write_new(out / "acquisition-complete.json", receipt)
    print(out)
    print(json.dumps({"status": receipt["status"], "periods": len(records),
                      "uncompressed_bytes": sum(r["xml"]["uncompressed_bytes"] for r in records),
                      "compressed_bytes": sum(r["xml"]["compressed_bytes"] for r in records)}))
    return out


if __name__ == "__main__":
    acquire()
