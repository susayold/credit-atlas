import json
from credit_atlas.hmda_sources import acquire_hmda_source
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    receipt = acquire_hmda_source(app_root())
    print(json.dumps({'source_id': receipt['source_id'], 'status': receipt['status'],
        'files': len(receipt['files']), 'bytes': sum(row['bytes'] for row in receipt['files']),
        'records': sum(row['records'] for row in receipt['profiles']),
        'profiles': [{key: row[key] for key in ('year', 'records', 'actions')} for row in receipt['profiles']]}, indent=2))
