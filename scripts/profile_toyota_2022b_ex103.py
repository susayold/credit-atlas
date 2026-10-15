"""Extract and version-track Toyota 2022-B EX-103 asset-field narratives."""
from __future__ import annotations

import gzip
import json
import re
import uuid
from collections import Counter, defaultdict
from pathlib import Path

from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "toyota-2022b-ex103-6e1500e4671f"
FIELD_PATTERN = re.compile(rb"<([A-Za-z][A-Za-z0-9]*)\s*/>\s*<!--(.*?)-->", re.DOTALL)


def clean_text(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="strict")
    return " ".join(text.split())


def profile() -> Path:
    source = contained(ROOT, "data/private/structured/" + SOURCE_ID)
    receipt_path = source / "acquisition-complete.json"
    receipt = read_json(receipt_path)
    if receipt.get("status") != "SEC_OFFICIAL_TOYOTA_2022B_EX103_ACQUIRED" or receipt.get("report_count") != 51:
        raise ValueError("Toyota 2022-B EX-103 acquisition receipt mismatch")
    definitions: dict[str, Counter] = defaultdict(Counter)
    periods_with_field: Counter = Counter()
    total_bytes = 0
    for report in receipt["reports"]:
        path = contained(source, report["file"])
        if path.stat().st_size != report["compressed_bytes"] or sha256(path) != report["compressed_sha256"]:
            raise ValueError(f"EX-103 hash/size mismatch for {report['report_date']}")
        total_bytes += report["uncompressed_bytes"]
        with gzip.open(path, "rb") as stream:
            raw = stream.read(2 * 1024**2 + 1)
        if len(raw) > 2 * 1024**2 or b"Explanatory Narrative" not in raw:
            raise ValueError("EX-103 narrative missing or oversized")
        matches = FIELD_PATTERN.findall(raw)
        fields_this_period = set()
        for raw_name, raw_description in matches:
            name = raw_name.decode("ascii")
            description = clean_text(raw_description)
            if name in fields_this_period:
                raise ValueError(f"Duplicate field narrative {name} in {report['report_date']}")
            fields_this_period.add(name)
            definitions[name][description] += 1
        periods_with_field.update(fields_this_period)
    if len(definitions) < 25:
        raise ValueError(f"Unexpectedly few EX-103 field narratives: {len(definitions)}")
    latest_definitions = {}
    changes = {}
    for name, versions in sorted(definitions.items()):
        selected = versions.most_common(1)[0][0]
        latest_definitions[name] = {"definition": selected,
                                    "periods_present": periods_with_field[name],
                                    "unique_text_versions": len(versions),
                                    "version_counts": dict(versions)}
        if len(versions) > 1:
            changes[name] = dict(versions)
    result = {
        "status": "TOYOTA_2022B_EX103_FIELD_NARRATIVES_PROFILED",
        "source_id": SOURCE_ID,
        "source_receipt_sha256": sha256(receipt_path),
        "linked_absee_source_id": receipt["linked_absee_source_id"],
        "period_count": receipt["report_count"], "report_start": receipt["report_start"],
        "report_end": receipt["report_end"], "uncompressed_source_bytes": total_bytes,
        "field_count": len(latest_definitions), "stable_field_definition_count": len(latest_definitions) - len(changes),
        "fields": latest_definitions, "field_definition_changes": changes,
        "source_scope": "Issuer-specific narrative accompanying EX-102; text definitions are copied from SEC EX-103 comments.",
        "limitations": ["EX-103 narrative supplements deal prospectus and Regulation AB; it does not replace either.",
                        "Text consistency does not validate every numeric value, aggregation sign, timing, or model label.",
                        "The profile retains deal-specific field wording; it does not infer cross-issuer semantic equivalence."],
        "created_at": timestamp(), "visibility": "private", "public_release_approved": False,
    }
    out = contained(ROOT, "artifacts/private/toyota-2022b-ex103-profile-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "profile.json", result)
    write_new(out / "receipt.json", {"status": result["status"], "profile_sha256": sha256(out / "profile.json"),
                                     "periods": result["period_count"], "fields": result["field_count"],
                                     "stable_definitions": result["stable_field_definition_count"],
                                     "changed_field_definitions": len(changes),
                                     "visibility": "private", "public_release_approved": False})
    print(out)
    print(json.dumps({"status": result["status"], "periods": result["period_count"],
                      "fields": result["field_count"], "stable_definitions": result["stable_field_definition_count"],
                      "changed_fields": len(changes)}))
    return out


if __name__ == "__main__":
    profile()
