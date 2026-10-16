"""Query the private, receipt-bound FHFA NMDB new/outstanding aggregate mart."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import duckdb

from .workspace import sha256

SOURCE_PAGE = "https://www.fhfa.gov/data/nmdb"
DICTIONARY_URL = "https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes"
MART_RELATIVE = Path("data/derived/fhfa-nmdb-market-statistics/market-statistics.parquet")
RECEIPT_RELATIVE = Path("data/derived/fhfa-nmdb-market-statistics/receipt.json")

PRODUCTS = {
    "new_annual": {
        "label": "New residential mortgages · annual",
        "kind": "origination_flow",
        "frequency": "Annual",
        "period_label": "Year",
        "first_year": 1998,
        "last_year": 2025,
        "definition": "New originations initially funded, classified by account opening date.",
        "value2_definition": "Weighted by the origination loan amount.",
        "source_file": "nmdb-new-mortgage-statistics-all-annual.zip",
        "profile_file": "new_annual-profile.json",
    },
    "outstanding_quarterly": {
        "label": "Outstanding residential mortgages · quarterly",
        "kind": "quarter_end_stock",
        "frequency": "Quarterly",
        "period_label": "Quarter",
        "first_year": 2013,
        "last_year": 2026,
        "definition": "Mortgages active at the end of each calendar quarter; stock changes through originations, payoffs and other terminations.",
        "value2_definition": "Weighted by unpaid principal balance (UPB) at quarter end.",
        "source_file": "nmdb-outstanding-mortgage-statistics-all-quarterly.zip",
        "profile_file": "outstanding_quarterly-profile.json",
    },
}

# Labels and concise definitions transcribed from FHFA Appendices B and C.
# Unit labels retain the publisher's scale; no currency/unit conversion occurs here.
NEW_SERIES = {
    "TOT_ORIG": ("Number of originations", "1,000 mortgages", "Count of funded originations; VALUE1 only."),
    "TOT_LOANAMT": ("Origination volume", "USD million", "Total original loan volume; VALUE1 only."),
    "AVE_LOANAMT": ("Average loan amount", "USD thousand", "Average origination loan amount, rounded to nearest USD 1,000."),
    "AVE_PAYMENT": ("Average initial required payment", "USD / month", "Average initial required payment after origination, rounded to nearest dollar."),
    "AVE_PROPVAL": ("Average purchase price / appraised value", "USD thousand", "Average purchase price or appraised property value, rounded to nearest USD 1,000."),
    "AVE_INTRATE": ("Average contract interest rate", "%", "Contract interest rate at origination."),
    "PCT_OWNOCC": ("Owner-occupied share", "%", "Share of originations secured by owner-occupied property."),
    "PCT_FTHB": ("First-time homebuyer share", "%", "Home-purchase loans where any borrower is a first-time homebuyer under FHFA's prior-mortgage definition."),
    "PCT_REPEATHB": ("Repeat homebuyer share", "%", "Home-purchase loans where none of the borrowers is a first-time homebuyer."),
    "PCT_HP": ("Home-purchase share", "%", "Loans whose purpose is to purchase a home."),
    "PCT_CASHOUT": ("Cash-out refinance share", "%", "Refinances classified as cash-out under FHFA's lien-balance definition."),
    "PCT_OTH_REFI": ("Rate-and-term refinance share", "%", "Refinances that are not cash-out and take advantage of rates and/or term."),
    "PCT_REFI": ("Refinance share", "%", "Loans whose purpose is to refinance an existing mortgage."),
    "AVE_TERM": ("Average term to maturity", "years", "Term to maturity at origination."),
    "PCT_ARM": ("Adjustable-rate mortgage share", "%", "Originations that are adjustable-rate mortgages."),
    "PCT_TERM_FRM_15": ("Fixed-rate term ≤15 years share", "%", "Fixed-rate mortgages with term to maturity at or below 15 years."),
    "PCT_TERM_FRM_30": ("Fixed-rate term >15 years share", "%", "Fixed-rate mortgages with term to maturity over 15 years."),
    "AVE_DTI": ("Average back-end DTI", "%", "Average back-end debt-to-income ratio."),
    "PCT_DTI_LE36": ("Back-end DTI ≤36% share", "%", "Share with debt-to-income ratio at or below 36%."),
    "PCT_DTI_3743": ("Back-end DTI 36.1–43% share", "%", "Share with debt-to-income ratio from 36.1% through 43%."),
    "PCT_DTI_GE44": ("Back-end DTI >43% share", "%", "Share with debt-to-income ratio above 43%."),
    "AVE_VANTAGESCR": ("Average borrower VantageScore", "score points", "Average VantageScore 3.0 across borrowers."),
    "PCT_VS_VERYPOOR": ("Very poor score share", "%", "Average borrower VantageScore from 300 to 499."),
    "PCT_VS_POOR": ("Poor score share", "%", "Average borrower VantageScore from 500 to 600."),
    "PCT_VS_FAIR": ("Fair score share", "%", "Average borrower VantageScore from 601 to 660."),
    "PCT_VS_GOOD": ("Good score share", "%", "Average borrower VantageScore from 661 to 780."),
    "PCT_VS_EXCELLENT": ("Excellent score share", "%", "Average borrower VantageScore from 781 to 850."),
    "AVE_LTV": ("Average first-lien LTV", "%", "Loan-to-value based on the first-lien mortgage."),
    "AVE_CLTV": ("Average combined LTV", "%", "Combined LTV based on the first lien and contemporaneous subordinate liens."),
    "PCT_CLTV_LE70": ("CLTV ≤70% share", "%", "Combined loan-to-value at or below 70%."),
    "PCT_CLTV_7080": ("CLTV 70.1–80% share", "%", "Combined loan-to-value between 70% and 80%."),
    "PCT_CLTV_8090": ("CLTV 80.1–90% share", "%", "Combined loan-to-value between 80% and 90%."),
    "PCT_CLTV_9095": ("CLTV 90.1–95% share", "%", "Combined loan-to-value between 90% and 95%."),
    "PCT_CLTV_9597": ("CLTV 95.1–97% share", "%", "Combined loan-to-value between 95% and 97%."),
    "PCT_CLTV_GT97": ("CLTV >97% share", "%", "Combined loan-to-value above 97%."),
    "PCT_GOVERNMENT": ("Government market share", "%", "Government-insured, guaranteed or direct loans."),
    "PCT_ENTERPRISE": ("Enterprise market share", "%", "Non-government loans acquired by Fannie Mae or Freddie Mac."),
    "PCT_OTHERCONFORMING": ("Other-conforming market share", "%", "Non-government, non-enterprise conforming loans."),
    "PCT_NONCONFORMING": ("Jumbo market share", "%", "Loans above the applicable FHFA conforming loan limit."),
    "PCT_WHT": ("All borrowers White alone share", "%", "All borrowers on the loan are White alone."),
    "PCT_BLK": ("All borrowers Black or African American alone share", "%", "All borrowers on the loan are Black or African American alone."),
    "PCT_ASN": ("All borrowers Asian alone share", "%", "All borrowers on the loan are Asian alone."),
    "PCT_HPI": ("All borrowers Native Hawaiian / Pacific Islander alone share", "%", "All borrowers on the loan are Native Hawaiian or Other Pacific Islander."),
    "PCT_AMI": ("All borrowers American Indian / Alaska Native alone share", "%", "All borrowers on the loan are American Indian or Alaska Native alone."),
    "PCT_MIX": ("Multiple-race borrower share", "%", "Borrower race reporting is multiple or borrowers on a joint loan have different races."),
    "PCT_HIS": ("All borrowers Hispanic or Latino share", "%", "All borrowers are Hispanic or Latino, including a sole borrower."),
    "PCT_HSP": ("At least one Hispanic or Latino borrower share", "%", "At least one borrower is Hispanic or Latino on a multi-borrower loan."),
    "PCT_WNH": ("All borrowers White, not Hispanic or Latino share", "%", "All borrowers are White and not Hispanic or Latino."),
    "PCT_MNH": ("Multiple / non-White, not Hispanic or Latino share", "%", "All borrowers are not Hispanic or Latino and are multiple-race or a race other than White."),
    "AVE_AGE_BORROWER": ("Average borrower age", "years", "Average age of all borrowers."),
    "PCT_AGE_LT25": ("Borrower age <25 share", "%", "Average borrower age is below 25."),
    "PCT_AGE_2534": ("Borrower age 25–34 share", "%", "Average borrower age is 25 to 34."),
    "PCT_AGE_3544": ("Borrower age 35–44 share", "%", "Average borrower age is 35 to 44."),
    "PCT_AGE_4554": ("Borrower age 45–54 share", "%", "Average borrower age is 45 to 54."),
    "PCT_AGE_5564": ("Borrower age 55–64 share", "%", "Average borrower age is 55 to 64."),
    "PCT_AGE_GE65": ("Borrower age ≥65 share", "%", "Average borrower age is at least 65."),
    "PCT_MALEBOR": ("Single male borrower share", "%", "One borrower and that borrower is male."),
    "PCT_FEMALEBOR": ("Single female borrower share", "%", "One borrower and that borrower is female."),
    "PCT_TWOBOR": ("Two-borrower share", "%", "Loans with two borrowers."),
    "PCT_MULTIBOR": ("More-than-two-borrower share", "%", "Loans with more than two borrowers."),
}

OUTSTANDING_SERIES = {
    "TOT_LOANS": ("Outstanding active loans", "1,000 mortgages", "Number of active mortgages; VALUE1 only."),
    "PCT_LOANS": ("Geographic share of active loans", "%", "Active loans in geography divided by nationwide active loans."),
    "TOT_UPB": ("Outstanding unpaid principal balance", "USD billion", "Current value of active mortgages; VALUE1 only."),
    "PCT_UPB": ("Geographic share of UPB", "%", "Active-loan UPB in geography divided by nationwide active-loan UPB."),
    "TOT_LOANAMT": ("Origination volume of active mortgages", "USD billion", "Total origination loan volume for mortgages still active."),
    "AVE_PAYMENT": ("Average monthly payment", "USD / month", "Average principal, interest and escrow (where applicable) payment for the month ending the quarter."),
    "AVE_MTMLTV": ("Average current mark-to-market LTV", "%", "Current UPB divided by estimated current property value using FHFA house-price indexes; not origination LTV."),
    "PCT_MTMLTV_LE60": ("Current MTM LTV ≤60% share", "%", "Mark-to-market LTV at or below 60%."),
    "PCT_MTMLTV_61_70": ("Current MTM LTV 60.1–70% share", "%", "Mark-to-market LTV between 60% and 70%."),
    "PCT_MTMLTV_71_80": ("Current MTM LTV 70.1–80% share", "%", "Mark-to-market LTV between 70% and 80%."),
    "PCT_MTMLTV_81_90": ("Current MTM LTV 80.1–90% share", "%", "Mark-to-market LTV between 80% and 90%."),
    "PCT_MTMLTV_91_100": ("Current MTM LTV 90.1–100% share", "%", "Mark-to-market LTV between 90% and 100%."),
    "PCT_MTMLTV_GT100": ("Current MTM LTV >100% share", "%", "Mark-to-market LTV above 100%."),
    "AVE_INTRATE": ("Average contract rate at origination", "%", "Average contract interest rate when the mortgage originated."),
    "PCT_INTRATE_LT_3": ("Origination rate <3% share", "%", "Share with contract interest rate below 3%."),
    "PCT_INTRATE_3_4": ("Origination rate 3.00–3.99% share", "%", "Share with contract interest rate from 3.00% to 3.99%."),
    "PCT_INTRATE_4_5": ("Origination rate 4.00–4.99% share", "%", "Share with contract interest rate from 4.00% to 4.99%."),
    "PCT_INTRATE_5_6": ("Origination rate 5.00–5.99% share", "%", "Share with contract interest rate from 5.00% to 5.99%."),
    "PCT_INTRATE_GE_6": ("Origination rate ≥6% share", "%", "Share with contract interest rate at or above 6%."),
    "AVE_VANTAGESCR": ("Average current borrower VantageScore", "score points", "Average VantageScore 3.0 across borrowers."),
    "PCT_VS_VERYPOOR": ("Very poor score share", "%", "Average borrower VantageScore from 300 to 499."),
    "PCT_VS_POOR": ("Poor score share", "%", "Average borrower VantageScore from 500 to 600."),
    "PCT_VS_FAIR": ("Fair score share", "%", "Average borrower VantageScore from 601 to 660."),
    "PCT_VS_GOOD": ("Good score share", "%", "Average borrower VantageScore from 661 to 780."),
    "PCT_VS_EXCELLENT": ("Excellent score share", "%", "Average borrower VantageScore from 781 to 850."),
    "AVE_AGE_LOAN": ("Average loan age", "months", "Average months elapsed since origination."),
    "PCT_TENURE_1_4": ("Loan age ≤4 years share", "%", "Outstanding loans originated within the prior four years."),
    "PCT_TENURE_5_7": ("Loan age 4.01–7 years share", "%", "Outstanding loans originated 4.01 to 7.00 years ago."),
    "PCT_TENURE_8_10": ("Loan age 7.01–10 years share", "%", "Outstanding loans originated 7.01 to 10.00 years ago."),
    "PCT_TENURE_11PL": ("Loan age >10 years share", "%", "Outstanding loans originated more than 10 years ago."),
    "PCT_TERM_ARM_1_4": ("ARM originated within prior 4 years share", "%", "Active adjustable-rate mortgages originated within the prior four years."),
    "PCT_TERM_ARM_5PL": ("ARM originated >4 years ago share", "%", "Active adjustable-rate mortgages originated more than four years ago."),
    "PCT_TERM_FRM_15": ("Fixed rate term ≤15 years share", "%", "Fixed-rate mortgages with term at or below 15 years."),
    "PCT_TERM_FRM_30": ("Fixed rate term >15 years share", "%", "Fixed-rate mortgages with term above 15 years."),
    "PCT_GOVERNMENT": ("Government market share", "%", "Government-insured, guaranteed or direct loans."),
    "PCT_ENTERPRISE": ("Enterprise market share", "%", "Non-government loans acquired by Fannie Mae or Freddie Mac."),
    "PCT_OTHER": ("Other conventional market share", "%", "Non-government, non-enterprise loans, including jumbo."),
}

SERIES = {
    "new_annual": NEW_SERIES,
    "outstanding_quarterly": OUTSTANDING_SERIES,
}
VALUE1_ONLY = {
    # FHFA Appendix B: these New Residential Mortgage Statistics are VALUE1 only.
    "new_annual": {"TOT_ORIG", "TOT_LOANAMT", "AVE_LOANAMT", "AVE_PAYMENT", "AVE_PROPVAL"},
    "outstanding_quarterly": {"TOT_LOANS", "PCT_LOANS", "TOT_UPB", "PCT_UPB", "TOT_LOANAMT", "AVE_PAYMENT"},
}
ALLOWED_QUERY = {"product", "geo_level", "geo_id", "market", "series_id", "measure", "from_year", "to_year"}


def _paths(root: Path) -> tuple[Path, Path, dict]:
    mart = root / MART_RELATIVE
    receipt_path = root / RECEIPT_RELATIVE
    if not mart.is_file() or not receipt_path.is_file():
        raise FileNotFoundError("FHFA NMDB market mart is not built; run scripts/build_fhfa_nmdb_market_mart.py")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected_rows = sum(int(item.get("source_rows", 0)) for item in receipt.get("source_evidence", {}).values())
    if receipt.get("status") != "PASS" or expected_rows <= 0 or receipt.get("row_count") != expected_rows:
        raise ValueError("FHFA NMDB market mart receipt is incomplete or unexpected")
    source_receipt = Path(receipt.get("source_receipt", ""))
    if not source_receipt.is_file() or sha256(source_receipt) != receipt.get("source_receipt_sha256"):
        raise ValueError("FHFA NMDB acquisition receipt differs from the mart lineage record")
    if sha256(mart) != receipt.get("mart_sha256"):
        raise ValueError("FHFA NMDB market mart hash differs from its receipt")
    return mart, receipt_path, receipt


@lru_cache(maxsize=1)
def _cached_catalog(root_str: str, receipt_mtime_ns: int, receipt_size: int) -> dict:
    root = Path(root_str)
    mart, _receipt_path, receipt = _paths(root)
    con = duckdb.connect(database=":memory:", read_only=False)
    try:
        mart_sql = str(mart).replace("'", "''")
        rows = con.execute(
            f"SELECT product, geography_level, geography_id, geography_name, market, series_id, "
            f"count(*) AS observations, min(year) AS first_year, max(year) AS last_year, "
            f"sum(CASE WHEN value1 IS NOT NULL THEN 1 ELSE 0 END) AS value1_present, "
            f"sum(CASE WHEN value2 IS NOT NULL THEN 1 ELSE 0 END) AS value2_present, "
            f"sum(CASE WHEN suppressed THEN 1 ELSE 0 END) AS suppressed "
            f"FROM read_parquet('{mart_sql}') GROUP BY ALL ORDER BY product, geography_level, geography_id, market, series_id"
        ).fetchall()
    finally:
        con.close()

    products = []
    for product_id, metadata in PRODUCTS.items():
        subset = [row for row in rows if row[0] == product_id]
        geos = {(row[1], row[2], row[3]) for row in subset}
        markets = sorted({row[4] for row in subset})
        series_ids = sorted({row[5] for row in subset})
        catalog_series = []
        for series_id in series_ids:
            label, unit, definition = SERIES[product_id].get(
                series_id, (series_id.replace("_", " ").title(), "source units", "See the FHFA Appendix for this series definition.")
            )
            matching = [row for row in subset if row[5] == series_id]
            catalog_series.append({
                "series_id": series_id, "label": label, "unit": unit, "definition": definition,
                "available_value1": any(row[9] for row in matching),
                "available_value2": any(row[10] for row in matching) and series_id not in VALUE1_ONLY[product_id],
                "supported_weights": ["VALUE1"] + (["VALUE2"] if any(row[10] for row in matching) and series_id not in VALUE1_ONLY[product_id] else []),
                "weight_note": "FHFA Appendix specifies VALUE1 only for this series." if series_id in VALUE1_ONLY[product_id] else "Select VALUE1 or VALUE2 where published; the weighting estimand differs.",
                "observations": sum(int(row[6]) for row in matching),
                "suppressed": sum(int(row[11]) for row in matching),
            })
        products.append({
            "product": product_id, **metadata,
            "row_count": len(subset) and sum(int(row[6]) for row in subset),
            "geographies": [{"geo_level": level, "geo_id": geo_id, "geo_name": name} for level, geo_id, name in sorted(geos)],
            "markets": markets,
            "series": catalog_series,
        })
    return {
        "status": "AVAILABLE", "source": "FHFA National Mortgage Database Aggregate Statistics",
        "source_page": SOURCE_PAGE, "dictionary_url": DICTIONARY_URL,
        "source_release_date": receipt["source_release_date"], "retrieved_at": receipt["retrieved_at"],
        "mart_sha256": receipt["mart_sha256"], "row_count": receipt["row_count"],
        "quality": receipt["quality"], "products": products,
        "interpretation": {
            "VALUE1": "Loan-count weighted; each sampled mortgage represents 20 actual mortgages.",
            "VALUE2_new": PRODUCTS["new_annual"]["value2_definition"],
            "VALUE2_outstanding": PRODUCTS["outstanding_quarterly"]["value2_definition"],
            "suppression": "SUPPRESSED=1 means a cell is based on fewer than three loans; displayed as suppressed/unavailable, never zero.",
        },
        "scope_notes": [
            "FHFA NMDB aggregate statistics are a 5% sample product, not loan-level records or a census.",
            "New originations are a flow; outstanding active loans are a quarter-end stock. Do not join as a loan panel or add them together.",
            "This market context has no loan-level default target and is not a PD estimate, Freddie vintage, or model validation set.",
            "VALUE1 and VALUE2 are distinct weighting estimands. Blank or suppressed values remain unavailable; no forecast or imputation is applied.",
        ],
    }


def catalog(root: Path) -> dict:
    receipt_path = root / RECEIPT_RELATIVE
    if not receipt_path.is_file():
        raise FileNotFoundError("FHFA NMDB market mart is not built")
    stat = receipt_path.stat()
    return _cached_catalog(str(root.resolve()), stat.st_mtime_ns, stat.st_size)


def report(root: Path, query: dict) -> dict:
    if set(query) - ALLOWED_QUERY:
        raise ValueError("NMDB market report received an unsupported filter")
    if not {"product", "geo_level", "geo_id", "market", "series_id", "measure"} <= set(query):
        raise ValueError("Select product, geography, market, series and weighting before querying NMDB")
    product = query["product"]
    if product not in PRODUCTS:
        raise ValueError("Unknown NMDB product")
    measure = query["measure"]
    if measure not in {"VALUE1", "VALUE2"}:
        raise ValueError("NMDB measure must be VALUE1 or VALUE2")
    selected = next(item for item in catalog(root)["products"] if item["product"] == product)
    if query["geo_level"] not in {row["geo_level"] for row in selected["geographies"]}:
        raise ValueError("Geography level is unavailable for this product")
    if (query["geo_level"], query["geo_id"]) not in {(row["geo_level"], row["geo_id"]) for row in selected["geographies"]}:
        raise ValueError("Geography is unavailable for this product")
    if query["market"] not in selected["markets"]:
        raise ValueError("Mortgage market is unavailable for this product")
    series_meta = {row["series_id"]: row for row in selected["series"]}
    if query["series_id"] not in series_meta:
        raise ValueError("Series is unavailable for this product")
    if not series_meta[query["series_id"]]["available_" + measure.lower()]:
        raise ValueError("Selected weighting has no observed values for this series")

    min_year = int(selected["first_year"])
    max_year = int(selected["last_year"])
    try:
        from_year = int(query.get("from_year", min_year))
        to_year = int(query.get("to_year", max_year))
    except ValueError as exc:
        raise ValueError("Year filters must be whole numbers") from exc
    if not min_year <= from_year <= max_year or not min_year <= to_year <= max_year or from_year > to_year:
        raise ValueError("Selected year range is outside the published coverage")

    mart, _receipt_path, receipt = _paths(root)
    measure_column = measure.lower()
    mart_sql = str(mart).replace("'", "''")
    con = duckdb.connect(database=":memory:", read_only=False)
    try:
        result_rows = con.execute(
            f"SELECT source, frequency, geography_level, geography_id, geography_name, market, period, year, quarter, month, "
            f"suppressed, series_id, value1_raw, value2_raw, value1, value2, {measure_column} AS selected_value "
            f"FROM read_parquet('{mart_sql}') "
            f"WHERE product = ? AND geography_level = ? AND geography_id = ? AND market = ? AND series_id = ? "
            f"AND year BETWEEN ? AND ? ORDER BY year, quarter NULLS FIRST",
            [product, query["geo_level"], query["geo_id"], query["market"], query["series_id"], from_year, to_year],
        ).fetchall()
    finally:
        con.close()

    columns = ["source", "frequency", "geography_level", "geography_id", "geography_name", "market", "period", "year", "quarter", "month", "suppressed", "series_id", "value1_raw", "value2_raw", "value1", "value2", "selected_value"]
    rows = [dict(zip(columns, row)) for row in result_rows]
    if not rows:
        raise ValueError("No NMDB observations match the selected filters")
    for row in rows:
        row["value1"] = float(row["value1"]) if row["value1"] is not None else None
        row["value2"] = float(row["value2"]) if row["value2"] is not None else None
        row["selected_value"] = float(row["selected_value"]) if row["selected_value"] is not None else None
    suppressed_count = sum(bool(row["suppressed"]) for row in rows)
    missing_count = sum(row["selected_value"] is None for row in rows)
    series = series_meta[query["series_id"]]
    return {
        "status": "AVAILABLE", "product": product, "product_label": selected["label"], "product_kind": selected["kind"],
        "frequency": selected["frequency"], "definition": selected["definition"], "series": series,
        "measure": measure, "measure_definition": catalog(root)["interpretation"]["VALUE1" if measure == "VALUE1" else ("VALUE2_new" if product == "new_annual" else "VALUE2_outstanding")],
        "supported_weights": series["supported_weights"], "weight_note": series["weight_note"],
        "filters": {"geo_level": query["geo_level"], "geo_id": query["geo_id"], "geo_name": rows[0]["geography_name"], "market": query["market"], "series_id": query["series_id"], "measure": measure, "from_year": from_year, "to_year": to_year},
        "source_release_date": receipt["source_release_date"], "retrieved_at": receipt["retrieved_at"], "mart_sha256": receipt["mart_sha256"],
        "quality": {"observations": len(rows), "suppressed_rows": suppressed_count, "selected_value_unavailable_rows": missing_count, "forecast_or_imputation_used": False},
        "rows": rows,
    }
