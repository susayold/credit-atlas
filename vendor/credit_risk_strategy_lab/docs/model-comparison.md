# Baseline versus challenger — implementation and evidence status

## Current conclusion

No model has been demonstrated superior on the mortgage dataset. B15 is PARTIAL.
The constant, logistic and histogram-boosting components can run through the same
private development assessment, but successful comparisons so far are synthetic
engineering tests only. The actual 2012-only split still blocks research fitting.

## Shared comparison contract

All configured models use the same explicit feature configuration, outer train,
calibration and validation loan populations and 12-month endpoint. Each encoder
is fitted on training only. Calibration is fitted separately for each model on
the common calibration cohort. Both raw and calibrated validation scores and
metrics are retained. No final-test model predictions are permitted in this
development runner, and it never automatically selects a champion.

The file-backed test verifies identical loan IDs for logistic and challenger
validation scores, six checked metric sets across three models, and retention
of every configured model. The verifier rejects omission of a configured model.
This establishes engineering consistency, not an empirical advantage.

## Challenger implementation

`src/crsl/models/challenger.py` uses scikit-learn 1.8.0
`HistGradientBoostingClassifier` with binary log loss. The candidate configuration
sets learning_rate=0.05, max_iter=100, max_leaf_nodes=15, min_samples_leaf=50,
l2_regularization=1 and seed=17. These are development settings, not tuned or
approved research values. Constructor bounds prevent an unbounded individual fit.

Early stopping and internal random validation are disabled; iteration count must
equal the configured budget. Class weights, warm starts and categorical dtype
inference are disabled. Features use the shared numeric/missing-flag/one-hot
encoder rather than a different native categorical or missing-value pipeline.
One native thread is used within fitting/scoring contexts for bounded local
execution; global machine settings are not changed.

Reference: [official scikit-learn 1.8 histogram boosting documentation](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html).

## JSON persistence and parity

The fitted numeric trees are exported into a versioned JSON structure: initial
raw score, per-node feature/threshold/children/leaf value, feature encoding and
fit provenance. Histogram leaf values already contain shrinkage and are not
multiplied by learning rate again. The exporter is pinned to reviewed scikit-learn
1.8.0 internal tree layout and refuses an unreviewed version or categorical tree.
This is a project-specific inference representation, not a stable scikit-learn
interchange guarantee.

Every fit checks JSON-tree predictions against native library predictions within
1e-12 on its training matrix. Tests additionally compare unseen-category
validation scoring. JSON save/load predictions are identical; loaded scoring
does not require reconstructing a pickle estimator. Reads require a retained
file digest and validate tree counts, bounds, finite values, feature references,
cycles/shared nodes and unreachable nodes. Malformed trees fail even when a test
updates the file digest. The digest is not a signature or research approval.

## Implemented checks

- Shared train-only inclusion, unique loan and label-availability contracts.
- Bounded iteration count; no automatic random-validation split.
- Input order and seeded fit reproducibility on synthetic fixtures.
- Validation scoring refuses pre-fit dates; final test scoring is rejected.
- Extra future outcome fields do not alter predictions.
- Native versus JSON scoring parity and exclusive-write roundtrip.
- Invalid parameters, forbidden features and malformed tree graph rejection.
- File-backed three-model calibration/validation with identical scored loan IDs.

## Required work before B15 can pass

1. Qualify additional actual vintages and approve the temporal research protocol.
2. Define and freeze a bounded challenger candidate menu with training-only selection.
   Current integration uses one predeclared configuration, not a completed tuning study.
3. Run feature/missingness/category ablations with the same comparison population.
4. Compare calibration, discrimination and fixed-cutoff retained risk/volume,
   with subgroup support and uncertainty rather than AUC alone.
5. Measure time/subgroup stability and record failed or inferior candidates.
6. Apply the predeclared champion rubric before opening final OOT.
7. Produce actual evidence-backed comparison tables/visuals and public-safe exports.

The correct eventual outcome may be retaining logistic. No challenger win,
causal screening benefit, approval-rate or lender-profit claim is made here.
