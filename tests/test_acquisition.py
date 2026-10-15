"""Source boundary tests use synthetic archives and never contact the network."""
import io
import json
import urllib.error
import zipfile

import pytest

from credit_atlas import acquisition as a


@pytest.mark.parametrize("url", [
    "http://claritydownload.fmapps.freddiemac.com/a",
    "https://claritydownload.fmapps.freddiemac.com.evil.example/a",
    "https://user:password@claritydownload.fmapps.freddiemac.com/a",
    "https://example.com/sample_2008.zip",
    "https://claritydownload.fmapps.freddiemac.com:8443/a",
])
def test_no_authentication_is_transmitted_to_unapproved_destination(url):
    with pytest.raises(ValueError):
        a.official_url(url)


def test_redirect_to_login_or_other_host_cannot_forward_download_request():
    handler = a.OfficialRedirects()
    with pytest.raises(ValueError):
        handler.redirect_request(None, None, 302, "", {}, "https://example.com/login")


def test_format_example_and_wrong_vintage_cannot_be_called_annual(tmp_path):
    archive = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("sample_orig_2012.txt", "SYNTHETIC")
        z.writestr("sample_perf_2012.txt", "SYNTHETIC")
    assert len(a.verify_annual_zip(archive, 2012)) == 2
    with pytest.raises(ValueError):
        a.verify_annual_zip(archive, 2008)


def test_legacy_member_names_are_not_silently_accepted_as_release47(tmp_path):
    archive = tmp_path / "legacy-synthetic.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("sample_orig_2012.txt", "SYNTHETIC")
        z.writestr("sample_svcg_2012.txt", "SYNTHETIC")
    with pytest.raises(ValueError):
        a.verify_annual_zip(archive, 2012)


def test_authentication_failure_is_recorded_without_secret_url(tmp_path, monkeypatch):
    monkeypatch.setattr(a.shutil, "disk_usage", lambda root: type("Usage", (), {"free": 100 * 1024**3})())
    url = "https://" + a.HOST + "/sample?token=DO-NOT-LOG"
    class Client:
        def open(self, request, timeout):
            raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, io.BytesIO())
    with pytest.raises(RuntimeError):
        a.download_annual(tmp_path, {"url": url, "year": 2008, "release": 47}, Client())
    receipt = next(tmp_path.glob("data/private/incoming/*/failed.json"))
    text = receipt.read_text()
    assert "DO-NOT-LOG" not in text
    assert json.loads(text)["http_status"] == 401
    assert not list(tmp_path.rglob("*.zip"))
