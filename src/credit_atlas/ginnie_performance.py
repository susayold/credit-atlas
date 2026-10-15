"""Private, source-specific structural audit for Ginnie Mae LoanPerf ZIP files.

This module intentionally returns aggregate diagnostics only.  It does not
materialize, export, or join loan-level records.  Callers must affirm that the
Ginnie Mae loan-level Terms of Use were accepted before profiling a payload.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


class GinnieLoanPerfError(ValueError):
    """Raised when a Ginnie LoanPerf package violates its source contract."""


@dataclass(frozen=True)
class GinnieLoanPerfAudit:
    source_file: str
    file_frequency: str
    catalog_report_period: str
    generated_date: str
    loan_period_rows: int
    distinct_loan_keys: int
    min_as_of_period: str | None
    max_as_of_period: str | None
    delinquency_status_counts: dict[str, int]
    removal_reason_counts: dict[str, int]
    blank_counts: dict[str, int]
    delinquency_history_counts: dict[str, int]
    member_name: str
    member_bytes: int
    member_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_PERIOD = re.compile(r"^\d{6}$")
_DATE = re.compile(r"^\d{8}$")
_HISTORY = re.compile(r"^(?:\d{2}|XX){0,24}$")
_FREQUENCY_PERIOD_LIMIT = {"Q": 3, "A": 12}
_REMOVAL_REASONS = {"1", "2", "3", "4", "5", "6"}


def _valid_period(value: str, label: str) -> str:
    value = value.strip()
    if not _PERIOD.fullmatch(value):
        raise GinnieLoanPerfError(f"{label} must be YYYYMM")
    month = int(value[4:6])
    if not 1 <= month <= 12:
        raise GinnieLoanPerfError(f"{label} has an invalid month")
    return value


def _month_number(value: str) -> int:
    return int(value[:4]) * 12 + int(value[4:6])


def _sha256_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    import hashlib

    digest = hashlib.sha256()
    with archive.open(member, "r") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def audit_ginnie_loanperf_zip(
    zip_path: str | Path,
    *,
    terms_accepted: bool = False,
    member_name: str | None = None,
) -> GinnieLoanPerfAudit:
    """Validate and profile a local Ginnie LoanPerf file without exposing IDs.

    ``terms_accepted`` must be set only after the user has personally accepted
    the publisher's current loan-level Terms of Use. The function never opens a
    network connection and never extracts the ZIP to disk.
    """

    if terms_accepted is not True:
        raise GinnieLoanPerfError(
            "Ginnie Mae loan-level Terms of Use must be accepted by the user "
            "before this payload is profiled"
        )

    path = Path(zip_path)
    if not path.is_file():
        raise GinnieLoanPerfError("LoanPerf ZIP does not exist")
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise GinnieLoanPerfError("Input is not a valid ZIP archive") from exc

    with archive:
        candidates = [
            info
            for info in archive.infolist()
            if not info.is_dir() and not info.filename.startswith("__MACOSX/")
        ]
        if member_name is not None:
            candidates = [item for item in candidates if item.filename == member_name]
        if len(candidates) != 1:
            raise GinnieLoanPerfError(
                "ZIP must contain exactly one selected LoanPerf data member"
            )
        member = candidates[0]
        if member.file_size == 0:
            raise GinnieLoanPerfError("LoanPerf data member is empty")

        status_counts: Counter[str] = Counter()
        removal_counts: Counter[str] = Counter()
        blank_counts: Counter[str] = Counter()
        history_counts: Counter[str] = Counter()
        seen_keys: set[tuple[str, str, str, str]] = set()
        loan_month_counts: Counter[tuple[str, str, str]] = Counter()
        periods: set[str] = set()
        record_types: Counter[str] = Counter()
        header: list[str] | None = None
        trailer: list[str] | None = None
        saw_trailer = False

        try:
            with archive.open(member, "r") as binary_stream:
                text_stream = io.TextIOWrapper(binary_stream, encoding="utf-8-sig", newline="")
                reader = csv.reader(text_stream, delimiter="|", quotechar='"')
                for line_number, raw_row in enumerate(reader, start=1):
                    row = [value.strip() for value in raw_row]
                    if not row or all(value == "" for value in row):
                        continue
                    if saw_trailer:
                        raise GinnieLoanPerfError("Unexpected data after TT trailer")
                    kind = row[0]
                    record_types[kind] += 1

                    if kind == "HH":
                        if line_number != 1 or header is not None:
                            raise GinnieLoanPerfError("HH must be the first and only header")
                        if len(row) != 4:
                            raise GinnieLoanPerfError("HH record must have 4 fields")
                        report_period = _valid_period(row[1], "HH report period")
                        frequency = row[2]
                        if frequency not in _FREQUENCY_PERIOD_LIMIT:
                            raise GinnieLoanPerfError("HH frequency must be Q or A")
                        if not _DATE.fullmatch(row[3]):
                            raise GinnieLoanPerfError("HH generated date must be YYYYMMDD")
                        header = row
                        continue

                    if header is None:
                        raise GinnieLoanPerfError("LP/TT record occurs before HH")

                    if kind == "LP":
                        if len(row) != 59:
                            raise GinnieLoanPerfError(
                                f"LP record must have 59 fields; line {line_number} has {len(row)}"
                            )
                        # Ginnie Mae's LP-02/03/07 are disclosure identifiers.
                        # Keep them in memory only for uniqueness checks; never
                        # include them in the returned audit.
                        cusip, pool_id, sequence = row[1], row[2], row[6]
                        if not cusip or not pool_id or not sequence:
                            raise GinnieLoanPerfError("LP disclosure key fields cannot be blank")
                        if len(cusip) != 9 or len(pool_id) != 6:
                            raise GinnieLoanPerfError("LP CUSIP/pool identifier width mismatch")
                        period = _valid_period(row[39], "LP as-of date")
                        if _month_number(period) > _month_number(report_period):
                            raise GinnieLoanPerfError("LP period exceeds HH report period")
                        key = (cusip, pool_id, sequence, period)
                        if key in seen_keys:
                            raise GinnieLoanPerfError("Duplicate loan-period disclosure key")
                        seen_keys.add(key)
                        loan_month_counts[(cusip, pool_id, sequence)] += 1
                        periods.add(period)

                        status = row[20]
                        if status:
                            if not status.isdigit() or int(status) > 6:
                                raise GinnieLoanPerfError("LP months-delinquent code is invalid")
                            status_counts[status] += 1
                        else:
                            blank_counts["months_delinquent"] += 1

                        removal = row[38]
                        if removal:
                            if removal not in _REMOVAL_REASONS:
                                raise GinnieLoanPerfError("LP removal-reason code is invalid")
                            removal_counts[removal] += 1
                        else:
                            removal_counts["blank"] += 1

                        for label, index in (
                            ("current_upb", 16),
                            ("ltv", 23),
                            ("total_debt_expense_ratio", 25),
                            ("credit_score", 26),
                            ("loan_origination_date", 40),
                        ):
                            if not row[index]:
                                blank_counts[label] += 1
                        history = row[58]
                        if history:
                            if not _HISTORY.fullmatch(history):
                                raise GinnieLoanPerfError(
                                    "LP-59 must contain up to 24 two-character statuses"
                                )
                            history_counts[str(len(history) // 2)] += 1
                        else:
                            history_counts["blank"] += 1
                        continue

                    if kind == "TT":
                        if len(row) != 3:
                            raise GinnieLoanPerfError("TT record must have 3 fields")
                        if row[1] != report_period:
                            raise GinnieLoanPerfError("TT report period differs from HH")
                        try:
                            expected_rows = int(row[2])
                        except ValueError as exc:
                            raise GinnieLoanPerfError("TT loan count must be an integer") from exc
                        if expected_rows != record_types["LP"]:
                            raise GinnieLoanPerfError("TT loan count does not match LP rows")
                        trailer = row
                        saw_trailer = True
                        continue

                    raise GinnieLoanPerfError(f"Unsupported record type {kind!r}")
        except (UnicodeDecodeError, csv.Error) as exc:
            raise GinnieLoanPerfError("LoanPerf member is not valid UTF-8 pipe-delimited text") from exc

        if header is None or trailer is None:
            raise GinnieLoanPerfError("LoanPerf file must have HH header and TT trailer")
        if record_types["HH"] != 1 or record_types["TT"] != 1:
            raise GinnieLoanPerfError("LoanPerf file must contain one HH and one TT")
        maximum_periods = _FREQUENCY_PERIOD_LIMIT[header[2]]
        if any(count > maximum_periods for count in loan_month_counts.values()):
            raise GinnieLoanPerfError("A disclosure key appears too many times for file frequency")

        return GinnieLoanPerfAudit(
            source_file=path.name,
            file_frequency=header[2],
            catalog_report_period=header[1],
            generated_date=header[3],
            loan_period_rows=record_types["LP"],
            distinct_loan_keys=len(loan_month_counts),
            min_as_of_period=min(periods) if periods else None,
            max_as_of_period=max(periods) if periods else None,
            delinquency_status_counts=dict(sorted(status_counts.items())),
            removal_reason_counts=dict(sorted(removal_counts.items())),
            blank_counts=dict(sorted(blank_counts.items())),
            delinquency_history_counts=dict(sorted(history_counts.items())),
            member_name=member.filename,
            member_bytes=member.file_size,
            member_sha256=_sha256_member(archive, member),
        )
