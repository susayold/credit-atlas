import csv
import hashlib
import json
import zipfile

import pytest

from credit_atlas import fhfa_pudb
from credit_atlas.fhfa_pudb import HEADERS, profile_archive


def _row(key, enterprise="1", purpose="1"):
    row = {name: "" for name in HEADERS}
    row.update({
        "year_acq": "2025",
        "year_census": "2020",
        "enterprise": enterprise,
        "record_num_sf_ctf": key,
        "purpose_ctf": purpose,
        "fed_guarantee_ctf": "1",
        "fthb": "1",
        "occupancy_sf_ctf": "1",
        "lien_status": "1",
        "dti_cat": "30",
        "score_borr_model": "12",
        "same_year_acq": "1",
        "preapproval": "2",
        "race1_borr": "3",
        "ethnicity_borr": "1",
        "sex_borr": "2",
        "age_borr_cat": "3",
        "tract_rural": "0",
    })
    return row


def _archive(path, rows):
    import io

    content = io.StringIO(newline="")
    writer = csv.DictWriter(content, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("2025_pudb_sf_ctf.csv", content.getvalue())
    return path


def test_profile_returns_only_aggregate_counts_and_hashes(tmp_path):
    path = _archive(tmp_path / "pudb.zip", [
        _row("synthetic-1", enterprise="1", purpose="1"),
        _row("synthetic-2", enterprise="2", purpose="7"),
    ])
    result = profile_archive(path, verify_release=False, expected_rows=2)
    assert result["rows"] == 2
    assert result["columns"] == 66
    assert result["unique_record_keys"] == 2
    assert result["enterprise_counts"] == {"1": 1, "2": 1}
    assert result["category_counts"]["purpose_ctf"] == {"1": 1, "7": 1}
    assert result["category_counts"]["sex_borr"] == {"2": 2}
    assert "synthetic-1" not in json.dumps(result)
    assert result["limitations"] and "no monthly payment performance" in result["limitations"][0]


def test_profile_rejects_duplicate_source_record_numbers(tmp_path):
    path = _archive(tmp_path / "duplicates.zip", [_row("same"), _row("same", enterprise="2")])
    with pytest.raises(ValueError, match="duplicate FHFA PUDB record number"):
        profile_archive(path, verify_release=False)


def test_profile_rejects_unexpected_year_and_category_codes(tmp_path):
    wrong_year = _row("record-1")
    wrong_year["year_acq"] = "2024"
    path = _archive(tmp_path / "wrong-year.zip", [wrong_year])
    with pytest.raises(ValueError, match="Unexpected PUDB acquisition or census year"):
        profile_archive(path, verify_release=False)

    wrong_code = _row("record-2", purpose="8")
    path = _archive(tmp_path / "wrong-purpose.zip", [wrong_code])
    with pytest.raises(ValueError, match="Unexpected mortgage-purpose code"):
        profile_archive(path, verify_release=False)


def test_profile_rejects_missing_wrong_zip_member(tmp_path):
    path = tmp_path / "wrong-member.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("other.csv", ",".join(HEADERS) + "\n")
    with pytest.raises(ValueError, match="Expected the single official FHFA Census Tract CSV member"):
        profile_archive(path, verify_release=False)


def test_reader_serves_only_integrity_checked_aggregate_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(fhfa_pudb, "EXPECTED_ROWS", 2)
    folder = tmp_path / "data" / "private" / "fhfa-enterprise-pudb" / "2025"
    folder.mkdir(parents=True)
    archive_path = _archive(folder / "2025_pudb_sf_ctf.zip", [
        _row("private-record-1", enterprise="1"),
        _row("private-record-2", enterprise="2", purpose="7"),
    ])
    profile = profile_archive(archive_path, verify_release=False, expected_rows=2)
    profile_path = folder / "profile-test.json"
    profile_path.write_text(json.dumps(profile), encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {
        "status": "PASS",
        "archive_sha256": digest(archive_path),
        "profile_file": profile_path.name,
        "profile_sha256": digest(profile_path),
    }
    (folder / "receipt-test.json").write_text(json.dumps(receipt), encoding="utf-8")
    response = fhfa_pudb.read(tmp_path)
    assert response["status"] == "AVAILABLE"
    assert response["visibility"] == "private"
    assert response["public_release_approved"] is False
    assert response["enterprise_counts"] == {"1": 1, "2": 1}
    assert "record_num_sf_ctf" not in response
    assert "private-record-1" not in json.dumps(response)
