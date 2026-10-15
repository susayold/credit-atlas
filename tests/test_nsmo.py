from datetime import date

import pytest

from credit_atlas.nsmo import (
    NSMO_ORIGINATION_CANDIDATES,
    decode_performance_code,
    iter_nsmo_performance_csv,
    parse_performance_column,
    wide_performance_to_long,
)


def test_delinquency_codes_keep_exact_buckets_and_do_not_create_target():
    assert decode_performance_code("1") == {
        "raw_status": "1",
        "status_family": "delinquent_30_59_dpd",
        "dpd_low": 30,
        "dpd_high": 59,
        "observation_available": True,
    }
    severe = decode_performance_code("6")
    assert severe["status_family"] == "delinquent_180_plus_dpd"
    assert severe["dpd_low"] == 180
    assert severe["dpd_high"] is None
    assert "pd_target" not in severe
    assert decode_performance_code(6.0)["status_family"] == "delinquent_180_plus_dpd"


def test_non_delinquency_events_and_censored_states_stay_distinct():
    assert decode_performance_code("7")["status_family"] == "bankruptcy_chapter_13"
    assert decode_performance_code("8")["status_family"] == "foreclosure_or_distressed_disposition"
    assert decode_performance_code("9")["status_family"] == "other_adverse_or_chargeoff"
    for code in ("A", "B", "K", "M", "P", "S"):
        status = decode_performance_code(code)
        assert status["observation_available"] is False
        assert status["status_family"] != "current"


def test_unknown_codes_fail_closed_and_blank_is_not_current():
    assert decode_performance_code(None)["observation_available"] is False
    assert decode_performance_code(" ")["status_family"] == "blank_or_missing_code"
    with pytest.raises(ValueError, match="Unknown NSMO"):
        decode_performance_code("Z")


def test_quarter_column_date_and_wide_to_long_ordering():
    assert parse_performance_column("Perf_Status_0325") == date(2025, 3, 31)
    rows = wide_performance_to_long(
        {
            "NSMOID": 123,
            "Perf_Status_0625": "C",
            "Perf_Status_0325": "3",
        }
    )
    assert [row["observation_date"] for row in rows] == ["2025-03-31", "2025-06-30"]
    assert rows[0]["nsmoid"] == "123"
    assert rows[0]["status_family"] == "delinquent_90_119_dpd"
    assert rows[1]["status_family"] == "current"


def test_quarter_columns_and_source_id_are_required():
    with pytest.raises(ValueError, match="quarter-end"):
        parse_performance_column("Perf_Status_0225")
    with pytest.raises(ValueError, match="identifier"):
        wide_performance_to_long({"Perf_Status_0325": "C"})
    with pytest.raises(ValueError, match="No quarterly"):
        wide_performance_to_long({"NSMOID": "abc", "Score_Orig_R": 700})


def test_origination_candidate_fields_are_explicitly_source_scoped():
    assert "Score_Orig_R" in NSMO_ORIGINATION_CANDIDATES
    assert "Perf_Status_0325" not in NSMO_ORIGINATION_CANDIDATES


def test_csv_streams_quarter_rows_and_rejects_duplicate_loans(tmp_path):
    path = tmp_path / "nsmo.csv"
    path.write_text(
        "NSMOID,Perf_Status_0325,Perf_Status_0625\n"
        "loan-a,3,C\nloan-b,M,9\n",
        encoding="utf-8",
    )
    rows = list(iter_nsmo_performance_csv(path))
    assert len(rows) == 4
    assert rows[0]["nsmoid"] == "loan-a"
    assert rows[0]["status_family"] == "delinquent_90_119_dpd"
    assert rows[2]["status_family"] == "missing_archive_gap"
    assert rows[2]["observation_available"] is False

    path.write_text(
        "NSMOID,Perf_Status_0325\nloan-a,C\nloan-a,1\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate NSMOID"):
        list(iter_nsmo_performance_csv(path))


def test_csv_stream_rejects_unknown_status_with_row_context(tmp_path):
    path = tmp_path / "nsmo.csv"
    path.write_text("NSMOID,Perf_Status_0325\nloan-a,Z\n", encoding="utf-8")
    with pytest.raises(ValueError, match="CSV row 2.*Unknown NSMO"):
        list(iter_nsmo_performance_csv(path))


def test_csv_stream_requires_unique_columns_and_performance_fields(tmp_path):
    path = tmp_path / "nsmo.csv"
    path.write_text("NSMOID,NSMOID,Perf_Status_0325\na,b,C\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate NSMO CSV column"):
        list(iter_nsmo_performance_csv(path))
    path.write_text("NSMOID,Score_Orig_R\na,700\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No quarterly"):
        list(iter_nsmo_performance_csv(path))


def test_csv_stream_matches_fhfa_puf_lowercase_headers(tmp_path):
    path = tmp_path / "nsmo-lowercase.csv"
    path.write_text(
        "nsmoid,perf_status_0313,perf_status_0613\nloan-a,P,C\n",
        encoding="utf-8",
    )
    rows = list(iter_nsmo_performance_csv(path))
    assert len(rows) == 2
    assert rows[0]["nsmoid"] == "loan-a"
    assert rows[0]["status_family"] == "pre_open"
    assert rows[1]["status_family"] == "current"


def test_csv_stream_rejects_case_insensitive_duplicate_headers(tmp_path):
    path = tmp_path / "nsmo-duplicate-case.csv"
    path.write_text(
        "NSMOID,nsmoid,Perf_Status_0325\na,b,C\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate NSMO CSV column"):
        list(iter_nsmo_performance_csv(path))
