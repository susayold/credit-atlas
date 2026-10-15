import argparse
import json
from credit_atlas.bank_panel import prepare_bank_panel, verify_bank_panel
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--acquisition', required=True)
    args = parser.parse_args()
    result = prepare_bank_panel(app_root(), args.acquisition)
    verify_bank_panel(app_root(), result['case_id'])
    print(json.dumps({key: result[key] for key in ('case_id', 'status', 'records',
                    'unique_certificates', 'reconciliation_differing_rows')}, indent=2))
