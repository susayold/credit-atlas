"""Query and export receipt-verified FHFA NMDB performance by geography."""
from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

from .nmdb_aggregate import SERIES, SOURCE_URL, read as aggregate_read
from .workspace import sha256


INDEX_URL = "https://www.fhfa.gov/data/nmdb"
EXPECTED_COLUMNS = [
    "SOURCE", "FREQUENCY", "GEOLEVEL", "GEOID", "GEONAME", "MARKET",
    "PERIOD", "YEAR", "QUARTER", "MONTH", "SUPPRESSED", "SERIESID", "VALUE1",
]
GEO_LEVELS = (
    "National", "Rural/Non-Rural", "Census Region", "Census Division", "State", "Metro",
)
MARKETS = (
    "All Mortgages", "Enterprise Acquisitions",
    "Government / Non-Conventional", "Other Conventional Market",
)
SERIES_IDS = tuple(SERIES)
PERIODS = tuple(
    f"{year}Q{quarter}"
    for year in range(2002, 2027)
    for quarter in range(1, 5)
    if (year, quarter) <= (2026, 2)
)
MAX_SELECTED_ROWS = 5_000


@contextmanager
def _open_zip(archive_path):
    """Open local archives normally and Drive archives through bounded range reads."""
    open_seekable = getattr(archive_path, "open_seekable", None)
    if callable(open_seekable):
        with open_seekable() as stream:
            with zipfile.ZipFile(stream) as archive:
                yield archive
    else:
        with zipfile.ZipFile(archive_path) as archive:
            yield archive


def _filters(query: dict | None) -> dict[str, str]:
    query = query or {}
    allowed = {"geo_level", "geo_id", "market", "series_id", "period"}
    unknown = set(query) - allowed
    if unknown:
        raise ValueError("Unsupported NMDB geography filter: " + ", ".join(sorted(unknown)))
    result = {
        "geo_level": str(query.get("geo_level") or "National"),
        "geo_id": str(query.get("geo_id") or "USA"),
        "market": str(query.get("market") or "All Mortgages"),
        "series_id": str(query.get("series_id") or "all"),
        "period": str(query.get("period") or "all"),
    }
    if result["geo_level"] not in GEO_LEVELS:
        raise ValueError("Select one FHFA geography level from the published source.")
    if result["market"] not in {"all", *MARKETS}:
        raise ValueError("Select one published FHFA mortgage market or all markets.")
    if result["series_id"] not in {"all", *SERIES_IDS}:
        raise ValueError("Select one published FHFA performance series or all series.")
    if result["period"] not in {"all", *PERIODS}:
        raise ValueError("Select a published quarter between 2002Q1 and 2026Q2, or all quarters.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,24}|all", result["geo_id"]):
        raise ValueError("Geography ID must be a source ID or all.")
    return result


def _full_package(root: Path, expected_sha: str) -> tuple[Path, dict]:
    folders = sorted(
        (root / "data" / "private" / "public-context").glob("fhfa-nmdb-performance-*"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for folder in folders:
        receipt_path = folder / "receipt.json"
        profile_path = folder / "profile.json"
        archive_path = folder / "official-performance-quarterly.zip"
        if not (receipt_path.is_file() and profile_path.is_file() and archive_path.is_file()):
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (receipt.get("status") != "PASS"
                or receipt.get("download", {}).get("requested_url") != SOURCE_URL
                or receipt.get("download", {}).get("sha256") != expected_sha):
            continue
        if sha256(profile_path) != receipt.get("profile_sha256"):
            raise ValueError("FHFA NMDB profile differs from its acquisition receipt")
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if sha256(archive_path) != expected_sha:
            raise ValueError("FHFA NMDB archive differs from its acquisition receipt")
        return archive_path, profile
    raise ValueError("Receipt-verified full-geography FHFA NMDB package was not found")


def report(root: Path, query: dict | None = None) -> dict:
    """Return a bounded, source-filtered extract without pooling geographies."""
    filters = _filters(query)
    source = aggregate_read(root)
    if source.get("status") != "AVAILABLE" or source.get("source_url") != SOURCE_URL:
        return {
            "status": "UNAVAILABLE",
            "available": False,
            "reason": "This checkout has a receipt-verified national fallback only; the full-geography ZIP is not present.",
            "source_page": source.get("source_page", INDEX_URL),
            "filters": filters,
        }

    archive_path, profile = _full_package(root, source["quality"]["archive_sha256"])
    geographies: dict[str, dict[str, str]] = {level: {} for level in GEO_LEVELS}
    geo_counts: Counter[str] = Counter()
    market_counts: Counter[str] = Counter()
    series_counts: Counter[str] = Counter()
    suppression_counts: Counter[str] = Counter()
    blank_counts: Counter[str] = Counter()
    selected: list[dict] = []
    row_count = 0
    quarter_rank = {period: index for index, period in enumerate(PERIODS)}

    with _open_zip(archive_path) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        csv_members = [member for member in members if member.filename.lower().endswith(".csv")]
        if len(members) != 1 or len(csv_members) != 1 or csv_members[0].filename != profile.get("member"):
            raise ValueError("FHFA NMDB archive must contain the receipt-profiled CSV only")
        with archive.open(csv_members[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            if reader.fieldnames != EXPECTED_COLUMNS:
                raise ValueError("Unexpected FHFA NMDB full-geography schema")
            for raw_row in reader:
                if None in raw_row or any(value is None for value in raw_row.values()):
                    raise ValueError("Malformed FHFA NMDB row width")
                if raw_row["SOURCE"] != "NMDB" or raw_row["FREQUENCY"] != "Quarterly":
                    raise ValueError("Unexpected FHFA source or frequency")
                level, geo_id, geo_name = raw_row["GEOLEVEL"], raw_row["GEOID"], raw_row["GEONAME"]
                market, series_id, period = raw_row["MARKET"], raw_row["SERIESID"], raw_row["PERIOD"]
                if level not in geographies or not geo_id or not geo_name:
                    raise ValueError("Unknown or blank FHFA geography identity")
                if market not in MARKETS or series_id not in SERIES:
                    raise ValueError("Unknown FHFA market or performance series")
                if period not in quarter_rank or not re.fullmatch(r"\d{4}Q[1-4]", period):
                    raise ValueError("Invalid FHFA quarterly period")
                try:
                    year, quarter = int(raw_row["YEAR"]), int(raw_row["QUARTER"])
                    suppressed = int(raw_row["SUPPRESSED"])
                except ValueError as error:
                    raise ValueError("Invalid FHFA year, quarter or suppression value") from error
                if (period != f"{year}Q{quarter}" or not 1 <= quarter <= 4
                        or suppressed not in (0, 1)):
                    raise ValueError("FHFA period or suppression fields do not reconcile")
                prior_name = geographies[level].setdefault(geo_id, geo_name)
                if prior_name != geo_name:
                    raise ValueError(f"FHFA geography name changed within {level} · {geo_id}")
                value_text = raw_row["VALUE1"]
                if value_text in ("", "."):
                    value = None
                    blank_counts["VALUE1"] += 1
                    if not (suppressed or (series_id == "PFORB" and period < "2019Q4")):
                        raise ValueError("Unexpected unsuppressed FHFA blank value")
                else:
                    try:
                        value = float(value_text)
                    except ValueError as error:
                        raise ValueError("Non-numeric FHFA performance percentage") from error
                    if not 0 <= value <= 100 or suppressed:
                        raise ValueError("FHFA percentage is outside range or suppressed value is exposed")

                row_count += 1
                geo_counts[level] += 1
                market_counts[market] += 1
                series_counts[series_id] += 1
                suppression_counts[str(suppressed)] += 1
                if (level != filters["geo_level"]
                        or (filters["geo_id"] != "all" and geo_id != filters["geo_id"])
                        or (filters["market"] != "all" and market != filters["market"])
                        or (filters["series_id"] != "all" and series_id != filters["series_id"])
                        or (filters["period"] != "all" and period != filters["period"])):
                    continue
                selected.append({
                    "geography_level": level,
                    "geography_id": geo_id,
                    "geography_name": geo_name,
                    "period": period,
                    "year": year,
                    "quarter": quarter,
                    "market": market,
                    "series_id": series_id,
                    "series_label": SERIES[series_id]["label"],
                    "value_pct": value,
                    "suppressed": bool(suppressed),
                    "value_state": (
                        "suppressed" if suppressed else
                        "unavailable_before_series_start" if value is None else
                        "reported"
                    ),
                })
                if len(selected) > MAX_SELECTED_ROWS:
                    raise ValueError(
                        f"Filters return more than {MAX_SELECTED_ROWS:,} rows. Select a geography, market, series or quarter."
                    )

    if row_count != profile.get("rows") or profile.get("unique_aggregate_keys") != row_count:
        raise ValueError("FHFA NMDB runtime rows do not reconcile to the source profile")
    if (dict(geo_counts) != profile.get("geography_level_row_counts")
            or dict(market_counts) != profile.get("market_row_counts")
            or dict(series_counts) != profile.get("series_row_counts")
            or dict(suppression_counts) != profile.get("suppression_row_counts")
            or dict(blank_counts) != profile.get("blank_or_dot_value_counts")):
        raise ValueError("FHFA NMDB runtime coverage differs from the receipt-bound profile")
    level_geos = geographies[filters["geo_level"]]
    if filters["geo_id"] != "all" and filters["geo_id"] not in level_geos:
        raise ValueError("Geography ID is not present at the selected FHFA level")
    if not selected:
        raise ValueError("No FHFA NMDB rows match the selected filters")
    selected.sort(key=lambda row: (
        quarter_rank[row["period"]], row["geography_name"], row["market"], row["series_id"]
    ))
    unavailable = sum(row["value_pct"] is None for row in selected)
    suppressed = sum(row["suppressed"] for row in selected)
    return {
        "status": "AVAILABLE",
        "available": True,
        "dataset": source["dataset"],
        "source": {
            "publisher": "Federal Housing Finance Agency",
            "source_page": source["source_page"],
            "source_url": source["source_url"],
            "release_date": source["source_release_date"],
            "retrieved_at": source["retrieved_at"],
            "archive_sha256": source["quality"]["archive_sha256"],
            "selected_csv_sha256": profile["csv_sha256"],
            "data_through": PERIODS[-1],
        },
        "filters": filters,
        "filter_options": {
            "geography_levels": list(GEO_LEVELS),
            "geographies": [
                {"geo_id": geo_id, "geo_name": name}
                for geo_id, name in sorted(level_geos.items(), key=lambda item: item[1].casefold())
            ],
            "markets": list(MARKETS),
            "series": [{"series_id": code, **SERIES[code]} for code in SERIES_IDS],
            "periods": list(PERIODS),
        },
        "coverage": {
            "source_rows": row_count,
            "source_geographies": len(level_geos),
            "selected_rows": len(selected),
            "reported_values": len(selected) - unavailable,
            "unavailable_values": unavailable,
            "suppressed_values": suppressed,
            "suppressed_values_overlap_unavailable": True,
            "selection_limit": MAX_SELECTED_ROWS,
        },
        "rows": selected,
        "definitions": {
            "denominator": "FHFA-reported active-mortgage estimate at quarter end; not a loan-level or cohort denominator.",
            "value_pct": "Source-reported percent on a 0–100 scale; no rescaling, aggregation, imputation or forecast is applied.",
            "suppression": "SUPPRESSED=1 is unavailable (FHFA uses this flag for cells with fewer than 3 loan records); it overlaps unavailable count.",
            "forbearance": "PFORB starts in 2019Q4; earlier source blanks are unavailable, not zero.",
            "preliminary": "The two latest quarters, including 2026Q1 and 2026Q2, are preliminary and may be revised.",
        },
        "limitations": [
            "NMDB aggregates are market context, not a borrower-level panel, Freddie cohort or fixed-horizon PD.",
            "Geography and mortgage-market rows are separate published estimates; do not sum overlapping categories or infer a pooled rate.",
            "Blank and suppressed values remain unavailable; no forecast or imputation is applied.",
            "The source is a latest-revised snapshot, not a point-in-time historical release series.",
        ],
    }


def workbook_bytes(result: dict) -> bytes:
    """Create a query-scoped Excel workbook while preserving blanks and suppression."""
    if not result.get("available"):
        raise ValueError(result.get("reason", "Full-geography NMDB data is unavailable"))
    if len(result["rows"]) > MAX_SELECTED_ROWS:
        raise ValueError("Selected NMDB extract exceeds the workbook bound")

    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.table import Table, TableStyleInfo
    from openpyxl.utils import get_column_letter

    navy = "243B53"
    book = Workbook()
    start = book.active
    start.title = "Start Here"
    filters = result["filters"]
    source = result["source"]
    coverage = result["coverage"]
    info = [
        ["CreditAtlas · FHFA NMDB all-geography performance", ""],
        ["Selected geography", filters["geo_level"] + " · " + ("All in level" if filters["geo_id"] == "all" else filters["geo_id"])],
        ["Selected mortgage market", filters["market"]],
        ["Selected series", filters["series_id"]],
        ["Selected quarter", filters["period"]],
        ["Rows in filtered extract", coverage["selected_rows"]],
        ["Source rows in official package", coverage["source_rows"]],
        ["Unavailable values", coverage["unavailable_values"]],
        ["Suppressed values", coverage["suppressed_values"]],
        ["FHFA release / data through", source["release_date"] + " / " + source["data_through"]],
        ["Retrieved at (UTC)", source["retrieved_at"]],
        ["Source archive SHA-256", source["archive_sha256"]],
        ["Source CSV SHA-256", source["selected_csv_sha256"]],
        ["Method", result["definitions"]["denominator"]],
        ["Missing and suppression", "Blank/dot values stay blank. Suppressed rows remain flagged and are not zero-filled."],
        ["Interpretation", "Aggregate performance context only; not loan-level PD, default incidence or model validation."],
        ["FHFA source page", source["source_page"]],
        ["FHFA technical notes", "https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf"],
    ]
    for row in info:
        start.append(row)
    start.merge_cells("A1:B1")
    start["A1"].fill = PatternFill("solid", fgColor=navy)
    start["A1"].font = Font(name="Aptos Display", size=16, bold=True, color="FFFFFF")
    start["A1"].alignment = Alignment(vertical="center")
    start.row_dimensions[1].height = 34
    start.column_dimensions["A"].width = 30
    start.column_dimensions["B"].width = 112
    for row in start.iter_rows(min_row=2):
        row[0].font = Font(name="Aptos", bold=True, color=navy)
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for index in range(2, len(info) + 1):
        start.row_dimensions[index].height = 34
    for cell in (start["B17"], start["B18"]):
        cell.hyperlink = cell.value
        cell.style = "Hyperlink"
    start.freeze_panes = "A2"

    detail = book.create_sheet("Selected data")
    detail.sheet_view.showGridLines = False
    headers = [
        "Geography level", "Geography ID", "Geography name", "Period", "Year", "Quarter",
        "Mortgage market", "Series ID", "Series label", "Source value (%)", "Suppressed", "Value state",
    ]
    detail.append(headers)
    for row in result["rows"]:
        detail.append([
            row["geography_level"], row["geography_id"], row["geography_name"], row["period"],
            row["year"], row["quarter"], row["market"], row["series_id"], row["series_label"],
            row["value_pct"], "Yes" if row["suppressed"] else "No", row["value_state"],
        ])
    table = Table(displayName="NMDBGeographySelection", ref=f"A1:L{detail.max_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
    detail.add_table(table)
    detail.freeze_panes = "A2"
    for cell in detail[1]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    detail.row_dimensions[1].height = 36
    for index, width in enumerate([20, 14, 32, 13, 10, 10, 36, 14, 42, 18, 14, 34], start=1):
        detail.column_dimensions[get_column_letter(index)].width = width
    for cell in detail["J"][1:]:
        cell.number_format = '0.0"%"'
    for row in detail.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    definitions = book.create_sheet("Definitions")
    definitions.append(["Field / concept", "Definition"])
    definition_rows = [
        ["Geography", "Use GEOLEVEL + GEOID + GEONAME together. Geography levels and markets are separately published dimensions."],
        ["Mortgage market", "FHFA market/submarket category. Do not sum All Mortgages with its components."],
        ["Performance states", "P3089DL = 30–89 DPD; P90DL = 90+ DPD; PFORECL = foreclosure/bankruptcy/deed-in-lieu; PFORB = forbearance."],
        ["Denominator", result["definitions"]["denominator"]],
        ["Source values", result["definitions"]["value_pct"]],
        ["Suppression", result["definitions"]["suppression"]],
        ["Forbearance", result["definitions"]["forbearance"]],
        ["Preliminary", result["definitions"]["preliminary"]],
    ]
    for row in definition_rows:
        definitions.append(row)
    definitions.freeze_panes = "A2"
    definitions.column_dimensions["A"].width = 26
    definitions.column_dimensions["B"].width = 112
    for cell in definitions[1]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(bold=True, color="FFFFFF")
    for row in definitions.iter_rows(min_row=2):
        row[0].font = Font(bold=True, color=navy)
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for index in range(2, definitions.max_row + 1):
        definitions.row_dimensions[index].height = 40

    quality = book.create_sheet("Quality & lineage")
    for row in [
        ["Check", "Result"],
        ["Filtered rows", coverage["selected_rows"]],
        ["Source package rows", coverage["source_rows"]],
        ["Reported values", coverage["reported_values"]],
        ["Unavailable values", coverage["unavailable_values"]],
        ["Suppressed values (overlaps unavailable)", coverage["suppressed_values"]],
        ["Selection row bound", coverage["selection_limit"]],
        ["Forecast / imputation / pooling", "None"],
        ["Archive SHA-256", source["archive_sha256"]],
        ["CSV SHA-256", source["selected_csv_sha256"]],
        ["Source page", source["source_page"]],
    ]:
        quality.append(row)
    quality.column_dimensions["A"].width = 42
    quality.column_dimensions["B"].width = 112
    for cell in quality[1]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(bold=True, color="FFFFFF")
    for row in quality.iter_rows(min_row=2):
        row[0].font = Font(bold=True, color=navy)
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for sheet in book.worksheets:
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
    output = BytesIO()
    book.save(output)
    return output.getvalue()
