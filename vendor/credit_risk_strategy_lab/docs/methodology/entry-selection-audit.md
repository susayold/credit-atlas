# Entry-selection audit — 2012 development sample

Evidence: private `attrition-5d4ccb408449/feature_distributions.parquet`.
Code: `src/crsl/attrition.py`; SQL: `sql/attrition_features.sql`.

The grouping variable is entry eligibility, not eventual label availability. This avoids
silently selecting a feature comparison sample by future repayment outcomes. Each of the
five feature profiles reconciles to all50,000 loans, including null values.

Compare like-for-like Relief Refinance segments rather than pooling different product mix:

| Segment | Early-entry eligible | Not early-entry | FICO median eligible / excluded | LTV median eligible / excluded |
|---|---:|---:|---:|---:|
| Non-Relief | 30,949 | 1,639 | 777 / 773 | 72 / 71 |
| Relief Refinance | 17,117 | 280 | 761 / 762.5 | 90 / 100 |

The terminal-at-entry group (13Non-Relief,2Relief) remains separately identifiable
privately and is too small for subgroup conclusions. These rows are not distributed publicly.

The excluded late-entry Relief group has a higher median LTV than the included group.
Therefore an early-entry risk result should not be described as applying unchanged to all
Relief Refinance loans. This is a descriptive selection difference, not a causal effect
of acquisition timing or a statistically adjusted estimate.

DTI has no observed values in the Relief group on either side of eligibility. Null-aware
summaries retain that absence rather than reporting a zero median. Among Non-Relief loans,
median DTI is31 for eligible versus32 for late-entry excluded loans (percentage points).

The full private table includes observed/missing counts, means, population standard
deviation, p10/median/p90 and range for FICO, DTI, LTV, CLTV and original principal.
No claims of distributional equivalence or uncertainty-adjusted subgroup differences
are made from medians alone. Further vintages must rerun the same selection audit.
