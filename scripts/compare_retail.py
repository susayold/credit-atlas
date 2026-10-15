import argparse
import json
from credit_atlas.retail_comparison import run_comparison
from credit_atlas.workspace import app_root

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Paired retail validation uncertainty; no final-test access")
    parser.add_argument("--assessment",required=True)
    args=parser.parse_args()
    print(json.dumps(run_comparison(app_root(),args.assessment),indent=2))
