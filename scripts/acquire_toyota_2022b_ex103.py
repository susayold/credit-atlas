"""Acquire Toyota 2022-B EX-103 field-definition narratives for every ABS-EE period."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "toyota-2022b-absee-history-435918e7209a"
CIK = "1914281"
ISSUER = "Toyota Auto Receivables 2022-B Owner Trust"
MAX_BYTES = 2 * 1024**2
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"


def get(url: str, limit: int) -> tuple[bytes, dict]:
    time.sleep(0.25)
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}), timeout=60) as response:
        if response.status != 200 or response.url != url or response.headers.get("Content-Type") != "text/xml":
            raise ValueError("Unexpected SEC EX-103 response")
        payload = response.read(limit + 1)
        if not payload or len(payload) > limit:
            raise ValueError("Empty or oversized SEC EX-103 attachment")
        return payload, {"url": response.url, "http_status": response.status,
                         "content_type": response.headers.get("Content-Type"),
                         "last_modified": response.headers.get("Last-Modified"),
                         "etag": response.headers.get("ETag")}


def acquire() -> Path:
    source = contained(ROOT, "data/private/structured/" + SOURCE_ID)
    source_receipt_path = source / "acquisition-complete.json"
    source_receipt = read_json(source_receipt_path)
    if (source_receipt.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_ABSEE_HISTORY_ACQUIRED"
            or source_receipt.get("period_count") != 51 or source_receipt.get("issuer") != ISSUER):
        raise ValueError("Toyota 2022-B source history prerequisite mismatch")
    out = ROOT / "data/private/structured" / ("toyota-2022b-ex103-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    reports = []
    for source_report in source_receipt["reports"]:
        report_date = source_report["report_date"]
        index_record = source_report["index"]
        index_path = contained(source, index_record["file"])
        if (index_path.stat().st_size != index_record["bytes"] or sha256(index_path) != index_record["sha256"]):
            raise ValueError(f"Filing index hash/size mismatch for {report_date}")
        index = json.loads(index_path.read_bytes())
        candidates = [item for item in index["directory"]["item"]
                      if re.fullmatch(r"taot22bex103[^/]*\.xml", item.get("name", ""), flags=re.IGNORECASE)]
        if len(candidates) != 1:
            raise ValueError(f"Expected one Toyota 2022-B EX-103 for {report_date}, found {len(candidates)}")
        file_name = candidates[0]["name"]
        advertised = int(candidates[0].get("size", 0))
        if advertised <= 0 or advertised > MAX_BYTES:
            raise ValueError(f"Invalid/oversized EX-103 in filing index for {report_date}")
        accession = source_report["xml"]["accession"]
        accession_path = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{CIK}/{accession_path}/{file_name}"
        payload, meta = get(url, MAX_BYTES)
        if len(payload) != advertised:
            raise ValueError(f"Downloaded EX-103 byte count differs from filing index for {report_date}")
        if b"<assetData" not in payload[:4096] or b"Explanatory Narrative" not in payload:
            raise ValueError(f"EX-103 XML/narrative marker missing for {report_date}")
        target = out / (report_date[:7] + "-ex103.xml.gz")
        digest = hashlib.sha256(payload).hexdigest()
        with target.open("xb") as stream:
            with gzip.GzipFile(filename=file_name, mode="wb", fileobj=stream, mtime=0) as zipped:
                zipped.write(payload)
        reports.append({"report_date": report_date, "filing_date": source_report["filing_date"],
                        "accession": accession, "attachment": file_name,
                        **meta, "file": target.name, "uncompressed_bytes": len(payload),
                        "uncompressed_sha256": digest, "compressed_bytes": target.stat().st_size,
                        "compressed_sha256": sha256(target)})
        print(f"{report_date} {len(payload)} {target.stat().st_size}", flush=True)
    result = {"source_id": out.name, "status": "SEC_OFFICIAL_TOYOTA_2022B_EX103_ACQUIRED",
              "issuer": ISSUER, "cik": CIK, "report_count": len(reports),
              "report_start": reports[0]["report_date"], "report_end": reports[-1]["report_date"],
              "linked_absee_source_id": SOURCE_ID,
              "linked_absee_receipt_sha256": sha256(source_receipt_path), "reports": reports,
              "acquired_at": timestamp(), "script": "scripts/acquire_toyota_2022b_ex103.py",
              "script_sha256": sha256(Path(__file__)), "visibility": "private",
              "public_release_approved": False,
              "limitations": ["EX-103 narrative is issuer-specific and supplements, but does not replace, prospectus/legal definitions.",
                              "Narrative text is source evidence, not proof that field values satisfy the definition." ]}
    write_new(out / "acquisition-complete.json", result)
    print(out)
    print(json.dumps({"status": result["status"], "reports": len(reports),
                      "uncompressed_bytes": sum(r["uncompressed_bytes"] for r in reports),
                      "compressed_bytes": sum(r["compressed_bytes"] for r in reports)}))
    return out


if __name__ == "__main__":
    acquire()
