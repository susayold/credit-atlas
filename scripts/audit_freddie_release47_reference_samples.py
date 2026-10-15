"""Profile the public Release 47 layout/example files without treating them as vintages."""
import json
import uuid
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from credit_atlas.workspace import sha256, timestamp, write_new

ROOT = Path(__file__).resolve().parents[1]
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def numeric_field_positions(xlsx_path, sheet_path):
    with zipfile.ZipFile(xlsx_path) as archive:
        root = ET.fromstring(archive.read(sheet_path))
    positions = []
    for row in root.findall(".//m:sheetData/m:row", NS):
        if int(row.attrib.get("r", "0")) < 3:
            continue
        cell = next((item for item in row.findall("m:c", NS)
                     if item.attrib.get("r", "").startswith("A")), None)
        if cell is None:
            continue
        value = cell.find("m:v", NS)
        if value is not None and value.text and value.text.isdigit():
            positions.append(int(value.text))
    return positions


def load_lines(archive, name, expected_fields):
    raw = archive.read(name).decode("utf-8-sig")
    lines = raw.splitlines()
    rows = [line.split("|") for line in lines]
    if not rows or any(len(row) != expected_fields for row in rows):
        raise ValueError(f"Unexpected field count in {name}")
    return rows


def audit(folder):
    receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("status") != "ACQUIRED" or receipt.get("added_annual_vintages") != 0:
        raise ValueError("Expected a successful public-reference acquisition only")
    by_name = {item["file"]: item for item in receipt["files"]}
    zip_path = folder / "release-47-sample-files.zip"
    xlsx_path = folder / "file-layout-july-2026.xlsx"
    if sha256(zip_path) != by_name[zip_path.name]["sha256"]:
        raise ValueError("Release 47 ZIP hash changed")
    if sha256(xlsx_path) != by_name[xlsx_path.name]["sha256"]:
        raise ValueError("Release 47 layout hash changed")
    orig_positions = numeric_field_positions(xlsx_path, "xl/worksheets/sheet1.xml")
    perf_positions = numeric_field_positions(xlsx_path, "xl/worksheets/sheet2.xml")
    if orig_positions != list(range(1, 32)) or perf_positions != list(range(1, 36)):
        raise ValueError("Unexpected Release 47 layout positions")
    with zipfile.ZipFile(zip_path) as archive:
        orig = load_lines(archive, "Sample Files/origination_sample_file.txt", len(orig_positions))
        perf = load_lines(archive, "Sample Files/performance_sample_file.txt", len(perf_positions))
    orig_ids = {row[19] for row in orig}
    perf_ids = {row[0] for row in perf}
    periods = [row[1] for row in perf]
    audit = {
        "created_at": timestamp(),
        "source_role": "public_format_reference_only_not_annual_loan_performance_sample",
        "release": 47,
        "source_retrieved_at": max(item["retrieved_at"] for item in receipt["files"]),
        "source_files": {name: {"sha256": by_name[name]["sha256"], "bytes": by_name[name]["bytes"]}
                         for name in (zip_path.name, xlsx_path.name)},
        "release_47_layout": {
            "origination_positions": len(orig_positions), "performance_positions": len(perf_positions),
            "position_sequences_contiguous": True,
        },
        "example_file_profile": {
            "origination_rows": len(orig), "origination_fields_each": len(orig[0]),
            "distinct_origination_loan_ids": len(orig_ids),
            "performance_rows": len(perf), "performance_fields_each": len(perf[0]),
            "distinct_performance_loan_ids": len(perf_ids),
            "performance_reference_months": len(set(periods)),
            "performance_month_range": [min(periods), max(periods)],
            "origination_performance_id_overlap": len(orig_ids & perf_ids),
        },
        "qualification": {
            "matches_published_layout_field_counts": True,
            "paired_loan_panel_usable": False,
            "annual_vintage_qualified": False,
            "annual_vintages_added": 0,
            "reason": "The public examples are small format files and their loan identifier populations do not overlap; the annual samples remain behind authenticated Clarity download.",
        },
        "limitation": "Counts and layout compatibility are verified for these public examples only; this does not establish annual sample schema compatibility, representativeness, source release of the supplied 2012 ZIP, or model eligibility.",
    }
    out = ROOT / "artifacts/private" / ("freddie-release47-reference-audit-" + uuid.uuid4().hex[:12])
    out.mkdir(parents=True)
    write_new(out / "audit.json", audit)
    write_new(out / "receipt.json", {"status": "PASS", "audit": str((out / "audit.json").relative_to(ROOT)),
              "audit_sha256": sha256(out / "audit.json"), "source_zip_sha256": by_name[zip_path.name]["sha256"],
              "layout_sha256": by_name[xlsx_path.name]["sha256"], "annual_vintages_added": 0})
    return {"audit": str(out / "audit.json"), **audit["example_file_profile"]}


if __name__ == "__main__":
    candidates = sorted(ROOT.glob("data/private/mortgage/freddie-public-reference-*"),
                        key=lambda path: path.stat().st_mtime, reverse=True)
    source = next(path for path in candidates if (path / "file-layout-july-2026.xlsx").is_file()
                  and (path / "release-47-sample-files.zip").is_file())
    print(json.dumps(audit(source), ensure_ascii=False))
