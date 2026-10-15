"""Read public PDF tables with bundled Python; preserve source pages/footnotes."""
import json,uuid
from pathlib import Path
from pypdf import PdfReader
import pypdfium2 as pdfium
from credit_atlas.utility_debt_service import context,parse_continuing,parse_acfr
from credit_atlas.workspace import sha256

root=Path.cwd();folder,receipt=context(root)
out=root/'artifacts/private'/('utility-debt-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
rows=[];rounded=[];documents=[];evidence=[]
for source in receipt['sources']:
    name=source['file']
    if not name.endswith('.pdf'):continue
    edition=int(name[-8:-4]);reader=PdfReader(folder/name)
    title=' '.join(reader.pages[0].extract_text().split())
    if 'EAST BAY MUNICIPAL UTILITY DISTRICT' not in title or str(edition) not in title:raise ValueError('Unexpected issuer/edition identity')
    documents.append({'file':name,'pages':len(reader.pages),'title_text':title,'source_sha256':source['sha256']})
    for i,page in enumerate(reader.pages):
        text=page.extract_text();normalized=' '.join(text.split())
        if name.startswith('ebmud-continuing'):
            system='wastewater' if 'TABLE 13:' in text and 'HISTORICAL OPERATING RESULTS AND DEBT SERVICE COVERAGE' in normalized else 'water' if 'TABLE 7:' in text and 'HISTORICAL OPERATING RESULTS AND DEBT SERVICE COVERAGE' in normalized else None
            if system:rows.extend(parse_continuing(text,system,edition,i+1))
        else:
            system='wastewater' if 'Wastewater System' in text else 'water' if 'Water System' in text else None
            if not ('Ten-Year Summary of Net Revenue and Debt Service Coverage' in normalized and '(in Millions)' in normalized):system=None
            if system:rounded.extend(parse_acfr(text,system,edition,i+1))
        if system:
            evidence.append({'file':name,'physical_page':i+1,'system':system,'text':text})
            with pdfium.PdfDocument(str(folder/name)) as pdf:
                bitmap=pdf[i].render(scale=1.4);bitmap.to_pil().save(out/f'{name[:-4]}-page-{i+1}.png');bitmap.close()
            if name.startswith('ebmud-continuing') and system=='water':
                evidence.append({'file':name,'physical_page':i+2,'system':system,'text':reader.pages[i+1].extract_text(),'role':'continued footnotes'})
                with pdfium.PdfDocument(str(folder/name)) as pdf:
                    bitmap=pdf[i+1].render(scale=1.4);bitmap.to_pil().save(out/f'{name[:-4]}-page-{i+2}.png');bitmap.close()
if len(rows)!=20 or len(rounded)!=60:raise ValueError('Incomplete utility source table coverage')
doc={'source_id':receipt['source_id'],'sources':receipt['sources'],'source_receipt_sha256':sha256(folder/'acquisition-complete.json'),
     'documents':documents,'continuing_rows':rows,'acfr_rounded_rows':rounded,'source_page_evidence':evidence,
     'contractual_compliance_qualified':False,'borrower_pd_lgd_calibrated':False,'original_publication_vintages_complete':False,
     'visibility':'private','public_release_approved':False}
p=out/'profile.json';p.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
(out/'receipt.json').write_text(json.dumps({'status':'PROFILE_BUILT','profile_sha256':sha256(p),
   'continuing_rows':len(rows),'rounded_acfr_rows':len(rounded),'source_pages':len(evidence),
   'parity_2dp_matches':sum(r['checks']['parity_matches_reported_2dp'] for r in rows),
   'total_2dp_matches':sum(r['checks']['total_matches_reported_2dp'] for r in rows)},indent=2),encoding='utf8')
print(out);print(sha256(p));print([(r['edition'],r['system'],r['year'],r['checks']) for r in rows if any(r['checks'][k]!='0' for k in ['revenue_bridge_residual_usd','maintenance_bridge_residual_usd','net_revenue_bridge_residual_usd','debt_service_bridge_residual_usd'])])
