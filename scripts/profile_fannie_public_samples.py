"""Descriptive public sample coverage; never qualify a full training population."""
import csv
import io
import re
import uuid
from collections import Counter
from datetime import datetime
from decimal import Decimal,InvalidOperation
from pathlib import Path
from credit_atlas.workspace import read_json,sha256,write_new

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/private/mortgage/fannie-public-samples-4d84128d3cb6'
EXPECTED='860dcf9ea0bc879977dc854f23d424c869e2783fd30dc9f36695939533429124'

def date_value(value,formats):
    for fmt in formats:
        try:return datetime.strptime(value,fmt).date()
        except ValueError:pass
    return None

def quality(rows,headers):
    return [{'position':i+1,'source_field':name,'rows':len(rows),'blank_cells':sum(r[i]=='' for r in rows),'literal_null_tokens':dict(sorted(Counter(r[i] for r in rows if r[i].strip().lower() in {'null','na','n/a'}).items()))} for i,name in enumerate(headers)]

def date_profile(values,formats):
    parsed=[date_value(x,formats) if x else None for x in values];valid=[x for x in parsed if x is not None]
    return {'valid':len(valid),'blank':sum(x=='' for x in values),'nonblank_unparsed':sum(bool(x) and y is None for x,y in zip(values,parsed)),'min':min(valid).isoformat() if valid else None,'max':max(valid).isoformat() if valid else None}

def load_rows(file,delimiter,header):
    rows=list(csv.reader(io.StringIO(file.read_text(encoding='utf-8-sig')),delimiter=delimiter))
    blank_records=sum(not r for r in rows)
    rows=[r for r in rows if r]
    if not rows:raise ValueError('Empty sample')
    headers=rows.pop(0) if header else ['position_'+str(i+1) for i in range(len(rows[0]))]
    if len(headers)!=len(set(headers)) or any(len(r)!=len(headers) for r in rows):raise ValueError('Inconsistent sample schema')
    return headers,rows,blank_records

def run():
    assert sha256(SOURCE/'acquisition-complete.json')==EXPECTED
    receipt=read_json(SOURCE/'acquisition-complete.json')
    for f in receipt['sources']:assert sha256(SOURCE/f['file'])==f['sha256']
    out=ROOT/'artifacts/private'/('fannie-public-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
    profiles=[];loan_keys={};dscr_keys=set()
    for f in receipt['sources']:
        if f['kind']!='sample':continue
        file=SOURCE/f['file']
        single=f['family']=='single-family'
        delimiter='|' if single else ','
        headers,rows,blank_records=load_rows(file,delimiter,not single)
        p={'file':f['file'],'family':f['family'],'rows':len(rows),'blank_csv_records':blank_records,'columns':len(headers),'source_positions':len(rows)*len(headers),'delimiter':delimiter,'header_present':not single,'quality':quality(rows,headers),'representative_sampling_qualified':False}
        if single:
            if len(headers)<44:raise ValueError('Unexpected SF sample width')
            ids=[r[1] for r in rows];months=[r[2] for r in rows]
            p.update({'loan_count':len(set(ids)),'blank_loan_identifiers':sum(not x for x in ids),'duplicate_loan_month_rows':len(rows)-len(set(zip(ids,months))),
                'reporting_period':date_profile(months,['%m%Y']),'origination_period':date_profile([r[13] for r in rows],['%m%Y']),
                'raw_delinquency_counts':dict(sorted(Counter(r[39] for r in rows).items())),'raw_zero_balance_counts':dict(sorted(Counter(r[43] for r in rows).items())),
                'positional_mapping_status':'candidate_first44_fields_against_current_dictionary_not_full_schema_or_training_qualification'})
            p['monthly_cells']=[{'reporting_month_raw':m,'raw_delinquency':s,'records':n} for (m,s),n in sorted(Counter((r[2],r[39]) for r in rows).items())]
        elif 'Reporting Period Date' in headers:
            d=[dict(zip(headers,r)) for r in rows];ids=[r['Loan Number'] for r in d];months=[r['Reporting Period Date'] for r in d]
            loan_keys['main']=set(ids)
            p.update({'loan_count':len(set(ids)),'duplicate_loan_reporting_rows':len(rows)-len(set(zip(ids,months))),
                'reporting_period':date_profile(months,['%m/%d/%Y','%Y-%m-%d']),
                'acquisition_period':date_profile([r['Acquisition Date'] for r in d],['%m/%d/%Y','%Y-%m-%d']),
                'payment_status_counts':dict(sorted(Counter(r['Loan Payment Status'] for r in d).items())),
                'sdq_indicator_counts':dict(sorted(Counter(r['SDQ Indicator'] for r in d).items()))})
            p['monthly_cells']=[{'reporting_period_raw':m,'payment_status':s,'records':n} for (m,s),n in sorted(Counter((r['Reporting Period Date'],r['Loan Payment Status']) for r in d).items())]
        elif headers==['Loan Number','Year','Year DSCR']:
            d=[dict(zip(headers,r)) for r in rows];ids=[r['Loan Number'] for r in d];loan_keys['dscr']=set(ids)
            ratios=[];invalid=0;missing=0
            for r in d:
                if not r['Year DSCR']:missing+=1;continue
                try:
                    value=Decimal(r['Year DSCR'])
                    if not value.is_finite():raise InvalidOperation
                    ratios.append(value)
                except InvalidOperation:invalid+=1
            dscr_keys={(r['Loan Number'],r['Year']) for r in d}
            p.update({'loan_count':len(set(ids)),'duplicate_loan_year_rows':len(rows)-len(dscr_keys),'years':dict(sorted(Counter(r['Year'] for r in d).items())),'reported_dscr':{'valid':len(ratios),'blank':missing,'invalid':invalid,'min_exact':str(min(ratios)) if ratios else None,'max_exact':str(max(ratios)) if ratios else None,'below_one':sum(x<1 for x in ratios),'ratio_recomputed_from_cashflow_and_debt_service':False},'definition':'Reported annual NCF/debt service;credit-facility value may be deal-level;not monthly DSCR.'})
        else:raise ValueError('Unknown multifamily sample schema')
        profiles.append(p)
    assert len(profiles)==3 and set(loan_keys)=={'main','dscr'}
    doc={'source_id':receipt['source_id'],'source_receipt_sha256':EXPECTED,'sources':receipt['sources'],'profiles':profiles,
         'multifamily_link_support':{'main_loans':len(loan_keys['main']),'annual_dscr_loans':len(loan_keys['dscr']),'overlap_loans':len(loan_keys['main']&loan_keys['dscr']),'dscr_only_loans':len(loan_keys['dscr']-loan_keys['main']),'main_only_loans':len(loan_keys['main']-loan_keys['dscr']),'annual_dscr_rows':len(dscr_keys),'monthly_join_performed':False},
         'gates':{'full_dataset_acquired':False,'sample_representativeness_proven':False,'full_schema_compatibility_qualified':False,'mortgage_pd12_training_qualified':False,'annual_dscr_numerator_denominator_available':False,'contractual_covenant_compliance_qualified':False,'authenticated_terms_accepted':False},
         'limitations':['Issuer offers these samples to format a database;sampling design/representative multi-vintage support has not been established.',
                        'Single-family field positions are candidate source descriptions;current dictionary and sample vintages may differ.',
                        'Multifamily annual DSCR is a reported ratio,not independently recomputed debt-service coverage;do not repeat annual ratios across monthly rows.',
                        'Full Data Dynamics data still requires registration/terms;public samples do not bypass that access requirement.',
                        'Fannie and Freddie populations/identifiers are separate;no merge into the frozen D01 panel or model refit performed.'],
         'visibility':'private','public_release_approved':False}
    write_new(out/'profile.json',doc);write_new(out/'receipt.json',{'status':'PUBLIC_SAMPLE_COVERAGE_PROFILED','profile_sha256':sha256(out/'profile.json'),'files_profiled':len(profiles),'source_rows':sum(p['rows'] for p in profiles),'source_positions':sum(p['source_positions'] for p in profiles)})
    print(out);print(sha256(out/'profile.json'))
    print([{k:p[k] for k in ['file','rows','columns','loan_count']} for p in profiles]);print(doc['multifamily_link_support'])
    return out

if __name__=='__main__':run()
