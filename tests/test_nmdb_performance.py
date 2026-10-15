import shutil
from pathlib import Path

import pytest

from credit_atlas.nmdb_performance import nmdb_performance_report


def test_nmdb_national_performance_aggregates_reconcile_and_keep_series_scope():
    root = Path(__file__).parents[1]
    report = nmdb_performance_report(root)
    assert report["status"] == "AVAILABLE"
    assert report["source"]["data_through"] == "2026Q2"
    assert report["periods"][0] == "2002Q1"
    assert report["periods"][-1] == "2026Q2"
    assert len(report["observations"]) == 1_568
    assert len(report["latest"]) == 16
    assert len(report["markets"]) == 4
    assert report["source"]["source_archive_sha256"] == "2083c4e1b5273fd2f471d2e58057b17b82b86ef3ac7ed13c58925b4453ec4e89"
    latest = {(row["market"], row["series_id"]): row["value_pct"] for row in report["latest"]}
    assert latest[("All Mortgages", "P3089DL")] == 1.7
    assert latest[("All Mortgages", "P90DL")] == 1.0
    assert latest[("All Mortgages", "PFORB")] == 0.5
    assert latest[("Government / Non-Conventional", "P90DL")] == 2.8
    early_forbearance = next(row for row in report["observations"]
                             if row["market"] == "All Mortgages" and row["series_id"] == "PFORB" and row["period"] == "2002Q1")
    assert early_forbearance["value_pct"] is None
    assert report["series"]["PFORB"]["first_nonblank_quarter"] == "2019Q4"
    assert any("not borrower/loan-level" in note for note in report["limitations"])
    assert "preliminary" in report["definitions"]["latest_vintages"]


def test_nmdb_report_rejects_curated_csv_hash_mismatch(tmp_path):
    source = Path(__file__).parents[1] / "docs/data"
    target = tmp_path / "docs/data"
    target.mkdir(parents=True)
    for name in ("nmdb-performance-national-quarterly-2026q2.csv",
                 "nmdb-performance-national-quarterly-2026q2-receipt.json"):
        shutil.copyfile(source / name, target / name)
    path = target / "nmdb-performance-national-quarterly-2026q2.csv"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match its acquisition receipt"):
        nmdb_performance_report(tmp_path)
