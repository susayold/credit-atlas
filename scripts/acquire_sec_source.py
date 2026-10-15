import json
from credit_atlas.sec_sources import acquire_sec_source
from credit_atlas.workspace import app_root

if __name__ == '__main__':
    receipt = acquire_sec_source(app_root())
    print(json.dumps({'source_id': receipt['source_id'], 'status': receipt['status'], 'entities': receipt['entities'],
                      'files': len(receipt['files']), 'bytes': sum(item['bytes'] for item in receipt['files'])}, indent=2))
