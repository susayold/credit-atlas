"""Acquire the documented official public source batch for all five workspaces."""
import json
from credit_atlas.public_sources import acquire_public_suite
from credit_atlas.workspace import app_root

if __name__ == "__main__":
    print(json.dumps(acquire_public_suite(app_root()), indent=2))
