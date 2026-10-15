"""Literal issuer workbook definitions and conservative prepared-column review."""
import json,uuid
from pathlib import Path
import openpyxl
from credit_atlas.workspace import sha256,read_json,write_new
root=Path.cwd();folder=root/'data/private/retail/lendingclub-dictionary-source-65e0222b7c42'
receipt=read_json(folder/'acquisition-complete.json');assert sha256(folder/'acquisition-complete.json')=='2c38861ef1b62a92dc79c1d37195ccf6f1e5885ef8f0f17c15d3c830061460ca'
source=receipt['sources'][0];path=folder/source['file'];assert sha256(path)==source['sha256']
workbook=openpyxl.load_workbook(path,read_only=True,data_only=False)
definitions=[]
for sheet in workbook:
    for number,row in enumerate(sheet.iter_rows(),1):
        a=row[0].value;b=row[1].value
        if number==1 or not isinstance(a,str) or not a.strip() or not isinstance(b,str) or not b.strip():continue
        if row[0].data_type=='f' or row[1].data_type=='f':raise ValueError('Unexpected formula definition')
        definitions.append({'sheet':sheet.title,'row':number,'source_field':a.strip(),'source_description':b.strip(),
                            'field_cell':row[0].coordinate,'description_cell':row[1].coordinate})
loan={}
for d in definitions:
    if d['sheet']=='LoanStats':
        if d['source_field'] in loan:raise ValueError('Duplicate LoanStats definition')
        loan[d['source_field']]=d
profile=read_json(root/'artifacts/private/lendingclub-profile-28db23b7bd0a/profile.json')
aliases={'SubGrade':'sub_grade','EmploymentLength':'emp_length','open_act_il':'open_il_6m'}
review=[]
for name in profile['columns']:
    key=name if name in loan else aliases.get(name)
    definition=loan.get(key);mapping='exact_name' if name in loan else 'proposed_alias_requires_contributor_provenance' if definition else 'no_issuer_definition'
    if name in {'loan_status','LoanStatus'}:role='outcome_exclude'
    elif name=='id':role='identifier_exclude'
    elif name=='issue_d':role='booking_month_exclude_as_decision_timestamp'
    elif name in {'grade','SubGrade','int_rate','installment','term'}:role='decision_or_contract_output_review'
    elif name=='loan_amnt':role='possibly_decision_modified_amount_review'
    elif name=='EmploymentLength':role='prepared_encoding_unverified'
    else:role='candidate_requires_application_asof_evidence'
    caveats=[]
    if name=='dti':caveats.append('Issuer definition excludes mortgage and requested LC loan;not total-obligation affordability DTI. Prepared scale/sentinel meaning still requires provenance.')
    if name=='annual_inc':caveats.append('Issuer definition is self-reported registration income;not verified net/disposable income.')
    if name=='loan_amnt':caveats.append('Issuer definition permits credit-department amount reduction;not certified original requested amount.')
    if name=='int_rate':caveats.append('Dictionary does not certify contributor fraction/percent conversion;source min/max alone are not a transformation recipe.')
    if name=='EmploymentLength':caveats.append('Observed0–11/fractional values are not explained by original string emp_length definition.')
    if name=='LoanStatus':caveats.append('No original definition;published rows prove0=ChargedOff,1=FullyPaid co-occurrence,not contributor code provenance.')
    review.append({'prepared_field':name,'definition_mapping':mapping,'issuer_definition':definition,'proposed_role':role,
                   'application_time_qualified':False,'contributor_transform_qualified':False,'caveats':caveats})
out=root/'artifacts/private'/('lendingclub-dictionary-profile-'+uuid.uuid4().hex[:12]);out.mkdir()
doc={'source_id':receipt['source_id'],'source_receipt_sha256':sha256(folder/'acquisition-complete.json'),'source':source,
     'definitions':definitions,'column_review':review,'workbook_metadata':{'created':str(workbook.properties.created),'modified':str(workbook.properties.modified)},
     'workbook_metadata_is_publication_vintage':False,'coverage':{'prepared_columns':len(review),
        'exact_names':sum(x['definition_mapping']=='exact_name' for x in review),
        'proposed_aliases':sum(x['definition_mapping'].startswith('proposed_alias') for x in review),
        'undefined':sum(x['issuer_definition'] is None for x in review)},
     'application_time_features_qualified':False,'contributor_preprocessing_verified':False,'model_training_performed':False,
     'visibility':'private','public_release_approved':False}
write_new(out/'profile.json',doc);print(out);print(sha256(out/'profile.json'));print(doc['coverage']);print('definitions',len(definitions))
