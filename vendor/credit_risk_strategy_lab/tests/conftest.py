"""Entirely synthetic records. No real IDs or source data included."""
from __future__ import annotations
import zipfile
import pytest
from crsl.contracts import fields_for

def record(table, **changes):
    row = {field: "" for field in fields_for(table)}
    row["loan_id"] = "F12Q10000001"
    if table == "origination":
        row.update(classic_fico="720", first_payment_date="201201",
                   maturity_date="204112", original_upb="100000",
                   original_interest_rate="4.500", amortization_type="FRM")
    else:
        row.update(period="201201", current_upb="100000.00", delinquency="00",
                   loan_age="1", remaining_months="359", current_rate="4.500")
    row.update(changes)
    return [row[field] for field in fields_for(table)]

@pytest.fixture
def make_record():
    return record

@pytest.fixture
def make_zip(tmp_path):
    def create(name="fixture.zip", origination=None, performance=None, kind="annual"):
        path = tmp_path/name
        names = ("sample_orig_2012.txt", "sample_perf_2012.txt") if kind == "annual" else (
            "Sample Files/origination_sample_file.txt", "Sample Files/performance_sample_file.txt")
        with zipfile.ZipFile(path, "w") as archive:
            for member, rows in zip(names, (origination or [record("origination")],
                                           performance or [record("performance")])):
                archive.writestr(member, "\n".join("|".join(row) for row in rows)+"\n")
        return path
    return create

