"""Official public-source acquisition and source-native profiling for five workspaces."""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import uuid
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .workspace import contained, sha256, timestamp, write_new

ALLOWED_HOSTS = {"archive.ics.uci.edu", "data.sba.gov", "api.fdic.gov", "fred.stlouisfed.org"}
MAX_BYTES = 512 * 1024**2


def catalog():
    sources = []
    def add(identifier, url, kind, modules, metadata, rights, scope):
        sources.append(dict(source_id=identifier, url=url, kind=kind, modules=modules,
                            metadata_url=metadata, rights=rights, scope=scope))
    for number, identifier, modules in [(350, "uci-retail", ["P1"]), (365, "uci-bankruptcy", ["P3"])]:
        page = "https://archive.ics.uci.edu/dataset/" + str(number)
        add(identifier, f"https://archive.ics.uci.edu/static/public/{number}/data.csv", "csv",
            modules, page, "CC BY 4.0; cite original dataset/DOI", "Source-specific benchmark, not local underwriting qualification")
        add(identifier + "-metadata", f"https://archive.ics.uci.edu/api/dataset?id={number}", "json",
            modules, page, "UCI source metadata", "Variable definitions and source interpretation")
    for program, ranges in [("7a", ["FY1991_FY1999", "FY2000_FY2009", "FY2010_FY2019", "FY2020_Present"]),
                            ("504", ["FY1991_FY2009", "FY2010_Present"])]:
        for years in ranges:
            name = f"FOIA_{program}_{years}_asof_260630.csv"
            add("sba-" + program + "-" + years.lower(),
                "https://data.sba.gov/sites/default/files/uploaded_resources/" + name, "csv", ["P3"],
                "https://data.sba.gov/dataset/7a-504-foia", "U.S. Government Works",
                "Snapshot as of 2026-06-30; status is not a fixed-horizon default label")
    add("sba-dictionary", "https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx",
        "xlsx", ["P3"], "https://data.sba.gov/dataset/7a-504-foia", "U.S. Government Works", "Source dictionary")
    query = urlencode({"filters": "REPDTE:20260630", "fields": "CERT,REPDTE,NAME,ASSET,DEP,EQ,ROA",
                       "limit": 10000, "offset": 0, "sort_by": "CERT", "sort_order": "ASC", "format": "json"})
    add("fdic-financials-20260630", "https://api.fdic.gov/banks/financials?" + query, "json", ["P4"],
        "https://api.fdic.gov/banks/docs", "Public FDIC data; cite FDIC", "One bank-quarter snapshot; not a bank loan book")
    add("fdic-failures", "https://api.fdic.gov/banks/failures?" + urlencode({"limit":10000,"offset":0,"format":"json"}),
        "json", ["P4"], "https://api.fdic.gov/banks/docs", "Public FDIC data; cite FDIC", "Failure/assistance events; not loan defaults")
    for series, modules in [("UNRATE", ["P2", "P4"]), ("USSTHPI", ["P2"]), ("MORTGAGE30US", ["P2", "P5"]),
                            ("DGS2", ["P5"]), ("DGS10", ["P5"]), ("DGS30", ["P5"]), ("BAMLC0A0CM", ["P5"])]:
        rights = ("ICE copyrighted: internal use only; no redistribution" if series == "BAMLC0A0CM" else
                  "Freddie Mac copyright; internal research and citation" if series == "MORTGAGE30US" else
                  "Public domain; citation requested")
        add("fred-" + series.lower(), "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + series,
            "csv", modules, "https://fred.stlouisfed.org/series/" + series, rights,
            "Native-frequency latest snapshot; not historical as-of availability or security-level quotes")
    return sources


def validate_source(source):
    url = urlsplit(source["url"])
    if (url.scheme != "https" or url.hostname not in ALLOWED_HOSTS or url.username or url.password
            or url.port is not None or not re.fullmatch(r"[a-z0-9_-]{1,100}", source["source_id"])
            or source["kind"] not in {"csv", "json", "xlsx"}):
        raise ValueError("Official credential-free HTTPS source required")


def profile(path, source):
    if source["kind"] == "xlsx":
        with zipfile.ZipFile(path) as archive:
            if ("xl/workbook.xml" not in archive.namelist()
                    or sum(info.file_size for info in archive.infolist()) > 100 * 1024**2
                    or archive.testzip() is not None):
                raise ValueError("Invalid or oversized workbook archive")
        return {"format": "xlsx", "status": "ARCHIVE_VERIFIED_DICTIONARY_NOT_YET_PARSED"}
    if source["kind"] == "json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if source["source_id"].startswith("fdic-"):
            rows = [item["data"] for item in payload["data"]]
            total = payload["meta"]["total"]
            if len(rows) != total:
                raise ValueError("FDIC query truncated; full pagination required")
            if not rows:
                raise ValueError("Empty FDIC query")
            fields = sorted(set().union(*(row.keys() for row in rows)))
            result = {"rows": len(rows), "source_total": total, "fields": fields,
                      "null_counts": {name: sum(row.get(name) is None for row in rows) for name in fields}}
            if source["source_id"].startswith("fdic-financials"):
                keys = [(row["CERT"], row["REPDTE"]) for row in rows]
                if len(set(keys)) != len(keys) or any(str(key[1]) != "20260630" for key in keys):
                    raise ValueError("Bank-quarter grain mismatch")
                result["grain"] = "CERT x REPDTE"
            return result
        if payload.get("status") != 200 or not isinstance(payload.get("data"), dict):
            raise ValueError("Invalid UCI metadata")
        return {"uci_id": payload["data"]["uci_id"], "data_url": payload["data"]["data_url"],
                "metadata_instances": payload["data"]["num_instances"], "note": "Verify payload counts and horizon subsets separately"}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(set(fields)) != len(fields) or any("<html" in name.lower() for name in fields):
            raise ValueError("Invalid CSV header")
        nulls = Counter({name: 0 for name in fields})
        count = 0
        label = next((name for name in ("Y", "class", "default payment next month") if name in fields), None)
        labels, years, statuses = Counter(), Counter(), Counter()
        keys = set()
        duplicate_ids = 0
        first_date = last_date = None
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed CSV row")
            count += 1
            nulls.update(name for name, value in row.items() if value.strip() in ("", "?", ".", "NaN", "nan"))
            if label:
                if row[label] not in ("0", "1"):
                    raise ValueError("Nonbinary source target")
                labels[row[label]] += 1
            if "year" in fields:
                years[row["year"]] += 1
            if "LoanStatus" in fields:
                statuses[row["LoanStatus"]] += 1
            key = row.get("ID")
            if key is not None:
                duplicate_ids += key in keys
                keys.add(key)
            if "observation_date" in fields:
                from datetime import date
                observed = date.fromisoformat(row["observation_date"])
                if last_date and observed <= last_date:
                    raise ValueError("Duplicate/unordered native dates")
                first_date = first_date or observed
                last_date = observed
        if not count:
            raise ValueError("Empty CSV")
        result = {"rows": count, "columns": len(fields), "fields": fields, "null_counts": dict(nulls)}
        if label:
            result.update(target_field=label, target_counts=dict(labels))
        if years:
            result["source_year_codes"] = dict(years)
        if statuses:
            result["source_status_counts"] = dict(statuses)
        if "ID" in fields:
            result["duplicate_source_ids"] = duplicate_ids
        if first_date:
            result.update(first_reference_date=first_date.isoformat(), last_reference_date=last_date.isoformat())
        return result


def acquire_one(root, folder, source):
    validate_source(source)
    filename = source["source_id"] + "." + source["kind"]
    partial = contained(root, str((folder / (filename + ".partial")).relative_to(root)))
    final = folder / filename
    try:
        response = subprocess.run(["curl.exe", "--fail", "--silent", "--show-error", "--proto", "=https",
            "--connect-timeout", "20", "--max-time", "120", "--max-filesize", str(MAX_BYTES),
            "--output", str(partial), "--write-out", "%{http_code}", source["url"]],
            capture_output=True, timeout=125, check=False)
        if response.returncode or response.stdout != b"200":
            raise RuntimeError(f"HTTP download failed: curl={response.returncode}, status={response.stdout.decode('ascii', errors='replace')[:3]}")
        if not partial.is_file() or not 0 < partial.stat().st_size <= MAX_BYTES:
            raise ValueError("Invalid download size")
        quality = profile(partial, source)
        partial.rename(final)
        return {**source, "status": "DOWNLOADED_AND_PROFILED", "file": filename,
                "sha256": sha256(final), "bytes": final.stat().st_size, "retrieved_at": timestamp(),
                "profile": quality, "model_qualified": False, "public_release_approved": False}
    except Exception as error:
        return {**source, "status": "FAILED", "failed_at": timestamp(), "exception_type": type(error).__name__,
                "error": str(error)[:200], "model_qualified": False, "public_release_approved": False}


def acquire_public_suite(root: Path):
    root = root.resolve()
    if root.drive.upper() != "D:":
        raise ValueError("D: workspace required")
    if shutil.disk_usage(root).free < 15 * 1024**3:
        raise ValueError("At least 15 GiB free space required")
    folder = contained(root, "data/private/public-suite/suite-" + uuid.uuid4().hex[:12])
    folder.mkdir(parents=True)
    sources = catalog()
    write_new(folder / "acquisition-start.json", {"started_at": timestamp(), "catalog": sources})
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(acquire_one, root, folder, source) for source in sources]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            write_new(folder / (result["source_id"] + "-receipt.json"), result)
            print(result["source_id"] + ": " + result["status"], flush=True)
    results.sort(key=lambda item: item["source_id"])
    failures = [item["source_id"] for item in results if item["status"] != "DOWNLOADED_AND_PROFILED"]
    receipt = {"schema_version": 1, "completed_at": timestamp(),
               "status": "COMPLETE" if not failures else "PARTIAL", "sources": results,
               "failed_sources": failures, "visibility": "private", "public_release_approved": False,
               "model_training_performed": False}
    write_new(folder / "acquisition-complete.json", receipt)
    return {"directory": str(folder), "status": receipt["status"], "sources": len(results),
            "downloaded": len(results) - len(failures), "failed_sources": failures}
