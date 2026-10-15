"""Independent PDF engine checks selected clause roles and document identity."""
import hashlib,json,re,uuid
from pathlib import Path
import pdfplumber
root=Path.cwd();source=root/'data/private/business/utility-contract-source-cac5d22ec69d'
profile=root/'artifacts/private/utility-contract-profile-05bce98c9db8/profile.json'
doc=json.loads(profile.read_text(encoding='utf8'));checks=[];issues=[]
out=root/'artifacts/private'/('utility-contract-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
hashes={s['file']:hashlib.sha256((source/s['file']).read_bytes()).hexdigest()==s['sha256'] for s in doc['sources']}
for item in doc['systems']:
    with pdfplumber.open(source/item['file']) as pdf:
        cover=' '.join(pdf.pages[0].extract_text().split())
        identity=len(pdf.pages)==item['physical_pages'] and 'EAST BAY MUNICIPAL UTILITY DISTRICT' in cover and 'Dated: '+item['statement_date_text'] in cover
        checks.append({'system':item['system'],'role':'identity','matches':identity})
        if not identity:issues.append([item['system'],'identity'])
        for evidence in item['evidence']:
            norm=' '.join(pdf.pages[evidence['physical_page']-1].extract_text().split())
            role=evidence['role'];needles={
                'cover':['Series 2026','Dated: '+item['statement_date_text']],
                'reported_rate_covenant':['Rate Covenant','1.1 times','Parity Debt'],
                'policy_target':['1.6 times','policy target','Board'],
                'future_amendment_conditions':['majority in principal','certificate','Trustee'],
                'definitions':['Adjusted Net','Rate Stabilization','Maintenance Costs'],
                'debt_service_definitions':['Debt Service','Excluded Principal','SIFMA'],
                'debt_service_continued':['interest rate swap','liquidity facility','Fiscal Year'],
                'summary_rate_covenant':['1.1 times','rates, fees and charges'],
                'proposed_amendment_notice':['blue underlining','red strikethrough','Effective Date'],
                'proposed_rate_redline':['Rates and Charges','reasonably expected'],
                'proposed_default_caveat':['shall not constitute a default','commencement of the succeeding Fiscal Year']}.get(role,[])
            good=bool(needles) and all(n in norm for n in needles)
            checks.append({'system':item['system'],'role':role,'physical_page':evidence['physical_page'],'matches':good})
            if not good:issues.append([item['system'],role,[n for n in needles if n not in norm]])
result={'status':'PASS' if all(hashes.values()) and not issues else 'ISSUES_FOUND','checks':checks,'issues':issues,
    'source_hash_checks':hashes,'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
    'scope':'Independent PDF identity and 20 selected page clause-role checks; not executed contract or amendment-effectiveness verification',
    'contractual_compliance_qualified':False}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(out);print(result['status']);print(issues)
if issues or not all(hashes.values()):raise SystemExit(1)
