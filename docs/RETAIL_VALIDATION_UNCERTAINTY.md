# P1 retail — paired validation uncertainty

Actual comparison run: `retail-comparison-b560ea676127`, based on development
assessment `retail-assessment-b8b96f471254`. No model refit, champion selection
or final-test scoring occurs in this comparison. The original point metrics
remain unchanged. Saved model/calibrator scores and all six validation metric
sets were reverified before and after comparison.

## Method and scope

1,000 bootstrap replicates, seed 676, same 4,499 client rows / 995 events.
Each replicate resamples clients within each outcome class, preserving observed
class counts. The same sampled client indices are used across every model and
raw/calibrated variant. The 95% percentile intervals are conditional on the
already-fitted models and observed event prevalence; they omit training/refit
and prevalence uncertainty. Unknown household clustering cannot be accounted
for without cluster keys. These are exploratory, unadjusted comparisons, not
a preregistered family of winner-selection hypothesis tests.

One historical random cohort does not test future calendar or geographic
transportability. Constant-model Brier intervals can have zero width because
class prevalence is held fixed; this does not mean general population risk is
known without uncertainty.

## Boosting versus logistic, raw variants

Positive improvement means higher AUC/AP or lower Brier/log loss for boosting.

| Metric | Point improvement | 95% lower | 95% upper |
|---|---:|---:|---:|
| ROC AUC | 0.007866 | -0.002189 | 0.017465 |
| Average precision | 0.012994 | -0.001883 | 0.026150 |
| Brier | 0.002411 | 0.000913 | 0.003993 |
| Log loss | 0.007848 | 0.003063 | 0.012823 |

Ranking-metric intervals include zero. Brier/log-loss intervals favor boosting
under this conditional validation analysis. This distinction matters: a higher
point AUC alone does not establish a clear ranking improvement.

For calibrated variants, Brier improvement is 0.002524 with interval
[0.000986, 0.004094]; log-loss improvement 0.008206 with interval
[0.003358, 0.013190]. AUC/AP remain unchanged by positive monotonic sigmoid
calibration in this run. The slight Brier/log-loss change from calibration
within either learned model has intervals containing zero; calibration benefit
has not been established by these validation intervals.

## Persistence and checks

Code: `src/credit_atlas/retail_comparison.py`.
Artifacts: configuration, access intent, comparison results with absolute and
paired intervals, completion receipt and SHA-256 digests. IDs, per-client scores
and source data remain private. Verification enforces one ordered client/target
cohort across models, complete artifact hashes, frozen case/feature lineage,
persisted model/calibration parity and recomputed metrics. A reordered score
file is rejected even when its artifact digest is updated.

Software checks cover deterministic bootstrap, exactly zero paired differences
for identical probabilities, metric-improvement directions, class-conditioned
constant intervals and invalid probability/row-grain rejection. They do not
establish real-world statistical assumptions or production model adequacy.
Full software suite at this checkpoint: 507 passing tests. Actual comparison
receipt verifies the current method source and every output SHA-256.

## Remaining selection steps

Define and save the comparison rubric, model/variant choice and rationale,
including simplicity and intended-use tradeoffs. Since development metrics
have already been inspected, record that rubric as a development decision;
do not claim it was preregistered before seeing these results. Freeze model,
encoder, source/case, settings and selection before touching the reserved
random final holdout. The final holdout remains a random-cohort benchmark,
not temporal OOT. Model card, policy/fairness review and app integration remain.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/compare_retail.py --assessment retail-assessment-b8b96f471254
```
