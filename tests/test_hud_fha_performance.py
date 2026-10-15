import shutil
from pathlib import Path

import pytest

from credit_atlas.hud_fha_performance import hud_fha_performance_report


def test_hud_fha_monthly_and_subgroup_aggregates_reconcile_to_august_report():
    root = Path(__file__).parents[1]
    report = hud_fha_performance_report(root)
    assert report["status"] == "AVAILABLE"
    assert len(report["monthly"]) == 26
    assert len(report["subgroups"]) == 60
    assert report["latest"]["NSA"]["active_iif_count"] == 8_416_639
    assert report["latest"]["NSA"]["serious_delinquency_pct"] == 6.42
    assert report["latest"]["SA"]["serious_delinquency_pct"] == 6.63
    score_low = next(row for row in report["subgroups"] if row["category"] == "< 500")
    score_high = next(row for row in report["subgroups"] if row["category"] == "720-850")
    assert score_low["serious_delinquency_pct"] == 11.28
    assert score_high["serious_delinquency_pct"] == 1.94
    assert next(row for row in report["subgroups"] if row["category"] == "2026")["serious_delinquency_pct"] == 1.02
    assert next(row for row in report["subgroups"] if row["category"] == "> 499")["serious_delinquency_pct"] == 6.56
    assert next(row for row in report["subgroups"] if row["category"] == "Townhouse")["serious_delinquency_pct"] == 7.12
    assert next(row for row in report["subgroups"] if row["category"] == "First-time")["serious_delinquency_pct"] == 7.43
    assert next(row for row in report["subgroups"] if row["category"] == "Seller funded")["serious_delinquency_pct"] == 9.33
    assert next(row for row in report["subgroups"] if row["category"] == "Streamline")["share_denominator"] == "Refinance loans"
    assert next(row for row in report["subgroups"] if row["category"] == "Loans with credit scores")["iif_share_pct"] is None
    assert report["source"]["raw_pdf_sha256"] is None
    assert any("not downloaded" in note for note in report["source"]["extraction"].split("; "))
    assert any("not NSMO" in limitation for limitation in report["limitations"])


def test_hud_fha_rejects_missing_monthly_observation(tmp_path):
    root = Path(__file__).parents[1]
    (tmp_path / "docs/data").mkdir(parents=True)
    source = root / "docs/data"
    shutil.copyfile(source / "hud-fha-performance-2026-08-subgroups.csv",
                    tmp_path / "docs/data/hud-fha-performance-2026-08-subgroups.csv")
    text = (source / "hud-fha-performance-2026-08.csv").read_text(encoding="utf-8")
    lines = text.splitlines()
    (tmp_path / "docs/data/hud-fha-performance-2026-08.csv").write_text(
        "\n".join(line for line in lines if not line.startswith("2026-08,SA,")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="13 NSA and 13 SA"):
        hud_fha_performance_report(tmp_path)
