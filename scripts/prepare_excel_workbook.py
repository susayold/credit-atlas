"""Verified aggregate exports as structured inputs for the bundled XLSX author."""
import json
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root,write_new,read_json

if __name__=='__main__':
    root=app_root(); service=ResearchService(root)
    source='exposure-import-57b88e00bedb'
    inventory=service.exposure_views.report({'import_id':source,'currency':'USD','dimension':'region'})
    scenario=service.exposure_scenario_views.report({'scenario_id':'exposure-scenario-9655e30419ec','source_import_id':source,'currency':'USD','dimension':'segment'})
    ecl=service.exposure_ecl_views.report({'ecl_id':'exposure-ecl-ba27d7207a44','source_import_id':source,'currency':'USD','dimension':'stage'})
    tail=service.exposure_tail_views.report({'tail_id':'exposure-tail-10a079f18dc9','source_import_id':source,'currency':'USD'})
    payload={'inventory':inventory,'scenario':scenario,'ecl':ecl,'tail':tail,'review':read_json(root/'artifacts/private/portfolio-review-draft-20261009.json')}
    write_new(root/'artifacts/private/excel-workbook-input-20261009.json',payload)
    print(json.dumps({'status':'verified','inventory_group_keys':list(inventory['groups'][0]) if 'groups' in inventory else list(inventory),
        'scenario_group_keys':list(scenario['scenarios'][0]['aggregates'][0])}))
