"""Acquire the official HMDA 2018 Three-Year national LAR via the Data Browser API.

2018 is the Three-Year freeze (2021-12-31), not a One-Year release. The raw
CSV and receipt are private on D:. No loan-level rows are copied into the repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


SOURCE_PAGE = "https://ffiec.cfpb.gov/data-browser/data/2018"
SOURCE_DOC = "https://ffiec.cfpb.gov/documentation/api/data-browser/"
FREEZE_DATE = "2021-12-31"
EXPECTED_ROWS = 15_138_510
EXPECTED_ACTIONS = {
    "1": 7_732_289,
    "2": 338_822,
    "3": 2_552_640,
    "4": 1_771_582,
    "5": 554_481,
    "6": 2_012_221,
    "7": 101_772,
    "8": 74_703,
}
SOURCE_URL = (
    "https://ffiec.cfpb.gov/v2/data-browser-api/view/nationwide/csv"
    "?years=2018&actions_taken=1,2,3,4,5,6,7,8"
)
MAX_BYTES = 8 * 1024**3
MIN_FREE_BYTES = 2 * 1024**3


class AcquisitionError(ValueError):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def acquire(root: Path) -> dict:
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise AcquisitionError("HMDA source files and receipts must stay on D:")
    if shutil.disk_usage(root).free < MIN_FREE_BYTES:
        raise AcquisitionError("Less than 2 GiB free on D:; refusing a large stream download")

    data_dir = root / "data/private/hmda/hmda-browser-three-year-2018"
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / "hmda-2018-three-year-national.csv"
    partial = data_dir / (target.name + ".partial")
    if target.exists() or partial.exists():
        raise AcquisitionError("2018 CSV or partial download already exists; preserve and inspect it first")

    request = urllib.request.Request(SOURCE_URL, headers={
        "User-Agent": "CreditAtlas public data audit/1.0",
        "Accept": "text/csv,application/csv;q=0.9,*/*;q=0.1",
    })
    digest = hashlib.sha256()
    received = 0
    first_bytes = bytearray()
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            content_type = response.headers.get_content_type().casefold()
            if response.status != 200 or content_type not in {"text/csv", "application/csv", "application/octet-stream"}:
                raise AcquisitionError(f"Unexpected HMDA API response: HTTP {response.status}, {content_type}")
            with partial.open("xb") as stream:
                while block := response.read(1024 * 1024):
                    received += len(block)
                    if received > MAX_BYTES:
                        raise AcquisitionError("HMDA 2018 stream exceeded the 8 GiB safety limit")
                    digest.update(block)
                    if len(first_bytes) < 4096:
                        first_bytes.extend(block[:4096 - len(first_bytes)])
                    stream.write(block)
        if received == 0 or b"activity_year" not in first_bytes or b"action_taken" not in first_bytes:
            raise AcquisitionError("HMDA response is empty or missing expected CSV headers")
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise

    receipt_id = "hmda-2018-browser-acq-" + uuid.uuid4().hex[:12]
    receipt = {
        "schema_version": 1,
        "status": "DOWNLOADED_PENDING_ROW_AUDIT",
        "receipt_id": receipt_id,
        "source": "FFIEC/CFPB HMDA Data Browser API",
        "source_page": SOURCE_PAGE,
        "source_documentation": SOURCE_DOC,
        "source_url": SOURCE_URL,
        "dataset_vintage": "2018 Three-Year National Loan-Level Dataset",
        "freeze_date": FREEZE_DATE,
        "expected_rows_from_official_aggregation_api": EXPECTED_ROWS,
        "expected_action_counts_from_official_aggregation_api": EXPECTED_ACTIONS,
        "bytes": received,
        "sha256": digest.hexdigest(),
        "content_type": "text/csv",
        "downloaded_at_utc": timestamp(),
        "private_path": str(target),
        "visibility": "private",
        "loan_level_rows_emitted_to_public_repo": False,
    }
    receipt_path = data_dir / "acquisition-receipt.json"
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return {key: receipt[key] for key in (
        "status", "receipt_id", "dataset_vintage", "freeze_date", "bytes", "sha256", "private_path")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(r"D:\data\Codex\credit-atlas"))
    args = parser.parse_args()
    try:
        print(json.dumps(acquire(args.root), indent=2, ensure_ascii=False))
    except (OSError, urllib.error.URLError, AcquisitionError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
