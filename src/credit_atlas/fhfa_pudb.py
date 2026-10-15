"""Aggregate-only reader for FHFA's 2025 Enterprise PUDB SF Census Tract file."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

from .workspace import sha256

SOURCE_URL = "https://www.fhfa.gov/document/d/pud/2025_pudb_sf_ctf.zip"
DICTIONARY_URL = "https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-data-dictionary.xlsx"
RECORD_COUNTS_URL = "https://www.fhfa.gov/document/d/pud/2025-enterprise-pudb-record-count.xlsx"
SOURCE_RELEASE_DATE = "2026-09-24"
ARCHIVE_MEMBER = "2025_pudb_sf_ctf.csv"
EXPECTED_ROWS = 2_093_767
EXPECTED_ENTERPRISE_COUNTS = {"1": 987_450, "2": 1_106_317}
MAX_ARCHIVE_BYTES = 150_000_000
MAX_MEMBER_BYTES = 600_000_000

HEADERS = [
    "year_acq", "year_census", "enterprise", "record_num_sf_ctf", "state_fips",
    "cbsa_metro_code", "county_fips", "tract_fips", "tract_minority_pct",
    "tract_income_med", "ami_local", "tract_income_ratio", "income_annual",
    "ami_hud", "income_ratio", "upb_acq", "purpose_ctf", "fed_guarantee_ctf",
    "borr_num", "fthb", "race1_borr", "race2_borr", "race3_borr", "race4_borr",
    "race5_borr", "ethnicity_borr", "race1_coborr", "race2_coborr",
    "race3_coborr", "race4_coborr", "race5_coborr", "ethnicity_coborr",
    "sex_borr", "sex_coborr", "age_borr_cat", "age_coborr_cat",
    "occupancy_sf_ctf", "rate_spread", "hoepa", "property_type", "lien_status",
    "age_borr_62_cat", "age_coborr_62_cat", "ltv", "same_year_acq", "term_orig",
    "units_num", "rate_orig", "upb_orig", "preapproval", "channel_apply", "aus",
    "score_borr_model", "score_coborr_model", "dti_cat", "points",
    "period_intro_rate", "mh_land_interest", "property_value", "tract_rural",
    "county_lower_ms_delta", "county_mid_appalachia", "county_persistent_poverty",
    "area_concentrated_poverty", "area_high_opp", "tract_colonias",
]

CATEGORY_FIELDS = {
    "enterprise": "Enterprise",
    "purpose_ctf": "Mortgage purpose",
    "fed_guarantee_ctf": "Federal guarantee",
    "fthb": "First-time home buyer",
    "occupancy_sf_ctf": "Occupancy",
    "lien_status": "Lien status",
    "dti_cat": "DTI category",
    "score_borr_model": "Borrower credit-score model",
    "same_year_acq": "Origination timing vs acquisition",
    "preapproval": "Preapproval request",
    "race1_borr": "Borrower race field 1",
    "ethnicity_borr": "Borrower ethnicity",
    "sex_borr": "Borrower sex",
    "age_borr_cat": "Borrower age band",
    "state_fips": "State FIPS",
    "tract_rural": "Rural census tract",
}

NUMERIC_FIELDS = (
    "income_annual", "tract_income_med", "ami_local", "tract_income_ratio",
    "income_ratio", "upb_acq", "rate_spread", "ltv", "term_orig", "rate_orig",
    "upb_orig", "property_value",
)

LIMITATIONS = [
    "Acquisition/origination characteristics only; the source contains no monthly payment performance, delinquency, default, foreclosure, prepayment, realized loss, or repayment outcome fields.",
    "This is an annual 2025 Enterprise acquisition file, not all mortgage applications, applicants, denials, or the 2012 Freddie performance cohort.",
    "Record numbers are source-scoped sequential identifiers. Do not identify people or join them to other loan files.",
    "Public demographic and census-tract fields support descriptive acquisition-composition analysis only; they do not identify disparate treatment, causal effects, or borrower-level credit risk.",
    "Counts are emitted only as one-dimensional aggregates. No loan-level records or record numbers are returned by this reader.",
]


def profile_archive(path: Path, *, verify_release: bool = True, expected_rows: int | None = None) -> dict:
    """Validate the published archive and return one-dimensional aggregates only."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("FHFA PUDB archive is missing or exceeds the configured size bound")
    digest = sha256(path)
    try:
        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) != 1 or members[0].filename != ARCHIVE_MEMBER:
                raise ValueError("Expected the single official FHFA Census Tract CSV member")
            info = members[0]
            if info.file_size > MAX_MEMBER_BYTES or info.file_size < 1:
                raise ValueError("FHFA PUDB CSV member exceeds the configured size bound")
            with archive.open(info) as stream:
                reader = csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig", errors="strict", newline=""))
                try:
                    headers = next(reader)
                except StopIteration as error:
                    raise ValueError("FHFA PUDB CSV is empty") from error
                if headers != HEADERS:
                    raise ValueError("Unexpected FHFA PUDB Census Tract schema")
                indexes = {name: position for position, name in enumerate(headers)}
                seen_keys: set[str] = set()
                category_counts = {name: Counter() for name in CATEGORY_FIELDS}
                blank_counts = Counter()
                rows = 0
                for row in reader:
                    rows += 1
                    if len(row) != len(headers):
                        raise ValueError("Malformed FHFA PUDB CSV row width")
                    key = row[indexes["record_num_sf_ctf"]].strip()
                    if not key or key in seen_keys:
                        raise ValueError("Blank or duplicate FHFA PUDB record number")
                    seen_keys.add(key)
                    if row[indexes["year_acq"]] != "2025" or row[indexes["year_census"]] != "2020":
                        raise ValueError("Unexpected PUDB acquisition or census year")
                    if row[indexes["enterprise"]] not in EXPECTED_ENTERPRISE_COUNTS:
                        raise ValueError("Unexpected Enterprise code")
                    if row[indexes["purpose_ctf"]] not in {"1", "2", "4", "7", "9"}:
                        raise ValueError("Unexpected mortgage-purpose code")
                    if row[indexes["fed_guarantee_ctf"]] not in {"1", "2", "3", "4"}:
                        raise ValueError("Unexpected federal-guarantee code")
                    for field, counter in category_counts.items():
                        counter[row[indexes[field]].strip() or "<BLANK>"] += 1
                    for field in NUMERIC_FIELDS:
                        if not row[indexes[field]].strip():
                            blank_counts[field] += 1
    except (zipfile.BadZipFile, OSError, UnicodeError, csv.Error) as error:
        raise ValueError("Invalid FHFA PUDB ZIP/CSV payload") from error

    if len(seen_keys) != rows:
        raise ValueError("FHFA PUDB record-key count does not match source row count")
    if expected_rows is not None and rows != expected_rows:
        raise ValueError(f"FHFA PUDB row count differs from expected {expected_rows}")
    if verify_release and rows != EXPECTED_ROWS:
        raise ValueError(f"FHFA PUDB row count differs from official record count {EXPECTED_ROWS}")
    enterprise_counts = dict(category_counts["enterprise"])
    if verify_release and enterprise_counts != EXPECTED_ENTERPRISE_COUNTS:
        raise ValueError("FHFA PUDB Enterprise counts differ from the official record-count workbook")

    return {
        "schema_version": 2,
        "dataset": "FHFA 2025 Enterprise PUDB Single-Family Census Tract File",
        "source_url": SOURCE_URL,
        "source_release_date": SOURCE_RELEASE_DATE,
        "archive_member": ARCHIVE_MEMBER,
        "archive_sha256": digest,
        "rows": rows,
        "columns": len(headers),
        "headers_sha256": hashlib.sha256("\n".join(headers).encode()).hexdigest(),
        "unique_record_keys": len(seen_keys),
        "duplicate_record_keys": 0,
        "malformed_rows": 0,
        "acquisition_year": 2025,
        "census_year": 2020,
        "enterprise_counts": enterprise_counts,
        "category_counts": {field: dict(counter) for field, counter in category_counts.items()},
        "blank_counts": dict(blank_counts),
        "limitations": LIMITATIONS,
    }


def read(root: Path) -> dict:
    """Read only an integrity-checked aggregate profile saved under private data."""
    folder = Path(root).resolve() / "data" / "private" / "fhfa-enterprise-pudb" / "2025"
    archive_path = folder / "2025_pudb_sf_ctf.zip"
    receipts = sorted(folder.glob("receipt-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not archive_path.is_file() or not receipts:
        return {"status": "UNAVAILABLE", "reason": "FHFA 2025 PUDB source archive/profile is not available locally."}
    try:
        receipt_path = receipts[0]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        profile_path = folder / receipt["profile_file"]
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "PASS" or receipt.get("archive_sha256") != sha256(archive_path):
            raise ValueError("FHFA PUDB source archive does not match its receipt")
        if receipt.get("profile_sha256") != sha256(profile_path):
            raise ValueError("FHFA PUDB profile does not match its receipt")
        if profile.get("archive_sha256") != receipt["archive_sha256"] or profile.get("rows") != EXPECTED_ROWS:
            raise ValueError("FHFA PUDB profile does not match the verified source contract")
        if profile.get("columns") != len(HEADERS) or profile.get("unique_record_keys") != profile.get("rows"):
            raise ValueError("FHFA PUDB source profile failed schema/uniqueness checks")
        return {"status": "AVAILABLE", "visibility": "private", "public_release_approved": False, **profile}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "UNAVAILABLE", "reason": str(error)}
