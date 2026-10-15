"""Download the official public FHFA questionnaires for NSMO survey waves."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


SOURCES = [
    ("waves-01-02", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-1-and-2", "1-2"),
    ("wave-03", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-3", "3"),
    ("wave-04", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-4", "4"),
    ("waves-05-06", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-5-and-6", "5-6"),
    ("wave-07", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-7", "7"),
    ("wave-08", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-8", "8"),
    ("wave-09", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-9", "9"),
    ("wave-10", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-10", "10"),
    ("waves-11-12", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-11-and-12", "11-12"),
    ("waves-13-14", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-13-and-14", "13-14"),
    ("waves-15-18", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-15-to-18", "15-18"),
    ("waves-19-22", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-19-to-22", "19-22"),
    ("waves-23-24", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-23-and-24", "23-24"),
    ("wave-25", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-25", "25"),
    ("waves-26-28", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-26-to-28", "26-28"),
    ("waves-29-30", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-29-and-30", "29-30"),
    ("waves-31-34", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-31-to-34.pdf", "31-34"),
    ("waves-35-38", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-35-to-38.pdf", "35-38"),
    ("wave-39", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-39.pdf", "39"),
    ("wave-40", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-40.pdf", "40"),
    ("waves-41-44", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-wave-41-to-44.pdf", "41-44"),
    ("waves-45-46", "https://www.fhfa.gov/document/d/nsmo/nsmo-questionnaire-waves-45-and-46.pdf", "45-46"),
]


def download_all(output_dir: Path, receipt_path: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for source_id, url, waves in SOURCES:
        if urlparse(url).hostname != "www.fhfa.gov":
            raise ValueError(f"Unapproved source host for {source_id}")
        request = urllib.request.Request(url, headers={"User-Agent": "CreditAtlas research downloader"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
        if urlparse(final_url).hostname != "www.fhfa.gov" or not payload.startswith(b"%PDF-"):
            raise ValueError(f"Unexpected response for {source_id}: {final_url}, {content_type}")
        path = output_dir / f"{source_id}.pdf"
        path.write_bytes(payload)
        records.append({
            "source_id": source_id,
            "waves": waves,
            "url": url,
            "final_url": final_url,
            "path": str(path),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": content_type,
        })
    report = {
        "schema_version": "nsmo-questionnaire-acquisition-v1",
        "status": "PASS",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "source_page": "https://www.fhfa.gov/data/nsmo",
        "documents": records,
        "document_count": len(records),
        "wave_coverage": "Waves 1-46 across 22 deduplicated official questionnaire packages",
        "storage_note": "Questionnaire PDFs and receipt are private local research inputs; do not add them to public Git.",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    report = download_all(args.output_dir, args.receipt)
    print(json.dumps({"status": report["status"], "documents": report["document_count"], "wave_coverage": report["wave_coverage"]}))


if __name__ == "__main__":
    main()
