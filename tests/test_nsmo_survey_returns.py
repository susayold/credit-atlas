import csv
import shutil
from pathlib import Path

import pytest

from scripts.audit_nsmo_survey_returns import parse_origin_usable_line, parse_row_line, parse_usable_row_line
from credit_atlas.nsmo_views import NsmoViews


def test_parse_table_three_superscript_footnotes_without_changing_counts():
    wave_27 = parse_row_line("2715 606.49 5,694 91 5,603 1,821 717 1,092 12 19")
    assert wave_27["survey_wave"] == 27
    assert wave_27["average_sampling_weight"] == "606.49"
    assert wave_27["surveys_completed_total"] == 1821

    wave_30 = parse_row_line("30 629.72 5,650 146 5,504 1,57616 646 916 14 22")
    assert wave_30["survey_wave"] == 30
    assert wave_30["surveys_completed_total"] == 1576
    assert wave_30["online_share_pct_of_completed"] == "59.01"


def test_parse_usable_and_origination_scope_tables():
    row = parse_usable_row_line("7 2,494 76 141 78 94 2,105")
    assert row == {
        "survey_wave": 7,
        "surveys_completed_total": 2494,
        "duplicate_or_ineligible": 76,
        "answered_no_to_q1": 141,
        "did_not_finish_survey": 78,
        "wrong_loan": 94,
        "usable_responses_table4": 2105,
    }
    assert parse_origin_usable_line("7 1,810 0 192 1,618 0 0") == (7, 1810)
    assert parse_origin_usable_line("46 432 0 0 0 0 0 0 432") == (46, 432)


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
    usability = list(csv.DictReader(open(root / "docs/data/nsmo-v70-usable-responses.csv", encoding="utf-8-sig")))
    assert len(usability) == 46
    assert sum(int(row["usable_responses_table4"]) for row in usability) == 63151
    assert sum(int(row["usable_responses_origination_2013_2024_tables5_6"]) for row in usability) == 62359
    assert sum(int(row["gap_to_usable_table4"]) for row in usability) == 792
    assert [(row["survey_wave"], row["gap_to_usable_table4"]) for row in usability if int(row["gap_to_usable_table4"])] == [
        ("7", "295"), ("45", "3"), ("46", "494")
    ]


def test_survey_returns_view_reconciles_puf_scope_and_mode_drift():
    root = Path(__file__).parents[1]
    data = NsmoViews(root).survey_returns()
    assert data["status"] == "AVAILABLE"
    assert len(data["waves"]) == 48
    assert data["puf_v70"]["waves"] == 46
    assert data["puf_v70"]["surveys_completed_total"] == 74193
    assert data["puf_v70"]["online_share_pct_of_completed"] == 45.55
    assert data["all_reported_waves"]["surveys_completed_total"] == 76405
    assert data["mode_shift"] == {
        "wave_1_online_share_pct": 23.87,
        "wave_46_online_share_pct": 64.93,
        "change_percentage_points": 41.06,
    }
    assert data["usability"]["usable_responses_table4"] == 63151
    assert data["usability"]["puf_v70_rows_and_tables5_6_2013_2024"] == 62359
    assert data["usability"]["usable_table4_minus_puf_scope"] == 792
    assert data["usability"]["wave_7_remote_rural_scope_gap"] == 295
    assert data["usability"]["wave_45_46_origination_scope_gap"] == 497
    assert "no respondent-level response-mode field" in " ".join(data["limitations"])


def test_survey_returns_view_rejects_modified_public_table(tmp_path):
    source_root = Path(__file__).parents[1]
    root = tmp_path / "workspace"
    data_dir = root / "docs/data"
    data_dir.mkdir(parents=True)
    source = source_root / "docs/data/nsmo-v70-survey-returns.csv"
    target = data_dir / source.name
    shutil.copyfile(source, target)
    target.write_bytes(target.read_bytes().replace(b"15000", b"15001", 1))
    with pytest.raises(ValueError, match="does not match the reviewed FHFA"):
        NsmoViews(root).survey_returns()


def test_survey_returns_view_requires_both_public_tables(tmp_path):
    source_root = Path(__file__).parents[1]
    root = tmp_path / "workspace"
    data_dir = root / "docs/data"
    data_dir.mkdir(parents=True)
    shutil.copyfile(source_root / "docs/data/nsmo-v70-survey-returns.csv", data_dir / "nsmo-v70-survey-returns.csv")
    with pytest.raises(ValueError, match="usable-response table"):
        NsmoViews(root).survey_returns()


def test_survey_returns_view_rejects_modified_usability_table(tmp_path):
    source_root = Path(__file__).parents[1]
    root = tmp_path / "workspace"
    data_dir = root / "docs/data"
    data_dir.mkdir(parents=True)
    for filename in ("nsmo-v70-survey-returns.csv", "nsmo-v70-usable-responses.csv"):
        shutil.copyfile(source_root / "docs/data" / filename, data_dir / filename)
    target = data_dir / "nsmo-v70-usable-responses.csv"
    target.write_bytes(target.read_bytes().replace(b"2105", b"2106", 1))
    with pytest.raises(ValueError, match="usable-response table"):
        NsmoViews(root).survey_returns()
