"""Refresh and audit the SEC submissions census for Nissan Auto Receivables 2024-B."""
from __future__ import annotations
import gzip, hashlib, json, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from credit_atlas.workspace import contained, read_json, sha256, timestamp, write_new

ROOT=Path(__file__).resolve().parents[1]
CIK="0002035264"
ISSUER="Nissan Auto Receivables 2024-B Owner Trust"
URL="https://data.sec.gov/submissions/CIK0002035264.json"
USER_AGENT="OpenAI Codex Credit Atlas research (https://openai.com)"
LOCAL_SOURCE="data/private/structured/nissan-2024b-validation-panel-7cd3605b4e07/sec-submissions.json"
TARGETS={"0000950131-25-003344":{"form":"ABS-EE","filing_date":"2025-08-20"},"0001193125-25-187356":{"form":"10-D","filing_date":"2025-08-25"}}

def acquire():
    req=Request(URL,headers={"User-Agent":USER_AGENT,"Accept-Encoding":"gzip, deflate"})
    with urlopen(req,timeout=60) as response:
        if response.status!=200 or response.url!=URL: raise ValueError("Unexpected SEC submissions response")
        encoded=response.read(8*1024*1024+1)
        if not encoded or len(encoded)>8*1024*1024: raise ValueError("SEC submissions response empty or too large")
        meta={"url":response.url,"http_status":response.status,"content_type":response.headers.get("Content-Type"),"content_encoding":response.headers.get("Content-Encoding"),"last_modified":response.headers.get("Last-Modified"),"etag":response.headers.get("ETag")}
    raw=gzip.decompress(encoded) if encoded[:2]==b"\x1f\x8b" else encoded
    body=json.loads(raw)
    if str(body.get("cik"))!=CIK or body.get("name")!=ISSUER: raise ValueError("SEC submissions identity mismatch")
    recent=body.get("filings",{}).get("recent",{})
    rows=[]
    for i,acc in enumerate(recent.get("accessionNumber",[])):
        rows.append({"accession":acc,"filing_date":recent["filingDate"][i],"form":recent["form"][i],"primary_document":recent["primaryDocument"][i],"report_date":recent.get("reportDate",[""]*len(recent["accessionNumber"]))[i]})
    seen={x["accession"]:x for x in rows}
    for acc,expected in TARGETS.items():
        row=seen.get(acc)
        if not row or row["form"]!=expected["form"] or row["filing_date"]!=expected["filing_date"]: raise ValueError(f"Expected paired July filing missing/changed: {acc}")
    amendments=[x for x in rows if x["form"] in {"10-D/A","ABS-EE/A"}]
    target_amendments=[x for x in amendments if x.get("report_date")=="2025-07-31"]
    local=contained(ROOT,LOCAL_SOURCE)
    local_sha=sha256(local); live_sha=hashlib.sha256(raw).hexdigest()
    if raw!=local.read_bytes(): raise ValueError("Live SEC submissions census differs from acquisition snapshot; inspect new rows")
    filing_window=[x for x in rows if "2025-08-15"<=x["filing_date"]<="2025-10-31" and x["form"] in {"ABS-EE","10-D","ABS-EE/A","10-D/A"}]
    return {"status":"NISSAN_2024B_SEC_SUBMISSIONS_REFRESH_VERIFIED","issuer":ISSUER,"cik":CIK,"snapshot_latest_filing_date":max(x["filing_date"] for x in rows),"submission_row_count":len(rows),"source":meta,"live_uncompressed_bytes":len(raw),"live_uncompressed_sha256":live_sha,"acquisition_snapshot_sha256":local_sha,"live_matches_acquisition_snapshot":True,"july_pair_verified":[seen[x] for x in TARGETS],"july_report_date_amendments":target_amendments,"all_submission_amendments":amendments,"filings_near_july_reporting_month":filing_window,"amendment_search_status":"NO_10-D/A_OR_ABS-EE/A_FOR_2025-07-31_IN_CURRENT_CIK_SUBMISSIONS" if not target_amendments else "AMENDMENT_FOUND_REQUIRES_REAUDIT","audited_at_utc":datetime.now(timezone.utc).isoformat(),"acquisition_script_sha256":sha256(Path(__file__)),"visibility":"private","public_release_approved":False},raw

def main():
    audit,raw=acquire()
    out=contained(ROOT,"artifacts/private/nissan-2024b-submission-refresh-"+uuid.uuid4().hex[:12]); out.mkdir(parents=True)
    write_new(out/"submissions.json",json.loads(raw))
    audit["saved_submissions_sha256"]=sha256(out/"submissions.json")
    write_new(out/"audit.json",audit)
    write_new(out/"receipt.json",{"status":audit["status"],"audit_sha256":sha256(out/"audit.json"),"submissions_sha256":audit["saved_submissions_sha256"],"latest_filing_date":audit["snapshot_latest_filing_date"],"amendments_for_2025_07_31":len(audit["july_report_date_amendments"]),"visibility":"private","public_release_approved":False})
    print(out); print(json.dumps({k:audit[k] for k in ("status","snapshot_latest_filing_date","submission_row_count","live_matches_acquisition_snapshot","july_pair_verified","july_report_date_amendments","all_submission_amendments","amendment_search_status")},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
