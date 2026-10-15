"""Source-bound statement clause evidence; proposed redlines are not operative."""
import json,uuid
from pathlib import Path
from pypdf import PdfReader
import pypdfium2 as pdfium
from credit_atlas.workspace import sha256,read_json
root=Path.cwd();source=root/'data/private/business/utility-contract-source-cac5d22ec69d'
receipt=read_json(source/'acquisition-complete.json')
assert sha256(source/'acquisition-complete.json')=='99a9782c07621805b5a437a389953d097bec71e389382493c225e8d59fa3eeb1'
for s in receipt['sources']:assert sha256(source/s['file'])==s['sha256'] and (source/s['file']).stat().st_size==s['bytes']
out=root/'artifacts/private'/('utility-contract-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
systems=[]
for system,date,pages,definition,policy,summary,future_start,future_rate,future_caveat in [
    ('water','March 31, 2026',308,263,119,273,303,304,305),
    ('wastewater','April 15, 2026',282,237,92,247,277,278,279)]:
    name=system+'-official-statement.pdf';reader=PdfReader(source/name)
    cover=' '.join(reader.pages[0].extract_text().split())
    assert len(reader.pages)==pages and 'EAST BAY MUNICIPAL UTILITY DISTRICT' in cover and 'Dated: '+date in cover
    selected=[('cover',1),('future_amendment_conditions',19),('reported_rate_covenant',22),
        ('definitions',definition),('debt_service_definitions',definition+1),('debt_service_continued',definition+2),('policy_target',policy),
        ('summary_rate_covenant',summary),('proposed_amendment_notice',future_start),
        ('proposed_rate_redline',future_rate),('proposed_default_caveat',future_caveat)]
    evidence=[]
    for role,page in selected:
        text=reader.pages[page-1].extract_text();norm=' '.join(text.split())
        if role=='reported_rate_covenant':assert '1.1 times' in norm and 'Rate Covenant' in norm
        if role=='policy_target':assert '1.6 times' in norm and 'policy target' in norm
        if role=='future_amendment_conditions':assert 'majority in principal' in norm and 'certificate' in norm and 'Trustee' in norm
        if role=='proposed_default_caveat':assert 'shall not constitute a default or an' in norm
        evidence.append({'role':role,'physical_page':page,'text':text})
        if role in {'reported_rate_covenant','proposed_rate_redline','proposed_default_caveat'}:
            with pdfium.PdfDocument(str(source/name)) as pdf:
                bitmap=pdf[page-1].render(scale=1.4);bitmap.to_pil().save(out/f'{system}-{role}-page-{page}.png');bitmap.close()
    systems.append({'system':system,'file':name,'physical_pages':pages,'statement_date_text':date,
        'reported_rate_covenant_multiple':'1.1','reported_policy_target_multiple':'1.6',
        'reported_rate_scope':'Adjusted net revenues / Bonds and Parity Debt; fiscal-year rate-setting covenant',
        'rate_covenant_source_type':'Official statement description and Appendix C summary; not an acquired executed full indenture',
        'proposed_amendment_supplement':'Thirty-Second' if system=='water' else 'Twenty-Second',
        'amendment_effective_condition':'Majority principal-owner consent plus written District certificate delivered/filed with Trustee',
        'amendment_effective_date':None,'amendment_effectiveness_verified':False,
        'future_caveat':'Proposed Appendix H caveat: failure to meet end-year threshold may not constitute default if specified rate-setting obligations were met; verify operative text and effective date first',
        'current_historical_applicability_qualified':False,'evidence':evidence})
doc={'source_id':receipt['source_id'],'source_receipt_sha256':sha256(source/'acquisition-complete.json'),
     'sources':receipt['sources'],'systems':systems,'contractual_compliance_qualified':False,
     'full_executed_indenture_chain_acquired':False,'visibility':'private','public_release_approved':False}
p=out/'profile.json';p.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
print(out);print(sha256(p));print('statement pages',sum(s['physical_pages'] for s in systems),'selected evidence pages',sum(len(s['evidence']) for s in systems))
