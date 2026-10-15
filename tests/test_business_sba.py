import csv
import json
from decimal import Decimal
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

import duckdb
import pyarrow.parquet as pq
import pytest

from credit_atlas.business_sba import (DATES, MONEY, INTEGERS, TEXT, canonical_sql,
                                      parse_dictionary, prepare_sba, source_quality, status_name, verify_sba)
from credit_atlas.workspace import read_json


def make_dictionary(path, fields_by_program, formula=False, external=False):
    uri = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    reluri = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    sheets = '<sheets><sheet name="504 Data Dictionary" sheetId="8" r:id="b"/><sheet name="7(a) Data Dictionary" sheetId="9" r:id="a"/></sheets>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{uri}" xmlns:r="{reluri}">{sheets}</workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="a" Target="worksheets/custom-a.xml"/><Relationship Id="b" Target="worksheets/custom-b.xml"' + (' TargetMode="External"' if external else '') + '/></Relationships>')
        for program, letter in (("7A", "a"), ("504", "b")):
            records = [("Field Name", "Definition")] + [(f, "SYNTHETIC definition " + f) for f in fields_by_program[program]]
            rows = []
            for i, (field, definition) in enumerate(records, 1):
                row = f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{escape(field)}</t></is></c>'
                row += f'<c r="B{i}" t="inlineStr">' + ('<f>1+1</f>' if formula and i == 2 else '')
                row += f'<is><t>{escape(definition)}</t></is></c><c r="C{i}" s="1"/></row>'
                rows.append(row)
            z.writestr(f"xl/worksheets/custom-{letter}.xml", f'<worksheet xmlns="{uri}"><sheetData>{"".join(rows)}</sheetData></worksheet>')


def test_dictionary_resolves_named_relationships_with_reordered_sheets_and_blank_style_cells(tmp_path):
    path = tmp_path / "dictionary.xlsx"
    make_dictionary(path, {"7A": ["LocationID", "LoanStatus"], "504": ["GrossApproval"]})
    result = parse_dictionary(path)
    assert [r["field"] for r in result["7A"]] == ["LocationID", "LoanStatus"]
    assert result["504"][0]["definition_cell"] == "B2"


@pytest.mark.parametrize("kwargs,pattern", [({"formula": True}, "formulas"), ({"external": True}, "relationships")])
def test_dictionary_rejects_formula_or_external_reference(tmp_path, kwargs, pattern):
    path = tmp_path / "dictionary.xlsx"
    make_dictionary(path, {"7A": ["LocationID"], "504": ["GrossApproval"]}, **kwargs)
    with pytest.raises(ValueError, match=pattern):
        parse_dictionary(path)


def test_status_definitions_preserve_withheld_and_closed_other_instead_of_negative_default():
    assert status_name("7A", "P I F") == status_name("504", "PIF") == "paid_in_full"
    assert status_name("7A", "EXEMPT") == "disbursed_status_withheld"
    assert status_name("504", "CLOSED") == "closed_other_legacy"
    assert status_name("7A", "CLOSED") == "unmapped"
    assert status_name("504", "new-code") == "unmapped"


def test_source_decimal_precision_and_scientific_amounts_are_checked_without_rounding():
    with duckdb.connect() as db:
        db.sql("SELECT '203325.03999999998'::VARCHAR AS GrossChargeOffAmount,'1.196E7'::VARCHAR AS ThirdPartyDollars,'2.5'::VARCHAR AS JobsSupported").create_view("native")
        quality = source_quality(db, ["GrossChargeOffAmount", "ThirdPartyDollars", "JobsSupported"])
        assert quality["GrossChargeOffAmount"]["fractional_cent_records"] == 1
        assert quality["GrossChargeOffAmount"]["precision_loss"] == 0
        assert quality["ThirdPartyDollars"]["scientific_not_exact"] == 0
        assert quality["JobsSupported"]["precision_loss"] == 1


def synthetic_sources(tmp_path, monkeypatch, invalid=False):
    folder = tmp_path / "SYNTHETIC-sources"
    folder.mkdir()
    (folder / "acquisition-complete.json").write_text('{"source_kind":"SYNTHETIC-QA"}')
    common = list(dict.fromkeys(["Program", "LoanStatus"] + list(DATES) + list(INTEGERS) + list(TEXT) + ["GrossApproval", "GrossChargeOffAmount"]))
    fields = {"7A": common + ["SBAGuaranteedApproval", "InitialInterestRate"], "504": common + ["ThirdPartyDollars"]}
    dictionary = folder / "dictionary.xlsx"
    make_dictionary(dictionary, fields)
    sources = [{"source_id": "sba-dictionary", "kind": "xlsx", "status": "DOWNLOADED_AND_PROFILED", "file": dictionary.name, "sha256": "a" * 64}]
    identifiers = ["sba-7a-fy1991_fy1999", "sba-7a-fy2000_fy2009", "sba-7a-fy2010_fy2019", "sba-7a-fy2020_present",
                   "sba-504-fy1991_fy2009", "sba-504-fy2010_present"]
    for source_id in identifiers:
        program = "504" if "504" in source_id else "7A"
        rows = []
        for index, status in enumerate(["CHGOFF", "EXEMPT", "EXEMPT"]):
            row = dict.fromkeys(fields[program], "")
            row.update(Program=program, LoanStatus=status, AsOfDate="2026-06-30", ApprovalDate="2020-01-01", ApprovalFY="2020",
                       TermInMonths="120", JobsSupported="2", GrossApproval="100.0", GrossChargeOffAmount="10.000000000001" if index == 0 else "0.0",
                       FirstDisbursementDate="2020-02-01", LocationID="SYNTHETIC-LENDER", ProjectState="CA", NaicsCode="541330")
            if index == 0:
                row["ChargeOffDate"] = "2022-01-01"
            if program == "504":
                row["ThirdPartyDollars"] = "1.196E7"
            else:
                row["SBAGuaranteedApproval"] = "75.0"
            rows.append(row)
        if invalid:
            rows[0]["JobsSupported"] = "2.5"
        path = folder / (source_id + ".csv")
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields[program])
            writer.writeheader(); writer.writerows(rows)
        sources.append({"source_id": source_id, "kind": "csv", "status": "DOWNLOADED_AND_PROFILED", "file": path.name,
                        "sha256": "b" * 64, "profile": {"fields": fields[program], "rows": len(rows)}})
    monkeypatch.setattr("credit_atlas.business_sba.verify_acquisition", lambda *a: (folder, {"sources": sources}))


def test_full_six_segment_flow_retains_duplicates_and_separates_504_amount_components(tmp_path, monkeypatch):
    synthetic_sources(tmp_path, monkeypatch)
    result = prepare_sba(tmp_path, "suite-aaaaaaaaaaaa")
    folder = Path(result["directory"])
    receipt = read_json(folder / "business-complete.json")
    assert result["rows"] == 18 and receipt["fixed_horizon_default_target_qualified"] is False
    quality = read_json(folder / "quality.json")
    assert all(v["exact_duplicate_excess_rows"] == 1 for v in quality.values())
    assert all(v["retained_rows"] == 3 for v in quality.values())
    rows = pq.read_table(folder / "sba-504-fy2010_present.parquet").to_pylist()
    assert all(r["guaranteed_approval_amount"] is None for r in rows)
    assert rows[0]["third_party_amount"] == Decimal("11960000")
    assert rows[0]["reported_chargeoff_amount"] == Decimal("10.000000000001")
    assert rows[1]["status"] == "disbursed_status_withheld"
    assert len({r["source_record_key"] for r in rows}) == 3
    for dimension in read_json(folder / "aggregates.json")["dimensions"].values():
        assert sum(r["records"] for r in dimension) == 18
    assert verify_sba(tmp_path, folder.name)[2]["source_record_count"] == 18
    path = folder / "aggregates.json"
    data = read_json(path)
    data["source_record_count"] = 19
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="evidence changed"):
        verify_sba(tmp_path, folder.name)


@pytest.mark.parametrize("identifier", [None, "../business-sba-aaaaaaaaaaaa", "d01-aaaaaaaaaaaa"])
def test_business_verifier_rejects_invalid_identifier_before_file_access(tmp_path, identifier):
    with pytest.raises(ValueError, match="identifier"):
        verify_sba(tmp_path, identifier)


def test_fractional_integer_is_not_silently_rounded_and_no_complete_receipt_written(tmp_path, monkeypatch):
    synthetic_sources(tmp_path, monkeypatch, invalid=True)
    with pytest.raises(ValueError, match="precision-losing"):
        prepare_sba(tmp_path, "suite-aaaaaaaaaaaa")
    output = next((tmp_path / "artifacts/private").glob("business-sba-*"))
    assert not (output / "business-complete.json").exists()
    assert read_json(output / "business-failed.json")["status"] == "FAIL"
