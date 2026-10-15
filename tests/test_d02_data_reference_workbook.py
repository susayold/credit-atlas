import csv
from pathlib import Path

from openpyxl import load_workbook


def test_d02_reference_workbook_includes_every_public_data_csv():
    root = Path(__file__).parents[1]
    path = root / "apps/excel/templates/CreditAtlas-D02-Data-Reference.xlsx"
    assert path.is_file()
    workbook = load_workbook(path, read_only=False, data_only=True)
    assert workbook.sheetnames == [
        "Start here", "NSMO fields", "NSMO feature gates", "NSMO routing", "NSMO categories", "NSMO wave coverage", "NSMO item wording",
        "NSMO returns", "NSMO usability", "NMDB quarterly", "HUD monthly", "HUD subgroups", "NMDB definitions",
    ]
    expected = {
        "NSMO fields": "nsmo-v70-field-dictionary.csv",
        "NSMO feature gates": "nsmo-v70-predictor-gates.csv",
        "NSMO routing": "nsmo-v70-routing-review.csv",
        "NSMO categories": "nsmo-v70-value-labels.csv",
        "NSMO wave coverage": "nsmo-v70-wave-coverage.csv",
        "NSMO item wording": "nsmo-v70-wave-item-comparability.csv",
        "NSMO returns": "nsmo-v70-survey-returns.csv",
        "NSMO usability": "nsmo-v70-usable-responses.csv",
        "NMDB quarterly": "nmdb-performance-national-quarterly-2026q2.csv",
        "HUD monthly": "hud-fha-performance-2026-08.csv",
        "HUD subgroups": "hud-fha-performance-2026-08-subgroups.csv",
    }
    for sheet_name, csv_name in expected.items():
        with (root / "docs/data" / csv_name).open(encoding="utf-8-sig", newline="") as stream:
            row_count = sum(1 for _ in csv.DictReader(stream))
        sheet = workbook[sheet_name]
        assert sheet.max_row == row_count + 1
        assert sheet.freeze_panes == "B2"
        assert len(sheet.tables) == 1
        table = next(iter(sheet.tables.values()))
        assert table.autoFilter is not None
    assert workbook["NSMO categories"].cell(2, 2).value in {"1", "'1'"}
    assert workbook["NMDB quarterly"].max_row == 1569
    returns = workbook["NSMO returns"]
    assert returns.max_row == 49
    assert returns.cell(2, 1).value == 1
    assert returns.cell(47, 17).value is True
    assert returns.cell(48, 17).value is False
    assert returns.cell(49, 17).value is False
    usability = workbook["NSMO usability"]
    assert usability.max_row == 47
    assert usability.cell(2, 7).value == 4618
    assert usability.cell(8, 9).value == 295
    assert usability.cell(46, 9).value == 3
    assert usability.cell(47, 9).value == 494
    assert workbook["Start here"]["B2"].value.startswith("Excel copy of the D02")
    gates = workbook["NSMO feature gates"]
    assert gates.max_row == 588
    assert gates.cell(2, 2).value == "nsmoid"
    assert gates.cell(2, 7).value == "IDENTIFIER_EXCLUDE"
    assert all(not str(gates.cell(row, 9).value).startswith("APPROVED") for row in range(2, gates.max_row + 1))
    assert workbook["Start here"]["B4"].value.startswith("The feature-gates sheet")
    routing = workbook["NSMO routing"]
    assert routing.max_row == 320
    statuses = [routing.cell(row, 16).value for row in range(2, routing.max_row + 1)]
    ref_statuses = [routing.cell(row, 6).value for row in range(2, routing.max_row + 1)]
    assert statuses.count("CONDITIONAL_ROUTING_DOCUMENTED") == 58
    assert statuses.count("LEGACY_GATEWAY_MAPPING_REQUIRED") == 12
    assert ref_statuses.count("RECONCILED_FROM_FIELD_ID_AND_QUESTIONNAIRE") == 7
