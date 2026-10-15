"""Create an explicit synthetic cash schedule/risk policy on real UPB observations."""
import json
import uuid
from credit_atlas.exposure_ecl import build,verify
from credit_atlas.workspace import app_root,write_new


def prepare(root):
    months=36
    segments={}
    for key,current in [('non_relief','0.001'),('relief','0.004')]:
        segments[key]={'remaining_months':months,'monthly_effective_rate':'0.004','principal_due_factors':['0']*35+['1'],
            'benchmark_hazards':['0.001']*months,'assessment_hazards':[current]*months,'declared_dpd':0,
            'declared_credit_impaired':False,'qualitative_sicr':False,'poci':False,'revolving':False,'cure_under_review':False}
    scenarios=[]
    for identifier,label,weight,hazards,recovery,cost,lag in [
        ('base','Illustrative base cash-flow assumptions','0.7',{'non_relief':'0.001','relief':'0.004'},'0.75','0.03',6),
        ('adverse','Illustrative adverse cash-flow assumptions','0.3',{'non_relief':'0.003','relief':'0.008'},'0.55','0.05',12)]:
        scenarios.append({'id':identifier,'label':label,'weight':weight,'segments':{key:{
            'conditional_default_hazards':[value]*months,'recovery_profile':[{'lag_months':lag,'recovery_fraction':recovery,'collection_cost_fraction':cost}]}
            for key,value in hazards.items()}})
    plan={'schema_version':1,'name':'Illustrative 36-month bullet cash-shortfall study','version':'illustrative-ecl-v1-20261009',
        'basis':'declared_research_cashflows_and_assessments','source_import_id':'exposure-import-57b88e00bedb',
        'eligible_source_states':['CURRENT'],'benchmark_comparison_basis':'same_remaining_horizon_declared_benchmark',
        'cash_convention':'default_at_start_of_month_contractual_cash_at_end',
        'staging_policy':{'relative_pd_ratio':'2','absolute_pd_increase':'0.02','sicr_dpd_gt':30,'default_dpd_gte':90,'zero_benchmark_policy':'any_positive_to_stage2'},
        'segments':segments,'scenarios':scenarios,'visibility':'private','public_release_approved':False}
    path=root/'data/private/portfolio'/('illustrative-ecl-input-'+uuid.uuid4().hex[:12])/'assumptions.json'; write_new(path,plan)
    receipt=build(root,str(path.relative_to(root))); _,_,report=verify(root,receipt['ecl_id'])
    return {'ecl_id':receipt['ecl_id'],'status':receipt['status'],'stages':{k:v['stage'] for k,v in report['stage_assessments'].items()},
        'totals':[row for row in report['probability_weighted_aggregates'] if row['dimension']=='total']}


if __name__=='__main__': print(json.dumps(prepare(app_root()),indent=2))
