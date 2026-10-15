"""Read-only contract discovery; outputs definitions and aggregate profiles."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import duckdb

root = Path(__file__).resolve().parents[1]
ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
with zipfile.ZipFile(root / "data/private/public-suite/suite-619b1ee9aa8c/sba-dictionary.xlsx") as z:
    strings = ["".join(n.itertext()) for n in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("s:si", ns)]
    for sheet in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"):
        records = []
        for row in ET.fromstring(z.read(sheet)).findall("s:sheetData/s:row", ns):
            record = {}
            for c in row.findall("s:c", ns):
                value = c.find("s:v", ns)
                if value is not None:
                    record[c.attrib["r"]] = strings[int(value.text)] if c.attrib.get("t") == "s" else value.text
            records.append(record)
        print(sheet, json.dumps(records, ensure_ascii=False))
with duckdb.connect() as db:
    db.execute("SET threads=2")
    for path in sorted((root / "artifacts/private/source-warehouse-281662304758").glob("sba-*.parquet")):
        db.read_parquet(str(path)).create_view("native", replace=True)
        print(path.name, db.sql("SELECT Program,AsOfDate,LoanStatus,count(*) AS records FROM native GROUP BY ALL ORDER BY ALL").fetchall())
        amount = "ThirdPartyDollars" if "504" in path.name else "SBAGuaranteedApproval"
        print("DATE/MONEY EXAMPLES", db.sql("SELECT ApprovalDate,ApprovalFY,FirstDisbursementDate,GrossApproval," + amount + ",GrossChargeOffAmount FROM native LIMIT 4").fetchall())
        print("SCHEMA", [r[0] for r in db.sql("DESCRIBE native").fetchall()])
