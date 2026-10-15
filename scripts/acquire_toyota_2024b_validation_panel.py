"""Acquire paired SEC ABS-EE, EX-103 and 10-D certificate history for Toyota 2024-B."""
from __future__ import annotations

import calendar
import gzip
import hashlib
import json
import re
import time
import uuid
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
CIK = "2012786"
ISSUER = "Toyota Auto Receivables 2024-B Owner Trust"
START = date(2024, 4, 1)
END = date(2026, 8, 31)
MAX_XML_BYTES = 512 * 1024**2
MAX_HTML_BYTES = 12 * 1024**2
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


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


def months() -> list[date]:
    result = []
    year, month = START.year, START.month
    while (year, month) <= (END.year, END.month):
        result.append(date(year, month, calendar.monthrange(year, month)[1]))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def stream_gzip_xml(folder: Path, url: str, filename: str, period: date, advertised: int) -> dict:
    path = folder / (period.strftime("%Y-%m") + ".xml.gz")
    digest, size, prefix = hashlib.sha256(), 0, bytearray()
    time.sleep(0.25)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}), timeout=120) as response:
        if response.status != 200 or response.url != url or response.headers.get("Content-Type") != "text/xml":
            raise ValueError("Unexpected SEC EX-102 XML response")
        metadata = {"url": response.url, "http_status": response.status,
                    "content_type": response.headers.get("Content-Type"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag")}
        with path.open("xb") as raw, gzip.GzipFile(filename=filename, mode="wb", fileobj=raw, mtime=0) as zipped:
            while chunk := response.read(1024**2):
                size += len(chunk)
                if size > MAX_XML_BYTES:
                    raise ValueError(f"Toyota 2024-B EX-102 exceeded file limit: {period}")
                digest.update(chunk)
                if len(prefix) < 8192:
                    prefix.extend(chunk[:8192 - len(prefix)])
                zipped.write(chunk)
    expected = period.strftime("%m-%d-%Y").encode()
    if (size != advertised or b"<assetData " not in bytes(prefix)
            or b"<reportingPeriodEndingDate>" + expected + b"</reportingPeriodEndingDate>" not in prefix):
        raise ValueError(f"Toyota 2024-B EX-102 root/date/size mismatch: {period}")
    return {**metadata, "file": path.name, "attachment": filename,
            "uncompressed_bytes": size, "uncompressed_sha256": digest.hexdigest(),
            "compressed_bytes": path.stat().st_size, "compressed_sha256": sha256(path)}


def select_attachment(index: dict, pattern: str, report_date: date) -> dict:
    candidates = [item for item in index.get("directory", {}).get("item", [])
                  if re.search(pattern, item.get("name", ""), re.I)]
    if len(candidates) != 1:
        raise ValueError(f"Expected one attachment matching {pattern} for {report_date}, found {len(candidates)}")
    item = candidates[0]
    size = int(item.get("size", 0))
    if size <= 0:
        raise ValueError(f"Invalid SEC-advertised attachment size for {report_date}")
    return item


def acquire() -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    out = ROOT / "data/private/structured" / ("toyota-2024b-validation-panel-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    submissions_url = f"https://data.sec.gov/submissions/CIK{CIK.zfill(10)}.json"
    submissions_bytes, submissions_meta = get(submissions_url, 8 * 1024**2)
    submissions_path = out / "sec-submissions.json"
    submissions_path.write_bytes(submissions_bytes)
    submissions = json.loads(submissions_bytes)
    if str(submissions.get("cik", "")).zfill(10) != CIK.zfill(10) or submissions.get("name") != ISSUER:
        raise ValueError("SEC submissions identity mismatch")
    recent = submissions["filings"]["recent"]
    selected = {"ABS-EE": {}, "10-D": {}}
    for i, form in enumerate(recent["form"]):
        if form not in selected or not recent["reportDate"][i]:
            continue
        report = date.fromisoformat(recent["reportDate"][i])
        if not START <= report <= END:
            continue
        if report in selected[form]:
            raise ValueError(f"Duplicate {form} filing for {report}")
        selected[form][report] = {"accession": recent["accessionNumber"][i],
                                  "filing_date": recent["filingDate"][i],
                                  "primary_document": recent["primaryDocument"][i]}
    expected = months()
    if sorted(selected["ABS-EE"]) != expected or sorted(selected["10-D"]) != expected:
        raise ValueError("ABS-EE and 10-D do not form the expected matching contiguous month series")

    records = []
    total_raw_bytes = total_gzip_bytes = 0
    for report in expected:
        month = report.strftime("%Y-%m")
        abs_filing = selected["ABS-EE"][report]
        ten_filing = selected["10-D"][report]
        abs_base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{abs_filing['accession'].replace('-', '')}"
        ten_base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{ten_filing['accession'].replace('-', '')}"
        abs_index_bytes, abs_index_meta = get(abs_base + "/index.json", 2 * 1024**2)
        ten_index_bytes, ten_index_meta = get(ten_base + "/index.json", 2 * 1024**2)
        abs_index, ten_index = json.loads(abs_index_bytes), json.loads(ten_index_bytes)
        ex102 = select_attachment(abs_index, r"ex102[^/]*\.xml$", report)
        ex103 = select_attachment(abs_index, r"ex103[^/]*\.xml$", report)
        ex99 = select_attachment(ten_index, r"dex991\.htm$|ex99[-.]?1[^/]*\.htm$", report)
        xml_url = abs_base + "/" + ex102["name"]
        asset_xml = stream_gzip_xml(out, xml_url, ex102["name"], report, int(ex102["size"]))
        ex103_bytes, ex103_meta = get(abs_base + "/" + ex103["name"], 2 * 1024**2)
        ex103_path = out / (month + "-ex103.xml")
        ex103_path.write_bytes(ex103_bytes)
        if (len(ex103_bytes) != int(ex103["size"]) or b"<assetData>" not in ex103_bytes
                or ISSUER.encode() not in ex103_bytes or b"Exhibit 103" not in ex103_bytes):
            raise ValueError(f"Toyota 2024-B EX-103 size/content mismatch: {report}")
        cert_bytes, cert_meta = get(ten_base + "/" + ex99["name"], MAX_HTML_BYTES)
        extractor = TextExtractor()
        extractor.feed(cert_bytes.decode("utf-8", errors="replace"))
        visible = " ".join(" ".join(extractor.parts).split())
        if (ISSUER not in visible or "Servicer" not in visible or "Collection Period" not in visible
                or report.strftime("%B") not in visible or str(report.year) not in visible):
            raise ValueError(f"Toyota 2024-B EX-99.1 certificate identity/date check failed: {report}")
        cert_path = out / (month + "-certificate.html")
        cert_path.write_bytes(cert_bytes)
        abs_index_path, ten_index_path = out / (month + "-absee-index.json"), out / (month + "-10d-index.json")
        abs_index_path.write_bytes(abs_index_bytes)
        ten_index_path.write_bytes(ten_index_bytes)
        records.append({
            "report_date": report.isoformat(),
            "abs_ee": {**abs_filing, "index": {**abs_index_meta, "file": abs_index_path.name,
                "bytes": len(abs_index_bytes), "sha256": sha256(abs_index_path)},
                "ex102": asset_xml,
                "ex103": {**ex103_meta, "file": ex103_path.name, "attachment": ex103["name"],
                           "bytes": len(ex103_bytes), "sha256": sha256(ex103_path)}},
            "10d": {**ten_filing, "index": {**ten_index_meta, "file": ten_index_path.name,
                "bytes": len(ten_index_bytes), "sha256": sha256(ten_index_path)},
                "ex99_1": {**cert_meta, "file": cert_path.name, "attachment": ex99["name"],
                           "advertised_attachment_bytes": int(ex99["size"]), "response_bytes": len(cert_bytes),
                           "response_minus_advertised_bytes": len(cert_bytes) - int(ex99["size"]),
                           "sha256": sha256(cert_path)}},
        })
        total_raw_bytes += asset_xml["uncompressed_bytes"]
        total_gzip_bytes += asset_xml["compressed_bytes"]
        print(f"{report.isoformat()} {asset_xml['uncompressed_bytes']} {asset_xml['compressed_bytes']} {len(cert_bytes)}", flush=True)

    receipt = {
        "source_id": out.name, "status": "SEC_OFFICIAL_TOYOTA_2024B_PAIRED_HISTORY_ACQUIRED",
        "issuer": ISSUER, "cik": CIK, "period_count": len(records),
        "report_start": expected[0].isoformat(), "report_end": expected[-1].isoformat(),
        "submissions": {**submissions_meta, "file": submissions_path.name,
                        "bytes": len(submissions_bytes), "sha256": sha256(submissions_path)},
        "reports": records, "total_ex102_uncompressed_bytes": total_raw_bytes,
        "total_ex102_compressed_bytes": total_gzip_bytes, "acquired_at": timestamp(),
        "script": "scripts/acquire_toyota_2024b_validation_panel.py", "script_sha256": sha256(Path(__file__)),
        "visibility": "private", "public_release_approved": False,
        "limitations": [
            "One additional Toyota trust/deal, not an independent servicer or issuer population.",
            "Raw source acquisition only; field/event/certificate tie-outs and model transfer evaluation remain separate steps.",
            "The panel begins at deal reporting start; no pre-ABS servicing history is included.",
        ],
    }
    write_new(out / "acquisition-complete.json", receipt)
    print(out)
    print(json.dumps({"status": receipt["status"], "periods": len(records),
                      "ex102_uncompressed_bytes": total_raw_bytes,
                      "ex102_compressed_bytes": total_gzip_bytes}, ensure_ascii=False))
    return out


if __name__ == "__main__":
    acquire()
