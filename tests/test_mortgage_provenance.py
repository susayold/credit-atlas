import hashlib
import json
from types import SimpleNamespace

import pytest

from credit_atlas.mortgage_provenance import report


def fixture(tmp_path):
    digest = "a" * 64
    case_path = tmp_path / "artifacts/private/d01-111111111111"
    case_path.mkdir(parents=True)
    receipt_path = tmp_path / f"vendor/credit_risk_strategy_lab/data/private/raw/{digest}.receipt.json"
    receipt_path.parent.mkdir(parents=True)
    receipt = dict(sha256=digest, release=47, data_kind="annual_sample", research_use_confirmed=True,
                   received_at="2026-09-09T00:00:00Z", release_confirmation="user_supplied; not authenticated by file hash registry")
    receipt_path.write_text(json.dumps(receipt))
    source_dir = tmp_path / "vendor/credit_risk_strategy_lab/artifacts/private/source"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "run-complete.json"
    source = dict(source_sha256=digest, release=47, data_kind="annual_sample",
                  started_at="2026-10-08T00:00:00Z", completed_at="2026-10-08T00:02:00Z")
    source_path.write_text(json.dumps(source))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    foundation = dict(raw_sha256=digest, source_use_receipt_sha256=h(receipt_path),
                      source_manifest_sha256=h(source_path), source_run=str(source_dir.relative_to(tmp_path)),
                      completed_at="2026-10-08T00:03:00Z")
    foundation_path = case_path / "foundation-complete.json"
    foundation_path.write_text(json.dumps(foundation))
    manifest = dict(raw_sha256=digest, case_id=case_path.name, pipeline_run="pipeline-111111111111",
                    source_years=[2012], completed_at="2026-10-08T00:04:00Z")
    service = SimpleNamespace(root=tmp_path, case=lambda _: dict(path=case_path, manifest=manifest))
    return service, receipt_path, source_path, foundation_path, manifest


def test_dates_declarations_and_private_boundary(tmp_path):
    service, *_ = fixture(tmp_path)
    result = report(service, {"run": "d01-111111111111"})
    assert result["publisher_publication_at"] is None
    assert result["publisher_release_authenticated"] is False
    assert result["receipt_received_at"] != result["extraction_started_at"]
    assert result["receipt_declared_release"] == 47
    assert result["research_use_declared"] is True
    assert result["public_release_approved"] is False
    assert "not the whole" in result["population_scope"]
    serialized = json.dumps(result)
    assert str(tmp_path) not in serialized
    assert "original_filename" not in serialized


@pytest.mark.parametrize("index", [1, 2])
def test_changed_receipts_fail_closed(tmp_path, index):
    items = fixture(tmp_path)
    items[index].write_text("{}")
    with pytest.raises(ValueError, match="receipt changed"):
        report(items[0], {"run": "d01-111111111111"})


@pytest.mark.parametrize("query", [{}, {"run": "x", "segment": "all"}, {"run": "x", "from": "2020-01"}])
def test_source_scope_has_no_segment_or_date_filters(tmp_path, query):
    with pytest.raises(ValueError, match="run only"):
        report(fixture(tmp_path)[0], query)


def test_bad_digest_cannot_select_private_path(tmp_path):
    service, _, _, _, manifest = fixture(tmp_path)
    manifest["raw_sha256"] = "../secret"
    with pytest.raises(ValueError, match="Invalid source digest"):
        report(service, {"run": "d01-111111111111"})


def test_declaration_conflict_even_with_valid_receipt_hash(tmp_path):
    service, receipt, _, foundation, _ = fixture(tmp_path)
    data = json.loads(receipt.read_text())
    data["release"] = 48
    receipt.write_text(json.dumps(data))
    f = json.loads(foundation.read_text())
    f["source_use_receipt_sha256"] = hashlib.sha256(receipt.read_bytes()).hexdigest()
    foundation.write_text(json.dumps(f))
    with pytest.raises(ValueError, match="declarations conflict"):
        report(service, {"run": "d01-111111111111"})
