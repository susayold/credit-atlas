import copy
import pytest
from credit_atlas.kpi_workbook import validate_report


def report():
    metrics=[{'name':'N','value':10,'unit':'count','formula':'Saved count','interpretation':'Source records','comparison':None}]
    filters={'domain':'P1','basis':'count'}
    snapshot={'domain':'P1','scope':'Historical','metrics':copy.deepcopy(metrics),'quality_metrics':[], 'filters':filters,'comparison_control':None,'evidence_refs':[{'kind':'suite','id':'suite-view-aaaaaaaaaaaa'}]}
    return {'schema_version':1,'read_at':'2026-10-10T00:00:00Z','filters':filters,'kpi_analysis':{'P1':{'title':'Retail','scope':'Historical','metrics':metrics,'data_quality':{'metrics':[],'tables':[]},'review_snapshot':snapshot,'tables':[]}}}


def test_zero_and_missing_actuals_distinct():
    p=report();m=p['kpi_analysis']['P1']['metrics'][0]
    for v in [0,None]:
        m['value']=v;p['kpi_analysis']['P1']['review_snapshot']['metrics']=copy.deepcopy(p['kpi_analysis']['P1']['metrics']);assert validate_report(p)==p


@pytest.mark.parametrize('case',['scope','snapshot','nan','string_actual','unit','table_shape','depth','unknown_field'])
def test_reject_bad_reports(case):
    p=report();r=p['kpi_analysis']['P1']
    if case=='scope':p['filters']['domain']='P2'
    if case=='snapshot':r['scope']='Different population'
    if case=='nan':r['metrics'][0]['value']=float('nan')
    if case=='string_actual':r['metrics'][0]['value']='=1+1';r['review_snapshot']['metrics']=copy.deepcopy(r['metrics'])
    if case=='unit':r['metrics'][0]['unit']='VND';r['review_snapshot']['metrics']=copy.deepcopy(r['metrics'])
    if case=='table_shape':r['tables']=[{'title':'Rows','columns':['A'],'rows':[[1,2]]}]
    if case=='depth':
        v=[]
        for _ in range(16):v=[v]
        r['extra']=v
    if case=='unknown_field':p['output_path']='C:/private.xlsx'
    with pytest.raises((ValueError,TypeError)):validate_report(p)
