"""Independent PDF word coordinates and rational debt-service recomputation."""
import hashlib,json,re,uuid
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import pdfplumber

root=Path.cwd();profile=root/'artifacts/private/utility-debt-profile-9b7023d435f2/profile.json'
doc=json.loads(profile.read_text(encoding='utf8'));source=root/'data/private/business'/doc['source_id']
out=root/'artifacts/private'/('utility-debt-audit-'+uuid.uuid4().hex[:12]);out.mkdir()
issues=[];checks=[];coordinates=[];hashes={s['file']:hashlib.sha256((source/s['file']).read_bytes()).hexdigest()==s['sha256'] for s in doc['sources']}
def number(text):
    text=re.sub(r'(?<=\d)\(\d{1,2}\)$','',text).replace('$','').replace(',','')
    if not re.fullmatch(r'\(?-?\d+(?:\.\d+)?\)?',text):return None
    return -Decimal(text[1:-1]) if text.startswith('(') and text.endswith(')') else Decimal(text)

grouped=defaultdict(list)
for row in doc['continuing_rows']:grouped[(row['file'],row['physical_page'])].append(row)
for (filename,page_number),records in grouped.items():
    with pdfplumber.open(source/filename) as pdf:words=pdf.pages[page_number-1].extract_words()
    years=[str(r['year']) for r in records];header_bands=defaultdict(list)
    for word in words:
        if word['text'] in years:header_bands[round(word['bottom'],1)].append(word)
    header=next((sorted(v,key=lambda w:w['x0']) for v in header_bands.values() if len(v)==5 and [w['text'] for w in sorted(v,key=lambda w:w['x0'])]==years),None)
    if not header:issues.append([filename,'year columns missing']);continue
    centers=[(w['x0']+w['x1'])/2 for w in header]
    edges=[centers[0]-(centers[1]-centers[0])/2,*[(a+b)/2 for a,b in zip(centers,centers[1:])],centers[-1]+(centers[-1]-centers[-2])/2]
    first_y=header[0]['bottom'];stop=min(w['top'] for w in words if w['text']=='(1)' and w['x0']<100 and w['top']>first_y)
    bands=defaultdict(dict)
    for word in words:
        if word['top']<first_y or word['top']>=stop:continue
        value=number(word['text']);x=(word['x0']+word['x1'])/2
        if value is None:continue
        column=next((i for i in range(5) if edges[i]<=x<edges[i+1]),None)
        if column is not None:bands[round(word['bottom'],0)][column]=value
    vectors=[(y,[v[i] for i in range(5)]) for y,v in bands.items() if set(v)==set(range(5))]
    for field in records[0]['values']:
        expected=[Decimal(r['values'][field]) for r in records]
        matching=[y for y,v in vectors if v==expected]
        if not matching:issues.append([filename,page_number,field,'column vector not found'])
        coordinates.append({'file':filename,'page':page_number,'field':field,'year_columns':years,'pdf_baselines':matching,'matches':bool(matching)})
    for r in records:
        v={k:int(x) for k,x in r['values'].items() if not k.startswith('reported_')}
        residuals={
            'revenue_bridge_residual_usd':v['revenue_after_transfers']-v['revenue_before_transfers']-v['stabilization_deposits']-v['stabilization_withdrawals'],
            'maintenance_bridge_residual_usd':v['operation_maintenance']-v['operating_expenses']-v['tax_expense_offset'],
            'net_revenue_bridge_residual_usd':v['net_revenues']-v['revenue_after_transfers']+v['operation_maintenance'],
            'debt_service_bridge_residual_usd':v['total_debt_service']-v['parity_debt_service']-v['subordinate_debt_service']}
        exact={basis:Fraction(v['net_revenues'],v[denominator]) for basis,denominator in [('parity','parity_debt_service'),('total','total_debt_service')]}
        rounded={basis:Decimal((f.numerator*200+f.denominator)//(2*f.denominator))/100 for basis,f in exact.items()}
        good=all(str(value)==r['checks'][key] for key,value in residuals.items()) and all(rounded[k]==Decimal(r['values']['reported_'+k+'_dscr']) for k in exact)
        if not good:issues.append([r['edition'],r['system'],r['year'],'rational calculation mismatch'])
        checks.append({'edition':r['edition'],'system':r['system'],'year':r['year'],'matches':good,'residuals_usd':residuals,
                       'rational_dscrs':{k:{'numerator':f.numerator,'denominator':f.denominator,'rounded_2dp':str(rounded[k])} for k,f in exact.items()}})

rounded_checks=[]
for file_name in sorted({r['file'] for r in doc['acfr_rounded_rows']}):
    records=[r for r in doc['acfr_rounded_rows'] if r['file']==file_name]
    with pdfplumber.open(source/file_name) as pdf:
        for page_number in sorted({r['physical_page'] for r in records}):
            rows=[r for r in records if r['physical_page']==page_number];words=pdf.pages[page_number-1].extract_words()
            for r in rows:
                expected=[Decimal(v) for v in r['values'].values()];found=[]
                for word in words:
                    if not re.fullmatch(str(r['year'])+r'(\(\d+\))?',word['text']):continue
                    candidates=[w for w in words if w['x0']>word['x1']+5 and abs(w['bottom']-word['bottom'])<1.5]
                    # PDF typography can split a number into touching glyph runs
                    # (e.g. "4" + "25.1"). Join only numeric runs whose boxes
                    # touch within 0.1 point; never join distinct table columns.
                    tokens=[]
                    for cell in sorted(candidates,key=lambda w:w['x0']):
                        if tokens and re.fullmatch(r'[\d,.]+',cell['text']) and re.fullmatch(r'[\d,.]+',tokens[-1]['text']) and abs(cell['x0']-tokens[-1]['x1'])<.1:
                            tokens[-1]={'text':tokens[-1]['text']+cell['text'],'x1':cell['x1']}
                        else:tokens.append({'text':cell['text'],'x1':cell['x1']})
                    numbers=[number(w['text']) for w in tokens];numbers=[n for n in numbers if n is not None]
                    if numbers==expected:found.append(word['bottom'])
                rounded_checks.append({'file':file_name,'page':page_number,'year':r['year'],'matches':bool(found)})
                if not found:issues.append([file_name,page_number,r['year'],'rounded row not found'])
result={'status':'PASS' if all(hashes.values()) and not issues else 'ISSUES_FOUND',
        'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),'source_hash_checks':hashes,
        'continuing_value_cells':sum(len(r['values']) for r in doc['continuing_rows']),
        'acfr_value_cells':sum(len(r['values']) for r in doc['acfr_rounded_rows']),
        'pdf_column_vector_checks':coordinates,'rational_checks':checks,'rounded_row_checks':rounded_checks,'issues':issues,
        'scope':'Independent PDF engine/word column vectors and exact rational calculations; not contractual compliance or whole-report accounting audit',
        'contractual_compliance_qualified':False}
(out/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(out);print(result['status']);print(issues[:20])
if result['status']!='PASS':raise SystemExit(1)
