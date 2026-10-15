"""Profile downloaded EDGAR agreement HTML and verify cited clause text is present."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from html.parser import HTMLParser
from pathlib import Path

from credit_atlas.workspace import sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "woart-legal-source-bfc00b6802b5"
SOURCE = ROOT / "data/private/structured" / SOURCE_ID
OUT = ROOT / "artifacts/private" / f"woart-legal-audit-{uuid.uuid4().hex[:12]}"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def load_text(path: Path) -> str:
    parser = TextExtractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.text()


def need(text: str, phrase: str, label: str) -> None:
    if phrase.casefold() not in text.casefold():
        raise ValueError(f"Required source wording not found: {label}")


def main() -> Path:
    receipt_path = SOURCE / "acquisition-complete.json"
    acquisition = json.loads(receipt_path.read_text(encoding="utf-8"))
    if acquisition.get("status") != "SEC_CLOSING_AGREEMENTS_AND_AMENDMENT_ACQUIRED":
        raise ValueError("Source acquisition is not complete")
    for source in acquisition["filings"]:
        path = SOURCE / source["file"]
        if not path.is_file() or sha256(path) != source["sha256"]:
            raise ValueError(f"Source SHA-256 mismatch: {source['file']}")
        if source["http_status"] != 200 or "www.sec.gov/Archives/edgar/data/2046523/" not in source["url"]:
            raise ValueError(f"Unverified origin/status: {source['file']}")

    sec_text = load_text(SOURCE / "tm252785d11_8k.htm")
    ssa = load_text(SOURCE / "tm252785d11_ex4-1.htm")
    indenture = load_text(SOURCE / "tm252785d11_ex4-2.htm")
    amendment_filing = load_text(SOURCE / "tm263585d12_8k.htm")
    amendment = load_text(SOURCE / "tm263585d12_ex4-1.htm")

    required = [
        (sec_text, "On the Closing Date", "closing-date execution statement"),
        (sec_text, "January 29, 2025", "closing date"),
        (sec_text, "Sale and Servicing Agreement", "SSA exhibit reference"),
        (sec_text, "Indenture", "Indenture exhibit reference"),
        (ssa, "Section 5.06", "SSA distributions section"),
        (ssa, "Class A Noteholders’ Interest Distributable Amount", "A interest priority"),
        (ssa, "Noteholders’ First Priority Principal Distributable Amount", "first principal priority"),
        (ssa, "the Reserve Account", "reserve account stage"),
        (indenture, "Section 8.02(d)", "Indenture ordinary payment route"),
        (indenture, "Section 8.02(e)", "Indenture accelerated payment route"),
        (amendment_filing, "Omnibus Amendment to Sale and Servicing Agreement", "2026 amendment event"),
        (amendment, "World Omni Auto Receivables Trust 2025-A", "amendment applies to 2025-A"),
        (amendment, "Conversion Date ” means the date on which the Sponsor begins using", "Conversion Date definition"),
        (amendment, "$40 with respect to payments effective on or prior to the Conversion Date", "pre-conversion amount threshold"),
        (amendment, "10% of the applicable scheduled payment for payments effective on or after the Conversion Date", "post-conversion amount threshold"),
        (amendment, "more than the Delinquency Threshold Amount of a scheduled payment is 120 or more days past due", "amended default definition"),
        (amendment, "repossessed and held the related Financed Vehicle in its repossession inventory for 45 days", "repossession default alternative"),
        (amendment, "The Principal Balance of any Receivable that becomes a Defaulted Receivable will be deemed to be zero", "default balance treatment"),
        (amendment, "This Amendment shall become effective as of January 13, 2026", "amendment stated effective date"),
    ]
    checks = []
    for content, phrase, label in required:
        need(content, phrase, label)
        checks.append({"check": label, "status": "PASS"})

    conversion_definition = re.search(
        r"Conversion Date.{0,40}?means the date on which the Sponsor begins using.{0,400}?\.",
        amendment,
        flags=re.I,
    )
    if not conversion_definition:
        raise ValueError("Conversion Date definition could not be isolated")
    # The source defines an operational trigger but gives no specific calendar date.
    concrete_date_after_label = bool(re.search(
        r"Conversion Date.{0,30}?(?:\s+is|\s+shall be|\s+means)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}",
        amendment,
        flags=re.I,
    ))
    if concrete_date_after_label:
        raise ValueError("Amendment text appears to state a calendar Conversion Date; re-review needed")

    profile = {
        "source_id": SOURCE_ID,
        "deal": "World Omni Auto Receivables Trust 2025-A",
        "cik": "0002046523",
        "source_receipt_sha256": sha256(receipt_path),
        "acquisition_completed_at": acquisition["completed_at"],
        "source_file_count": len(acquisition["filings"]),
        "checks": checks,
        "ordinary_and_accelerated_waterfall_are_distinct": True,
        "amendment_conversion_date": "UNKNOWN_NOT_STATED_AS_CALENDAR_DATE_IN_AMENDMENT",
        "amendment_effective_date": "2026-01-13, subject to the listed effectiveness conditions",
        "lineage": {
            "closing_filing": "0001104659-25-007200",
            "amendment_filing": "0001104659-26-005075",
            "all_source_files_sha256_verified": True,
        },
        "limitations": [
            "This is source-text presence and hash verification, not legal interpretation or counsel opinion.",
            "Rating Agency Condition and legal-opinion delivery evidence were not acquired.",
            "The source does not identify the operational Conversion Date; threshold cannot be time-sliced from this amendment alone.",
            "No asset-level receivable tape was acquired or reclassified.",
            "No app waterfall code or contractual-compliance qualification was changed.",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=False)
    profile_path = OUT / "profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "status": "SOURCE_HASH_AND_CLAUSE_AUDIT_PASS",
        "audit_id": OUT.name,
        "script": str(Path(__file__).relative_to(ROOT)).replace("\\", "/"),
        "script_sha256": sha256(Path(__file__)),
        "source_receipt_sha256": sha256(receipt_path),
        "profile": str(profile_path.relative_to(ROOT)).replace("\\", "/"),
        "profile_sha256": sha256(profile_path),
        "checks_passed": len(checks),
        "checks_failed": 0,
        "conversion_date": profile["amendment_conversion_date"],
        "completed_at": timestamp(),
    }
    write_new(OUT / "receipt.json", receipt)
    print(json.dumps({"audit": str(OUT.relative_to(ROOT)).replace("\\", "/"), "checks": len(checks), "conversion_date": profile["amendment_conversion_date"]}, ensure_ascii=False))
    return OUT


if __name__ == "__main__":
    main()
