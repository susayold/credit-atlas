import json
from types import SimpleNamespace

import pytest

from credit_atlas.public_sources import catalog, profile, validate_source, acquire_one
from credit_atlas.public_suite import verify_acquisition
from credit_atlas.workspace import sha256, write_new


def mini_acquisition(tmp_path, monkeypatch):
    item = source("uci-retail")
    monkeypatch.setattr("credit_atlas.public_suite.catalog", lambda: [item])
    identifier = "suite-aaaaaaaaaaaa"
    folder = tmp_path / "data/private/public-suite" / identifier
    folder.mkdir(parents=True)
    path = folder / "uci-retail.csv"
    path.write_text("ID,X1,Y\n1,?,0\n2,NaN,1\n3,,0\n", encoding="utf-8")
    receipt = {**item, "status":"DOWNLOADED_AND_PROFILED", "file":path.name,
               "sha256":sha256(path), "bytes":path.stat().st_size,
               "profile":profile(path,item), "model_qualified":False, "public_release_approved":False}
    write_new(folder / "uci-retail-receipt.json", receipt)
    write_new(folder / "acquisition-complete.json", {"schema_version":1,"status":"COMPLETE",
        "sources":[receipt],"failed_sources":[],"visibility":"private",
        "public_release_approved":False,"model_training_performed":False})
    return identifier, path


def test_source_native_warehouse_preserves_empty_and_missing_codes(tmp_path, monkeypatch):
    from credit_atlas.public_suite import build_source_warehouse
    from pathlib import Path
    import pyarrow.parquet as pq
    identifier, _ = mini_acquisition(tmp_path, monkeypatch)
    result = build_source_warehouse(tmp_path, identifier)
    assert result["tables"] == 1 and result["model_training_performed"] is False
    rows = pq.read_table(Path(result["directory"]) / "uci-retail.parquet").to_pylist()
    assert [row["X1"] for row in rows] == ["?", "NaN", ""]
    assert [row["Y"] for row in rows] == ["0", "1", "0"]


def test_modified_raw_even_same_size_blocks_warehouse(tmp_path, monkeypatch):
    from credit_atlas.public_suite import build_source_warehouse
    identifier, path = mini_acquisition(tmp_path, monkeypatch)
    raw = path.read_text()
    path.write_text(raw.replace("1,?", "9,?"))
    with pytest.raises(ValueError, match="content changed"):
        build_source_warehouse(tmp_path, identifier)
    assert not (tmp_path / "artifacts/private").exists()


def source(identifier):
    return next(item for item in catalog() if item["source_id"] == identifier)


def test_catalog_covers_five_workspaces_without_credentials_and_has_unique_names():
    items = catalog()
    assert len(items) == len({item["source_id"] for item in items}) == 20
    assert {module for item in items for module in item["modules"]} == {"P1", "P2", "P3", "P4", "P5"}
    for item in items:
        validate_source(item)
    assert "internal use only" in source("fred-bamlc0a0cm")["rights"]


@pytest.mark.parametrize("url", ["http://data.sba.gov/file.csv", "https://other.example/file.csv",
                                  "https://user:secret@data.sba.gov/file.csv", "https://data.sba.gov:443/file.csv"])
def test_unknown_insecure_or_credential_url_rejected(url):
    with pytest.raises(ValueError):
        validate_source({**source("uci-retail"), "url": url})


def test_csv_profiles_native_sentinels_horizons_and_binary_support(tmp_path):
    path = tmp_path / "native.csv"
    path.write_text("year,A1,class\n1,?,0\n5,NaN,1\n5,3,0\n", encoding="utf-8")
    result = profile(path, source("uci-bankruptcy"))
    assert result["rows"] == 3 and result["null_counts"]["A1"] == 2
    assert result["source_year_codes"] == {"1": 1, "5": 2}
    assert result["target_counts"] == {"0": 2, "1": 1}


def test_truncated_fdic_page_is_rejected(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"meta":{"total":2},"data":[{"data":{"CERT":1,"REPDTE":"20260630"}}]}))
    with pytest.raises(ValueError, match="pagination"):
        profile(path, source("fdic-financials-20260630"))


def test_duplicate_bank_quarter_is_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    row = {"data":{"CERT":1,"REPDTE":"20260630"}}
    path.write_text(json.dumps({"meta":{"total":2},"data":[row,row]}))
    with pytest.raises(ValueError, match="grain"):
        profile(path, source("fdic-financials-20260630"))


def test_http_redirect_cannot_be_promoted_to_dataset(tmp_path, monkeypatch):
    def redirect(args, **kwargs):
        assert "--location" not in args and "--proto" in args
        return SimpleNamespace(returncode=0, stdout=b"302")
    monkeypatch.setattr("credit_atlas.public_sources.subprocess.run", redirect)
    result = acquire_one(tmp_path, tmp_path, source("uci-retail"))
    assert result["status"] == "FAILED" and not (tmp_path / "uci-retail.csv").exists()


@pytest.mark.parametrize("identifier", ["../suite-123456789012", "suite-x", None])
def test_invalid_run_id_rejected_before_receipt_read(tmp_path, identifier):
    with pytest.raises(ValueError, match="ID"):
        verify_acquisition(tmp_path, identifier)
