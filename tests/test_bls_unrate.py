from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest

from scripts.acquire_bls_unrate import (
    compare_fred,
    latest_fred_unrate_comparator,
    parse_response,
    SERIES_URL,
)
from credit_atlas.workspace import sha256, write_new


def _response(rows):
    return json.dumps({
        "status": "REQUEST_SUCCEEDED",
        "Results": {"series": [{"seriesID": "LNS14000000", "data": rows}]},
    }).encode("utf-8")


def test_bls_response_parser_sorts_months_and_preserves_footnotes():
    rows, notes = parse_response(_response([
        {"year": "2026", "period": "M02", "value": "4.4", "footnotes": [{}]},
        {"year": "2026", "period": "M01", "value": "4.3", "footnotes": [{"code": "P", "text": "Preliminary."}]},
    ]), 2026, 2026)
    assert [row["observation_date"] for row in rows] == [date(2026, 1, 1), date(2026, 2, 1)]
    assert [row["value"] for row in rows] == ["4.3", "4.4"]
    assert notes == [{"observation_date": "2026-01-01", "code": "P", "text": "Preliminary."}]


def test_bls_missing_marker_requires_and_preserves_official_reason():
    rows, notes = parse_response(_response([
        {"year": "2025", "period": "M10", "value": "-",
         "footnotes": [{"code": "9", "text": "Data unavailable due to the 2025 lapse in appropriations."}]},
    ]), 2025, 2025)
    assert rows[0]["value"] is None
    assert notes[0]["code"] == "9"
    assert "Data unavailable" in notes[0]["text"]


@pytest.mark.parametrize("bad_row", [
    {"year": "2026", "period": "M13", "value": "4.4", "footnotes": []},
    {"year": "2025", "period": "M02", "value": "4.4", "footnotes": []},
    {"year": "2026", "period": "M02", "value": "NaN", "footnotes": []},
    {"year": "2026", "period": "M02", "value": "-", "footnotes": []},
])
def test_bls_response_parser_rejects_invalid_periods_ranges_and_values(bad_row):
    with pytest.raises(ValueError):
        parse_response(_response([bad_row]), 2026, 2026)


def test_bls_vs_fred_parity_uses_exact_decimal_values_and_reports_gaps():
    bls = [
        {"observation_date": date(2026, 1, 1), "value": "4.30"},
        {"observation_date": date(2026, 2, 1), "value": "4.5"},
    ]
    fred = {
        date(2026, 1, 1): Decimal("4.3"),
        date(2026, 3, 1): Decimal("4.4"),
    }
    result = compare_fred(bls, fred)
    assert result["overlap_count"] == 1
    assert result["value_mismatch_count"] == 0
    assert result["only_in_bls_count"] == 1
    assert result["only_in_fred_count"] == 1


def test_future_bls_refresh_keeps_legacy_fred_as_the_comparator(tmp_path):
    public_context = tmp_path / "data/private/public-context"
    legacy = public_context / "fred-legacy"
    direct = public_context / "fred-bls-direct"
    legacy.mkdir(parents=True)
    direct.mkdir(parents=True)
    for folder, completed, source_url in (
        (legacy, "2026-10-10T00:00:00+00:00", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE"),
        (direct, "2026-10-18T00:00:00+00:00", SERIES_URL),
    ):
        csv_path = folder / "UNRATE.csv"
        csv_path.write_text("observation_date,UNRATE\n2026-09-01,4.3\n", encoding="utf-8")
        write_new(folder / "run-complete.json", {
            "status": "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE",
            "completed_at": completed,
            "series": [{"series_id": "UNRATE", "source_url": source_url,
                        "sha256": sha256(csv_path)}],
        })

    chosen_folder, chosen_receipt = latest_fred_unrate_comparator(tmp_path)
    assert chosen_folder == legacy
    assert chosen_receipt["completed_at"] == "2026-10-10T00:00:00+00:00"


def test_fred_comparator_selection_fails_closed_when_receipt_hash_is_bad(tmp_path):
    folder = tmp_path / "data/private/public-context/fred-legacy"
    folder.mkdir(parents=True)
    csv_path = folder / "UNRATE.csv"
    csv_path.write_text("observation_date,UNRATE\n2026-09-01,4.3\n", encoding="utf-8")
    write_new(folder / "run-complete.json", {
        "status": "DOWNLOADED_AND_CONTEXT_RUN_COMPLETE",
        "completed_at": "2026-10-10T00:00:00+00:00",
        "series": [{"series_id": "UNRATE",
                    "source_url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE",
                    "sha256": "0" * 64}],
    })
    with pytest.raises(ValueError, match="failed its receipt digest"):
        latest_fred_unrate_comparator(tmp_path)
