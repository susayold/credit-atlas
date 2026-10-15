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
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    rows, audit = extract(args.source_pdf)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS + ["source_pdf_page"])
        writer.writeheader()
        writer.writerows(rows)
    audit["derived_table"] = {
        "filename": args.output_csv.name,
        "rows": len(rows),
        "sha256": hashlib.sha256(args.output_csv.read_bytes()).hexdigest(),
    }
    audit["built_at"] = datetime.now(timezone.utc).isoformat()
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "waves": audit["waves"], "puf_v70_waves": audit["puf_v70_waves"],
                      "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
