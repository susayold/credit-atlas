import csv
from pathlib import Path

from openpyxl import load_workbook

def test_nsmo_reference_workbook_contains_all_reviewed_metadata():
    root = Path(__file__).parents[1]
    output = root / "apps/excel/templates/CreditAtlas-NSMO-Reference.xlsx"
    assert output.is_file()
    workbook = load_workbook(output, read_only=False, data_only=True)
    assert workbook.sheetnames == [
        "Bat dau", "Tu dien 587 truong", "Nhan va category", "Coverage theo wave", "So sanh wording item",
        "Do nhay horizon",
    ]
    expected = {
        "Tu dien 587 truong": "nsmo-v70-field-dictionary.csv",
        "Nhan va category": "nsmo-v70-value-labels.csv",
        "Coverage theo wave": "nsmo-v70-wave-coverage.csv",
        "So sanh wording item": "nsmo-v70-wave-item-comparability.csv",
        "Do nhay horizon": "NSMO_HORIZON_SENSITIVITY_2026-10-16.csv",
    }
    for sheet_name, csv_name in expected.items():
        csv_path = root / "docs" / csv_name if sheet_name == "Do nhay horizon" else root / "docs" / "data" / csv_name
        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            row_count = sum(1 for _ in csv.DictReader(stream))
        sheet = workbook[sheet_name]
        assert sheet.max_row == row_count + 1
        # The workbook freezes both the header row and the identifier column.
        assert sheet.freeze_panes == "B2"
        assert len(sheet.tables) == 1
        table = next(iter(sheet.tables.values()))
        assert table.ref.startswith("A1:")
        assert table.autoFilter is not None
    labels = workbook["Nhan va category"]
    assert labels[1][1].value == "Mã category (giữ nguyên)"
    assert labels.max_row > 100
    assert workbook["Bat dau"]["B4"].value.startswith("Năm sheet dữ liệu")
    sensitivity = workbook["Do nhay horizon"]
    assert sensitivity.max_row == row_count + 1
    assert sensitivity["A2"].value == "all"
    assert sensitivity["C2"].value == 2 and sensitivity["D2"].value == 6
    assert sensitivity["I2"].value == 661
    assert sensitivity["J2"].value == 394
    assert sensitivity["G2"].value == "CENSOR_M"
    assert any(sensitivity.cell(row, 1).value == "origination_year" for row in range(2, sensitivity.max_row + 1))
