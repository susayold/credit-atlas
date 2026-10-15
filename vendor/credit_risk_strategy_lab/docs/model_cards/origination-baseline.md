# Origination baseline — development model card

## Status

B14 is PARTIAL. Constant-risk and logistic fitting/scoring/persistence components
are implemented and tested on synthetic fixtures. No real baseline model has
been fitted or evaluated. Calibration and probability-metric/reliability-table
components are synthetic-tested; source-integrated calibration/evaluation,
reliability charts, decision metrics and approved regularization selection remain incomplete.

The real command was attempted against `splits-357cd54010a4`,
`labels-60786ddbc109` and `canonical-40ec3098d5a0`. It correctly stopped at the
training gate before materializing model inputs or creating model artifacts.
The split is unapproved, required vintages are missing, and train has only 100
events versus this runner's development minimum 200. Other partition support
is absent. These thresholds are research settings, not universal standards.

## Intended target and population

Already-funded U.S. fixed-rate mortgages, first-observed early-entry 12-month
numeric D3 before prepayment. Latest-release fields are not independently
verified historical-publication PIT. No lending approval or causal claims.
Feature names are constrained by the reviewed origination allowlist. The encoder
fits only included training rows and persists medians, scaling, missing flags,
category levels and unseen-category handling.

## Baselines

- Constant: training event count / training row count. Evaluation labels never
  change this probability.
- Logistic: scikit-learn 1.8.0, LBFGS, regularization C explicitly supplied,
  max_iter=2000, tolerance=1e-8, no class weights or oversampling. Convergence
  warnings fail the fit rather than silently accepting incomplete optimization.
  C=1 in engineering tests is not an optimized research choice.

Implementation reference: [official LogisticRegression 1.8 documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.linear_model.LogisticRegression.html).

Rows must have unique IDs, train/included flags, binary targets and labels known
strictly before fit cutoff. Calibration/validation scoring cannot predate fitting.
The development scorer rejects final-test partitions. In-sample train predictions
are permitted only for engineering parity checks, not out-of-sample claims.

## Persistence and checks

JSON stores encoder state, coefficients/intercept, prevalence, fit cutoff and
evidence class. No pickle deserialization is used. Loading requires the retained
file SHA256 and validates coefficient dimensions, ordered feature schema,
numeric scaling state and prevalence reconciliation. JSON scoring matches the
training library within 1e-12 on synthetic tests; save/load scores match exactly.
An external hash pin detects changed files but is not a signature or proof of
research approval. Optional model dependencies have a separate pinned lock file.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-models.lock
.\.venv\Scripts\python.exe -m crsl.models.train --split-run artifacts/private/splits-357cd54010a4 --label-run artifacts/private/labels-60786ddbc109 --canonical-run artifacts/private/canonical-40ec3098d5a0 --C 1
.\scripts\test.ps1
```

The training command is expected to refuse the current incomplete source split.
Do not change approval flags or lower support just to obtain model metrics.
The train-only runner now rederives every split assignment and the complete
support audit from the source label table and frozen split configuration before
fitting. This is partition QA, not test model scoring. Direct verification on the
current 50,000-loan source matched all saved assignments and support, confirming
that training remains blocked. Changed assignment roles or inflated support are
covered by regression tests. Training-only tuning, calibration and
evaluation orchestration are required before B14 can pass.

## Calibration component

`models/calibration.py` fits regularized sigmoid-on-logit recalibration using
only included calibration rows. C is explicit; the default support guard is 50
events and 50 non-events. These are development settings awaiting protocol
approval. It verifies a common upstream model digest/evidence class, unique loan
IDs and model availability <= landmark <= label-known date < calibration cutoff.
It does not independently load the upstream score/model artifacts yet.

Valid endpoint probabilities 0 and 1 are clipped at 1e-12 only for finite logit
computation; invalid probabilities fail instead of being repaired. Negative
calibration slope triggers investigation, not automatic score-rank reversal.
Validation scoring must follow the calibration cutoff; test scoring is refused.
JSON persistence with a retained digest preserves predictions exactly in tests.
The implementation uses logistic regression on logits, not a claim of exact
equivalence to scikit-learn's CalibratedClassifierCV sigmoid estimator. No claim
of improved calibration is made before real validation evaluation.

## Evaluation component

`models/evaluation.py` provides validation-only ROC-AUC, average precision,
Brier score, clipped log loss and fixed-edge reliability tables. Average precision
is explicitly named; it is not mislabeled as trapezoidal PR-AUC. Event prevalence
and raw sample/event support accompany the scores. AUC/AP are suppressed when
either class has fewer than the configured minimum events (default 50).

Reliability bins are left-closed/right-open except the final bin includes 1.
Every bin includes its loan/event counts and support flag; empty-bin rates remain
null. Brier score uses the original probabilities. Log loss uses an explicit
1e-15 clip and reports the number clipped. Invalid PDs are rejected first.
Unique loans, included validation membership, label/score availability and a
common supplied score-artifact digest are required. The function does not yet
load and verify the underlying score artifact itself. Final-test inputs fail.
Known toy examples, bin boundaries, nulls and mixed-artifact guards are tested;
no real validation metrics or reliability chart has been generated.

## Integrated development assessment

`models/assessment.py` composes both constant/logistic models, separate
calibration and raw/calibrated validation metrics on disjoint loan IDs. It
rejects test/unused rows and requires all three input cohorts. All model outputs
are retained; no champion is selected. Changing validation outcomes leaves both
fitted models, calibration parameters and predictions unchanged in regression
tests. Real-evidence calls require split gate metadata and matching cutoffs;
source-file loading/hash verification is provided by `assessment_run.py` below.

The integration test exposed a degenerate calibration case: constant input
scores do not identify a data-driven slope. Those fits now use slope zero and an
intercept equal to the calibration-prevalence logit, explicitly labeled
`constant_input_intercept_only`. Raw constant-model predictions still use train
prevalence. Varying-score fits with negative slopes still fail for investigation.
The successful integrated runs are synthetic tests only, not mortgage results.

## File-backed assessment command

`models/assessment_run.py` verifies canonical/label/split receipt hashes, rederives
split assignments and class support, checks endpoint semantics and join support,
then materializes included train/calibration/validation rows only. Test labels
are used only in upstream split-support QA, never model scoring or selection.
It records source receipts, code fingerprint, feature/assessment settings and
private results in a new run directory. Failure receipts are distinct from
completion receipts. Neither completion status nor config C=1 constitutes final
research approval or optimized tuning.

```powershell
.\.venv\Scripts\python.exe -m crsl.models.assessment_run --split-run artifacts/private/splits-357cd54010a4 --label-run artifacts/private/labels-60786ddbc109 --canonical-run artifacts/private/canonical-40ec3098d5a0
```

This command currently refuses the actual 2012-only split before model creation.
Its successful file-backed test uses 1,600 explicitly synthetic loans across four
vintages: 400 train, 400 calibration, 400 validation and 400 untouched test loans.
Saved output contains only validation predictions, retains both models and both
raw/calibrated metric sets, and is marked synthetic/private/not research-ready.
A corrupted canonical file fails before output creation. Real calibration and
validation findings, approved tuning, reliability visualization and final OOT
remain unavailable.

## Training-only regularization selection

`models/tuning.py` implements an explicit finite C grid over at least two
predeclared internal temporal folds. It accepts only included outer-training
loans with labels known before the outer fit cutoff. Each fold refits its own
encoder on labels available before its fit cutoff; held-out landmarks follow
that cutoff and their labels must be known before the fold evaluation cutoff.
Internal holdout loans cannot overlap across folds.

The objective is pooled held-out log loss (weighted by loan count), with smaller
C as the deterministic exact-tie rule. All candidates/fold scores and failures
are returned. A candidate failing any fold is not eligible for selection; if all
fail, no C is selected. Calibration, outer validation and test records are
rejected. Under-supported folds fail rather than silently being removed.

Synthetic tests verify encoder fit counts, chronology/support and rejection of
non-train partitions. The assessment now runs this tuner before final training
when `logistic_tuning` is configured, and persists its results and selected C.
Fixed C and tuning are mutually exclusive; failed tuning cannot fall back to a
default. The repository's candidate development configuration has four C values
and two internal time folds (2009 and 2011 landmarks), with explicit support
guards. These settings are not yet an approved/frozen research protocol.
No real C has been selected. The current 2012-only source cannot support this
multi-period research selection. Integration tests verify final logistic fitting
uses the selected C and includes all outer-training rows afterward.

When every tuning candidate fails, the file runner saves `tuning-failed.json`
with each candidate/fold failure and a hash in `run-failed.json`. It creates no
assessment-completion receipt and uses no default C. Failure-injection tests
verify both the all-candidate result and the persisted failure path. These test
failures are synthetic, not hidden real research failures.

## Saved assessment verification

`models/verify_assessment.py` checks receipt/source hashes, validation loan
identities, model/calibration content linkage and all four saved metric sets
(constant/logistic × raw/calibrated). It reattaches labels from the source,
recomputes metrics and independently reconciles Brier arithmetic. A test edits a
saved metric and updates its file hash; source recomputation still rejects it.
This verifies source/score/metric consistency, not model refitting, historical
PIT, research approval or external timestamp authenticity. Downstream publication
and policy integration must retain those separate gates.

The assessment runner now invokes this verification before writing its completion
receipt. It saves `verification.json` and its hash only after reconciliation
passes. A failed verification preserves the private assessment and failure
receipt but produces no completion receipt. Failure-injection coverage verifies
this ordering; downstream readers must require the completed receipt.
