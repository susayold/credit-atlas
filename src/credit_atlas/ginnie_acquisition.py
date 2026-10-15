"""Bounded authenticated acquisition for the official Ginnie Mae LoanPerf file."""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import shutil
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit


PORTAL = "https://bulk.ginniemae.gov/"
PROFILE_URL = "https://www.ginniemae.gov/user-profiles/api/profile"
CATALOG_URL = "https://www.ginniemae.gov/bulk-content/api/disclosure-data"
DOWNLOAD_BASE = "https://www.ginniemae.gov/disclosure-api/api/download"
DOWNLOAD_FILE = "data_bulk/LoanPerf_202606.zip"
OUTPUT_RELATIVE = Path("data/private/ginnie-mae/source/loanperf-quarterly-pilot/production")
RECEIPT_RELATIVE = Path("artifacts/private/ginnie-loanperf-production-202606/receipt.json")
COOKIE_NAME = "gm_up_token"
OFFICIAL_HOSTS = {"bulk.ginniemae.gov", "www.ginniemae.gov"}
MAX_BYTES = 1_073_741_824
MIN_FREE_BYTES = 2 * 1_073_741_824


class GinnieAcquisitionError(ValueError):
    """Raised when the official authenticated acquisition gate is not satisfied."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _under_d(path: Path) -> bool:
    return path.drive.upper() == "D:"


def _domain_applies_to_download(cookie: http.cookiejar.Cookie) -> bool:
    domain = cookie.domain.lstrip(".").casefold()
    if domain == "www.ginniemae.gov":
        return True
    # A parent-domain cookie is valid only when Netscape format marks it as a
    # domain cookie. Host-only cookies for bulk.ginniemae.gov are not sent to
    # the official user-profile/download host.
    return domain == "ginniemae.gov" and cookie.domain_initial_dot


def load_official_cookie_jar(cookie_file: Path) -> http.cookiejar.MozillaCookieJar:
    cookie_file = cookie_file.resolve()
    if not _under_d(cookie_file) or not cookie_file.is_file():
        raise GinnieAcquisitionError("Provide an existing Netscape cookie file on D:")
    jar = http.cookiejar.MozillaCookieJar()
    try:
        jar.load(str(cookie_file), ignore_discard=True, ignore_expires=False)
    except (OSError, http.cookiejar.LoadError) as exc:
        raise GinnieAcquisitionError("The supplied file is not a readable Netscape cookie jar") from exc

    applicable = [cookie for cookie in jar if cookie.name == COOKIE_NAME
                  and _domain_applies_to_download(cookie) and cookie.secure]
    if not applicable:
        raise GinnieAcquisitionError(
            "No unexpired secure gm_up_token cookie applies to www.ginniemae.gov"
        )
    keep = {id(cookie) for cookie in applicable}
    for cookie in list(jar):
        if id(cookie) not in keep:
            jar.clear(cookie.domain, cookie.path, cookie.name)
    return jar


class _OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        parsed = urlsplit(new_url)
        if (parsed.scheme != "https" or parsed.hostname not in OFFICIAL_HOSTS
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or parsed.fragment):
            raise GinnieAcquisitionError("Ginnie Mae redirected outside its official HTTPS hosts")
        return super().redirect_request(request, response, code, message, headers, new_url)


def _profile_is_valid(opener) -> None:
    request = urllib.request.Request(PROFILE_URL, headers={"Accept": "application/json"})
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                raise GinnieAcquisitionError("Ginnie Mae profile validation did not return HTTP 200")
            # Read only a small bounded response; profile contents are not stored or logged.
            if len(response.read(1024 * 1024 + 1)) > 1024 * 1024:
                raise GinnieAcquisitionError("Ginnie Mae profile response exceeded its bound")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise GinnieAcquisitionError("Ginnie Mae session is expired or not authorized") from exc
        raise GinnieAcquisitionError(f"Ginnie Mae profile check failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise GinnieAcquisitionError("Ginnie Mae profile endpoint is unavailable") from exc


def _validate_download_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "www.ginniemae.gov"
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.path != "/disclosure-api/api/download"
            or parsed.fragment):
        raise GinnieAcquisitionError("Unexpected Ginnie Mae download URL")


def _catalog_entry(filename: str) -> dict:
    request = urllib.request.Request(CATALOG_URL, headers={"Accept": "application/json"})
    opener = urllib.request.build_opener(_OfficialRedirects())
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200 or response.headers.get_content_type().casefold() != "application/json":
                raise GinnieAcquisitionError("Ginnie Mae public catalog did not return JSON")
            raw = response.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise GinnieAcquisitionError("Ginnie Mae catalog exceeded its size bound")
        catalog = json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise GinnieAcquisitionError(f"Ginnie Mae public catalog returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GinnieAcquisitionError("Ginnie Mae public catalog could not be read") from exc
    matches = []
    if not isinstance(catalog, dict):
        raise GinnieAcquisitionError("Ginnie Mae public catalog schema changed")
    for category_rows in catalog.values():
        if not isinstance(category_rows, list):
            continue
        matches.extend(row for row in category_rows
                       if isinstance(row, dict) and row.get("fileName") == filename
                       and row.get("directoryName") == "data_bulk")
    if len(matches) != 1:
        raise GinnieAcquisitionError("The requested LoanPerf release is not uniquely listed in the official catalog")
    row = matches[0]
    try:
        size = int(str(row["fileSize"]).replace(",", ""))
    except (KeyError, ValueError) as exc:
        raise GinnieAcquisitionError("Ginnie Mae catalog file size is invalid") from exc
    if size <= 0 or size > MAX_BYTES:
        raise GinnieAcquisitionError("Catalog LoanPerf ZIP exceeds the 1 GiB acquisition bound")
    return {"file_name": filename, "directory": "data_bulk", "bytes": size,
            "last_modified": str(row.get("lastModified", ""))}


def download_loanperf_202606(root: Path, cookie_file: Path) -> dict:
    """Download the catalog-listed quarterly ZIP without persisting credentials."""
    root = root.resolve()
    if not _under_d(root):
        raise GinnieAcquisitionError("Ginnie Mae source data and receipts must remain on D:")
    metadata = _catalog_entry("LoanPerf_202606.zip")
    if shutil.disk_usage(root).free < metadata["bytes"] + MIN_FREE_BYTES:
        raise GinnieAcquisitionError("Insufficient D: space for the official LoanPerf pilot")

    jar = load_official_cookie_jar(cookie_file)
    opener = urllib.request.build_opener(_OfficialRedirects(), urllib.request.HTTPCookieProcessor(jar))
    _profile_is_valid(opener)

    url = f"{DOWNLOAD_BASE}?dlfile={quote(DOWNLOAD_FILE, safe='')}"
    _validate_download_url(url)
    output_dir = root / OUTPUT_RELATIVE
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "LoanPerf_202606.zip"
    partial = output_dir / "LoanPerf_202606.zip.partial"
    if target.exists() or partial.exists():
        raise GinnieAcquisitionError("Production ZIP or partial download already exists; preserve it and review first")

    digest = hashlib.sha256()
    size = 0
    partial_created = False
    request = urllib.request.Request(url, headers={"Accept": "application/zip,application/octet-stream"})
    try:
        with opener.open(request, timeout=60) as response:
            if response.status != 200:
                raise GinnieAcquisitionError(f"Ginnie Mae download returned HTTP {response.status}")
            content_type = response.headers.get_content_type().casefold()
            if content_type in {"text/html", "application/json"}:
                raise GinnieAcquisitionError("Ginnie Mae returned an app/login page instead of the ZIP")
            with partial.open("xb") as stream:
                partial_created = True
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise GinnieAcquisitionError("LoanPerf download exceeded the 1 GiB safety bound")
                    digest.update(chunk)
                    stream.write(chunk)
        if size != metadata["bytes"]:
            raise GinnieAcquisitionError(
                f"Catalog file size changed: expected {metadata['bytes']} bytes, received {size}"
            )
        if not zipfile.is_zipfile(partial):
            raise GinnieAcquisitionError("Ginnie Mae response is not a valid ZIP archive")
        with zipfile.ZipFile(partial) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != 1 or members[0].file_size <= 0 or members[0].flag_bits & 1:
                raise GinnieAcquisitionError("LoanPerf ZIP member structure is unexpected or encrypted")
        partial.replace(target)
    except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
        if partial_created:
            partial.unlink(missing_ok=True)
        if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403):
            raise GinnieAcquisitionError("Ginnie Mae rejected the download session") from exc
        raise GinnieAcquisitionError("Official Ginnie Mae download failed; no credential values were logged") from exc
    except Exception:
        if partial_created:
            partial.unlink(missing_ok=True)
        raise

    receipt = {
        "status": "DOWNLOADED_PENDING_AGGREGATE_AUDIT",
        "source": "Ginnie Mae Disclosure Data Download",
        "catalog_url": PORTAL,
        "catalog_metadata_url": CATALOG_URL,
        "profile_validated": True,
        "terms_accepted_by_user": True,
        "catalog_file": "LoanPerf_202606.zip",
        "catalog_bytes": metadata["bytes"],
        "catalog_last_modified": metadata["last_modified"],
        "bytes": size,
        "sha256": digest.hexdigest(),
        "downloaded_at_utc": _timestamp(),
        "private_path": str(target),
        "cookie_contents_recorded": False,
        "loan_rows_emitted": False,
        "aggregate_audit_required": True,
    }
    receipt_path = root / RECEIPT_RELATIVE
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt
