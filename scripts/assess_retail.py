import argparse
import json
from credit_atlas.retail_assessment import run_assessment
from credit_atlas.workspace import app_root

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Fit private retail development benchmark; final-test remains reserved")
    parser.add_argument("--features",required=True)
    args=parser.parse_args()
    print(json.dumps(run_assessment(app_root(),args.features),indent=2))
