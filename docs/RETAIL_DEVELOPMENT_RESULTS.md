# P1 retail — actual development benchmark, 09/10/2026

UCI350 Taiwan historical credit-card cohort, source-defined next-month payment
default. The frozen client-level class-stratified random partitions were used;
this is not out-of-time validation or a calibrated model for Vietnam.

Actual run: `private evidence omitted from public release`.
Source case `retail-case-470bdb40682f`, feature preparation
`retail-features-d53aa8ba9ed6`. Raw sources, canonical case and feature receipts
are verified before fitting and again before the completion receipt.

## Same-cohort results

All models fit on 17,999 train clients and use the same 81 encoded columns,
derived from 13 numerical and six categorical source fields. Calibration uses
4,501 separate clients. Validation uses 4,499 clients, including 995 events.
3,001 final-test clients remain reserved; their predictors are not selected by
this assessment. No champion has been selected or final-test scored.

| Model / variant | ROC AUC | Average precision | Brier score | Log loss |
|---|---:|---:|---:|---:|
| Constant raw | 0.500000 | 0.221160 | 0.172248 | 0.528373 |
| Constant calibrated | 0.500000 | 0.221160 | 0.172248 | 0.528373 |
| Logistic raw | 0.776344 | 0.548004 | 0.134773 | 0.431000 |
| Logistic calibrated | 0.776344 | 0.548004 | 0.134855 | 0.431242 |
| Boosting raw | 0.784210 | 0.560998 | 0.132362 | 0.423153 |
| Boosting calibrated | 0.784210 | 0.560998 | 0.132331 | 0.423037 |

Average precision is not trapezoidal PR AUC. Brier/log loss lower is better.
Calibration slightly worsened logistic validation Brier/log loss on this split;
the pipeline retains this result rather than assuming calibration improves every
model. Boosting has better point estimates here; uncertainty and selection
criteria have not yet established a final winner. These values do not prove
performance on later calendar cohorts, different populations or a production
underwriting/collections workflow.

## Predeclared settings

`settings.json` was saved before fit: logistic C=1, lbfgs max_iter=2,000,
tol=1e-8; boosting learning_rate=.05, 120 iterations, max_leaf_nodes=15,
min_samples_leaf=50, l2_regularization=1, random_state=71. Boosting has no
internal random validation split or early stopping. No hyperparameter search
was performed. Both learned models receive the same train-only encoder.

Sigmoid-on-logit calibration fits only calibration labels, C=1, with input
probabilities clipped at 1e-12 only for finite logit arithmetic. Constant input
uses intercept-only calibration prevalence. Negative slopes or convergence
failures abort the run for investigation. Validation reliability bins are ten
predeclared intervals; the last includes probability 1. Counts reconcile to
the full validation cohort. No cost/threshold policy was selected in this run.

## Saved evidence and verification

Three model JSONs, three calibration JSONs, settings, fit/access receipts,
aggregate metrics/reliability bins, private validation score Parquet and the
completion/verification receipts are private. No pickle model loading is used.
Tree export is restricted to the installed, reviewed sklearn 1.8.0 binary
numerical-tree layout; a different version requires review and new parity checks.

Reloaded model JSONs reproduce native-library predictions on all 26,999
development clients to absolute tolerance 1e-12. Every aggregate metric is
recomputed from saved validation score rows for all six model/variant sets.
Every actual output hash and the current assessment source digest verified.
The status is `RETAIL_DEVELOPMENT_ASSESSMENT_VERIFIED`, with production
qualification, champion selection and final-test scoring explicitly false.

Paired uncertainty/support analysis has now run; see
[RETAIL_VALIDATION_UNCERTAINTY.md](RETAIL_VALIDATION_UNCERTAINTY.md).
Development-only selection, model/feature freeze, reserved random holdout
evaluation and research model card have subsequently completed; see
[RETAIL_FROZEN_HOLDOUT_AND_MODEL_CARD.md](RETAIL_FROZEN_HOLDOUT_AND_MODEL_CARD.md).
App integration, fairness/intended-use and economic-policy assessment remain
separate requirements. P2 mortgage data gates and other workspace work remain.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/assess_retail.py --features retail-features-d53aa8ba9ed6
```
