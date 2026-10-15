import io
import json
import stat
import zipfile
import pytest
from crsl.source import safe_members, select_pair, copy_annual, sha256, fetch_public

@pytest.mark.parametrize("name", ["../escape.txt", "/absolute.txt", "C:/escape.txt"])
def test_unsafe_archive_path(tmp_path, name):
    path = tmp_path/"bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, "x")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="Unsafe"):
        safe_members(archive)

def test_raw_backslash_member_rejected():
    from types import SimpleNamespace
    # Windows ZipInfo construction normalizes separators. Test the validator's
    # raw-input boundary directly instead of a fixture normalized by zipfile.
    item = zipfile.ZipInfo("safe")
    item.filename = "a\\b.txt"
    with pytest.raises(ValueError, match="Unsafe"):
        safe_members(SimpleNamespace(infolist=lambda: [item]))

def test_symlink_rejected(tmp_path):
    path = tmp_path/"bad.zip"
    item = zipfile.ZipInfo("link")
    item.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(item, "target")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="symlink"):
        safe_members(archive)

def test_expanded_budget(tmp_path):
    path = tmp_path/"large.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("small.txt", "x"*100)
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="budget"):
        safe_members(archive, max_total=50)

def test_annual_pair_required(make_zip):
    with zipfile.ZipFile(make_zip(kind="format")) as archive:
        with pytest.raises(ValueError, match="annual origination"):
            select_pair(archive, "annual_sample")

def test_pair_matching_year(tmp_path):
    path=tmp_path/"mismatch.zip"
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("sample_orig_2012.txt", "")
        archive.writestr("sample_perf_2013.txt", "")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="Matching"):
        select_pair(archive, "annual_sample")

def test_annual_requires_confirmation(make_zip, tmp_path):
    with pytest.raises(PermissionError):
        copy_annual(tmp_path/"root", make_zip(), 47, False)

def test_unsupported_release(make_zip, tmp_path):
    with pytest.raises(ValueError, match="47"):
        copy_annual(tmp_path/"root", make_zip(), 46, True)

def test_annual_immutable_copy(make_zip, tmp_path):
    archive=make_zip()
    target=copy_annual(tmp_path/"root", archive, 47, True)
    assert target != archive
    assert sha256(target) == sha256(archive)
    assert copy_annual(tmp_path/"root", archive, 47, True) == target

def test_source_cache_detects_mutation(tmp_path, monkeypatch):
    base=tmp_path/"data/private/source_documents/release47"
    base.mkdir(parents=True)
    (base/"format-example.zip").write_bytes(b"changed")
    (base/"format-example.zip.receipt.json").write_text(json.dumps({
        "sha256":"wrong", "url":"https://www.freddiemac.com/fmac-resources/research/docs/release-47-sample-files.zip"}))
    def forbidden(*args, **kwargs):
        raise AssertionError("Cache check must not use network")
    monkeypatch.setattr("crsl.source.urlopen", forbidden)
    with pytest.raises(ValueError, match="mismatch"):
        fetch_public(tmp_path)
