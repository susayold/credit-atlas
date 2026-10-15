import json
import sys
from credit_atlas.abs_audit import audit
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    r=audit(app_root(),sys.argv[1])
    print(json.dumps({k:r[k] for k in ('audit_id','status','different_cell_rows','source_cells','failed_checks')}))
