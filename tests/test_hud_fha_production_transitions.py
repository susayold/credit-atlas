import csv
import shutil
from pathlib import Path

import pytest

from credit_atlas.hud_fha_production_transitions import hud_fha_production_transitions


def test_hud_production_transition_rows_reconcile_to_published_counts():
    root = Path(__file__).parents[1]
    report = hud_fha_production_transitions(root)

    assert report["status"] == "AVAILABLE"
    assert len(report["monthly"]) == 13
    assert report["source"]["source_table"] == 2
    assert report["source"]["source_page"] == 3
    assert report["source"]["raw_pdf_sha256"] is None
    assert report["latest"]["period"] == "2026-08"
    assert report["latest"]["beginning_serious_delinquency_inventory"] == 537_258
    assert report["latest"]["serious_delinquency_entries"] == 65_811
    assert report["latest"]["cures_leaving_serious_delinquency"] == 57_893
    assert report["latest"]["ending_serious_delinquency_inventory"] == 540_410
    assert report["latest"]["cure_ratio_pct"] == 88.0
    assert all(row["flow_identity_difference"] == 0 for row in report["monthly"])
    assert all(row["prior_ending_plus_adjustment_difference"] == 0 for row in report["monthly"][1:])
    assert next(row for row in report["monthly"] if row["period"] == "2026-03")["cure_ratio_pct"] == 108.0
    assert "not a matched-cohort" in report["definitions"]["cure_ratio_pct"]


def test_hud_production_rejects_a_broken_inventory_rollforward(tmp_path):
    source = Path(__file__).parents[1] / "docs" / "data" / "hud-fha-production-transitions-2026-08.csv"
    target = tmp_path / "docs" / "data" / source.name
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    with target.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fields = rows[0].keys()
    rows[-1]["ending_serious_delinquency_inventory"] = "540411"
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="flow does not reconcile"):
        hud_fha_production_transitions(tmp_path)
