# P1 — frozen validation model explanations, 10/10/2026

Study `retail-explanations-84b3ac3bab6e` inspects frozen boosting/raw model
`retail-freeze-3dc86f5afe01` on the existing 4,499 validation clients/995
next-month source events. Baseline Brier0.1323618952 and AUC0.7842100055 match
the saved validation scores within absolute1e-12. Model weights, encoder,
calibration and selection are reused; no fit or final holdout scoring occurs.

## What the study answers

Global: how much the fitted model's predictive performance deteriorates when
one declared group is shuffled across the whole validation cohort.

Local: how four declared groups allocate the difference between a fixed
training-reference probability and a selected validation client's model
probability. This is model behavior under a defined reference distribution,
not causal effects, realistic intervention outcomes or approved adverse-action
reasons. Local examples use study-specific validation-case labels; source IDs
and reference records remain private and are absent from HTTP exports.

## Four groups and whole-validation permutation

All 19 allowed source predictors, including every encoded one-hot column,
belong to exactly one group:

| Group | Source fields | Mean Brier increase | Mean AUC decrease |
|---|---|---:|---:|
| Repayment status | PAY_0, PAY_2…PAY_6 | 0.0554565521 | 0.1714291109 |
| Payment history | PAY_AMT1…PAY_AMT6 | 0.0092033955 | 0.0535272921 |
| Bill history | BILL_AMT1…BILL_AMT6 | 0.0046384849 | 0.0114338339 |
| Credit limit | LIMIT_BAL | 0.0019218600 | 0.0169629540 |

For each group, all its columns use one common shuffled donor-row order.
This retains valid one-hot categories and within-group six-month trajectories.
Three PCG64 seeds20261010/11/12 are saved individually; their arithmetic means
are descriptive repeat summaries, not confidence intervals. Positive Brier
increase/AUC decrease indicates reliance under this perturbation. Negative
values are preserved. Correlation between groups can affect the ranking; a
low importance does not prove a source field is irrelevant.

See [scikit-learn's permutation-importance documentation](https://scikit-learn.org/stable/modules/permutation_importance)
and its [correlated-feature example](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html).
The engine uses grouped columns explicitly, rather than independently shuffling
encoded categories or describing single-feature importance.

## Exact local grouped Shapley

The reference consists of32 training clients chosen by seeded SHA-256 ID rank.
No validation targets select the reference. Twelve local cases are selected at
evenly spaced validation probability ranks, including the extremes, without
label-based selection. They are examples, not a random sample for estimating
population explanation distributions.

There are four players and16 coalitions. For each coalition and each of32
reference rows, present groups come from the selected client and absent groups
come from that one reference row. The coalition value is the mean predicted
probability. Exact Shapley subset weights allocate this finite-reference game;
the four probability contributions plus the empty-coalition reference equal
the full model probability within1e-12.

Values are probability contributions; the UI multiplies by100 and labels them
percentage points. They are neither log-odds nor relative percent changes.
The four-player calculation is exhaustive, without Monte Carlo permutation
sampling or a TreeExplainer call. It is grouped Shapley, not individual-feature
SHAP. Changing the groups/reference changes the explanation.

Within-group dependence is retained; cross-group dependence is broken. Hybrid
records may not be economically plausible. No causal meaning follows from the
term marginal substitution. Background dependence and output-scale choices are
also discussed in the [SHAP explainer documentation](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html).

## Source contracts, serving and evidence

Only saved development train/validation rows are materialized for inspection.
Source score identities and targets must match the validation rows exactly;
all replayed probabilities must match their fixed selected-model/variant
scores. The original acquisition, canonical/feature/assessment/comparison/
freeze graph and outputs are hash-pinned. Numerical library versions and
method sources are included in the immutable study receipt. A complete verify
replays all permutations, reference selection,16-coalition games and aggregates.

The report, assumptions and private reference/coalition evidence have separate
digests. Serving performs a full replay before caching and hashes every pinned
input/output/receipt on subsequent requests. Same-size/mtime evidence changes
are rejected. No raw private-reference endpoint is exposed.

Retail → Model explanations → choose study → choose validation case → export.
GET `/api/retail-explanations` requires freeze_id. GET
`/api/retail-explanation` and `/api/retail-explanation-report` require freeze_id
and explanations_id, with an optional valid validation case. A case-filtered
export keeps the whole-cohort global summary and only that local explanation.
Unknown cases, mismatched models and traversal identifiers are rejected.
Responses are private/no-store; the export carries source/model scope and
limitations. No policy version is needed: this study explains the frozen model,
not threshold/action decisions.

Independent audit `retail-explanations-audit-d4c7f6227d3d.json`: **375 checks
PASS**. It uses its own depth-first saved-tree traversal, sklearn Brier,
tie-aware concordance AUC, independent encoder-group positions, seed/reference
and case selection, and all24 group orderings for Shapley. The original
consumed holdout ledger remains byte-identical to the pre-study baseline.

Actual browser receipt `retail-explanations-browser-qa-eb83c145ee0f/receipt.json`:
**5 checks PASS**, whole-validation global groups,12 cases, selected-case
export/reconstruction, desktop/390px mobile and unchanged holdout, with no
unexpected browser errors. Full source replay occurs before navigation;
subsequent API reads still hash-check the complete evidence graph. The mobile
export is152.4375px wide, within the390px viewport, and its label does not wrap.

An initial browser harness stalled and was explicitly interrupted; that receipt
is not a PASS. An independent warm-page diagnostic verified the actual UI and
export. The final harness uses DOMContentLoaded plus explicit data assertions
and phase logging. Its first completed run exposed an overly strict test
expectation of inline-flex on a flex child; the final check accepts CSS
blockification to flex while checking actual geometry and nowrap. Numerical
methods/model artifacts were unchanged throughout these harness corrections.

Complete regression: **1,090 tests PASS**, all113 files across15 fresh
sequential batches, no failures/errors/skips/retries. Full collection matches
JUnit totals in `test-batches-94ff9b4cc30d/receipt.json`. Includes13 focused
explanation tests: additive/interaction/symmetry/dummy/efficiency properties,
saved-score parity, fixed configuration, partition/SQL holdout exclusion,
immutable replay/corruption, source-bound HTTP/privacy and independent tree/AUC
edge cases. A missing internal-node value in a test fixture was corrected
before this complete run; production model artifacts were unchanged.
Live8770 restarted with the updated service. Receipt
`retail-explanations-live-70f96ee3fb04/receipt.json`: **PASS**, frozen-model
catalog binding, exact saved/API selected-case report/export parity, private
no-store responses and unchanged consumed holdout ledger.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_explanations.py --assumptions private evidence omitted from public release
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_explanations.py --verify retail-explanations-84b3ac3bab6e
.\.venv\Scripts\python.exe -X utf8 scripts/audit_retail_explanations.py --explanations-id retail-explanations-84b3ac3bab6e
.\.venv\Scripts\python.exe -X utf8 scripts/browser_retail_explanations_qa.py
.\.venv\Scripts\python.exe -X utf8 scripts/check_retail_explanations_live.py
```

Build creates a new study version. Use verify for existing evidence. This
parent study implements global inspection and12 local validation examples.
The subsequent [complete-cohort workflow](RETAIL_COHORT_EXPLANATIONS_WORKFLOW.md)
now supports all4,499 saved validation clients and whole-cohort local-contribution
distributions, while preserving this parent study and its reference.
Intended-use validation, regulated decision explanations, background sensitivity analysis,
application affordability/limit-pricing, interventions and temporal monitoring
remain open. The full five-workspace suite is not complete.
