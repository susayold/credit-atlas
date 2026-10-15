import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_nsmo_puf.py"
SPEC = importlib.util.spec_from_file_location("audit_nsmo_puf", SCRIPT)
AUDITOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(AUDITOR)


def test_audit_reports_only_aggregate_nsmo_profile(tmp_path):
    path = tmp_path / "nsmo.csv"
    path.write_text(
        "nsmoid,survey_wave,analysis_weight,open_year,open_month,perf_status_0313,perf_status_0613\n"
        "private-loan-key-a,1,10,2013,1,P,C\n"
        "private-loan-key-b,1,20,2013,2,C,1\n",
        encoding="utf-8",
    )

    report = AUDITOR.audit(path)

    assert report["status"] == "PASS"
    assert report["row_count"] == 2
    assert report["unique_nonblank_nsmoid"] == 2
    assert report["performance"]["cell_count"] == 4
    assert report["performance"]["status_counts_unweighted"] == {
        "1": 1,
        "C": 2,
        "P": 1,
    }
    serialized = json.dumps(report)
    assert "private-loan-key-a" not in serialized
    assert "private-loan-key-b" not in serialized


def test_audit_fails_closed_on_unknown_status_code(tmp_path):
    path = tmp_path / "nsmo-unknown.csv"
    path.write_text(
        "nsmoid,survey_wave,analysis_weight,open_year,open_month,perf_status_0313\n"
        "private-loan-key,1,10,2013,1,Z\n",
        encoding="utf-8",
    )

    report = AUDITOR.audit(path)

    assert report["status"] == "FAIL"
    assert report["performance"]["unknown_status_counts"] == {"Z": 1}
    assert "private-loan-key" not in json.dumps(report)
