"""Bounded official HTTP acquisition; authentication is supplied locally."""
from __future__ import annotations

import hashlib
import http.cookiejar
import shutil
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

from .workspace import read_json, sha256, timestamp, write_new

PORTAL = "https://claritydownload.fmapps.freddiemac.com/CRT/"
HOST = "claritydownload.fmapps.freddiemac.com"
MAX_ZIP = 512 * 1024**2
MAX_EXPANDED = 4 * 1024**3


def official_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != HOST or
            parsed.username is not None or parsed.password is not None or
            parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("An official HTTPS Clarity download URL is required")
    return url


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        official_url(newurl)
        return super().redirect_request(request, response, code, message, headers, newurl)


def http_client(cookie_file: Path | None = None):
    jar = http.cookiejar.MozillaCookieJar()
    if cookie_file:
        jar.load(str(cookie_file), ignore_discard=True, ignore_expires=False)
        # Only exact destination cookies are retained. No browser profile access.
        for cookie in list(jar):
            if cookie.domain.lstrip(".") != HOST:
                jar.clear(cookie.domain, cookie.path, cookie.name)
    return urllib.request.build_opener(OfficialRedirects(), urllib.request.HTTPCookieProcessor(jar))


def probe(root: Path, cookie_file: Path | None = None):
    result = {"checked_at": timestamp(), "source": "Freddie Mac SFLLD",
              "official_portal": PORTAL, "authentication_supplied": cookie_file is not None,
              "data_downloaded": False}
    try:
        with http_client(cookie_file).open(PORTAL, timeout=30) as response:
            result.update(http_status=response.status, status="PORTAL_REACHABLE_DOWNLOAD_URLS_STILL_REQUIRED")
    except urllib.error.HTTPError as error:
        result.update(http_status=error.code, status="AUTHENTICATION_REQUIRED" if error.code in (401, 403) else "HTTP_ERROR")
    except (urllib.error.URLError, TimeoutError, ValueError):
        result.update(status="PORTAL_UNAVAILABLE_OR_REDIRECT_REJECTED")
    path = root / "artifacts/private" / ("source-access-" + uuid.uuid4().hex[:12] + ".json")
    write_new(path, result)
    return result


def verify_annual_zip(path: Path, year: int):
    with zipfile.ZipFile(path) as archive:
        expected = {f"sample_orig_{year}.txt", f"sample_perf_{year}.txt"}
        members = archive.infolist()
        if {m.filename for m in members} != expected or len(members) != 2:
            raise ValueError("Expected the two official annual-sample members for this vintage")
        if sum(m.file_size for m in members) > MAX_EXPANDED or any(m.flag_bits & 1 for m in members):
            raise ValueError("Annual archive is oversized or encrypted")
        if archive.testzip() is not None:
            raise ValueError("ZIP member CRC failed")
        # Structural archive verification is separate from schema/population qualification.
        return [{"name": m.filename, "expanded_bytes": m.file_size} for m in members]


def download_annual(root: Path, item: dict, client=None):
    url = official_url(item["url"])
    year, release = item["year"], item["release"]
    if type(year) is not int or not 1999 <= year <= 2026 or release != 47:
        raise ValueError("A valid annual vintage and supported Release 47 are required")
    if shutil.disk_usage(root).free < 25 * 1024**3 + MAX_ZIP:
        raise ValueError("Insufficient storage headroom for source acquisition")
    output = root / "data/private/incoming" / ("download-" + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    partial = output / "source.partial"
    client = client or http_client()
    receipt = {"source": "Freddie Mac SFLLD", "year": year, "release": release,
               "source_host": HOST, "url_fingerprint": hashlib.sha256(url.encode()).hexdigest(),
               "started_at": timestamp(), "visibility": "private", "public_release_approved": False,
               "research_use_confirmed": False, "schema_qualified": False}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "CreditAtlasResearch/0.1"})
        with client.open(request, timeout=60) as response, partial.open("xb") as stream:
            official_url(response.url)
            total = 0
            while chunk := response.read(1024**2):
                total += len(chunk)
                if total > MAX_ZIP:
                    raise ValueError("Annual sample exceeds bounded download size")
                stream.write(chunk)
        members = verify_annual_zip(partial, year)
        digest = sha256(partial)
        final = output / (digest + ".zip")
        partial.rename(final)
        receipt.update(status="DOWNLOADED_ARCHIVE_VERIFIED_AWAITING_QUALIFICATION", sha256=digest,
                       bytes=total, archive=final.name, original_filename=f"sample_{year}.zip",
                       members=members, completed_at=timestamp())
        write_new(output / "receipt.json", receipt)
        return {"status": receipt["status"], "year": year, "receipt": str(output / "receipt.json")}
    except Exception as error:
        receipt.update(status="DOWNLOAD_FAILED", exception_type=type(error).__name__)
        if isinstance(error, urllib.error.HTTPError):
            receipt["http_status"] = error.code
        write_new(output / "failed.json", receipt)
        raise RuntimeError("Official annual download failed; inspect its private receipt") from None


def download_manifest(root: Path, manifest_path: Path, cookie_file: Path | None = None):
    manifest = read_json(manifest_path)
    items = manifest.get("annual_samples")
    if not isinstance(items, list) or not 1 <= len(items) <= 12:
        raise ValueError("A manifest of 1–12 official annual download URLs is required")
    # Validate the entire batch before network writes; no guessed endpoint construction.
    for item in items:
        official_url(item["url"])
        if type(item.get("year")) is not int or not 1999 <= item["year"] <= 2026 or item.get("release") != 47:
            raise ValueError("Unsupported vintage or release")
    client = http_client(cookie_file)
    return {"downloads": [download_annual(root, item, client) for item in items],
            "model_ready": False, "next_stage": "source rights/schema/population qualification"}
