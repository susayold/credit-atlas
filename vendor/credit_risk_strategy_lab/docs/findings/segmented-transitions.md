# B12: segment transition evidence

The private run `segmented-transitions-5f034c3464c3` uses hash-verified
`canonical-f7322e3f7bc4` inputs. It produces 61 segment/origin/destination
cells covering 4,460,559 adjacent loan-month pairs. Segment totals reconcile
to the unsplit pair population and count probabilities sum to one per origin
within each segment.

Relief and non-Relief are source-defined groups. A separate unknown group is
retained if present. Each cell includes pair count, distinct contributing loans,
opening balance, missing-balance pair count and both count/balance probabilities.
Cells with fewer than 30 distinct loans are marked sparse. This threshold is a
descriptive warning, not a guarantee of statistical precision.

Repeated observations of a loan are dependent. Confidence intervals assuming
independent pairs would overstate precision. Loan-cluster uncertainty and
calendar-period stratification remain to be implemented before drawing stability
conclusions. Group differences alone cannot identify a program treatment effect.

Reproduce from the repository root:

```powershell
python -m crsl.segmented_transitions --canonical-run artifacts/private/canonical-f7322e3f7bc4
```

The implementation has focused tests for gap exclusion, missing-balance semantics,
segment support, duplicate dimension rejection and hash-checked ID-free export.
The verified aggregate is now integrated into the local website Transitions view,
the `05_Transitions` Excel sheet, the private report-data contract and the safe
aggregate package as `segmented-transitions.csv`. The source Parquet remains
private; only the bounded aggregate rows are exported.
