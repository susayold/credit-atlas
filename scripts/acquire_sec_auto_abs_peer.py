"""Acquire one official Toyota Auto Receivables ABS-EE peer period from EDGAR."""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
PEERS = {
    "2026-c": {"cik": "2099541", "accession": "000119312526297053",
               "issuer": "Toyota Auto Receivables 2026-C Owner Trust", "report_date": "2026-05-31",
               "filing_date": "2026-07-07", "attachment": "taot26cex102_0623-1858sp.xml"},
    "2022-b": {"cik": "1914281", "accession": "000119312526284181",
               "issuer": "Toyota Auto Receivables 2022-B Owner Trust", "report_date": "2026-05-31",
               "filing_date": "2026-06-26", "attachment": "taot22bex102.xml"},
}
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"
MAX_XML_BYTES = 256 * 1024**2


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


def acquire(peer_id: str = "2026-c") -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    if peer_id not in PEERS:
        raise ValueError(f"Choose a configured peer: {', '.join(sorted(PEERS))}")
    peer = PEERS[peer_id]
    CIK, ACCESSION, ISSUER = peer["cik"], peer["accession"], peer["issuer"]
    REPORT_DATE, FILING_DATE, ATTACHMENT = peer["report_date"], peer["filing_date"], peer["attachment"]
    out = ROOT / "data/private/structured" / ("sec-auto-abs-peer-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    submissions_url = f"https://data.sec.gov/submissions/CIK{CIK.zfill(10)}.json"
    submissions_bytes, submissions_meta = get(submissions_url, 4 * 1024**2)
    submissions = json.loads(submissions_bytes)
    if str(submissions.get("cik", "")).zfill(10) != CIK.zfill(10) or submissions.get("name") != ISSUER:
        raise ValueError("SEC submissions issuer identity mismatch")
    recent = submissions["filings"]["recent"]
    matching_filings = [i for i, acc in enumerate(recent["accessionNumber"]) if acc == ACCESSION]
    if len(matching_filings) > 1:
        raise ValueError("Accession duplicated in SEC submissions")
    if matching_filings:
        i = matching_filings[0]
        if (recent["form"][i] != "ABS-EE" or recent["filingDate"][i] != FILING_DATE
                or recent["reportDate"][i] != REPORT_DATE):
            raise ValueError("SEC filing metadata does not match configured peer sample")
    submissions_path = out / "sec-submissions.json"
    submissions_path.write_bytes(submissions_bytes)
    index_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/index.json"
    index_bytes, index_meta = get(index_url, 2 * 1024**2)
    index = json.loads(index_bytes)
    items = index.get("directory", {}).get("item", [])
    match = [x for x in items if x.get("name") == ATTACHMENT]
    if len(match) != 1 or int(match[0].get("size", 0)) <= 0 or int(match[0]["size"]) > MAX_XML_BYTES:
        raise ValueError("SEC index does not uniquely qualify the expected Toyota asset-data exhibit")
    index_path = out / "filing-index.json"
    index_path.write_bytes(index_bytes)
    accession_dashed = ACCESSION[:10] + "-" + ACCESSION[10:12] + "-" + ACCESSION[12:]
    filing_page_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/{accession_dashed}-index.htm"
    filing_page_bytes, filing_page_meta = get(filing_page_url, 2 * 1024**2)
    filing_page_text = filing_page_bytes.decode("utf-8", errors="replace")
    if (ISSUER not in filing_page_text or FILING_DATE not in filing_page_text or REPORT_DATE not in filing_page_text
            or "ABS-EE" not in filing_page_text or ATTACHMENT not in filing_page_text):
        raise ValueError("Official filing detail page does not confirm configured issuer/report/exhibit")
    filing_page_path = out / "filing-detail.html"
    filing_page_path.write_bytes(filing_page_bytes)

    xml_url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSION}/{ATTACHMENT}"
    raw_path = out / "asset-data.xml.gz"
    import hashlib
    digest = hashlib.sha256()
    size = 0
    prefix = bytearray()
    time.sleep(0.25)
    with urlopen(Request(xml_url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}), timeout=120) as response:
        if response.status != 200 or response.url != xml_url or response.headers.get("Content-Type") != "text/xml":
            raise ValueError("Unexpected SEC XML response")
        xml_meta = {"url": response.url, "http_status": response.status,
                    "content_type": response.headers.get("Content-Type"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag")}
        with raw_path.open("xb") as target:
            with gzip.GzipFile(filename=ATTACHMENT, mode="wb", fileobj=target, mtime=0) as zipped:
                while chunk := response.read(1024**2):
                    size += len(chunk)
                    if size > MAX_XML_BYTES:
                        raise ValueError("Toyota ABS-EE XML exceeded the per-file bound")
                    digest.update(chunk)
                    if len(prefix) < 8192:
                        prefix.extend(chunk[:8192 - len(prefix)])
                    zipped.write(chunk)
    expected = REPORT_DATE[5:7] + "-" + REPORT_DATE[8:10] + "-" + REPORT_DATE[:4]
    xml_prefix = re.sub(br"^\s*<\?xml[^>]*\?>\s*", b"", bytes(prefix), count=1)
    if not xml_prefix.startswith(b"<assetData ") or (
            b"<reportingPeriodEndingDate>" + expected.encode() + b"</reportingPeriodEndingDate>") not in prefix:
        raise ValueError("Toyota XML root/reporting date mismatch")
    if size != int(match[0]["size"]):
        raise ValueError("Downloaded XML byte count differs from SEC filing index")

    receipt = {
        "source_id": out.name,
        "status": "SEC_OFFICIAL_AUTO_ABS_PEER_PERIOD_ACQUIRED",
        "issuer": ISSUER,
        "cik": CIK,
        "accession": ACCESSION,
        "form": "ABS-EE",
        "filing_date": FILING_DATE,
        "report_date": REPORT_DATE,
        "submissions": {**submissions_meta, "file": submissions_path.name, "bytes": len(submissions_bytes),
                        "sha256": sha256(submissions_path),
                        "accession_in_recent_list": bool(matching_filings)},
        "filing_detail_page": {**filing_page_meta, "file": filing_page_path.name,
                               "bytes": len(filing_page_bytes), "sha256": sha256(filing_page_path)},
        "index": {**index_meta, "file": index_path.name, "bytes": len(index_bytes), "sha256": sha256(index_path)},
        "asset_data_xml": {**xml_meta, "file": raw_path.name, "attachment": ATTACHMENT,
                            "uncompressed_bytes": size, "uncompressed_sha256": digest.hexdigest(),
                            "compressed_bytes": raw_path.stat().st_size, "compressed_sha256": sha256(raw_path)},
        "acquired_at": timestamp(),
        "script": "scripts/acquire_sec_auto_abs_peer.py",
        "script_sha256": sha256(Path(__file__)),
        "visibility": "private",
        "public_release_approved": False,
        "limitations": [
            "One Toyota deal and one report month; this is a schema/coverage peer sample, not a vintage panel or representative comparison.",
            "No PD, default, recovery, repayment, or exit labels are derived during acquisition.",
            "Source values remain private, source-native, and unnormalized pending XSD/schema/field comparison.",
        ],
    }
    write_new(out / "acquisition-complete.json", receipt)
    print(out)
    print(json.dumps({"status": receipt["status"], "issuer": ISSUER, "report_date": REPORT_DATE,
                      "uncompressed_bytes": size, "compressed_bytes": raw_path.stat().st_size}))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 2:
        raise SystemExit("Usage: acquire_sec_auto_abs_peer.py [2026-c|2022-b]")
    acquire(sys.argv[1] if len(sys.argv) == 2 else "2026-c")
