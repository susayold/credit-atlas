"""Acquire the SEC ABS XML v1.9 specification and local XSD taxonomy."""
from __future__ import annotations

import json
import io
import re
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://www.sec.gov/files/info/edgar/specifications/absxml.htm"
URL = "https://www.sec.gov/info/edgar/specifications/absxml-1.9.zip"
MAX_BYTES = 16 * 1024**2
USER_AGENT = "OpenAI Codex Credit Atlas research (https://openai.com)"


def acquire() -> Path:
    if ROOT.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    folder = ROOT / "data/private/structured" / ("sec-abs-xml-spec-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    request = Request(URL, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=60) as response:
        if response.status != 200 or response.url != URL or response.headers.get("Content-Type") != "application/zip":
            raise ValueError("Unexpected official SEC specification response")
        payload = response.read(MAX_BYTES + 1)
        metadata = {
            "url": response.url,
            "http_status": response.status,
            "content_type": response.headers.get("Content-Type"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }
    if not payload or len(payload) > MAX_BYTES:
        raise ValueError("Empty or oversized SEC specification archive")
    archive = folder / "absxml-1.9.zip"
    archive.write_bytes(payload)
    extracted = []
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip():
            raise ValueError("Corrupt SEC technical specification archive")
        xsd_root = folder / "xsd"
        sources = [("", bundle)]
        for info in bundle.infolist():
            if info.filename.lower().endswith(".zip"):
                nested = zipfile.ZipFile(io.BytesIO(bundle.read(info)))
                if nested.testzip():
                    raise ValueError("Corrupt nested SEC taxonomy archive")
                sources.append((Path(info.filename).stem, nested))
        for prefix, source in sources:
            for info in source.infolist():
                if not info.filename.lower().endswith(".xsd"):
                    continue
                member = PurePosixPath(info.filename)
                if member.is_absolute() or ".." in member.parts:
                    raise ValueError("Unsafe path in SEC specification archive")
                relative = Path(prefix, *member.parts) if prefix else Path(*member.parts)
                target = xsd_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read(info))
                extracted.append({"file": str(relative).replace("\\", "/"), "bytes": target.stat().st_size,
                                  "sha256": sha256(target)})
    if not extracted:
        raise ValueError("SEC archive contained no XSD files")
    auto_xsds = [x for x in extracted if re.search(r"Auto.*Loan|Loan.*Auto", x["file"], re.I)]
    receipt = {
        "source_id": folder.name,
        "status": "SEC_OFFICIAL_ABS_XML_SPEC_ACQUIRED",
        "title": "EDGAR ABS XML Technical Specification",
        "version": "1.9",
        "implementation_date": "2021-02-25",
        "official_page": PAGE,
        "archive": {**metadata, "file": archive.name, "bytes": len(payload), "sha256": sha256(archive)},
        "extracted_xsds": extracted,
        "auto_loan_xsds": auto_xsds,
        "acquired_at": timestamp(),
        "visibility": "private",
        "public_release_approved": False,
        "limitations": [
            "Specification describes the EDGAR taxonomy version and implementation date; confirm no relevant schema change before future use.",
            "Acquiring a schema does not mean the dataset has been validated against it.",
        ],
    }
    write_new(folder / "acquisition-complete.json", receipt)
    print(folder)
    print(json.dumps({"status": receipt["status"], "archive_bytes": len(payload),
                      "xsd_count": len(extracted), "auto_loan_xsds": auto_xsds}))
    return folder


if __name__ == "__main__":
    acquire()
