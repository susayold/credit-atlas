import argparse
import json
from credit_atlas.retail_holdout import evaluate_holdout
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the frozen retail model once on its reserved random cohort")
    parser.add_argument("--freeze", required=True)
    args = parser.parse_args()
    print(json.dumps(evaluate_holdout(app_root(), args.freeze), indent=2))
