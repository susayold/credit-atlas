import argparse,json
from credit_atlas.retail_freeze import freeze_model
from credit_atlas.workspace import app_root

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Freeze validation-selected retail benchmark model")
    parser.add_argument("--comparison",required=True)
    args=parser.parse_args()
    print(json.dumps(freeze_model(app_root(),args.comparison),indent=2))
