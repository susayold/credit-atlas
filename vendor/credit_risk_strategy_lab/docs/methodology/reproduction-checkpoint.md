# Development reproduction checkpoint

## Current eight-stage integration — 2026-09-11

`pipeline-95694e244d60` and `pipeline-a3dc9c35f0c0` ran the same completed source
snapshot through canonical, labels, audit, portfolio, splits, attrition, metrics
and independently verified vintage. Both have the same implementation fingerprint.
All 13 Parquet relations matched by identical SHA256 or symmetric `EXCEPT ALL`;
all four stable JSON summaries matched, including vintage bootstrap results.

Reproduce the comparison:

```powershell
python scripts/compare_pipeline_runs.py --left artifacts/private/pipeline-95694e244d60 --right artifacts/private/pipeline-a3dc9c35f0c0
```

The comparator rejects a missing stage instead of silently narrowing the comparison.
It verifies saved table hashes and schema before comparing complete row multiplicity.
The pipeline pins the vintage verification and completion receipts and stops if
the independent source/matrix check fails. It still does not authorize model fitting.

### Defect found and repaired

The first eight-stage pair failed exact reproduction in attrition standard deviation:
floating-point reductions differed in their last digits. The mean and population
standard deviation now explicitly aggregate in unique loan-ID order. A synthetic
regression reverses input order and changes DuckDB threads from one to four;
results must match exactly. No tolerance was widened to hide the discrepancy.

Reference: [DuckDB floating-point nondeterminism](https://duckdb.org/docs/current/operations_manual/non-deterministic_behavior).

The same review also found a stable-summary ordering defect in the audit export:
`relief_dti_crosscheck` had identical rows but no explicit order. The query now
uses `ORDER BY is_relief_refinance`. The post-fix integration run
`pipeline-83667cc64126` completed all eight stages and produced the current
website/workbook inputs. A second post-fix rerun was stopped during canonical
artifact creation by the machine's temporary disk exhaustion, so the latest pair
must not be described as a fully reproduced pair; the historical pair above and
the deterministic regression tests remain the reproducibility evidence.

These checks cover development transformations and stable summaries, not clean-machine
installation, all model results, public release, website/Excel integration or full V4 R0.
The following is the earlier seven-stage checkpoint retained as history.

Run: `pipeline-ca9d8efec1e7`, from the completed annual source inspection
`d3167b604110-30526467`. All7 stages completed in order using fresh upstream outputs.

Canonical: `canonical-40ec3098d5a0`; labels: `labels-60786ddbc109`;
audit: `audit-ac7f34f6aac8`; portfolio: `portfolio-cf01004d8fe1`;
splits: `splits-357cd54010a4`; attrition: `attrition-a8879138fe3c`;
metrics: `metrics-6e41d5e04c6c`.

Compared complete relations with symmetric `EXCEPT ALL`, preserving duplicate multiplicity:

- Fresh labels vs `labels-ec5d5fb7b61a`:0differing rows.
- Fresh monthly stocks vs `portfolio-a317e27aa17d`:0differing rows.
- Fresh transition matrix vs the same portfolio baseline:0differing rows.
- Fresh episode events vs the same portfolio baseline:0differing rows.

This verifies rerunning the implemented transformation stack in the current pinned
environment. It is not a clean-machine dependency-install audit, a fresh raw ZIP parse,
CI execution on GitHub, cross-engine byte-identical Parquet guarantee or full R0 release.
Missing-vintage, model, publication, website and Excel requirements remain unchanged.

CLI: `python -m crsl.pipeline --source-run <completed annual source run>`.
The pipeline emits per-stage receipts, stops on failure and never promotes development
success into full research readiness. Prior runs remain untouched.
