"""Synthetic panels verify year boundaries, denominator and gap semantics."""
import datetime as dt
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from credit_atlas.period_transitions import aggregate

SQL = Path(__file__).resolve().parents[1] / "vendor/credit_risk_strategy_lab/sql"


def panel(db):
    db.execute("CREATE TABLE dim_loan(loan_id VARCHAR,is_relief_refinance BOOLEAN)")
    db.execute("INSERT INTO dim_loan VALUES ('A',TRUE),('B',FALSE),('C',NULL)")
    db.execute("""CREATE TABLE fact_loan_month(loan_id VARCHAR,period DATE,
        current_upb DECIMAL(18,6),delinquency_state VARCHAR,terminal_type VARCHAR)""")
    records = [
        ("A", "2020-12-01", "100.123456", "CURRENT", None),
        ("A", "2021-01-01", "90.000001", "D1", None),
        ("A", "2021-02-01", "80", "CURRENT", None),
        ("A", "2021-04-01", "70", "D3PLUS", None),  # March gap never bridged.
        ("A", "2021-05-01", "0", "CURRENT", "PREPAID_OR_MATURED"),
        ("A", "2021-06-01", "0", "CURRENT", None),  # Terminal-origin pair excluded.
        ("B", "2020-12-01", None, "CURRENT", None),
        ("B", "2021-01-01", "99", "D1", None),
        ("C", "2021-01-01", None, "UNKNOWN", None),
        ("C", "2021-02-01", None, "CURRENT", None),
    ]
    db.executemany("INSERT INTO fact_loan_month VALUES (?,?,?,?,?)", records)


def test_cross_year_gap_terminal_missing_upb_and_distinct_support():
    with duckdb.connect() as db:
        panel(db)
        cells, total = aggregate(db, SQL)
        assert total == 5
        december = next(r for r in cells if r["reporting_year"] == 2020 and
                        r["segment"] == "all" and r["origin"] == "CURRENT")
        assert december["destination"] == "D1" and december["pairs"] == 2
        assert december["distinct_loans"] == 2 and december["missing_balance_pairs"] == 1
        assert december["opening_upb"] == pytest.approx(100.123456)
        assert december["origin_pairs"] == 2 and december["count_probability"] == 1
        assert december["balance_probability"] == 1
        null_balance = next(r for r in cells if r["reporting_year"] == 2020 and
                            r["segment"] == "non_relief")
        assert null_balance["opening_upb"] is None
        assert null_balance["balance_probability"] is None
        assert not any(r["origin"] == "CURRENT" and r["destination"] == "D3PLUS" for r in cells)
        terminal = next(r for r in cells if r["reporting_year"] == 2021 and r["segment"] == "all"
                        and r["origin"] == "D3PLUS")
        assert terminal["destination"] == "PREPAID_OR_MATURED"
        assert terminal["pairs"] == 1
        assert db.execute("""SELECT SUM(opening_upb) FROM period_cells
            WHERE reporting_year IS NOT NULL AND segment='all'""").fetchone()[0] == Decimal("260.123457")
        lifetime = [r for r in cells if r["reporting_year"] is None and r["segment"] == "all"]
        assert sum(r["pairs"] for r in lifetime) == total


def test_same_loan_in_two_years_is_not_double_counted_in_lifetime_distinct():
    with duckdb.connect() as db:
        panel(db)
        db.execute("INSERT INTO fact_loan_month VALUES ('B','2021-02-01',90,'CURRENT',NULL),('B','2021-03-01',80,'D1',NULL)")
        cells, _ = aggregate(db, SQL)
        selected = [r for r in cells if r["segment"] == "all" and r["origin"] == "CURRENT"
                    and r["destination"] == "D1"]
        assert sum(r["distinct_loans"] for r in selected if r["reporting_year"] is not None) == 3
        assert next(r["distinct_loans"] for r in selected if r["reporting_year"] is None) == 2


@pytest.mark.parametrize("mutation", [
    "INSERT INTO dim_loan VALUES ('A',TRUE)",
    "INSERT INTO fact_loan_month SELECT * FROM fact_loan_month LIMIT 1",
    "INSERT INTO fact_loan_month VALUES ('MISSING','2021-01-01',0,'CURRENT',NULL)",
])
def test_invalid_join_or_monthly_grain_is_rejected(mutation):
    with duckdb.connect() as db:
        panel(db)
        db.execute(mutation)
        with pytest.raises(ValueError):
            aggregate(db, SQL)
