"""CFR definition evidence for observed mirror fields; no XSD or filing qualification."""
import re
from xml.etree import ElementTree as ET
from .workspace import contained,read_json,sha256
from .absee_profile import saved_report

SOURCE='schedule-al-1b72bcb43754'
RECEIPT='4cfb99d09c146fb50bd81ef83ca0b7009fe0c1c94d5e968748c5f8833a28b91b'
OFFICIAL_AUDIT='artifacts/private/woart-absee-field-semantics-audit-fafadee77978/audit.json'
OFFICIAL_RECEIPT='artifacts/private/woart-absee-field-semantics-audit-fafadee77978/receipt.json'
OFFICIAL_AUDIT_SHA256='5698bb42fcca33c7781d7d117b080d116b24ad8028dbb8338a6efbf1214368f8'
GROUPS={
 'a':['assetTypeNumber','assetNumber'],
 'b':['reportingPeriodBeginningDate','reportingPeriodEndingDate'],
 'c':['originatorName','originationDate','originalLoanAmount','originalLoanTerm','loanMaturityDate',
      'originalInterestRatePercentage','interestCalculationTypeCode','originalInterestRateTypeCode',None,
      'originalFirstPaymentDate','underwritingIndicator','gracePeriodNumber','paymentTypeCode','subvented'],
 'd':['vehicleManufacturerName','vehicleModelName','vehicleNewUsedCode','vehicleModelYear','vehicleTypeCode','vehicleValueAmount','vehicleValueSourceCode'],
 'e':['obligorCreditScoreType','obligorCreditScore','obligorIncomeVerificationLevelCode','obligorEmploymentVerificationCode','coObligorIndicator','paymentToIncomePercentage','obligorGeographicLocation'],
 'f':['assetAddedIndicator','remainingTermToMaturityNumber','reportingPeriodModificationIndicator','servicingAdvanceMethodCode',
      'reportingPeriodBeginningLoanBalanceAmount','nextReportingPeriodPaymentAmountDue','reportingPeriodInterestRatePercentage',
      'nextInterestRatePercentage','servicingFeePercentage',None,None,'otherAssessedUncollectedServicerFeeAmount',
      'scheduledInterestAmount','scheduledPrincipalAmount','otherPrincipalAdjustmentAmount','reportingPeriodActualEndBalanceAmount',
      'reportingPeriodScheduledPaymentAmount','totalActualAmountPaid','actualInterestCollectedAmount','actualPrincipalCollectedAmount',
      'actualOtherCollectedAmount',None,'interestPaidThroughDate',None,'currentDelinquencyStatus'],
 'g':['primaryLoanServicerName',None],
 'i':['chargedoffPrincipalAmount','recoveredAmount'],
 'j':['modificationTypeCode','paymentExtendedNumber'],
 'k':['repossessedProceedsAmount',None]}
MAPPING={field:f'3({group})({i})' for group,fields in GROUPS.items() for i,field in enumerate(fields,1) if field}
MAPPING.update({'zeroBalanceEffectiveDate':'3(f)(24)(i)','zeroBalanceCode':'3(f)(24)(ii)',
                'assetSubjectDemandIndicator':'3(h)','repossessedIndicator':'3(k)'})

def clauses(payload):
    if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper():raise ValueError('DTD not accepted')
    tree=ET.fromstring(payload);result={};active=False;section=None;number=None
    headings={'a':'Asset numbers.','b':'Reporting period.','c':'General information about the automobile loan.',
              'd':'Information related to the vehicle.','e':'Information related to the obligor.',
              'f':'Information related to activity on the loan.','g':'Information related to servicers.',
              'h':'Asset subject to demand.','i':'Information related to loans that have been charged off.',
              'j':'Information related to loan modifications.','k':'Repossessed.'}
    for position,p in enumerate(tree.iter('P')):
        text=' '.join(''.join(p.itertext()).split())
        if text.startswith('Item 3. Automobile loans.'):active=True;continue
        if active and text.startswith('Item 4. Automobile leases.'):break
        if not active or text.startswith('Instruction'):continue
        head=next((k for k,v in headings.items() if text.startswith(f'({k}) '+v)),None)
        if head:
            section=head;number=None
            match=re.search(r'\((\d+)\) ',text)
            if match:number=match[1];key=f'3({section})({number})'
            else:key=f'3({section})'
        else:
            match=re.match(r'^\((\d+)\) ',text)
            roman=re.match(r'^\((i|ii)\) ',text)
            if match:
                number=match[1];key=f'3({section})({number})'
            elif roman and section=='f' and number=='24':key=f'3(f)(24)({roman[1]})'
            else:continue
        if key in result:raise ValueError('Duplicate Schedule AL clause')
        result[key]={'text':text,'xml_paragraph_index':position}
    if len(result)<65 or '3(f)(25)' not in result:raise ValueError('Incomplete automobile-loan clauses')
    return result

def report(root,query):
    if query:raise ValueError('ABS-EE dictionary has no scope filters')
    folder=contained(root,'data/private/structured/'+SOURCE)
    if sha256(folder/'acquisition-complete.json')!=RECEIPT:raise ValueError('Schedule AL receipt changed')
    receipt=read_json(folder/'acquisition-complete.json')
    for item in receipt['sources']:
        path=contained(folder,item['file'])
        if path.stat().st_size!=item['bytes'] or sha256(path)!=item['sha256']:raise ValueError('Schedule AL source changed')
    xml=next(x for x in receipt['sources'] if x['file'].endswith('.xml'))
    definitions=clauses((folder/xml['file']).read_bytes())
    profile=saved_report(root,{})
    columns=sorted({c for p in profile['periods'] for c in p['columns']})
    rows=[]
    for field in columns:
        item=MAPPING.get(field)
        if item not in definitions:raise ValueError('Observed field lacks proposed CFR correspondence')
        periods=[p for p in profile['periods'] if field in p['columns']]
        rows.append({'field':field,'schedule_al_item':item,'definition':definitions[item]['text'],
                     'xml_paragraph_index':definitions[item]['xml_paragraph_index'],
                     'present_periods':len(periods),'absent_periods':len(profile['periods'])-len(periods),
                     'present_schema_rows':sum(p['rows'] for p in periods),
                     'missing_present_schema_rows':sum(p['missing_by_field'][field] for p in periods),
                     'mapping_status':'ANALYST_PROPOSED_CORRESPONDENCE_NOT_XSD_VERIFIED',
                     'source_url':xml['url']})
    official_path=contained(root,OFFICIAL_AUDIT)
    official_receipt_path=contained(root,OFFICIAL_RECEIPT)
    official_receipt=read_json(official_receipt_path)
    if (sha256(official_path)!=OFFICIAL_AUDIT_SHA256
            or sha256(official_path)!=official_receipt.get('audit_sha256')):
        raise ValueError('Official ABS-EE field semantics audit changed')
    official=read_json(official_path)
    if (official.get('status')!='AUTO_LOAN_XSD_FIELDS_PROFILED_AGAINST_OFFICIAL_PANEL'
            or official.get('row_count')!=880773 or official.get('period_count')!=20
            or len(official.get('field_profiles',{}))!=15
            or official.get('dataset_receipt_sha256')!=sha256(contained(root,'data/private/derived/woart-absee-panel-91efe12963d6/dataset-complete.json'))):
        raise ValueError('Official ABS-EE panel profile failed integrity checks')
    official_fields=[]
    for field,official_profile in official['field_profiles'].items():
        official_fields.append({'field':field,'panel_column':official_profile['panel_column'],'xsd_type':official_profile['xsd']['type'],
            'xsd_facets':official_profile['xsd']['facets'],'present_cells':official_profile['present_cells'],
            'null_or_empty_cells':official_profile['null_or_empty_cells'],'decimal_min':official_profile['decimal_min'],
            'decimal_max':official_profile['decimal_max'],'decimal_max_observed_scale':official_profile['decimal_max_observed_scale'],
            'decimal_negative_value_count':official_profile['decimal_negative_value_count'],
            'decimal_zero_value_count':official_profile['decimal_zero_value_count'],
            'observed_value_counts':official_profile['observed_value_counts'],
            'observed_examples':official_profile['observed_examples']})
    return {'source_id':SOURCE,'source_receipt_sha256':RECEIPT,'edition':receipt['edition'],
            'observed_fields':len(columns),'fields':rows,'mirror_source_id':profile['source_id'],
            'mirror_profile_sha256':'94e1e9d5742d04e20cd6203da0d11b7dafe7f18ba7ef517de5588d8c68c13ddd',
            'definition_scope':'2025 CFR Item3 automobile loans; not current-rule or technical enumeration verification',
            'xsd_verified':False,'xsd_verified_field_count':len(official_fields),
            'mirror_fidelity_verified':False,'model_ready':False,
            'raw_filing_xml_acquired':True,'official_panel':{'status':official['status'],
                'period_count':official['period_count'],'row_count':official['row_count'],
                'dataset_id':official['dataset_id'],'fields':official_fields,
                'cross_field_checks':official['cross_field_checks'],
                'audit_path':OFFICIAL_AUDIT,'receipt_sha256':sha256(official_receipt_path),
                'source_url':'https://www.sec.gov/Archives/edgar/data/2046523/000110465926111552/index.json',
                'xsd_url':'https://www.sec.gov/files/info/edgar/specifications/absxml.htm'},
            'current_rule_verified':False,
            'visibility':'private','public_release_approved':False,
            'interpretation_notes':[
                'Proposed mapping distinguishes origination score/PTI from current borrower information; PTI is not an affordability decision.',
                'Item3(f)(25) describes days delinquent under governing transaction terms. No sentinel conversion, default label or legal compliance conclusion is made.',
                'The official SEC Auto Loan XSD verifies the technical types/facets for the 15 fields shown in the official panel; this is not a full 62-field XML validation.',
                'Schedule AL requires reasons for zero balance; the Auto Loan XSD provides codes 1, 2, 3, 4, 5, 99. No code-to-causal-exit or default label is inferred.',
                'Schedule AL defines recoveries after charge-off and repossession proceeds net of fees/expenses. Counts in the panel are repeated row-month observations, not unique borrowers.',
                'Loan-level KPI dashboard, full current-field semantic verification, percentage display scale and legal transaction qualification remain open.']}
