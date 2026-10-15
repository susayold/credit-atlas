# Gated development assessment

assess-study composes the pinned constant/logistic/boosting, separate calibration
and validation components across verified annual cases. No champion is selected,
final-test predictors materialized or final-test performance calculated.

## Check gates

    .\.venv\Scripts\python.exe -m credit_atlas.cli assess-study --study study-e7b5a47685c1 --feature-audit feature-audit-585be3bb2299

Current actual 2012 result: BLOCKED_BEFORE_FIT. Missing required vintages,
insufficient class support, candidate protocol and absent development feature
review remain blockers. The command preserves access/blocked receipts and
creates no model artifacts or scores.

When qualified data and a reviewed specification exist:

    .\.venv\Scripts\python.exe -m credit_atlas.cli assess-study --study <actual-study-id> --feature-audit <matching-feature-audit-id> --review-file <review-json-on-D>

The pinned gate requires at least 200 positive and 200 negative train loans
and at least 50 of each class in calibration, validation and test. The
approved protocol's own support requirements also apply. Missing sources,
changed evidence, unapproved protocols, absent training features or entirely
missing training predictors do not qualify.

## Review contract

The JSON identifies exact study/feature receipts using SHA-256, reviewer and
rationale, with predeclared settings. Development review does not approve a
model, champion, final-test access or production scoring.

Draft example; replace placeholders and complete review:

    {
      "schema_version": 1,
      "status": "draft",
      "study_id": "<actual-study-id>",
      "study_receipt_sha256": "<actual-digest>",
      "feature_audit_id": "<matching-feature-audit-id>",
      "feature_receipt_sha256": "<actual-digest>",
      "reviewer": "<review-record-owner>",
      "rationale": "<source/availability/feature/temporal review>",
      "settings": {
        "train_cutoff": "2014-01-01",
        "calibration_cutoff": "2016-01-01",
        "evaluation_cutoff": "2018-01-01",
        "logistic_C": 1.0,
        "calibration_C": 1.0,
        "minimum_events": 50,
        "bin_edges": ["0", "0.001", "0.005", "0.01", "0.02", "0.05", "0.1", "0.2", "0.5", "1"],
        "challenger_parameters": {
          "learning_rate": 0.05,
          "max_iter": 100,
          "max_leaf_nodes": 15,
          "min_samples_leaf": 50,
          "l2_regularization": 1.0,
          "random_state": 17
        }
      }
    }

Executable status is approved_for_development; draft is rejected. Dates must
match the prepared protocol exactly. minimum_events cannot be below 50 or
exceed available calibration/validation class counts. Regularization and
boosting parameters are bounded before fit.

Fixed logistic C is supported. Alternatively set logistic_C to null and add
logistic_tuning with folds, C_grid, minimum_train_class and
minimum_holdout_class, using the pinned engine's temporal-fold structure.
There must be 2–8 predeclared folds and 1–8 distinct positive C candidates
no greater than 100. Inner minima remain at least 200 train / 50 holdout.
Folds precede outer train fitting, preserve label-known timing and use
disjoint holdout loans. Only outer train data tunes C.

Internal fold support is preflighted. fit-plan.json records declared fit
calls and encoded float64 matrix bytes. The memory estimate excludes Python
objects, copied arrays and library workspaces; it is not peak RAM. Failed
tuning has no default-C fallback; the engine's candidate failure ledger is
retained when available.

## Results and verification

Completed development runs preserve reviewed settings, access intent,
source/study/feature lineage, fit plan, model JSON and separate calibration
JSON. Every model shares target, features and outer cohorts. Raw/calibrated
validation scores and metrics remain private.

The adapter reloads every model/calibrator, checks scoring parity on all
validation loans, rederives source metrics and independently calculates
Brier score. Inputs are checked again after fitting.

DEVELOPMENT_ASSESSMENT_VERIFIED retains research_ready=false,
champion_selected=false and final_test_scored=false. Selection/rubric freezing,
out-of-time evaluation, model cards and validated scoring remain later steps.

Validation identities and score rows in assessment.json are private and
absent from browser bundles/descriptive exports. Synthetic integration tests
verify software orchestration; they do not prove actual mortgage performance.

## Application evidence

`/api/studies` and Models & validation now list related completed assessments.
Every summary verifies study/feature/method lineage and the full expected
artifact digests. Completed development results also require reviewed settings,
prepared cohort support, validation denominators and persisted parity evidence.
The API exposes raw/calibrated ROC AUC, average precision, Brier and log loss
as aggregates only; loan identities, score rows, model parameters and private
paths are excluded. Average precision is not trapezoidal PR AUC.

Blocked attempts show explicit reason codes and no performance metrics.
Changed/legacy artifacts are marked unavailable. Actual annual 2012 remains
blocked before fitting; no champion or final OOT evidence is implied.
