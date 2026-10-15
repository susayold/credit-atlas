"""Generate the clean, private-input B04-B07 companion with nbformat."""
from pathlib import Path
import nbformat as nbf

root=Path(__file__).resolve().parents[1]
nb=nbf.v4.new_notebook()
md=nbf.v4.new_markdown_cell; code=nbf.v4.new_code_cell
nb.cells=[
md('''## tl;dr
The 2012 pilot has 48,066 early-entry eligible loans and 102 numeric-D3 events
within the following 12 months. 374 disclosed loss records reconcile with the
signed Release-47 formula. This is a private foundation audit, not a trained model.
'''),
md('''## Context & Methods
Canonical raw preservation, date/sentinel conversion, observation entry, label
boundaries, loss arithmetic and adjacent transitions are separate contracts.
### Key Assumptions
Only the authorized 2012 annual sample is used. No full-market weighting, strict
historical point-in-time claim, causal treatment effect or public release is asserted.
Guide: https://www.freddiemac.com/fmac-resources/research/pdf/general_user_guide_july_2026.pdf
Input run names below are explicit reproducibility parameters. Raw IDs never print.
'''),
code('''import json
from pathlib import Path
import duckdb
from crsl.source import sha256
root=Path.cwd()
if root.name=='notebooks': root=root.parent
canonical=root/'artifacts/private/canonical-c36cd6b9b666'
label_run=root/'artifacts/private/labels-ec5d5fb7b61a'
manifest=json.loads((canonical/'run-complete.json').read_text())
assert manifest['status']=='CANONICAL_COMPLETE'
db=duckdb.connect()
db.execute("SET memory_limit='1GB'")
for table in ('dim_loan','fact_loan_month'):
    path=canonical/(table+'.parquet')
    assert sha256(path)==manifest['outputs_sha256'][path.name]
    db.read_parquet(str(path)).create_view(table)
print('Validated canonical input hashes; source release:',manifest['release'])
'''),
md('''## Data
Inspect aggregate missingness, not source identifiers. Amounts remain USD; rates
remain percentage points. Blank and source sentinel are distinct in raw columns.
'''),
code('''print(db.execute("""SELECT COUNT(*) AS loans,
 COUNT(*) FILTER (WHERE original_dti IS NULL) AS dti_missing,
 COUNT(*) FILTER (WHERE vantagescore IS NULL) AS vs4_missing,
 COUNT(*) FILTER (WHERE is_relief_refinance) AS relief_refinance,
 COUNT(*) FILTER (WHERE is_harp_subset) AS harp_subset
 FROM dim_loan""").fetchall())
'''),
md('''## Results
### Recompute full labels and compare every row
This is a new calculation, not a read-back of the saved summary. The config is
the original run's captured contract, not whatever a future default may become.
'''),
code('''from crsl.labels import create_labels
saved_manifest=json.loads((label_run/'run-complete.json').read_text())
assert saved_manifest['canonical_run']==canonical.name
create_labels(db,root/'sql',saved_manifest['config'])
assert sha256(label_run/'labels.parquet')==saved_manifest['outputs_sha256']['labels.parquet']
db.read_parquet(str(label_run/'labels.parquet')).create_view('saved_labels')
assert db.execute("""SELECT COUNT(*) FROM (
 (SELECT * FROM labels EXCEPT SELECT * FROM saved_labels)
 UNION ALL (SELECT * FROM saved_labels EXCEPT SELECT * FROM labels))""").fetchone()[0]==0
print(db.execute('SELECT outcome,COUNT(*) FROM labels GROUP BY 1 ORDER BY 1').fetchall())
print('Full saved label table matches fresh SQL.')
'''),
md('''### Reconcile actual-loss components
Null losses are not zero. Signed recoveries enter by addition in Release47.
This arithmetic check does not approve a severity model or unresolved-loss labels.
'''),
code('''from crsl.audit import loss_checks
loss=loss_checks(db,root/'sql')
print(loss)
assert loss['loss_reconciliation'][0]['loss_mismatch']==0
assert loss['loss_reconciliation'][0]['incomplete_formula']==0
'''),
md('''### Adjacent transition and monthly-stock checks
Matrix rows reconcile to one; gaps/missing-next observations remain separately visible.
Opening-balance weighting is not closing-balance weighting or a causal estimate.
'''),
code('''from crsl.portfolio import create_marts
create_marts(db,root/'sql')
print(db.execute('SELECT origin,SUM(count_probability) FROM transition_matrix GROUP BY 1 ORDER BY 1').fetchall())
assert db.execute('SELECT COUNT(*) FROM monthly WHERE active_loans+terminal_loans<>reported_loans').fetchone()[0]==0
print('Monthly stock counts reconcile. Months:',db.execute('SELECT COUNT(*) FROM monthly').fetchone()[0])
db.close()
'''),
md('''## Takeaways
Source parsing alone would have hidden DTI/score sentinels, competing exits and
the small 12-month positive class. Continue descriptive cohort/transition work;
multi-vintage train/calibration/validation/OOT approval remains open.
No credentials, raw IDs or hidden source records are exported in this notebook.
''')]
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
             'language_info':{'name':'python','version':'3.12'}}
nbf.validate(nb)
nbf.write(nb,root/'notebooks/01_foundation_contracts.ipynb')
