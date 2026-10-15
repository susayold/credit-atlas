import json
import shutil
from pathlib import Path

import pytest

from credit_atlas.nmdb_state_performance import DATA_NAME, RECEIPT_NAME, nmdb_state_performance_report


def test_curated_nmdb_state_panel_has_complete_separate_coverage():
    root = Path(__file__).parents[1]
    report = nmdb_state_performance_report(root)
    assert report["status"] == "AVAILABLE"
    assert report["geography"] == "50 states and District of Columbia"
    assert len(report["states"]) == 51
    assert report["periods"][0] == "2002Q1" and report["periods"][-1] == "2026Q2"
    assert len(report["observations"]) == 79_968
    assert len(report["latest"]) == 816
    assert all(row["value_pct"] is not None and not row["suppressed"] for row in report["latest"])
    assert report["definitions"]["forbearance"].startswith("PFORB starts 2019Q4")
    california = nmdb_state_performance_report(root, "CA")
    assert california["selected_state"] == "CA"
    assert len(california["observations"]) == 1_568
    assert len(california["latest"]) == 16
    with pytest.raises(ValueError, match="State code"):
        nmdb_state_performance_report(root, "ZZ")


def test_nmdb_state_receipt_detects_data_tampering(tmp_path):
    root = Path(__file__).parents[1]
    target = tmp_path / "docs/data"
    target.mkdir(parents=True)
    shutil.copyfile(root / "docs/data" / DATA_NAME, target / DATA_NAME)
    shutil.copyfile(root / "docs/data" / RECEIPT_NAME, target / RECEIPT_NAME)
    with (target / DATA_NAME).open("ab") as stream:
        stream.write(b"tamper\n")
    with pytest.raises(ValueError, match="does not match"):
        nmdb_state_performance_report(tmp_path)
