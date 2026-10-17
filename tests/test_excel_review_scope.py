from types import SimpleNamespace
from credit_atlas.excel_workbench import ExcelWorkbench
from credit_atlas.exposure_imports import import_exposures
from credit_atlas.exposure_views import ExposureViews
from credit_atlas.workspace import sha256,write_new
from tests.test_exposure_imports import metadata,rows,write_csv


def test_report_uses_review_for_selected_native_currency(tmp_path):
    anchor=tmp_path/'source-anchor.txt';anchor.write_text('verified upstream source fixture',encoding='utf-8')
    meta=metadata();meta.update(dataset_kind='source_observation',amount_kind='reported_outstanding_principal',
        source_namespace='Freddie-Mac-2012-annual-sample',
        source_description='Loan-month observations in sample; reported raw UPB, not owned positions, EAD or default PD.',
        source_lineage=[{'path':'source-anchor.txt','sha256':sha256(anchor)}])
    write_csv(tmp_path/'input.csv',rows());write_new(tmp_path/'metadata.json',meta)
    receipt=import_exposures(tmp_path,'input.csv','metadata.json');views=ExposureViews(tmp_path)
    source=receipt['import_id']
    inventory=views.report({'import_id':source,'currency':'USD','dimension':'region'})
    records={'vnd-review':{'id':'vnd-review','currency':'VND'},'usd-review':{'id':'usd-review','currency':'USD'}}
    service=SimpleNamespace(root=tmp_path,
        exposure_views=views,
        exposure_scenario_views=SimpleNamespace(catalog=lambda source:{'scenario_sets':[]}),
        exposure_ecl_views=SimpleNamespace(catalog=lambda source:{'ecl_studies':[]}),
        exposure_tail_views=SimpleNamespace(catalog=lambda source:{'tail_studies':[]}),
        portfolio_reviews=SimpleNamespace(list=lambda source:{'packages':[
            {'id':'vnd-review','updated_at':'2026-10-10T02:00:00Z','evidence_current':True},
            {'id':'usd-review','updated_at':'2026-10-10T01:00:00Z','evidence_current':True}]},
            report=lambda source,identifier:records[identifier]))
    workbench=ExcelWorkbench(service)
    payload=workbench.payload({'import_id':source,'currency':'USD','dimension':'region'})
    assert payload['review']['id']=='usd-review'
    provenance=payload['source_provenance']
    assert provenance['import_id']==source and provenance['receipt_sha256']==sha256(tmp_path/'artifacts/private'/source/'import-complete.json')
    assert provenance['source_namespace']=='Freddie-Mac-2012-annual-sample'
    assert provenance['dataset_kind']=='source_observation' and provenance['amount_kind']=='reported_outstanding_principal'
    assert provenance['record_count']==inventory['records'] and provenance['all_currency_record_count']==3
    assert provenance['source_lineage']==[{'path':'source-anchor.txt','sha256':sha256(anchor)}]
    assert 'does not prove assets owned' in provenance['scope_warning'] and provenance['ownership_certified'] is False
    assert provenance['amount_is_ead'] is False and provenance['public_release_approved'] is False
    assert str(tmp_path) not in str(payload)
    records['usd-review']['currency']='VND'
    assert workbench.payload({'import_id':source,'currency':'USD','dimension':'region'})['review'] is None
