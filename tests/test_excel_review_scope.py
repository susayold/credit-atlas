from types import SimpleNamespace
from credit_atlas.excel_workbench import ExcelWorkbench


def test_report_uses_review_for_selected_native_currency(tmp_path):
    inventory={'import_id':'source','currencies':[{'currency':'USD'}]}
    records={'vnd-review':{'id':'vnd-review','currency':'VND'},'usd-review':{'id':'usd-review','currency':'USD'}}
    service=SimpleNamespace(root=tmp_path,
        exposure_views=SimpleNamespace(report=lambda query:inventory),
        exposure_scenario_views=SimpleNamespace(catalog=lambda source:{'scenario_sets':[]}),
        exposure_ecl_views=SimpleNamespace(catalog=lambda source:{'ecl_studies':[]}),
        exposure_tail_views=SimpleNamespace(catalog=lambda source:{'tail_studies':[]}),
        portfolio_reviews=SimpleNamespace(list=lambda source:{'packages':[
            {'id':'vnd-review','updated_at':'2026-10-10T02:00:00Z','evidence_current':True},
            {'id':'usd-review','updated_at':'2026-10-10T01:00:00Z','evidence_current':True}]},
            report=lambda source,identifier:records[identifier]))
    workbench=ExcelWorkbench(service)
    assert workbench.payload({'import_id':'source','currency':'USD'})['review']['id']=='usd-review'
    records['usd-review']['currency']='VND'
    assert workbench.payload({'import_id':'source','currency':'USD'})['review'] is None
