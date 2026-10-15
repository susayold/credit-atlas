from pathlib import Path
import json,uuid
from credit_atlas.absee_dictionary import report
from credit_atlas.workspace import sha256
root=Path.cwd();doc=report(root,{})
out=root/'artifacts/private'/('absee-dictionary-'+uuid.uuid4().hex[:12]);out.mkdir()
(out/'dictionary.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
(out/'receipt.json').write_text(json.dumps({'status':'PASS','observed_fields':doc['observed_fields'],
    'dictionary_sha256':sha256(out/'dictionary.json'),'source_receipt_sha256':doc['source_receipt_sha256'],
    'all_fields_have_clause_evidence':all(x['definition'] for x in doc['fields']),
    'xsd_verified':False,'mirror_fidelity_verified':False,'model_ready':False},indent=2),encoding='utf8')
print(out);print(doc['observed_fields'])
