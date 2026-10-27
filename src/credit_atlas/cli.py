"""Local/private CreditAtlas commands; stages preserve model/data gates."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .workspace import app_root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=app_root())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inventory")
    probe = sub.add_parser("source-access")
    probe.add_argument("--cookie-file", type=Path)
    download = sub.add_parser("download-samples")
    download.add_argument("--manifest", type=Path, required=True)
    download.add_argument("--cookie-file", type=Path)
    annual = sub.add_parser("import-annual")
    annual.add_argument("--archive", type=Path, required=True)
    annual.add_argument("--release", type=int, required=True)
    annual.add_argument("--expected-sha256", required=True)
    annual.add_argument("--research-use-confirmed", action="store_true")
    study = sub.add_parser("prepare-study")
    study.add_argument("--case", action="append", required=True)
    study.add_argument("--protocol", type=Path)
    features = sub.add_parser("prepare-features")
    features.add_argument("--study", required=True)
    assessment = sub.add_parser("assess-study")
    assessment.add_argument("--study", required=True)
    assessment.add_argument("--feature-audit", required=True)
    assessment.add_argument("--review-file", type=Path)
    rebuild = sub.add_parser("rebuild")
    rebuild.add_argument("--asset-index", type=int, default=0)
    snapshot = sub.add_parser("build-snapshot")
    snapshot.add_argument("--case", type=Path, required=True)
    reproduce = sub.add_parser("reproduce")
    reproduce.add_argument("--case", type=Path, required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8770)
    serve.add_argument("--nsmo-drive-remote", help="Read D02 data from a read-only rclone remote, e.g. creditatlas:")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if root.drive.upper() != "D:":
        parser.error("CreditAtlas workspace and new task files must remain on D:")
    if args.command == "assess-study":
        from .assessment import run
        result = run(root, args.study, args.feature_audit, args.review_file)
    elif args.command == "prepare-features":
        from .study_features import prepare_features
        result = prepare_features(root, args.study)
    elif args.command == "prepare-study":
        from .study import prepare
        result = prepare(root, args.case, args.protocol)
    elif args.command == "import-annual":
        from .source_registry import import_annual
        result = import_annual(root, args.archive, args.release, args.research_use_confirmed, args.expected_sha256)
    elif args.command == "source-access":
        from .acquisition import probe
        result = probe(root, args.cookie_file)
    elif args.command == "download-samples":
        from .acquisition import download_manifest
        result = download_manifest(root, args.manifest, args.cookie_file)
    elif args.command == "inventory":
        from .inventory import inventory
        result = inventory(root)
    elif args.command == "rebuild":
        from .foundation import rebuild
        result = {"case_directory": str(rebuild(root, args.asset_index))}
    elif args.command == "reproduce":
        from .foundation import compare_rebuild
        result = compare_rebuild(root, args.case.resolve())
    elif args.command == "build-snapshot":
        from .snapshot import build_case
        result = build_case(root, args.case.resolve())
    else:
        from .server import serve
        serve(root, args.port, nsmo_drive_remote=args.nsmo_drive_remote)
        return 0
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
