# Policy comparison cohort QA

## Overall assessment: usable for private development, not final research

Question: does the saved comparison preserve the same endpoint-available loan
population for the fixed S0/S1 descriptive replay? This is pipeline QA, not a
policy recommendation. No risk improvement has been estimated here.

Sources: `labels-60786ddbc109`, `policy-replay-74aac4ddd2df` and generated
`policy-cohort-de365a1b8314`, under ignored `artifacts/private/`.
Evaluation cutoff is 2026-04-01, exclusive, using date-only monthly label times.
These are latest-release retrospective records, not historical-publication PIT.

## Checks and results

- Source and output hashes verified; replay must reference the exact label input.
- Origination 12-month numeric D3-before-prepayment contract checked.
- All 50,000 source loan identities required in both decision tables before filtering.
- Decision dates, original principal and base eligibility must agree across inputs.
- S0 must retain every base-eligible loan.
- 47,984 rows included, with 47,984 unique loan IDs.
- Exclusions reconcile: 1,934 entry-ineligible plus 82 endpoint-unavailable.
- Independent SQL set comparison against labels: zero missing/extra loan IDs.
- Seven synthetic tests cover changed dates/principal/eligibility, invalid decision
  states, missing join keys, cutoff equality and policy-required missing data.

## Methodology boundaries and incomplete gates

Common endpoint availability is an evaluation filter, not an input to policy
screening. Candidate-specific data-ineligible decisions do not shrink the common
evaluation denominator. A missing endpoint is not a negative target. The 82
unavailable cases are retained in attrition accounting; they may induce selection
bias and are not claimed to be missing at random.

No charts are produced by this engineering check. Source-integrated bootstrap,
validation candidate selection, subgroup checks and final OOT remain pending.
Only 2012 is available; results cannot establish temporal generalization.
Private use only until publication rights review. No actual approval, causal
uplift or lender-profit claim is permitted.

## Reproduce

The primary artifact is executable project code; checks are preserved as a script
rather than duplicated into a new notebook for this integration increment.

```powershell
.\.venv\Scripts\python.exe -m crsl.policy.comparison --label-run artifacts/private/labels-60786ddbc109 --replay-run artifacts/private/policy-replay-74aac4ddd2df --evaluation-cutoff 2026-04-01
.\.venv\Scripts\python.exe scripts/verify_policy_cohort.py --cohort-run artifacts/private/policy-cohort-de365a1b8314
.\scripts\test.ps1
```
