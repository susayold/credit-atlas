import csv
from pathlib import Path

from scripts.audit_nsmo_survey_returns import parse_row_line


def test_parse_table_three_superscript_footnotes_without_changing_counts():
    wave_27 = parse_row_line("2715 606.49 5,694 91 5,603 1,821 717 1,092 12 19")
    assert wave_27["survey_wave"] == 27
    assert wave_27["average_sampling_weight"] == "606.49"
    assert wave_27["surveys_completed_total"] == 1821

    wave_30 = parse_row_line("30 629.72 5,650 146 5,504 1,57616 646 916 14 22")
    assert wave_30["survey_wave"] == 30
    assert wave_30["surveys_completed_total"] == 1576
    assert wave_30["online_share_pct_of_completed"] == "59.01"


def test_nsmo_wave_return_data_reconciles_and_separates_puf_coverage():
    root = Path(__file__).parents[1]
    path = root / "docs/data/nsmo-v70-survey-returns.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 48
    assert [int(row["survey_wave"]) for row in rows] == list(range(1, 49))
    assert [row["included_in_nsmo_v70_puf"] == "True" for row in rows] == [True] * 46 + [False] * 2
    for row in rows:
        assert int(row["surveys_mailed"]) == int(row["surveys_delivered"]) + int(row["postal_nondelivery"])
        assert int(row["surveys_completed_total"]) == (
            int(row["completed_by_mail"]) + int(row["online_english"]) + int(row["online_spanish"])
        )
    first, last = rows[0], rows[45]
    assert first["online_share_pct_of_completed"] == "23.87"
    assert last["online_share_pct_of_completed"] == "64.93"
    assert sum(int(row["surveys_completed_total"]) for row in rows) == 76405
