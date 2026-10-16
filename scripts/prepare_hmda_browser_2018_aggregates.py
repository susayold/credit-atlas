import argparse
import json
from pathlib import Path
import duckdb

parser=argparse.ArgumentParser(description="Build private aggregate tables for the official 2018 HMDA Three-Year LAR.")
parser.add_argument("--data-root",type=Path,required=True,help="CreditAtlas data workspace root that contains data/private/hmda and artifacts/private")
root=parser.parse_args().data_root.resolve()
case=root/"data/private/hmda/hmda-browser-three-year-2018"
source=case/"hmda-2018-three-year-national.csv"
out=root/"artifacts/private/hmda-2018-work/aggregates.json"
tmp=root/"artifacts/private/hmda-2018-work/tmp"
tmp.mkdir(parents=True,exist_ok=True)
# Include practical portfolio/underwriting/geography slices. Do not export institution IDs.
dims=["loan_type","loan_purpose","lien_status","occupancy_type","derived_dwelling_category","debt_to_income_ratio","derived_race","derived_ethnicity","derived_sex","applicant_credit_score_type","ltv_band","rate_band","state_code","county_code","purchaser_type","preapproval"]
fields=",\n".join(f'("{x}")' for x in dims)
case_expr=" ".join(f"WHEN GROUPING(\"{x}\")=0 THEN '{x}'" for x in dims)
value_expr=" ".join(f"WHEN GROUPING(\"{x}\")=0 THEN coalesce(\"{x}\", '(blank)')" for x in dims)
con=duckdb.connect()
con.execute("SET threads=4")
con.execute("SET memory_limit='4GB'")
con.execute("SET temp_directory=?",[str(tmp)])
query=f'''SELECT CASE {case_expr} END AS dimension, CASE {value_expr} END AS category,
 count(*) AS records,
 count(*) FILTER (WHERE action_taken IN ('1','2','3')) AS decision_denominator,
 count(*) FILTER (WHERE action_taken='3') AS denied_numerator
FROM (SELECT *,
 CASE WHEN trim(coalesce("loan_to_value_ratio",'')) IN ('NA','Exempt') THEN trim("loan_to_value_ratio") WHEN try_cast("loan_to_value_ratio" AS DOUBLE) IS NULL THEN 'Other/missing' WHEN try_cast("loan_to_value_ratio" AS DOUBLE)<60 THEN '<60' WHEN try_cast("loan_to_value_ratio" AS DOUBLE)<80 THEN '60-<80' WHEN try_cast("loan_to_value_ratio" AS DOUBLE)<90 THEN '80-<90' WHEN try_cast("loan_to_value_ratio" AS DOUBLE)<100 THEN '90-<100' ELSE '100+' END AS ltv_band,
 CASE WHEN trim(coalesce("interest_rate",'')) IN ('NA','Exempt') THEN trim("interest_rate") WHEN try_cast("interest_rate" AS DOUBLE) IS NULL THEN 'Other/missing' WHEN try_cast("interest_rate" AS DOUBLE)<3 THEN '<3' WHEN try_cast("interest_rate" AS DOUBLE)<4 THEN '3-<4' WHEN try_cast("interest_rate" AS DOUBLE)<5 THEN '4-<5' WHEN try_cast("interest_rate" AS DOUBLE)<6 THEN '5-<6' WHEN try_cast("interest_rate" AS DOUBLE)<7 THEN '6-<7' ELSE '7+' END AS rate_band
 FROM read_csv(?, header=true, all_varchar=true, strict_mode=true, ignore_errors=false, null_padding=false)) src
WHERE action_taken IN ('1','2','3','4','5','6','7','8')
GROUP BY GROUPING SETS ({fields})
ORDER BY dimension, records DESC, category'''
rows=con.execute(query,[str(source)]).fetchall()
# Denial reasons have meaning only on action 3; preserve exact source codes, do not infer value labels.
reason_fields=['denial_reason-1','denial_reason-2','denial_reason-3','denial_reason-4']
reason_rows=[]
for field in reason_fields:
    q=f'''SELECT '{field}' AS dimension, coalesce("{field}",'(blank)') AS category,
    count(*) AS records, count(*) AS decision_denominator, count(*) AS denied_numerator
    FROM read_csv(?,header=true,all_varchar=true,strict_mode=true,ignore_errors=false,null_padding=false)
    WHERE action_taken='3' GROUP BY 2 ORDER BY 3 DESC,2'''
    reason_rows.extend(con.execute(q,[str(source)]).fetchall())
# Public official action counts, reconciled in the separate audit receipt.
rec=json.loads((case/'audit-receipt.json').read_text(encoding='utf-8'))
actions=rec['profile']['recognized_action_counts']
allrows=[]
for dim,cat,n,den,num in rows+reason_rows:
    rate=(num/den) if den else None
    allrows.append({'dimension':dim,'category':cat,'records':int(n),'decision_denominator':int(den),'denied_numerator':int(num),'descriptive_denied_share':rate})
summary=rec['profile']['summary']
decision_den=sum(int(actions[str(i)]) for i in (1,2,3)); denied=int(actions['3'])
payload={'status':'PASS','dataset_vintage':rec['dataset_vintage'],'freeze_date':rec['freeze_date'],'source_sha256':rec['sha256'],'audit_id':rec['audit_id'],'source_rows':int(summary['records']),'in_domain_rows':sum(int(x) for x in actions.values()),'quarantined_rows':int(summary['invalid_action_rows']),'decision_denominator':decision_den,'denied_numerator':denied,'descriptive_denied_share':denied/decision_den,'actions':{k:int(v) for k,v in actions.items()},'breakdowns':allrows,'dimension_fields':dims+reason_fields,'bin_definitions':{'ltv_band':'<60; 60-<80; 80-<90; 90-<100; 100+; preserve NA/Exempt; unknown as Other/missing','rate_band':'<3; 3-<4; 4-<5; 5-<6; 6-<7; 7+; preserve NA/Exempt; unknown as Other/missing'},'notes':['Action-code -1 rows are excluded from these aggregations and quarantined, not recoded.','Denied share is action 3 divided by actions 1+2+3; it is not probability of default, delinquency, or repayment performance.','Denial-reason categories are action-3 rows only.','No row-level LEI, applicant identifier, or loan-level record is exported.']}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','output':str(out),'aggregates':len(allrows),'dimensions':len(set(r['dimension'] for r in allrows)),'records':payload['in_domain_rows'],'quarantined':payload['quarantined_rows'],'denominator':decision_den,'denied':denied,'share':payload['descriptive_denied_share']}))
