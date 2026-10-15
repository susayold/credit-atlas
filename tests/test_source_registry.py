import json
import zipfile

import pytest

from credit_atlas.source_registry import register_asset, validate_import, require_technical_profile
from credit_atlas.workspace import sha256, write_new


def synthetic_archive(tmp_path):
    archive = tmp_path / "SYNTHETIC-sample.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("sample_orig_2008.txt", "SYNTHETIC-NOT-QUALIFIED")
        zipped.writestr("sample_perf_2008.txt", "SYNTHETIC-NOT-QUALIFIED")
    return archive


def test_structural_import_requires_rights_release_and_expected_hash(tmp_path):
    archive = synthetic_archive(tmp_path)
    digest = sha256(archive)
    assert validate_import(archive, 47, True, digest) == (2008, digest)
    with pytest.raises(PermissionError):
        validate_import(archive, 47, False, digest)
    with pytest.raises(ValueError):
        validate_import(archive, 46, True, digest)
    with pytest.raises(ValueError):
        validate_import(archive, 47, True, "0" * 64)


def registered_input(tmp_path):
    archive = synthetic_archive(tmp_path)
    receipt = tmp_path / "synthetic-receipt.json"
    digest = sha256(archive)
    write_new(receipt, {"sha256": digest, "release": 47, "data_kind": "annual_sample",
                        "research_use_confirmed": True, "public_release_approved": False,
                        "source_kind": "SYNTHETIC-QA"})
    return {"archive": archive.name, "receipt": receipt.name, "sha256": digest}


def test_source_registration_is_idempotent_and_preserves_existing_config(tmp_path):
    asset = registered_input(tmp_path)
    write_new(tmp_path / "workspace.local.json", {"annual_assets": [], "other_settings": "preserve"})
    assert register_asset(tmp_path, asset) == 0
    assert register_asset(tmp_path, asset) == 0
    config = json.loads((tmp_path / "workspace.local.json").read_text())
    assert config == {"annual_assets": [asset], "other_settings": "preserve"}
    assert not (tmp_path / ".workspace-source.lock").exists()


def test_other_writer_lock_cannot_be_removed_by_failed_attempt(tmp_path):
    asset = registered_input(tmp_path)
    lock = tmp_path / ".workspace-source.lock"
    lock.write_text("OTHER-WRITER")
    with pytest.raises(FileExistsError):
        register_asset(tmp_path, asset)
    assert lock.read_text() == "OTHER-WRITER"
    assert not (tmp_path / "workspace.local.json").exists()


def test_bad_receipt_cannot_change_registry(tmp_path):
    asset = registered_input(tmp_path)
    receipt = tmp_path / asset["receipt"]
    record = json.loads(receipt.read_text())
    record["research_use_confirmed"] = False
    receipt.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        register_asset(tmp_path, asset)
    assert not (tmp_path / "workspace.local.json").exists()


def test_profiled_status_alone_does_not_allow_downstream_analytics():
    result = {"status": "PROFILED", "gates": {"format_parse": "PASS", "referential_integrity": "FAIL"}}
    with pytest.raises(ValueError):
        require_technical_profile(result)
    result["gates"] = {"format_parse": "PASS", "referential_integrity": "PASS",
                       "research_sample_identity": "PASS_USER_ATTESTED", "history_presence_screen": "PASS",
                       "source_qualification": "CANDIDATE_FOR_COHORT_REVIEW"}
    require_technical_profile(result)
