"""Source-backed note terms; issue principal is not current outstanding principal."""
from pathlib import Path
from datetime import datetime,timezone
import json,re,uuid
from credit_atlas.workspace import read_json,sha256
from credit_atlas.sec_sources import verify_source
from credit_atlas.sec_financials import normalize_filings
root=Path(__file__).resolve().parents[1];folder=root/'data/private/sec-documents/sec-documents-fbf41f7fbac2'
r=read_json(folder/'acquisition.json');assert r['status']=='ACQUIRED' and sha256(folder/r['file'])==r['sha256']
pages=read_json(folder/'pages.json');assert len(pages)==90
secfolder,secreceipt=verify_source(root,'sec-source-2dd5a9f2962a')
filings,_=normalize_filings(secfolder,secreceipt,'0000320193')
filing=next(x for x in filings if x['accession']=='0001140361-25-018400')
assert filing['filing_date']=='2025-05-12' and filing['report_date']=='2025-05-05' and filing['form']=='8-K'
def evidence(number,anchors):
 text=re.sub(r'\s+',' ',pages[number-1]['text']);assert all(a in text for a in anchors),(number,anchors)
 return {'pdf_page':number,'anchors':anchors,'page_text':text}
notes=[]
for year,rate,principal,term_pages,interest_page,cusip,isin in [(2028,'0.04000','1500000000',[35],48,'037833EY2','US037833EY27'),(2030,'0.04200','1000000000',[37],59,'037833EZ9','US037833EZ91'),(2032,'0.04500','1000000000',[39],70,'037833FA3','US037833FA32'),(2035,'0.04750','1000000000',[40,41],81,'037833FB1','US037833FB15')]:
    ev=[evidence(p,['4.' if p==40 else f'May 12, {year}']) for p in term_pages]
    ev.append(evidence(interest_page,['360-day year','twelve 30-day months','next succeeding Business Day']))
    # Full issue size and title occur in the certificate introduction.
    ev.append(evidence(35,[{'2028':'$1,500,000,000'}.get(str(year),'$1,000,000,000'),f'Notes due {year}']))
    notes.append({'note_id':f'apple-2025-{year}','cik':'0000320193','title':f'{float(rate)*100:.3f}% Notes due {year}','cusip_source_label':cusip,'isin_source_label':isin,'original_issue_principal_usd_exact':principal,'coupon_rate_exact':rate,'issue_date':'2025-05-12','maturity_date':f'{year}-05-12','first_coupon_date':'2025-11-12','coupon_month_days':[[5,12],[11,12]],'frequency':2,'interest_basis':'360-day year / twelve 30-day months; FINRA11620(b)','business_day_rule':'Next succeeding Business Day; base indenture definition and calendar require review','callable':True,'current_outstanding_usd_exact':None,'evidence':ev})
payload={'cik':'0000320193','issuer':'Apple Inc.','filing_identity':filing,'source':{'folder':folder.name,'file':r['file'],'url':r['url'],'pdf_sha256':r['sha256'],'pages_sha256':sha256(folder/'pages.json'),'pages':90,'filing_date':filing['filing_date']},'notes':notes,'qualification':{'full_legal_terms_reviewed':False,'latest_outstanding_supported':False,'business_day_calendar_qualified':False,'actual_payments_supported':False,'issuer_total_debt_service_supported':False,'dscr_supported':False}}
out=root/'artifacts/private'/('apple-notes-'+uuid.uuid4().hex[:12]);out.mkdir(parents=True)
(out/'catalog.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
(out/'catalog-complete.json').write_text(json.dumps({'catalog_id':out.name,'created_at':datetime.now(timezone.utc).isoformat(),'catalog_sha256':sha256(out/'catalog.json'),'builder_sha256':sha256(Path(__file__)),'sec_source_id':secreceipt['source_id'],'visibility':'private'},indent=2),encoding='utf8');print(out)
