import argparse
import json
from credit_atlas.service import ResearchService
from credit_atlas.workspace import app_root,contained,read_json,write_new

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--input',required=True); parser.add_argument('--output',required=True); args=parser.parse_args()
    root=app_root(); service=ResearchService(root); record=service.portfolio_reviews.save(read_json(contained(root,args.input)))
    exported=service.portfolio_reviews.report(record['source_import_id'],record['id'],record['revision'])
    write_new(contained(root,args.output),exported)
    print(json.dumps({'id':record['id'],'revision':record['revision'],'status':record['status'],'evidence_current':exported['evidence_current']}))
