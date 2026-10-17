"""Download the bounded official Treasury HAMP quarterly summary PDF set."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from pypdf import PdfReader


SOURCE_INDEX = Path(__file__).resolve().parents[1] / "docs/data/treasury-hamp-quarterly-summary-sources-2026-10-17.json"
ALLOWED_HOSTS = {"home.treasury.gov"}
MAX_PDF_BYTES = 10 * 1024 * 1024


class AcquisitionError(ValueError):
    pass


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urlsplit(new_url)
        if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.fragment):
            raise AcquisitionError("Treasury PDF redirected outside the official HTTPS host")
        return super().redirect_request(request, response, code, message, headers, new_url)


def load_sources() -> tuple[str, list[dict]]:
    index = json.loads(SOURCE_INDEX.read_text(encoding="utf-8"))
    reports = index.get("reports", [])
    if index.get("source_count") != len(reports) or len({r["source_id"] for r in reports}) != len(reports):
        raise AcquisitionError("Source index count or IDs are not unique/consistent")
    for report in reports:
        parsed = urlsplit(report["url"])
        if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.fragment
                or Path(report["file"]).name != report["file"]):
            raise AcquisitionError("Source index contains an unapproved URL or filename")
    return index["source_page"], reports


def acquire(root: Path) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise AcquisitionError("Treasury PDFs and receipts must stay on D:")
    source_page, reports = load_sources()
    output_dir = root / "data/private/mortgage/treasury-hamp/source_docs/quarterly_summaries"
    output_dir.mkdir(parents=True, exist_ok=True)
    opener = urllib.request.build_opener(OfficialRedirects())
    acquired = []
    for report in reports:
        target = output_dir / report["file"]
        if target.exists():
            payload = target.read_bytes()
            state = "EXISTING_VERIFIED_PDF"
        else:
            request = urllib.request.Request(report["url"], headers={
                "User-Agent": "CreditAtlas official Treasury research/1.0",
                "Accept": "application/pdf",
            })
            try:
                with opener.open(request, timeout=60) as response:
                    content_type = response.headers.get_content_type().casefold()
                    final_url = response.geturl()
                    if response.status != 200 or content_type != "application/pdf":
                        raise AcquisitionError(f"Unexpected Treasury response for {report['source_id']}")
                    payload = response.read(MAX_PDF_BYTES + 1)
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
                raise AcquisitionError(f"Treasury download failed for {report['source_id']}") from exc
            if len(payload) > MAX_PDF_BYTES:
                raise AcquisitionError(f"Treasury PDF exceeds size cap: {report['source_id']}")
            state = "DOWNLOADED"
        if not payload.startswith(b"%PDF-") or not payload:
            raise AcquisitionError(f"Downloaded content is not a PDF: {report['source_id']}")
        reader = PdfReader(__import__("io").BytesIO(payload), strict=True)
        if len(reader.pages) != 1:
            raise AcquisitionError(f"Expected one-page summary PDF: {report['source_id']}")
        text = reader.pages[0].extract_text(extraction_mode="layout") or ""
        if "Home Affordable Modification Program" not in text or "Performance" not in text:
            raise AcquisitionError(f"PDF text does not look like a HAMP summary: {report['source_id']}")
        if not target.exists():
            partial = target.with_suffix(target.suffix + ".partial")
            if partial.exists():
                raise AcquisitionError(f"Partial PDF already exists; inspect before retry: {partial.name}")
            try:
                with partial.open("xb") as stream:
                    stream.write(payload)
                partial.replace(target)
            except Exception:
                partial.unlink(missing_ok=True)
                raise
        acquired.append({
            **report,
            "state": state,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "page_count": len(reader.pages),
            "private_path": str(target),
        })
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "receipt_id": "treasury-hamp-quarterly-acq-" + uuid.uuid4().hex[:12],
        "source_page": source_page,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_count": len(acquired),
        "reports": acquired,
        "visibility": "private",
        "raw_loan_level_data": False,
        "model_fit_performed": False,
    }
    receipt_dir = root / "artifacts/private" / receipt["receipt_id"]
    receipt_dir.mkdir(parents=True, exist_ok=False)
    with (receipt_dir / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return {"status": receipt["status"], "receipt_id": receipt["receipt_id"],
            "report_count": receipt["report_count"], "reports": [
                {"source_id": r["source_id"], "state": r["state"], "bytes": r["bytes"], "sha256": r["sha256"]}
                for r in acquired]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    args = parser.parse_args()
    try:
        print(json.dumps(acquire(args.root), indent=2, ensure_ascii=False))
    except (OSError, AcquisitionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
