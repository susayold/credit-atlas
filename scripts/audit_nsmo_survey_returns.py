"""Extract and reconcile the public NSMO Technical Report v7.0 Table 3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

SOURCE_URL = "https://www.fhfa.gov/document/d/nsmo/nsmo-technical-report-v70.pdf"
EXPECTED_TOTALS = {
    "surveys_mailed": 281942,
    "postal_nondelivery": 9494,
    "surveys_delivered": 272448,
    "surveys_completed_total": 76405,
    "completed_by_mail": 41254,
    "online_english": 34529,
    "online_spanish": 622,
    "opt_out": 1259,
}
FIELDS = [
    "survey_wave", "average_sampling_weight", "surveys_mailed", "postal_nondelivery",
    "surveys_delivered", "surveys_completed_total", "completed_by_mail", "online_english",
    "online_spanish", "opt_out", "completion_pct_of_mailed", "completion_pct_of_delivered",
    "mail_share_pct_of_completed", "online_share_pct_of_completed",
    "online_english_share_pct_of_completed", "online_spanish_share_pct_of_completed",
    "included_in_nsmo_v70_puf", "source_note",
]
USABILITY_FIELDS = [
    "survey_wave", "surveys_completed_total", "duplicate_or_ineligible", "answered_no_to_q1",
    "did_not_finish_survey", "wrong_loan", "usable_responses_table4",
    "usable_responses_origination_2013_2024_tables5_6", "gap_to_usable_table4",
    "source_pdf_page_table4", "source_pdf_pages_tables5_6", "source_note",
]
EXPECTED_USABILITY_TOTALS = {
    "surveys_completed_total": 74193,
    "duplicate_or_ineligible": 2009,
    "answered_no_to_q1": 4102,
    "did_not_finish_survey": 2592,
    "wrong_loan": 2339,
    "usable_responses_table4": 63151,
    "usable_responses_origination_2013_2024_tables5_6": 62359,
    "gap_to_usable_table4": 792,
}


def _integer(value: str) -> int:
    return int(value.replace(",", ""))


def parse_row_line(line: str) -> dict | None:
    """Parse one Table 3 row, including the two superscript footnote artifacts."""
    cells = line.split()
    if len(cells) != 10:
        return None
    wave_token = cells[0]
    if wave_token == "2715":
        wave = 27  # superscript 15 is attached to the printed wave number
    elif wave_token.isdigit():
        wave = int(wave_token)
    else:
        return None
    if wave not in range(1, 49):
        return None

    data = cells[1:]
    if wave == 30 and data[4] == "1,57616":
        data[4] = "1,576"  # superscript 16 is attached to this table cell
    try:
        avg_weight = Decimal(data[0])
        mailed, nondelivery, delivered, completed, by_mail, online_en, online_es, opt_out = (
            _integer(value) for value in data[1:]
        )
    except (ValueError, ArithmeticError):
        return None
    if mailed != nondelivery + delivered:
        raise ValueError(f"Wave {wave}: mailed does not reconcile to delivered plus non-delivery")
    if completed != by_mail + online_en + online_es:
        raise ValueError(f"Wave {wave}: total completed does not reconcile to response modes")
    if completed > delivered:
        raise ValueError(f"Wave {wave}: completed surveys exceed delivered surveys")

    def pct(numerator: int, denominator: int) -> str:
        return str((Decimal(numerator) * 100 / Decimal(denominator)).quantize(Decimal("0.01")))

    mode_share_denom = completed
    note = ""
    if wave == 27:
        note = "FHFA footnote: average sampling weight increased in 2020 due to unusually high originations."
    elif wave == 30:
        note = "FHFA footnote: responses noticeably dropped; FHFA cites vaccination and rate changes as possible factors."
    return {
        "survey_wave": wave,
        "average_sampling_weight": str(avg_weight),
        "surveys_mailed": mailed,
        "postal_nondelivery": nondelivery,
        "surveys_delivered": delivered,
        "surveys_completed_total": completed,
        "completed_by_mail": by_mail,
        "online_english": online_en,
        "online_spanish": online_es,
        "opt_out": opt_out,
        "completion_pct_of_mailed": pct(completed, mailed),
        "completion_pct_of_delivered": pct(completed, delivered),
        "mail_share_pct_of_completed": pct(by_mail, mode_share_denom),
        "online_share_pct_of_completed": pct(online_en + online_es, mode_share_denom),
        "online_english_share_pct_of_completed": pct(online_en, mode_share_denom),
        "online_spanish_share_pct_of_completed": pct(online_es, mode_share_denom),
        "included_in_nsmo_v70_puf": wave <= 46,
        "source_note": note,
    }


def parse_usable_row_line(line: str) -> dict | None:
    """Parse one Table 4 usable-response disposition row."""
    cells = line.split()
    if len(cells) != 7 or not cells[0].isdigit():
        return None
    wave = int(cells[0])
    if wave not in range(1, 47):
        return None
    returned, duplicate, no_q1, breakoff, wrong_loan, usable = (_integer(value) for value in cells[1:])
    if returned != duplicate + no_q1 + breakoff + wrong_loan + usable:
        raise ValueError(f"Wave {wave}: Table 4 usable dispositions do not reconcile to returned surveys")
    return {
        "survey_wave": wave,
        "surveys_completed_total": returned,
        "duplicate_or_ineligible": duplicate,
        "answered_no_to_q1": no_q1,
        "did_not_finish_survey": breakoff,
        "wrong_loan": wrong_loan,
        "usable_responses_table4": usable,
    }


def parse_origin_usable_line(line: str) -> tuple[int, int] | None:
    """Return wave and published total for one Table 5 or Table 6 row."""
    cells = line.split()
    if len(cells) not in {7, 9} or not cells[0].isdigit():
        return None
    wave = int(cells[0])
    if wave not in range(1, 47):
        return None
    reported_total = _integer(cells[1])
    year_counts = [_integer(value) for value in cells[2:]]
    if reported_total != sum(year_counts):
        raise ValueError(f"Wave {wave}: Tables 5/6 origination-year counts do not reconcile")
    return wave, reported_total


def extract_usable_responses(pdf_path: Path) -> tuple[list[dict], dict]:
    """Reconcile returned → usable → published-originations counts in Tables 4–6."""
    try:
        import pdfplumber
    except ImportError as error:
        raise RuntimeError("Install the research optional dependencies: pip install -e .[research]") from error
    table4: dict[int, dict] = {}
    tables56: dict[int, int] = {}
    pages56: dict[int, list[int]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if "Usable Survey Responses" not in text:
                continue
            is_table4 = "Table 4. Usable Survey Responses" in text
            is_tables56 = ("Table 5. Usable Survey Responses" in text
                           or "Table 6. Usable Survey Responses" in text)
            for line in text.splitlines():
                usable_row = parse_usable_row_line(line) if is_table4 else None
                if usable_row:
                    wave = usable_row["survey_wave"]
                    if wave in table4:
                        raise ValueError(f"Duplicate Table 4 wave {wave}")
                    usable_row["source_pdf_page_table4"] = page_number
                    table4[wave] = usable_row
                origin_row = parse_origin_usable_line(line) if is_tables56 else None
                if origin_row:
                    wave, amount = origin_row
                    tables56[wave] = tables56.get(wave, 0) + amount
                    pages56.setdefault(wave, []).append(page_number)
    if set(table4) != set(range(1, 47)):
        raise ValueError(f"Expected Table 4 waves 1–46, got {len(table4)}")
    if set(tables56) != set(range(1, 47)):
        raise ValueError(f"Expected Tables 5/6 origination summary for waves 1–46, got {len(tables56)}")
    rows = []
    for wave in range(1, 47):
        row = table4[wave]
        published = tables56[wave]
        gap = row["usable_responses_table4"] - published
        note = ""
        if wave == 7:
            note = "Table 5 footnote excludes the special remote-rural sample; usable count is 295 above the published 2013–2024 origination table."
        elif wave in {45, 46}:
            note = "Table 4 includes usable returns beyond the 2013–2024 origination scope of Tables 5/6 and the v7.0 PUF."
        if gap < 0:
            raise ValueError(f"Wave {wave}: Tables 5/6 usable count exceeds Table 4")
        rows.append({
            **row,
            "usable_responses_origination_2013_2024_tables5_6": published,
            "gap_to_usable_table4": gap,
            "source_pdf_pages_tables5_6": ";".join(str(page) for page in sorted(set(pages56[wave]))),
            "source_note": note,
        })
    totals = {field: sum(row[field] for row in rows) for field in EXPECTED_USABILITY_TOTALS}
    if totals != EXPECTED_USABILITY_TOTALS:
        raise ValueError(f"Tables 4–6 usable-response totals do not reconcile to FHFA printed totals: {totals}")
    audit = {
        "waves": 46,
        "reconciliation": {"matches_printed_totals": True, "aggregate_totals": totals},
        "limitation": "Difference between Table 4 and Tables 5/6 is aggregate scope reconciliation; no survey respondent is linked to a PUF record by this extraction.",
    }
    return rows, audit


def extract(pdf_path: Path) -> tuple[list[dict], dict]:
    try:
        import pdfplumber
    except ImportError as error:
        raise RuntimeError("Install the research optional dependencies: pip install -e .[research]") from error
    rows_by_wave: dict[int, dict] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if "Survey Samples and Returns" not in text:
                continue
            for line in text.splitlines():
                row = parse_row_line(line)
                if row is None:
                    continue
                if row["survey_wave"] in rows_by_wave:
                    raise ValueError(f"Duplicate Table 3 wave {row['survey_wave']}")
                row["source_pdf_page"] = page_number
                rows_by_wave[row["survey_wave"]] = row
    if set(rows_by_wave) != set(range(1, 49)):
        missing = sorted(set(range(1, 49)) - set(rows_by_wave))
        extra = sorted(set(rows_by_wave) - set(range(1, 49)))
        raise ValueError(f"Expected Table 3 waves 1–48; missing={missing}, extra={extra}")
    rows = [rows_by_wave[wave] for wave in range(1, 49)]
    totals = {field: sum(int(row[field]) for row in rows) for field in EXPECTED_TOTALS}
    if totals != EXPECTED_TOTALS:
        raise ValueError(f"Table 3 totals do not reconcile to printed totals: {totals}")
    completed = totals["surveys_completed_total"]
    totals["completion_pct_of_mailed"] = str(
        (Decimal(completed) * 100 / Decimal(totals["surveys_mailed"])).quantize(Decimal("0.01"))
    )
    totals["mail_share_pct_of_completed"] = str(
        (Decimal(totals["completed_by_mail"]) * 100 / Decimal(completed)).quantize(Decimal("0.01"))
    )
    totals["online_share_pct_of_completed"] = str(
        (Decimal(totals["online_english"] + totals["online_spanish"]) * 100 / Decimal(completed)).quantize(Decimal("0.01"))
    )
    audit = {
        "status": "PASS",
        "source": {"sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(), "url": SOURCE_URL},
        "table": "NSMO Technical Report v7.0 Table 3, printed pages 10–11",
        "waves": 48,
        "puf_v70_waves": 46,
        "reconciliation": {"matches_printed_totals": True, "aggregate_totals": totals},
        "limitations": [
            "Table 3 reports wave-level counts only; it does not link response mode to a mortgage row or performance outcome.",
            "Waves 47–48 are in the report but are outside the v7.0 public-use-file waves 1–46.",
            "Response-mode shares describe completed surveys and are not adjusted estimates of mode-specific outcomes.",
        ],
    }
    return rows, audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--usable-output-csv", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    rows, audit = extract(args.source_pdf)
    usable_rows, usability_audit = extract_usable_responses(args.source_pdf)
    usable_output = args.usable_output_csv or args.output_csv.with_name("nsmo-v70-usable-responses.csv")
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS + ["source_pdf_page"])
        writer.writeheader()
        writer.writerows(rows)
    usable_output.parent.mkdir(parents=True, exist_ok=True)
    with usable_output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=USABILITY_FIELDS)
        writer.writeheader()
        writer.writerows(usable_rows)
    audit["derived_table"] = {
        "filename": args.output_csv.name,
        "rows": len(rows),
        "sha256": hashlib.sha256(args.output_csv.read_bytes()).hexdigest(),
    }
    audit["built_at"] = datetime.now(timezone.utc).isoformat()
    audit["usable_responses"] = usability_audit
    audit["related_table"] = {
        "filename": usable_output.name,
        "rows": len(usable_rows),
        "sha256": hashlib.sha256(usable_output.read_bytes()).hexdigest(),
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "waves": audit["waves"], "puf_v70_waves": audit["puf_v70_waves"],
                      "usable_waves": len(usable_rows), "usable_total": usability_audit["reconciliation"]["aggregate_totals"]["usable_responses_table4"],
                      "puf_scope_total": usability_audit["reconciliation"]["aggregate_totals"]["usable_responses_origination_2013_2024_tables5_6"],
                      "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
