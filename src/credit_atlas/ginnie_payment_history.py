"""Aggregate-only audit for Ginnie Mae monthly loan payment-history files."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from contextlib import ExitStack
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


class GinniePaymentHistoryError(ValueError):
    """Raised when a payment-history source file violates its layout contract."""


@dataclass(frozen=True)
class GinniePaymentHistoryAudit:
    source_file: str
    report_period: str
    generated_date: str
    pool_count: int
    loan_count: int
    record_count: int
    delinquency_code_counts: dict[str, int]
    history_length_counts: dict[int, int]
    current_status_counts: dict[str, int]
    missing_history_occurrences: int
    pool_count_reconciles: bool
    loan_count_reconciles: bool
    record_count_reconciles: bool
    file_bytes: int
    member_name: str
    member_bytes: int
    file_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_PERIOD = re.compile(r"^\d{6}$")
_DATE = re.compile(r"^\d{8}$")
_CODE = re.compile(r"^(?:\d{2}|XX)$")
_WIDTHS = {"HH": 3, "PH": 8, "LL": 5, "PT": 9, "TT": 6}


def _valid_period(value: str) -> bool:
    return bool(_PERIOD.fullmatch(value)) and 1 <= int(value[4:6]) <= 12


def audit_ginnie_payment_history(
    file_path: str | Path,
    *,
    terms_accepted: bool = False,
) -> GinniePaymentHistoryAudit:
    """Validate one local Ginnie payment-history text file without retaining keys."""

    if terms_accepted is not True:
        raise GinniePaymentHistoryError(
            "Ginnie Mae loan-level Terms of Use must be accepted by the user "
            "before this payload is profiled"
        )

    path = Path(file_path)
    if not path.is_file():
        raise GinniePaymentHistoryError("Ginnie payment-history file does not exist")

    file_bytes = path.stat().st_size
    member_name = path.name
    member_bytes = file_bytes
    digest = hashlib.sha256()
    is_zip = zipfile.is_zipfile(path)
    if is_zip:
        try:
            with zipfile.ZipFile(path) as archive:
                members = [item for item in archive.infolist() if not item.is_dir()]
                if len(members) != 1:
                    raise GinniePaymentHistoryError(
                        "ZIP must contain exactly one payment-history data member"
                    )
                member = members[0]
                member_name = member.filename
                member_bytes = member.file_size
                with archive.open(member, "r") as binary_stream:
                    while chunk := binary_stream.read(1024 * 1024):
                        digest.update(chunk)
        except zipfile.BadZipFile as exc:
            raise GinniePaymentHistoryError("Input is not a valid ZIP archive") from exc
    else:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)

    record_counts: Counter[str] = Counter()
    delinquency_counts: Counter[str] = Counter()
    history_lengths: Counter[int] = Counter()
    current_status: Counter[str] = Counter()
    missing_occurrences = 0
    pool_count = 0
    loan_count = 0
    pool_loan_counts: dict[tuple[str, str], int] = {}
    pool_meta: dict[tuple[str, str], tuple[str, ...]] = {}
    header: list[str] | None = None
    trailer: list[str] | None = None
    active_pool: tuple[str, str] | None = None
    last_pool_id: str | None = None
    last_sequence: str | None = None
    saw_trailer = False
    previous_kind: str | None = None
    actual_records = 0

    try:
        with ExitStack() as stack:
            if is_zip:
                archive = stack.enter_context(zipfile.ZipFile(path))
                binary_stream = stack.enter_context(archive.open(member_name, "r"))
                text_stream = io.TextIOWrapper(
                    binary_stream, encoding="utf-8-sig", newline=""
                )
                stack.callback(text_stream.close)
            else:
                text_stream = stack.enter_context(
                    path.open("r", encoding="utf-8-sig", newline="")
                )
            reader = csv.reader(text_stream, delimiter="|", quotechar='"')
            for line_number, raw_row in enumerate(reader, start=1):
                row = [value.strip() for value in raw_row]
                if not row or all(value == "" for value in row):
                    continue
                if saw_trailer:
                    raise GinniePaymentHistoryError("Unexpected data after TT trailer")
                kind = row[0]
                if kind not in _WIDTHS:
                    raise GinniePaymentHistoryError(f"Unsupported record type {kind!r}")
                if len(row) == _WIDTHS[kind] + 1 and row[-1] == "":
                    row.pop()
                if len(row) != _WIDTHS[kind]:
                    raise GinniePaymentHistoryError(
                        f"{kind} record has invalid field count at line {line_number}"
                    )
                record_counts[kind] += 1
                actual_records += 1

                if kind == "HH":
                    if line_number != 1 or header is not None:
                        raise GinniePaymentHistoryError("HH must be the first and only header")
                    if not _valid_period(row[1]) or not _DATE.fullmatch(row[2]):
                        raise GinniePaymentHistoryError("HH period/date format is invalid")
                    header = row
                    previous_kind = kind
                    continue

                if header is None:
                    raise GinniePaymentHistoryError("Record occurs before HH header")

                if kind == "PH":
                    if active_pool is not None:
                        raise GinniePaymentHistoryError("PH encountered before prior PT trailer")
                    pool_id = row[2]
                    if not pool_id or len(pool_id) != 6:
                        raise GinniePaymentHistoryError("PH pool identifier is invalid")
                    if row[3] not in {"X", "C", "M"}:
                        raise GinniePaymentHistoryError("PH pool indicator is invalid")
                    if not re.fullmatch(r"\d{8}", row[5]) or not _valid_period(row[7]):
                        raise GinniePaymentHistoryError("PH date/period format is invalid")
                    if row[7] != header[1]:
                        raise GinniePaymentHistoryError("PH report period differs from HH")
                    key = (row[1], pool_id)
                    if last_pool_id is not None and pool_id <= last_pool_id:
                        raise GinniePaymentHistoryError("Pool records are not sorted ascending")
                    pool_count += 1
                    pool_meta[key] = tuple(row[1:8])
                    pool_loan_counts[key] = 0
                    active_pool = key
                    last_pool_id = pool_id
                    last_sequence = None
                    previous_kind = kind
                    continue

                if kind == "LL":
                    if active_pool is None:
                        raise GinniePaymentHistoryError("LL record occurs outside a PH/PT pool")
                    pool_id, sequence, issuer, packed = row[1:]
                    if pool_id != active_pool[1] or not re.fullmatch(r"\d{10}", sequence):
                        raise GinniePaymentHistoryError("LL pool/sequence key is invalid")
                    if issuer and not re.fullmatch(r"\d{4}", issuer):
                        raise GinniePaymentHistoryError("LL issuer identifier format is invalid")
                    if not packed or len(packed) > 48 or len(packed) % 2:
                        raise GinniePaymentHistoryError("LL history must contain 1–24 two-character periods")
                    if last_sequence is not None and sequence <= last_sequence:
                        raise GinniePaymentHistoryError("LL disclosure sequence is not ascending")
                    loan_count += 1
                    last_sequence = sequence
                    statuses = [packed[pos : pos + 2] for pos in range(0, len(packed), 2)]
                    if any(not _CODE.fullmatch(status) for status in statuses):
                        raise GinniePaymentHistoryError("LL history contains an invalid status code")
                    for status in statuses:
                        delinquency_counts[status] += 1
                    history_lengths[len(statuses)] += 1
                    current_status[statuses[0]] += 1
                    missing_occurrences += statuses.count("XX")
                    pool_loan_counts[active_pool] += 1
                    previous_kind = kind
                    continue

                if kind == "PT":
                    if active_pool is None:
                        raise GinniePaymentHistoryError("PT record occurs without a PH record")
                    pool_id = row[2]
                    key = (row[1], pool_id)
                    if key != active_pool:
                        raise GinniePaymentHistoryError("PT pool key differs from PH")
                    if tuple(row[1:8]) != pool_meta[key]:
                        raise GinniePaymentHistoryError("PT pool metadata differs from PH")
                    if row[7] != header[1] or not row[8].isdigit():
                        raise GinniePaymentHistoryError("PT period/count format is invalid")
                    if int(row[8]) != pool_loan_counts[key]:
                        raise GinniePaymentHistoryError("PT loan count does not match LL rows")
                    active_pool = None
                    previous_kind = kind
                    continue

                if kind == "TT":
                    if active_pool is not None:
                        raise GinniePaymentHistoryError("TT encountered before final PT trailer")
                    if previous_kind not in {"PT", "PH"}:
                        raise GinniePaymentHistoryError("TT must follow a pool trailer")
                    if not _valid_period(row[1]) or not _DATE.fullmatch(row[2]):
                        raise GinniePaymentHistoryError("TT period/date format is invalid")
                    if row[1] != header[1] or row[2] != header[2]:
                        raise GinniePaymentHistoryError("TT period/date differs from HH")
                    if any(not value.isdigit() for value in row[3:]):
                        raise GinniePaymentHistoryError("TT totals must be integers")
                    trailer = row
                    saw_trailer = True
                    previous_kind = kind
    except (UnicodeDecodeError, csv.Error) as exc:
        raise GinniePaymentHistoryError("File is not valid UTF-8 pipe-delimited text") from exc

    if header is None or trailer is None:
        raise GinniePaymentHistoryError("File must contain one HH header and one TT trailer")
    if record_counts["HH"] != 1 or record_counts["TT"] != 1:
        raise GinniePaymentHistoryError("File must contain exactly one HH and one TT")
    if record_counts["PH"] != record_counts["PT"] or active_pool is not None:
        raise GinniePaymentHistoryError("Every PH pool must have exactly one PT trailer")

    declared_pools, declared_loans, declared_records = map(int, trailer[3:6])
    return GinniePaymentHistoryAudit(
        source_file=path.name,
        report_period=header[1],
        generated_date=header[2],
        pool_count=pool_count,
        loan_count=loan_count,
        record_count=actual_records,
        delinquency_code_counts=dict(sorted(delinquency_counts.items())),
        history_length_counts=dict(sorted(history_lengths.items())),
        current_status_counts=dict(sorted(current_status.items())),
        missing_history_occurrences=missing_occurrences,
        pool_count_reconciles=declared_pools == pool_count,
        loan_count_reconciles=declared_loans == loan_count,
        record_count_reconciles=declared_records == actual_records,
        file_bytes=file_bytes,
        member_name=member_name,
        member_bytes=member_bytes,
        file_sha256=digest.hexdigest(),
    )
