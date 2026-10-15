"""Private S0/S1 descriptive replay. Not policy selection, final OOT, or approval."""
import argparse
import json
import uuid
from decimal import Decimal
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from .engine import ScreeningEngine
from ..cli import code_fingerprint
from ..evidence_checks import require, require_hash
from ..source import sha256, utc_now, write_json_new


def run(root, label_run, canonical_run):
    label_manifest = json.loads((label_run / 'run-complete.json').read_text())
    canonical_manifest = json.loads((canonical_run / 'run-complete.json').read_text())
    require(label_manifest['status'] == 'LABELS_DEVELOPMENT_COMPLETE', 'Completed labels required')
    require(canonical_manifest['status'] == 'CANONICAL_COMPLETE', 'Completed canonical input required')
    require(label_manifest['canonical_run'] == canonical_run.name, 'Mixed canonical/label lineage')
    require_hash(label_run / 'labels.parquet', label_manifest['outputs_sha256']['labels.parquet'])
    require_hash(canonical_run / 'dim_loan.parquet', canonical_manifest['outputs_sha256']['dim_loan.parquet'])
    config = json.loads((root / 'configs/policies.json').read_text())
    engine = ScreeningEngine(config)
    with duckdb.connect() as db:
        db.read_parquet(str(label_run / 'labels.parquet')).create_view('labels')
        db.read_parquet(str(canonical_run / 'dim_loan.parquet')).create_view('loans')
        # Future outcomes, label availability and realized losses never enter policy inputs.
        records = db.sql('''SELECT l.loan_id AS record_id, CAST(l.landmark AS VARCHAR) AS as_of,
          CAST(l.landmark AS VARCHAR) AS features_as_of, TRUE AS funded,
          l.eligibility_reason='eligible' AS data_eligible,
          CAST(d.original_upb AS VARCHAR) AS original_upb, d.classic_fico, d.occupancy
          FROM labels l JOIN loans d USING(loan_id) ORDER BY l.loan_id''').arrow().read_all().to_pylist()
        expected = db.sql("SELECT COUNT(*), SUM(original_upb) FROM labels WHERE eligibility_reason='eligible'").fetchone()
        require(len(records) == db.sql('SELECT COUNT(*) FROM labels').fetchone()[0], 'Input join cardinality changed')
    output = root / 'artifacts/private' / ('policy-replay-' + uuid.uuid4().hex[:12])
    output.mkdir(parents=True)
    manifest = {'started_at': utc_now(), 'label_run': label_run.name, 'canonical_run': canonical_run.name,
                'code_sha256': code_fingerprint(root), 'policy_sha256': engine.policy_hash, 'config': config,
                'inputs_sha256': {'labels': sha256(label_run / 'labels.parquet'), 'loans': sha256(canonical_run / 'dim_loan.parquet')},
                'visibility': 'private', 'public_release_approved': False, 'research_ready': False,
                'evidence_class': 'retrospective_observed', 'policy_selection_performed': False,
                'note': 'Illustrative S0/S1 descriptive replay. No historical-publication PIT proof or causal/approval claim.'}
    write_json_new(output / 'run-start.json', manifest)
    try:
        summaries = []
        schema = pa.schema([('record_id', pa.string()), ('as_of', pa.string()), ('policy_id', pa.string()),
                            ('policy_version', pa.string()), ('policy_sha256', pa.string()),
                            ('evidence_class', pa.string()), ('decision', pa.string()), ('base_eligible', pa.bool_()),
                            ('original_upb', pa.string()), ('reason_codes', pa.list_(pa.string())), ('trace_json', pa.string())])
        for policy_id in ('S0', 'S1'):
            result = engine.screen(records, policy_id, 'retrospective_observed')
            summary = result['summary']
            require(summary['base_eligible_rows'] == expected[0], 'Base eligibility differs from source cohort')
            require(Decimal(summary['base_eligible_principal']) == expected[1], 'Base principal differs from source cohort')
            if policy_id == 'S0':
                require(summary['decision_counts']['selected'] == expected[0], 'S0 does not retain every eligible loan')
                require(Decimal(summary['selected_principal']) == expected[1], 'S0 principal differs from baseline')
            with pq.ParquetWriter(output / f'{policy_id}-decisions.parquet', schema, compression='zstd') as writer:
                decisions = result['decisions']
                for start in range(0, len(decisions), 10000):
                    rows = [{key: value for key, value in d.items() if key != 'trace'} |
                            {'trace_json': json.dumps(d['trace'], sort_keys=True, allow_nan=False)} for d in decisions[start:start + 10000]]
                    writer.write_table(pa.Table.from_pylist(rows, schema=schema))
            summaries.append(summary)
        write_json_new(output / 'summary.json', {'policies': summaries, 'universe_rows': len(records),
                       'model_based_policies': 'not_replayed_without_evaluated_model_artifacts'})
        manifest.update(status='POLICY_DESCRIPTIVE_REPLAY_COMPLETE', completed_at=utc_now(),
                        outputs_sha256={p.name: sha256(p) for p in output.glob('*.parquet')} |
                        {'summary.json': sha256(output / 'summary.json')})
        write_json_new(output / 'run-complete.json', manifest)
    except Exception as error:
        write_json_new(output / 'run-failed.json', {'failed_at': utc_now(), 'exception_type': type(error).__name__})
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-run', type=Path, required=True)
    parser.add_argument('--canonical-run', type=Path, required=True)
    args = parser.parse_args()
    print(run(Path(__file__).resolve().parents[3], args.label_run.resolve(), args.canonical_run.resolve()))
