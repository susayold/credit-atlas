import http.cookiejar
import io
import json
import zipfile
import urllib.error
import urllib.request
from email.message import Message

import pytest

from credit_atlas import ginnie_acquisition as acquisition


def _cookie(name, domain, *, domain_specified, domain_initial_dot, secure=True):
    return http.cookiejar.Cookie(
        version=0, name=name, value="synthetic-test-token", port=None,
        port_specified=False, domain=domain, domain_specified=domain_specified,
        domain_initial_dot=domain_initial_dot, path="/", path_specified=True,
        secure=secure, expires=None, discard=True, comment=None,
        comment_url=None, rest={}, rfc2109=False,
    )


def _jar_with_token(value="synthetic-test-token"):
    jar = http.cookiejar.MozillaCookieJar()
    jar.set_cookie(_cookie("gm_up_token", ".ginniemae.gov", domain_specified=True, domain_initial_dot=True))
    cookie = next(iter(jar))
    cookie.value = value
    return jar


def _save_cookies(path, cookies):
    jar = http.cookiejar.MozillaCookieJar(str(path))
    for cookie in cookies:
        jar.set_cookie(cookie)
    jar.save(ignore_discard=True, ignore_expires=True)


def test_cookie_loader_keeps_only_secure_ginnie_download_token(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "_under_d", lambda _path: True)
    path = tmp_path / "session.cookies.txt"
    _save_cookies(path, [
        _cookie("gm_up_token", ".ginniemae.gov", domain_specified=True, domain_initial_dot=True),
        _cookie("analytics", ".ginniemae.gov", domain_specified=True, domain_initial_dot=True),
        _cookie("gm_up_token", "bulk.ginniemae.gov", domain_specified=False, domain_initial_dot=False),
        _cookie("gm_up_token", ".example.invalid", domain_specified=True, domain_initial_dot=True),
    ])

    jar = acquisition.load_official_cookie_jar(path)

    assert [(cookie.name, cookie.domain) for cookie in jar] == [("gm_up_token", ".ginniemae.gov")]


def test_cookie_loader_rejects_bulk_host_only_token_for_www_api(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "_under_d", lambda _path: True)
    path = tmp_path / "session.cookies.txt"
    _save_cookies(path, [
        _cookie("gm_up_token", "bulk.ginniemae.gov", domain_specified=False, domain_initial_dot=False),
    ])

    with pytest.raises(acquisition.GinnieAcquisitionError, match="No unexpired secure gm_up_token"):
        acquisition.load_official_cookie_jar(path)


def test_redirect_allowlist_rejects_external_hosts():
    handler = acquisition._OfficialRedirects()
    request = urllib.request.Request("https://www.ginniemae.gov/disclosure-api/api/download")

    with pytest.raises(acquisition.GinnieAcquisitionError, match="outside its official HTTPS hosts"):
        handler.redirect_request(request, None, 302, "Found", {}, "https://example.invalid/file.zip")


def test_catalog_metadata_selects_exact_official_data_bulk_file(monkeypatch):
    class FakeResponse(io.BytesIO):
        status = 200

        def __init__(self, payload):
            super().__init__(payload)
            self.headers = Message()
            self.headers["Content-Type"] = "application/json; charset=utf-8"

    payload = json.dumps({"Other Files": [
        {"fileName": "LoanPerf_202606.zip", "directoryName": "data_bulk",
         "fileSize": "782,688,297", "lastModified": "07/16/2026"},
        {"fileName": "LoanPerf_202606.zip", "directoryName": "samples",
         "fileSize": "100", "lastModified": "07/16/2026"},
    ]}).encode("utf-8")

    class FakeOpener:
        def open(self, request, timeout):
            assert request.full_url == acquisition.CATALOG_URL
            return FakeResponse(payload)

    monkeypatch.setattr(acquisition.urllib.request, "build_opener", lambda *_handlers: FakeOpener())

    assert acquisition._catalog_entry("LoanPerf_202606.zip") == {
        "file_name": "LoanPerf_202606.zip", "directory": "data_bulk",
        "bytes": 782_688_297, "last_modified": "07/16/2026",
    }


def test_expired_or_unauthorized_profile_stops_before_download(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "_under_d", lambda _path: True)
    monkeypatch.setattr(acquisition.shutil, "disk_usage", lambda _root: type("Usage", (), {"free": 10**12})())
    monkeypatch.setattr(acquisition, "_catalog_entry", lambda _filename: {"bytes": 100, "last_modified": ""})
    monkeypatch.setattr(acquisition, "load_official_cookie_jar", lambda _path: _jar_with_token())

    class UnauthorizedOpener:
        def open(self, request, timeout):
            assert request.full_url == acquisition.PROFILE_URL
            assert request.get_header("Authorization") == "Bearer synthetic-test-token"
            raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(acquisition.urllib.request, "build_opener", lambda *_handlers: UnauthorizedOpener())

    with pytest.raises(acquisition.GinnieAcquisitionError, match="session is expired or not authorized"):
        acquisition.download_loanperf_202606(tmp_path, tmp_path / "cookie.txt")

    assert not (tmp_path / acquisition.OUTPUT_RELATIVE).exists()
    assert not (tmp_path / acquisition.RECEIPT_RELATIVE).exists()


def test_authenticated_download_writes_private_zip_and_credential_free_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(acquisition, "_under_d", lambda _path: True)
    monkeypatch.setattr(acquisition.shutil, "disk_usage", lambda _root: type("Usage", (), {"free": 10**12})())
    monkeypatch.setattr(acquisition, "MIN_FREE_BYTES", 0)
    monkeypatch.setattr(acquisition, "_catalog_entry", lambda filename: {
        "file_name": filename, "directory": "data_bulk", "bytes": len(zip_payload),
        "last_modified": "test-only",
    })
    monkeypatch.setattr(acquisition, "load_official_cookie_jar", lambda _path: _jar_with_token())

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("LoanPerf_202606.txt", "synthetic-only")
    zip_payload = buffer.getvalue()

    class FakeResponse(io.BytesIO):
        status = 200

        def __init__(self, body, content_type):
            super().__init__(body)
            self.headers = Message()
            self.headers["Content-Type"] = content_type

    class FakeOpener:
        def __init__(self):
            self.requests = []

        def open(self, request, timeout):
            self.requests.append(request.full_url)
            assert request.get_header("Authorization") == "Bearer synthetic-test-token"
            if request.full_url == acquisition.PROFILE_URL:
                return FakeResponse(b"{}", "application/json")
            assert request.full_url == (
                acquisition.DOWNLOAD_BASE + "?dlfile=data_bulk%2FLoanPerf_202606.zip"
            )
            return FakeResponse(zip_payload, "application/zip")

    fake_opener = FakeOpener()
    monkeypatch.setattr(acquisition.urllib.request, "build_opener", lambda *_handlers: fake_opener)

    receipt = acquisition.download_loanperf_202606(tmp_path, tmp_path / "cookie.txt")

    target = tmp_path / acquisition.OUTPUT_RELATIVE / "LoanPerf_202606.zip"
    saved_receipt = json.loads((tmp_path / acquisition.RECEIPT_RELATIVE).read_text(encoding="utf-8"))
    assert target.read_bytes() == zip_payload
    assert receipt["sha256"] == saved_receipt["sha256"]
    assert receipt["cookie_contents_recorded"] is False
    assert receipt["loan_rows_emitted"] is False
    assert "synthetic-test-token" not in json.dumps(saved_receipt)
    assert len(fake_opener.requests) == 2
    assert fake_opener.requests[0] == acquisition.PROFILE_URL
    assert "?dlfile=" in fake_opener.requests[1]


def test_authorization_token_rejects_ambiguous_or_header_unsafe_values():
    with pytest.raises(acquisition.GinnieAcquisitionError, match="one unambiguous"):
        acquisition._authorization_token(http.cookiejar.MozillaCookieJar())
    with pytest.raises(acquisition.GinnieAcquisitionError, match="malformed"):
        acquisition._authorization_token(_jar_with_token("token\r\nInjected: yes"))
