"""Source-based full-issue/no-redemption note schedules, distinct from actual payments."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import re
from .workspace import read_json,sha256,contained

def catalog(root):
    found=[]
    for p in (root/'artifacts/private').glob('apple-notes-*/catalog-complete.json'):
        if re.fullmatch(r'apple-notes-[0-9a-f]{12}',p.parent.name):
            receipt=read_json(p);found.append((receipt['created_at'],p,receipt))
    if not found:raise ValueError('No acquired note terms catalog')
    _,p,receipt=max(found,key=lambda x:x[0]);data=read_json(p.parent/'catalog.json');source=data['source']
    if receipt['catalog_id']!=p.parent.name or sha256(p.parent/'catalog.json')!=receipt['catalog_sha256'] or sha256(root/'scripts/build_apple_note_catalog.py')!=receipt['builder_sha256']:raise ValueError('Note catalog or extraction method changed')
    if not re.fullmatch(r'sec-documents-[0-9a-f]{12}',source['folder']):raise ValueError('Invalid acquired note folder')
    folder=contained(root,'data/private/sec-documents/'+source['folder']);acq=read_json(folder/'acquisition.json')
    if acq['status']!='ACQUIRED' or acq['url']!=source['url'] or acq['file']!=source['file'] or acq['sha256']!=source['pdf_sha256'] or sha256(contained(root,'data/private/sec-documents/'+source['folder']+'/'+source['file']))!=source['pdf_sha256'] or sha256(folder/'pages.json')!=source['pages_sha256']:raise ValueError('Acquired note evidence changed')
    pages=read_json(folder/'pages.json')
    for note in data['notes']:
        for e in note['evidence']:
            text=re.sub(r'\s+',' ',pages[e['pdf_page']-1]['text'])
            if text!=e['page_text'] or not all(a in text for a in e['anchors']):raise ValueError('Note clause evidence changed')
    return data,receipt

def contractual_path(note):
    """Regular May/November coupons only; no inferred principal reductions or calls."""
    if note['frequency']!=2 or note['coupon_month_days']!=[[5,12],[11,12]]:raise ValueError('Unsupported regular coupon pattern')
    principal=Decimal(note['original_issue_principal_usd_exact']);rate=Decimal(note['coupon_rate_exact'])
    issue=date.fromisoformat(note['issue_date']);maturity=date.fromisoformat(note['maturity_date']);first=date.fromisoformat(note['first_coupon_date'])
    if principal<=0 or not rate.is_finite() or not Decimal(0)<rate<Decimal(1) or issue.month!=5 or issue.day!=12 or first!=date(issue.year,11,12) or maturity.month!=5 or maturity.day!=12 or not issue<maturity or maturity.year-issue.year>50:raise ValueError('Unsupported source note terms')
    prior=issue;result=[]
    for year in range(issue.year,maturity.year+1):
        for month in [5,11]:
            due=date(year,month,12)
            if not first<=due<=maturity:continue
            days360=360*(due.year-prior.year)+30*(due.month-prior.month)+(due.day-prior.day)
            if days360!=180:raise ValueError('Unsupported irregular coupon period')
            interest=principal*rate*Decimal(days360)/Decimal(360)
            redemption=principal if due==maturity else Decimal(0)
            if interest*100!=(interest*100).to_integral_value():raise ValueError('Sub-cent contractual amount requires rounding convention')
            result.append({'note_id':note['note_id'],'nominal_coupon_date':str(due),'adjusted_payment_date':None,'accrual_start':str(prior),'accrual_end_exclusive':str(due),'days360':days360,'year_fraction_exact':'0.5','basis_principal_usd_exact':str(principal),'coupon_rate_exact':str(rate),'scheduled_interest_usd_exact':format(interest,'f'),'scheduled_principal_usd_exact':format(redemption,'f'),'scheduled_total_usd_exact':format(interest+redemption,'f'),'formula':'original_issue_principal × coupon_rate × 180/360; principal at contractual maturity','source_pdf_pages':sorted({e['pdf_page'] for e in note['evidence']})})
            prior=due
    return result

def report(views,identifier,query):
    if set(query)-{'view_id','cik','asof','end','note_id'} or query.get('view_id',identifier)!=identifier:raise ValueError('Invalid note schedule filters')
    cutoff=query.get('asof','2026-10-10');end=query.get('end','2035-05-12')
    for value in [cutoff,end]:
        if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('ISO schedule dates required')
        date.fromisoformat(value)
    if end<cutoff or (date.fromisoformat(end)-date.fromisoformat(cutoff)).days>50*366:raise ValueError('Bounded future schedule range required')
    snapshot=views.view(identifier);cik=query.get('cik','0000320193');entity=next((e for e in snapshot['entities'] if e['cik']==cik),None)
    if entity is None:raise ValueError('Unknown note issuer CIK')
    data,receipt=catalog(views.root);note_id=query.get('note_id','all')
    if note_id not in {'all',*(n['note_id'] for n in data['notes'])}:raise ValueError('Unknown acquired note')
    supported=cik==data['cik'] and data['source']['filing_date']<=cutoff
    notes=[n for n in data['notes'] if note_id in {'all',n['note_id']}] if supported else []
    rows=sorted([r for n in notes for r in contractual_path(n) if cutoff<r['nominal_coupon_date']<=end],key=lambda r:(r['nominal_coupon_date'],r['note_id']))
    annual={}
    for r in rows:
        key=r['nominal_coupon_date'][:4];bucket=annual.setdefault(key,{'year':key,'scheduled_interest_usd_exact':Decimal(0),'scheduled_principal_usd_exact':Decimal(0),'scheduled_total_usd_exact':Decimal(0),'rows':0})
        for field in ['scheduled_interest_usd_exact','scheduled_principal_usd_exact','scheduled_total_usd_exact']:bucket[field]+=Decimal(r[field])
        bucket['rows']+=1
    annual=[{k:format(v,'f') if isinstance(v,Decimal) else v for k,v in b.items()} for b in annual.values()]
    fields=['scheduled_interest_usd_exact','scheduled_principal_usd_exact','scheduled_total_usd_exact']
    totals={f:format(sum((Decimal(r[f]) for r in rows),Decimal(0)),'f') if notes else None for f in fields}
    return {'view_id':identifier,'entity':entity,'filters':{'cik':cik,'asof':cutoff,'end':end,'note_id':note_id},'catalog_id':receipt['catalog_id'],'catalog_sha256':receipt['catalog_sha256'],'status':'SOURCE_TERMS_SCENARIO_AVAILABLE' if notes else 'NO_ACQUIRED_NOTE_TERMS_AS_OF','source':data['source'] if supported else None,'filing_identity':data['filing_identity'] if supported else None,'notes':notes,'rows':rows,'annual':annual,'totals':totals,'path_assumptions':{'principal_basis':'Original full issue principal; current outstanding is unknown','early_redemption':False,'default_or_restructuring':False,'additional_issuance':False,'business_day_adjustment':'Unresolved; nominal coupon dates retained separately from adjusted payment dates'},'qualification':data['qualification'],'method_source_sha256':sha256(Path(__file__)),
        'limitations':['Source terms are real; projected amounts assume original full issue principal and no calls/defaults/additional issuance. They are not actual paid or current outstanding amounts.','Only four May2025 Apple note series; not all issuer debt and not a borrower DSCR denominator.','Cutoff filters source filing availability and nominal coupon dates (asof exclusive, end inclusive). No paid/unpaid status is inferred.','Business Day is defined by the base indenture; calendar/holiday adjustments are unqualified and adjusted payment dates remain null.','Dates near the cutoff may move under business-day rules; nominal-date totals are not exact settlement-date cashflow totals.','No make-whole/early redemption valuation, overdue interest, default recovery or full legal regime engine.','Annual buckets are calendar-year nominal schedules, not fiscal-year financial statement maturity buckets.'],'visibility':'private','public_release_approved':False}
