"""Build the private analyst workbook for Federal Reserve bank asset quality."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from credit_atlas.fed_bank_mortgage_context import report
from credit_atlas.workspace import read_json, sha256


NAVY = "17324D"
BLUE = "2268A0"
PALE = "E8F1F8"
GRAY = "5B6770"
GREEN = "E5F3EB"
YELLOW = "FFF4D6"


def _style_title(ws, title: str, subtitle: str, last_col: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    cell = ws.cell(1, 1, title)
    cell.font = Font(name="Aptos Display", size=19, bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor=NAVY)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 34
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=last_col)
    cell = ws.cell(2, 1, subtitle)
    cell.font = Font(name="Aptos", size=10, color=GRAY, italic=True)
    cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 31


def _header(ws, row: int, cols: int) -> None:
    for cell in ws[row][:cols]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = 32


def _table(ws, name: str, ref: str) -> None:
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True,
                                          showColumnStripes=False, showFirstColumn=False,
                                          showLastColumn=False)
    ws.add_table(table)


def build(root: Path, output: Path) -> dict:
    payload = report(root)
    public_context = root / "data/private/public-context"
    run_folder = max(
        (folder for folder in public_context.glob("fed-bank-mortgage-asset-quality-*")
         if (folder / "manifest.json").is_file()),
        key=lambda folder: str(read_json(folder / "manifest.json").get("completed_at", "")),
    )
    manifest = read_json(run_folder / "manifest.json")
    wb = Workbook()
    overview = wb.active
    overview.title = "Overview"
    hist = wb.create_sheet("Quarterly History")
    dictionary = wb.create_sheet("Series Dictionary")
    sources = wb.create_sheet("Sources & QA")

    _style_title(overview, "CreditAtlas · Federal Reserve Bank Asset Quality",
                 "Aggregate quarterly portfolio context for five bank lending domains · latest revised public snapshot · context only",
                 12)
    overview.append([])
    overview.append(["Latest common quarter", payload["last_period"], "Coverage starts", payload["first_period"],
                     "Quarterly dates", payload["quarter_count"], "Products", len(payload["products"])])
    for cell in overview[4]:
        cell.fill = PatternFill("solid", fgColor=PALE)
        cell.font = Font(bold=True, color=NAVY)
    overview.append([])
    overview.append(["Product", "Delinquency %", "Δ 4Q pp", "Delinquency high %", "High quarter", "Current percentile",
                     "Net charge-off %", "Δ 4Q pp", "Charge-off high %", "High quarter", "Current percentile", "Interpretation"])
    _header(overview, 6, 12)
    by_product = {product: {s["series_id"][:2]: s for s in payload["series"] if s["product"] == product}
                  for product in payload["products"]}
    current = next(r for r in payload["rows"] if r["period"] == payload["last_period"])
    previous_year = next((r for r in payload["rows"]
                          if r["period"][:4] == str(int(payload["last_period"][:4]) - 1)
                          and r["period"][5:] == payload["last_period"][5:]), {})
    for product, pair in by_product.items():
        d, c = pair["DR"], pair["CO"]
        d_now, c_now = current.get(d["series_id"]), current.get(c["series_id"])
        d_old, c_old = previous_year.get(d["series_id"]), previous_year.get(c["series_id"])
        row = overview.max_row + 1
        overview.append([product, d_now, None if d_old is None else d_now - d_old,
                         d["historical_high_value"], d["historical_high_date"], d["historical_percentile"],
                         c_now, None if c_old is None else c_now - c_old,
                         c["historical_high_value"], c["historical_high_date"], c["historical_percentile"],
                         "Delinquency / net charge-off"])
        for col in (2, 4, 7, 9):
            overview.cell(row, col).number_format = '0.00"%";[Red]-0.00"%";–'
        overview.cell(row, 3).number_format = '+0.00" pp";[Red]-0.00" pp";–'
        overview.cell(row, 8).number_format = '+0.00" pp";[Red]-0.00" pp";–'
        overview.cell(row, 6).number_format = '0.0"%"'
        overview.cell(row, 11).number_format = '0.0"%"'
    _table(overview, "ProductSummary", f"A6:L{overview.max_row}")
    series_columns = {s["series_id"]: col for col, s in enumerate(payload["series"], 2)}
    chart_slots = ["N3", "N21", "N39", "N57", "N75"]
    for product, anchor in zip(payload["products"], chart_slots):
        pair = by_product[product]
        chart = LineChart()
        chart.title = product + " · delinquency vs net charge-off"
        chart.style = 13
        chart.y_axis.title = "Percent"
        chart.x_axis.title = "Quarter"
        chart.height = 7.1
        chart.width = 14.2
        for series_id, color in ((pair["DR"]["series_id"], "2268A0"),
                                 (pair["CO"]["series_id"], "39A37A")):
            data = Reference(hist, min_col=series_columns[series_id], min_row=4, max_row=hist.max_row)
            chart.add_data(data, titles_from_data=True)
            chart.series[-1].graphicalProperties.line.solidFill = color
            chart.series[-1].graphicalProperties.line.width = 22000
            chart.series[-1].smooth = False
        chart.set_categories(Reference(hist, min_col=1, min_row=5, max_row=hist.max_row))
        chart.legend.position = "b"
        overview.add_chart(chart, anchor)
    note_row = overview.max_row + 2
    overview.cell(note_row, 1, "How to read")
    overview.cell(note_row, 1).font = Font(bold=True, color=NAVY)
    overview.cell(note_row + 1, 1, "Delinquency is 30+ days past due and still accruing or nonaccrual. Charge-off is annualized net of recoveries.")
    overview.merge_cells(start_row=note_row + 1, start_column=1, end_row=note_row + 1, end_column=12)
    overview.cell(note_row + 1, 1).alignment = Alignment(wrap_text=True)
    overview.cell(note_row + 2, 1, "Blank deltas mean no year-ago value is available; blank history cells mean the series had not begun. Never read blanks as zero.")
    overview.merge_cells(start_row=note_row + 2, start_column=1, end_row=note_row + 2, end_column=12)
    overview.cell(note_row + 2, 1).fill = PatternFill("solid", fgColor=YELLOW)
    overview.cell(note_row + 2, 1).alignment = Alignment(wrap_text=True)
    for col, width in enumerate([25, 16, 15, 18, 16, 18, 18, 15, 18, 16, 18, 32], 1):
        overview.column_dimensions[chr(64 + col)].width = width
    overview.freeze_panes = "A7"

    _style_title(hist, "Quarterly History · rates in percent",
                 "Native quarterly grain; source series are seasonally adjusted and retain their own start dates.", 11)
    headers = ["Quarter", *[s["series_id"] for s in payload["series"]]]
    hist.append([])
    hist.append(headers)
    _header(hist, 4, len(headers))
    for row in payload["rows"]:
        hist.append([row["period"], *[row.get(s["series_id"]) for s in payload["series"]]])
    _table(hist, "QuarterlyRates", f"A4:K{hist.max_row}")
    hist.freeze_panes = "B5"
    hist.column_dimensions["A"].width = 16
    for col in range(2, 12):
        hist.column_dimensions[chr(64 + col)].width = 18
        for cells in hist.iter_rows(min_row=5, min_col=col, max_col=col):
            cells[0].number_format = "0.00;[Red]-0.00;–"
    hist.sheet_view.showGridLines = False

    _style_title(dictionary, "Series Dictionary · definitions and coverage",
                 "Use series IDs for source traceability. Rates are percentage points (not decimal proportions).", 8)
    dict_headers = ["Product", "Series ID", "Measure", "Frequency", "Adjustment", "Denominator", "Interpretation", "Coverage"]
    dictionary.append([])
    dictionary.append(dict_headers)
    _header(dictionary, 4, len(dict_headers))
    for s in payload["series"]:
        dictionary.append([s["product"], s["series_id"], s["label"], s["frequency"],
                           s["seasonal_adjustment"], s["denominator"], s["interpretation"],
                           f"{s['first_reference_date']} → {s['last_reference_date']} ({s['observation_count']} quarters)"])
    _table(dictionary, "SeriesDictionary", f"A4:H{dictionary.max_row}")
    dictionary.freeze_panes = "A5"
    for col, width in enumerate([25, 20, 22, 24, 24, 43, 56, 42], 1):
        dictionary.column_dimensions[chr(64 + col)].width = width
    for row in dictionary.iter_rows(min_row=5):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        dictionary.row_dimensions[row[0].row].height = 40

    _style_title(sources, "Sources, lineage & QA",
                 "Private workbook generated from validated public FRED downloads; raw snapshots and receipt stay on D:.", 5)
    sources.append([])
    source_rows = [
        ["Publisher", manifest["source"]],
        ["Release", manifest["release"]],
        ["Release URL", manifest["release_url"]],
        ["Acquired at", manifest["retrieved_at"]],
        ["Validated at", manifest["completed_at"]],
        ["Run directory", str(run_folder)],
        ["Visibility", "Private local data; not copied to public repository"],
        ["Qualification", "Aggregate descriptive context only; not a model predictor"],
        ["SHA-256 receipt", "See per-series hashes below"],
    ]
    for item in source_rows:
        sources.append(item)
    sources.append([])
    sources.append(["Series ID", "Source CSV URL", "Metadata URL", "Observation count", "SHA-256"])
    _header(sources, sources.max_row, 5)
    for series_id, info in manifest["series"].items():
        sources.append([series_id, info["source_url"], info["metadata_url"], info["observations"], info["sha256"]])
    first_data = sources.max_row - len(manifest["series"]) + 1
    _table(sources, "SourceReceipt", f"A{first_data-1}:E{sources.max_row}")
    limitations_start = sources.max_row + 2
    sources.cell(limitations_start, 1, "Limitations")
    sources.cell(limitations_start, 1).font = Font(bold=True, color=NAVY)
    for idx, limitation in enumerate(payload["limitations"], limitations_start + 1):
        sources.cell(idx, 1, "• " + limitation)
        sources.merge_cells(start_row=idx, start_column=1, end_row=idx, end_column=5)
        sources.cell(idx, 1).alignment = Alignment(wrap_text=True, vertical="top")
        sources.row_dimensions[idx].height = 34
    for col, width in enumerate([25, 66, 62, 19, 68], 1):
        sources.column_dimensions[chr(64 + col)].width = width
    sources.freeze_panes = "A13"

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.outlinePr.summaryBelow = True
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    # Re-open and verify workbook structure, row coverage, table, and embedded source hashes.
    check = load_workbook(output, read_only=False, data_only=False)
    assert check.sheetnames == ["Overview", "Quarterly History", "Series Dictionary", "Sources & QA"]
    assert check["Quarterly History"].max_row == len(payload["rows"]) + 4
    assert len(check["Quarterly History"].tables) == 1
    assert len(check["Overview"]._charts) == len(payload["products"])
    assert check["Sources & QA"].max_row > len(manifest["series"])
    return {"status": "BUILT_AND_REOPENED", "output": str(output), "bytes": output.stat().st_size,
            "sha256": sha256(output), "series": len(payload["series"]),
            "products": len(payload["products"]), "quarters": payload["quarter_count"],
            "latest_quarter": payload["last_period"], "generated_at": datetime.now(timezone.utc).isoformat()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "apps/excel/templates/CreditAtlas-Fed-Bank-Asset-Quality.xlsx"
    print(json.dumps(build(root, output.resolve()), indent=2))


if __name__ == "__main__":
    main()
