import json
import os
from pathlib import Path

import pytest

from credit_atlas.suite_snapshot import SuiteViews, METHODS
from credit_atlas.workspace import write_new, sha256


@pytest.fixture
def suite(tmp_path):
    identifier = "suite-view-aaaaaaaaaaaa"
    folder = tmp_path / "artifacts/private" / identifier
    folder.mkdir(parents=True)
    source = tmp_path / "data/private/source.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"SYNTHETIC-DATA")
    snapshot = {"schema_version": 1, "view_id": identifier, "suite_id": "suite-bbbbbbbbbbbb",
                "visibility": "private", "public_release_approved": False, "retail": {"holdout": {"loans": 100}}}
    write_new(folder / "snapshot.json", snapshot)
    import credit_atlas.suite_snapshot as module
    receipt = {"schema_version": 1, "view_id": identifier, "status": "SUITE_AGGREGATE_VIEW_VERIFIED",
               "visibility": "private", "public_release_approved": False,
               "snapshot_sha256": sha256(folder / "snapshot.json"),
               "inputs_sha256": {str(source.relative_to(tmp_path)): sha256(source)},
               "method_sources_sha256": {n: sha256(Path(module.__file__).with_name(n + ".py")) for n in METHODS}}
    write_new(folder / "view-complete.json", receipt)
    return SuiteViews(tmp_path), identifier, folder, source


def test_catalog_and_projection_do_not_expose_private_manifests(suite):
    views, identifier, _, _ = suite
    result = views.view(identifier)
    assert views.catalog()["views"] == [{"view_id": identifier, "status": "verified", "suite_id": "suite-bbbbbbbbbbbb"}]
    assert "inputs_sha256" not in result and "method_sources_sha256" not in result
    result["retail"]["holdout"]["loans"] = 999
    assert views.view(identifier)["retail"]["holdout"]["loans"] == 100


def test_modified_source_rejects_cached_view_instead_of_serving_old_metrics(suite):
    views, identifier, _, source = suite
    views.view(identifier)
    source.write_bytes(b"CHANGED")
    with pytest.raises(ValueError, match="evidence changed"):
        views.view(identifier)
    assert views.catalog()["views"][0]["status"] == "evidence_unavailable_or_changed"


def test_snapshot_tamper_with_restored_stat_is_rejected(suite):
    views, identifier, folder, _ = suite
    views.view(identifier)
    path = folder / "snapshot.json"
    old = path.stat()
    path.write_bytes(path.read_bytes().replace(b'100', b'999'))
    os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
    with pytest.raises(ValueError, match="snapshot changed"):
        views.view(identifier)


def test_updated_receipt_cannot_replace_cached_projection(suite):
    views, identifier, folder, _ = suite
    views.view(identifier)
    path = folder / "view-complete.json"
    receipt = json.loads(path.read_text())
    receipt["extra"] = "changed"
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="receipt changed"):
        views.view(identifier)


@pytest.mark.parametrize("identifier", ["../suite-view-aaaaaaaaaaaa", "d01-aaaaaaaaaaaa", None])
def test_invalid_identifier_rejected_before_filesystem_access(suite, identifier):
    with pytest.raises(ValueError, match="identifier"):
        suite[0].view(identifier)
