import json
from credit_atlas.bank_panel import acquire_bank_history
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    result = acquire_bank_history(app_root())
    print(json.dumps({key: result[key] for key in ('acquisition_id', 'status', 'rows', 'bytes')}, indent=2))
