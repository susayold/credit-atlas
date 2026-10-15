"""Read-only independent SQL cardinality check against saved labels."""
import argparse
import json
from pathlib import Path

import duckdb

from crsl.evidence_checks import require, require_hash

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cohort-run', type=Path, required=True)
args = parser.parse_args()
output = args.cohort_run.resolve()
manifest = json.loads((output / 'run-complete.json').read_text())
require(manifest['status'] == 'DESCRIPTIVE_COMPARISON_COHORT_COMPLETE', 'Completed cohort required')
for name, digest in manifest['outputs_sha256'].items():
    require_hash(output / name, digest)
labels = output.parent / manifest['label_run']
require_hash(labels / 'run-complete.json', manifest['inputs_sha256']['label_receipt'])
label_manifest = json.loads((labels / 'run-complete.json').read_text())
require_hash(labels / 'labels.parquet', label_manifest['outputs_sha256']['labels.parquet'])
audit = json.loads((output / 'attrition.json').read_text())
with duckdb.connect() as db:
    db.read_parquet(str(labels / 'labels.parquet')).create_view('labels')
    db.read_parquet(str(output / 'comparison.parquet')).create_view('cohort')
    expected = db.execute("SELECT COUNT(*) FROM labels WHERE eligibility_reason='eligible' "
                          "AND target IS NOT NULL AND label_known_month < CAST(? AS DATE)",
                          [audit['evaluation_cutoff']]).fetchone()[0]
    actual = db.sql('SELECT COUNT(*),COUNT(DISTINCT loan_id) FROM cohort').fetchone()
    require(actual == (expected, expected), 'Independent source count mismatch')
    differences = db.execute('''SELECT COUNT(*) FROM (
      (SELECT loan_id FROM labels WHERE eligibility_reason='eligible' AND target IS NOT NULL
       AND label_known_month < CAST(? AS DATE) EXCEPT ALL SELECT loan_id FROM cohort)
      UNION ALL
      (SELECT loan_id FROM cohort EXCEPT ALL SELECT loan_id FROM labels
       WHERE eligibility_reason='eligible' AND target IS NOT NULL AND label_known_month < CAST(? AS DATE)))''',
       [audit['evaluation_cutoff'], audit['evaluation_cutoff']]).fetchone()[0]
    require(differences == 0, 'Independent loan identity mismatch')
print(json.dumps({'status': 'PASS', 'source_expected': expected, 'saved_rows': actual[0],
                  'identity_differences': differences, 'attrition': audit}))
