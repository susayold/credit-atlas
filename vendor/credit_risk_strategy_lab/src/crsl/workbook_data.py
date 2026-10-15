"""Build an aggregate-only private workbook payload from one development pipeline."""
import argparse
import datetime
import decimal
import json
from pathlib import Path

import duckdb

from .evidence_checks import require, require_hash, require_outcome_totals
from .metrics import REGISTRY, validate_monthly
from .losses import summarize as summarize_losses
from .source import sha256
from .segmented_transition_export import load as load_segmented_transitions
from .portfolio_profile_export import load as load_portfolio_profile
from .vintage_export import load as load_vintage


def serial(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def build(root, pipeline, segmented_run=None, profile_run=None):
    root, pipeline = root.resolve(), pipeline.resolve()
    manifest = json.loads((pipeline / 'run-complete.json').read_text())
    require(manifest['status'] == 'DEVELOPMENT_PIPELINE_COMPLETE', 'Incomplete pipeline')
    require(all(s['status'] == 'PASS' for s in manifest['stages']), 'Failed pipeline stage')
    stages = {s['stage']: root / 'artifacts/private' / s['output_run'] for s in manifest['stages']}
    hashes = {}

    def verified(stage, filename):
        directory = stages[stage]
        receipt = json.loads((directory / 'run-complete.json').read_text())
        path = directory / filename
        require_hash(path, receipt['outputs_sha256'][filename])
        hashes[f'{stage}/{filename}'] = sha256(path)
        return path

    with duckdb.connect() as db:
        for table, stage, filename in [
            ('labels', 'labels', 'labels.parquet'),
            ('monthly', 'portfolio', 'monthly.parquet'),
            ('transitions', 'portfolio', 'transition_matrix.parquet'),
            ('episodes', 'portfolio', 'episodes.parquet'),
        ]:
            db.read_parquet(str(verified(stage, filename))).create_view(table)
        label_receipt = json.loads((stages['labels'] / 'run-complete.json').read_text())
        portfolio_receipt = json.loads((stages['portfolio'] / 'run-complete.json').read_text())
        require(label_receipt['canonical_run'] == stages['canonical'].name == portfolio_receipt['canonical_run'],
                'Mixed canonical runs')
        def rows(sql):
            return db.sql(sql).arrow().read_all().to_pylist()
        monthly = rows('SELECT * FROM monthly ORDER BY period')
        validate_monthly(monthly)
        outcomes = rows('SELECT outcome,COUNT(*) AS loans FROM labels GROUP BY 1 ORDER BY 1')
        coverage = rows('SELECT eligibility_reason,COUNT(*) AS loans,SUM(original_upb) AS original_upb_usd FROM labels GROUP BY 1 ORDER BY 1')
        controls = rows('SELECT COUNT(*) AS loans,COUNT(DISTINCT loan_id) AS distinct_loans,SUM(original_upb) AS original_upb_usd FROM labels')[0]
        require(controls['loans'] == controls['distinct_loans'], 'Duplicate label loans')
        require_outcome_totals(outcomes, controls['loans'])
        vintage = rows('''SELECT origination_year,COUNT(*) AS loans,
            COUNT(*) FILTER(WHERE target IS NOT NULL) AS available_labels,
            COUNT(*) FILTER(WHERE target=1) AS d3_events,
            COUNT(*) FILTER(WHERE target IS NULL) AS unavailable_labels
            FROM labels GROUP BY 1 ORDER BY 1''')
        transitions = rows('SELECT * FROM transitions ORDER BY origin,destination')
        episodes = rows('''SELECT event_type,COUNT(*) AS event_records,
            COUNT(DISTINCT loan_id) AS distinct_loans FROM episodes GROUP BY 1 ORDER BY 1''')
        audit = json.loads(verified('audit', 'findings.json').read_text())
        loss_audit_path = verified('audit', 'loss_audit.parquet')
        loss_records = db.execute('SELECT * FROM read_parquet(?) ORDER BY loan_id, period', [str(loss_audit_path)]).to_arrow_table().to_pylist()
        loss_summary = summarize_losses(loss_records)
        vintage_evidence = None
        if 'vintage' in stages:
            vintage_evidence = load_vintage(root, stages['canonical'], stages['vintage'])
        segmented_evidence = None
        if segmented_run is not None:
            segmented_evidence = load_segmented_transitions(root, segmented_run)
            require(segmented_evidence['canonical_run'] == stages['canonical'].name,
                    'Segmented transition mart uses a different canonical run')
        profile_evidence = None
        if profile_run is not None:
            profile_evidence = load_portfolio_profile(root, stages['canonical'], profile_run)
    return {
        'schema_version': 2, 'visibility': 'private', 'public_release_approved': False,
        'evidence_class': 'derived_observed_sample', 'pipeline_run': pipeline.name,
        'pipeline_sha256': sha256(pipeline / 'run-complete.json'), 'input_hashes': hashes,
        'controls': controls, 'coverage': coverage, 'outcomes': outcomes,
        'monthly': monthly, 'vintage': vintage, 'transitions': transitions,
        'episodes': episodes, 'loss_reconciliation': audit['loss_reconciliation'],
        'loss_summary': loss_summary,
        'vintage_evidence': vintage_evidence,
        'segmented_transitions': segmented_evidence,
        'portfolio_profile': profile_evidence,
        'metrics': REGISTRY,
        'source_url': 'https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset',
        'guide_url': 'https://www.freddiemac.com/fmac-resources/research/pdf/general_user_guide_july_2026.pdf',
        'release': 47,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pipeline-run', type=Path, required=True)
    parser.add_argument('--segmented-run', type=Path)
    parser.add_argument('--profile-run', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    payload = build(root, args.pipeline_run,
                    args.segmented_run.resolve() if args.segmented_run else None,
                    args.profile_run.resolve() if args.profile_run else None)
    output = root / 'artifacts/private' / (payload['pipeline_run'] + '-workbook-input.json')
    output.write_text(json.dumps(payload, default=serial, indent=2, allow_nan=False), encoding='utf-8')
    print(output)
