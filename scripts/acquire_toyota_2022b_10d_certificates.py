"""Acquire SEC 10-D EX-99.1 servicer certificates for Toyota Auto Receivables 2022-B."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
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
SUBMISSIONS = ROOT / "data/private/structured/toyota-2022b-absee-history-435918e7209a/sec-submissions.json"
SUBMISSIONS_SHA256 = "aec310cf815f3a3acea2e080d6931c87313af8b51ed9d3ef19900c116a5accb8"
START = date(2022, 4, 1)
END = date(2026, 6, 30)
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


def acquire() -> Path:
    if ROOT.drive.upper() != "D:" or not SUBMISSIONS.is_file() or sha256(SUBMISSIONS) != SUBMISSIONS_SHA256:
        raise ValueError("Expected verified Toyota 2022-B SEC submissions snapshot on D:")
    submission = json.loads(SUBMISSIONS.read_text(encoding="utf-8"))
    if str(submission.get("cik", "")).zfill(10) != CIK.zfill(10) or submission.get("name") != ISSUER:
        raise ValueError("SEC submissions identity mismatch")
    recent = submission["filings"]["recent"]
    selected = {}
    for i, form in enumerate(recent["form"]):
        if form != "10-D" or not recent["reportDate"][i]:
            continue
        period = date.fromisoformat(recent["reportDate"][i])
        if not (START <= period <= END):
            continue
        if period in selected:
            raise ValueError(f"Duplicate 10-D report period: {period}")
        selected[period] = {
            "accession": recent["accessionNumber"][i],
            "filing_date": recent["filingDate"][i],
            "report_date": period.isoformat(),
        }
    absee = json.loads((ROOT / "data/private/structured/toyota-2022b-absee-history-435918e7209a/acquisition-complete.json").read_text(encoding="utf-8"))
    expected = {date.fromisoformat(item["report_date"]): item for item in absee["reports"]}
    if set(selected) != set(expected) or len(selected) != 51:
        missing = sorted(set(expected) - set(selected))
        extra = sorted(set(selected) - set(expected))
        raise ValueError(f"10-D periods do not exactly match ABS-EE: missing={missing}, extra={extra}")

    out = ROOT / "data/private/structured" / ("toyota-2022b-10d-certificates-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    records = []
    for report_period in sorted(selected):
        filing = selected[report_period]
        accession = filing["accession"].replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession}"
        index_bytes, index_meta = get(base + "/index.json", 2 * 1024**2)
        index = json.loads(index_bytes)
        items = index.get("directory", {}).get("item", [])
        candidates = [item for item in items
                      if re.search(r"dex991\.htm$|ex99[-.]?1[^/]*\.htm$", item.get("name", ""), re.I)]
        if len(candidates) != 1:
            raise ValueError(f"Expected one EX-99.1 servicer certificate for {report_period}, found {len(candidates)}")
        item = candidates[0]
        advertised = int(item.get("size", 0))
        if advertised <= 0 or advertised > MAX_HTML_BYTES:
            raise ValueError(f"Invalid/oversized SEC-served certificate size for {report_period}")
        body, html_meta = get(base + "/" + item["name"], MAX_HTML_BYTES)
        text = body.decode("utf-8", errors="replace")
        extractor = TextExtractor()
        extractor.feed(text)
        visible_text = " ".join(" ".join(extractor.parts).split())
        response_wrapped = body.startswith(b"<DOCUMENT>") and b"<TEXT>" in body and b"</DOCUMENT>" in body
        size_delta = len(body) - advertised
        if ((size_delta != 0 and not response_wrapped) or abs(size_delta) > 512
                or ISSUER not in visible_text):
            raise ValueError(f"Certificate identity/size check failed for {report_period}")
        if "Servicer" not in visible_text or "Collection Period" not in visible_text:
            raise ValueError(f"Certificate content markers missing for {report_period}")
        expected_report_date = report_period.strftime("%B")
        if expected_report_date not in visible_text or str(report_period.year) not in visible_text:
            raise ValueError(f"Certificate report date marker missing for {report_period}")
        path = out / (report_period.strftime("%Y-%m") + ".html")
        path.write_bytes(body)
        index_path = out / (report_period.strftime("%Y-%m") + "-index.json")
        index_path.write_bytes(index_bytes)
        records.append({
            **filing,
            "abs_ee_accession": expected[report_period]["xml"]["accession"],
            "index": {**index_meta, "file": index_path.name, "bytes": len(index_bytes), "sha256": sha256(index_path)},
            "certificate": {**html_meta, "file": path.name, "attachment": item["name"],
                            "advertised_attachment_bytes": advertised, "response_bytes": len(body),
                            "sec_document_envelope_present": response_wrapped,
                            "response_minus_advertised_bytes": size_delta, "sha256": sha256(path)},
        })
        print(f"{report_period.isoformat()} {filing['accession']} {len(body)}", flush=True)

    receipt = {
        "source_id": out.name,
        "status": "SEC_OFFICIAL_TOYOTA_2022B_10D_CERTIFICATES_ACQUIRED",
        "issuer": ISSUER, "cik": CIK, "form": "10-D", "exhibit": "EX-99.1 Servicer's Certificate",
        "period_count": len(records), "report_start": min(selected).isoformat(), "report_end": max(selected).isoformat(),
        "submissions_snapshot": {"file": str(SUBMISSIONS.relative_to(ROOT)), "sha256": SUBMISSIONS_SHA256},
        "reports": records, "acquired_at": timestamp(),
        "script": "scripts/acquire_toyota_2022b_10d_certificates.py", "script_sha256": sha256(Path(__file__)),
        "visibility": "private", "public_release_approved": False,
        "limitations": [
            "Acquisition and identity markers only; figures still require table parsing and reconciliation.",
            "Certificate aggregate values do not create individual-loan lifetime labels.",
            "HTML is preserved byte-for-byte; parsed tables must retain cell context, units and reporting period.",
        ],
    }
    write_new(out / "acquisition-complete.json", receipt)
    print(out)
    print(json.dumps({"status": receipt["status"], "periods": len(records),
                      "certificate_response_bytes": sum(r["certificate"]["response_bytes"] for r in records)}))
    return out


if __name__ == "__main__":
    acquire()
