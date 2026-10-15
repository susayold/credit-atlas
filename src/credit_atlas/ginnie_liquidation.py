"""Aggregate-only structural audit for Ginnie Mae liquidation ZIP files."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


class GinnieLiquidationError(ValueError):
    """Raised when a Ginnie liquidation package violates its source contract."""


@dataclass(frozen=True)
class GinnieLiquidationAudit:
    source_file: str
    report_period: str
    generated_date: str
    liquidation_rows: int
    unique_loan_keys: int
    removal_reason_counts: dict[str, int]
    blank_amount_counts: dict[str, int]
    invalid_amount_counts: dict[str, int]
    negative_amount_counts: dict[str, int]
    member_name: str
    member_bytes: int
    member_sha256: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_PERIOD = re.compile(r"^\d{6}$")
_DATE = re.compile(r"^\d{8}$")
_REMOVAL_REASONS = {"1", "2", "3", "4", "5", "6"}
_AMOUNTS = {
    "original_principal_balance": 11,
    "unpaid_principal_balance": 12,
    "liquidation_balance": 13,
}


def _digest_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with archive.open(member, "r") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def audit_ginnie_liquidation_zip(
    zip_path: str | Path,
    *,
    terms_accepted: bool = False,
    member_name: str | None = None,
) -> GinnieLiquidationAudit:
    """Validate and summarize one liquidation file without returning loan IDs."""

    if terms_accepted is not True:
        raise GinnieLiquidationError(
            "Ginnie Mae loan-level Terms of Use must be accepted by the user "
            "before this payload is profiled"
        )

    path = Path(zip_path)
    if not path.is_file():
        raise GinnieLiquidationError("Ginnie liquidation ZIP does not exist")
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise GinnieLiquidationError("Input is not a valid ZIP archive") from exc

    with archive:
        members = [
            item
            for item in archive.infolist()
            if not item.is_dir() and not item.filename.startswith("__MACOSX/")
        ]
        if member_name is not None:
            members = [item for item in members if item.filename == member_name]
        if len(members) != 1:
            raise GinnieLiquidationError(
                "ZIP must contain exactly one selected liquidation data member"
            )
        member = members[0]
        if member.file_size == 0:
            raise GinnieLiquidationError("Ginnie liquidation data member is empty")

        counts: Counter[str] = Counter()
        reason_counts: Counter[str] = Counter()
        blank_amounts: Counter[str] = Counter()
        invalid_amounts: Counter[str] = Counter()
        negative_amounts: Counter[str] = Counter()
        seen_keys: set[tuple[str, str, str, str]] = set()
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
                        raise GinnieLiquidationError("Unexpected data after TT trailer")
                    kind = row[0]
                    expected_width = {"HH": 3, "LR": 15, "TT": 3}.get(kind)
                    if (
                        expected_width is not None
                        and len(row) == expected_width + 1
                        and row[-1] == ""
                    ):
                        row.pop()
                    counts[kind] += 1

                    if kind == "HH":
                        if line_number != 1 or header is not None:
                            raise GinnieLiquidationError("HH must be the first and only header")
                        if len(row) != 3:
                            raise GinnieLiquidationError("HH record must have 3 fields")
                        if not _PERIOD.fullmatch(row[1]) or not 1 <= int(row[1][4:6]) <= 12:
                            raise GinnieLiquidationError("HH report period must be YYYYMM")
                        if not _DATE.fullmatch(row[2]):
                            raise GinnieLiquidationError("HH generated date must be YYYYMMDD")
                        header = row
                        continue

                    if header is None:
                        raise GinnieLiquidationError("LR/TT record occurs before HH")

                    if kind == "LR":
                        if len(row) != 15:
                            raise GinnieLiquidationError(
                                f"LR record must have 15 fields; line {line_number} has {len(row)}"
                            )
                        cusip, pool_id, sequence = row[1], row[2], row[6]
                        if len(cusip) != 9 or len(pool_id) != 6 or not sequence:
                            raise GinnieLiquidationError("LR disclosure key width/value is invalid")
                        if not _PERIOD.fullmatch(row[8]) or not 1 <= int(row[8][4:6]) <= 12:
                            raise GinnieLiquidationError("LR report period must be YYYYMM")
                        if row[8] != header[1]:
                            raise GinnieLiquidationError("LR report period differs from HH")
                        key = (cusip, pool_id, sequence, row[8])
                        if key in seen_keys:
                            raise GinnieLiquidationError("Duplicate liquidation disclosure key")
                        seen_keys.add(key)

                        reason = row[14]
                        if reason not in _REMOVAL_REASONS:
                            raise GinnieLiquidationError("LR removal reason code is invalid")
                        reason_counts[reason] += 1

                        for label, index in _AMOUNTS.items():
                            value = row[index]
                            if not value:
                                blank_amounts[label] += 1
                                continue
                            try:
                                amount = Decimal(value)
                            except InvalidOperation:
                                invalid_amounts[label] += 1
                                continue
                            if not amount.is_finite():
                                invalid_amounts[label] += 1
                            elif amount < 0:
                                negative_amounts[label] += 1
                        continue

                    if kind == "TT":
                        if len(row) != 3:
                            raise GinnieLiquidationError("TT record must have 3 fields")
                        if row[1] != header[1]:
                            raise GinnieLiquidationError("TT report period differs from HH")
                        try:
                            expected_rows = int(row[2])
                        except ValueError as exc:
                            raise GinnieLiquidationError("TT loan count must be an integer") from exc
                        if expected_rows != counts["LR"]:
                            raise GinnieLiquidationError("TT loan count does not match LR rows")
                        trailer = row
                        saw_trailer = True
                        continue

                    raise GinnieLiquidationError(f"Unsupported record type {kind!r}")
        except (UnicodeDecodeError, csv.Error) as exc:
            raise GinnieLiquidationError(
                "Liquidation member is not valid UTF-8 pipe-delimited text"
            ) from exc

        if header is None or trailer is None:
            raise GinnieLiquidationError("File must have HH header and TT trailer")
        if counts["HH"] != 1 or counts["TT"] != 1:
            raise GinnieLiquidationError("File must contain one HH and one TT")

        return GinnieLiquidationAudit(
            source_file=path.name,
            report_period=header[1],
            generated_date=header[2],
            liquidation_rows=counts["LR"],
            unique_loan_keys=len(seen_keys),
            removal_reason_counts=dict(sorted(reason_counts.items())),
            blank_amount_counts=dict(sorted(blank_amounts.items())),
            invalid_amount_counts=dict(sorted(invalid_amounts.items())),
            negative_amount_counts=dict(sorted(negative_amounts.items())),
            member_name=member.filename,
            member_bytes=member.file_size,
            member_sha256=_digest_member(archive, member),
        )
