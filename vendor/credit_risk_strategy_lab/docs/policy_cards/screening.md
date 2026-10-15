# S0–S3 screening engine — development policy card

## Intended use and status

Retrospective screening of already-funded mortgages, not an underwriting approval
system. B21 is PARTIAL. No policy has been selected on validation data or evaluated
on the final out-of-time cohort. All thresholds in `configs/policies.json` are
illustrative engineering inputs, not recommended lender risk appetite.

| Policy | Rule | Current evidence |
| --- | --- | --- |
| S0 | Retain every base-eligible loan | Private 2012 descriptive replay |
| S1 | Classic FICO >= 680 | Private 2012 descriptive replay |
| S2 | Calibrated 12-month PD <= 0.02 | Synthetic UAT only |
| S3 | S2 plus occupancy principal-share caps: I <= 20%, S <= 20% | Synthetic UAT only |

The risk estimand is numeric D3 before prepayment. These are not probabilities
of loss, unconditional lifetime defaults, or actual approval decisions.

## Stable population and ordered decisions

Each input loan/landmark must appear exactly once. All policies retain the same
input identities and base-eligible denominator. Outcomes never enter rule inputs.
The ordered base gates require funded status, cohort eligibility, positive finite
original principal, and a feature snapshot no later than the decision landmark.
Failed base gates produce `data_ineligible` before any risk rule runs.

Policy-required missing/invalid FICO or occupancy also produces `data_ineligible`,
but does not shrink the common base denominator. Missing model inputs produce
`review`; they are not replaced with zero risk. Invalid supplied PD is a data
failure. Cutoff equality passes. Each row records version, configuration hash,
ordered reasons and evaluated values/thresholds in a private audit trace.

S2/S3 require matching landmark, horizon and estimand, model/calibration IDs,
availability dates no later than the landmark, and the correct evidence context.
These metadata checks are necessary, not independent certification that a model
was properly trained or calibrated. The real replay runner therefore permits
only S0/S1 until evaluated model artifacts and temporal gates are implemented.

S3 calculates caps using original principal among provisionally selected loans.
It compares exact decimal amounts, not rounded displayed percentages. Any cap
breach marks the candidate `infeasible_concentration` and moves its provisional
selections to review. It does not greedily discard individual loans, relax a cap,
or optimize composition. B22 must address optimization separately. With no
provisional selections, shares are undefined and status is `no_selected_loans`.

## Verified private 2012 replay

Run: `policy-replay-74aac4ddd2df`, using `labels-60786ddbc109` and
`canonical-40ec3098d5a0`. Both inputs are hash-checked and linked by manifest.

| Measure | S0 | S1 |
| --- | ---: | ---: |
| Input loans | 50,000 | 50,000 |
| Common base eligible | 48,066 | 48,066 |
| Selected | 48,066 | 44,774 |
| Review | 0 | 3,292 |
| Data ineligible | 1,934 | 1,934 |
| Selected original principal, USD | 9,926,901,000 | 9,343,930,000 |
| Principal retained / eligible original principal | 100% | 94.1274% |

No risk reduction or causal benefit is inferred. Retention is not an approval
rate. This single-vintage replay uses the latest source release, not archived
historical publication snapshots, and has no strict historical PIT claim.
Loan-level outputs remain private; publication rights have not been approved.

## Reproduce

From the repository root, using the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m crsl.policy.engine demo
.\.venv\Scripts\python.exe -m crsl.policy.engine demo --minimum-fico 700 --maximum-pd 0.01
.\.venv\Scripts\python.exe -m crsl.policy.replay --label-run artifacts/private/labels-60786ddbc109 --canonical-run artifacts/private/canonical-40ec3098d5a0
.\scripts\test.ps1
```

Each run writes a new ignored private directory. Demo records are explicitly
synthetic. The replay writes two Parquet decision tables, summary, source/config/
code fingerprints and completion receipt; failures never get a completion receipt.

## Remaining acceptance gates

- Evaluated calibrated model artifacts with independently verified train/cutoff lineage.
- Missing annual calibration, validation and test cohorts; approved split protocol.
- Validation-only candidate selection, feasibility/Pareto analysis and paired uncertainty.
- Frozen final-OOT evaluation and policy comparison with observed outcomes.
- Public-safe evidence exports, website strategy page and workbook integration.
