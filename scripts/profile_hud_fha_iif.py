"""Acquire and profile the public HUD FHA tract snapshot into private data storage."""
from __future__ import annotations

import argparse
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from credit_atlas.hud_fha_iif import SOURCE_URL, acquire_and_profile
from credit_atlas.workspace import app_root

MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


def download(root: Path) -> Path:
    parsed = urllib.parse.urlparse(SOURCE_URL)
    if parsed.scheme != "https" or parsed.hostname != "hudgis-hud.opendata.arcgis.com":
        raise ValueError("HUD downloader accepts only the official HTTPS host")
    folder = root / "data" / "private" / "hud-fha-iif-tract"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "fha-insurance-in-force-by-tract.csv"
    if target.exists():
        raise FileExistsError("Refusing to overwrite an existing HUD source file")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "CreditAtlas-Research/1.0"})
    temporary = None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final = urllib.parse.urlparse(response.geturl())
            if final.scheme != "https" or final.hostname not in {"hudgis-hud.opendata.arcgis.com"}:
                raise ValueError("HUD download redirected outside the approved official host")
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_DOWNLOAD_BYTES:
                raise ValueError("HUD source download exceeds the 100 MiB bound")
            fd, temporary = tempfile.mkstemp(prefix=".hud-fha-iif-", suffix=".partial", dir=folder)
            written = 0
            with os.fdopen(fd, "wb") as output:
                while chunk := response.read(1024 * 1024):
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_BYTES:
                        raise ValueError("HUD source download exceeds the 100 MiB bound")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        os.replace(temporary, target)
        temporary = None
        return target
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="download if the private source file is absent")
    args = parser.parse_args()
    root = app_root()
    source = root / "data" / "private" / "hud-fha-iif-tract" / "fha-insurance-in-force-by-tract.csv"
    if args.download and not source.exists():
        source = download(root)
    result = acquire_and_profile(root, source)
    profile = result["profile"]
    print(f"PASS: {profile['rows']:,} unique tracts; SHA-256 {profile['source_sha256']}")
    print(f"Nonblank totals: {profile['national_totals_nonblank_tracts']}")
    print(f"Quarantined source codes: {profile['uninterpreted_source_codes']}")
    print(f"Receipt: data/private/hud-fha-iif-tract/receipt-{profile['source_sha256'][:12]}.json")


if __name__ == "__main__":
    main()
