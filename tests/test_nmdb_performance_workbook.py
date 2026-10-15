import csv
from pathlib import Path

from openpyxl import load_workbook


def test_nmdb_workbook_has_latest_summary_and_filterable_full_series():
    root = Path(__file__).parents[1]
    workbook = load_workbook(root / "apps/excel/templates/CreditAtlas-NMDB-Performance.xlsx", data_only=True)
    assert workbook.sheetnames == ["Bat dau", "Latest KPIs", "Quarterly data", "Definitions"]
    with (root / "docs/data/nmdb-performance-national-quarterly-2026q2.csv").open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    latest = workbook["Latest KPIs"]
    assert latest.max_row == 5
    assert latest["A2"].value == "2026Q2"
    assert latest["D2"].value == 1.7
    assert latest["E2"].value == 1.0
    assert latest["G2"].value == 0.5
    assert latest.freeze_panes == "B2"
    assert len(latest.tables) == 1
    quarterly = workbook["Quarterly data"]
    assert quarterly.max_row == len(source_rows) + 1
    assert quarterly["G2"].value == "2002Q1"
    assert quarterly["G1569"].value == "2026Q2"
    assert quarterly["M4"].value is None
    assert quarterly.freeze_panes == "B2"
    assert len(quarterly.tables) == 1
    assert next(iter(quarterly.tables.values())).autoFilter is not None
    assert "2019Q4" in workbook["Definitions"]["D5"].value
