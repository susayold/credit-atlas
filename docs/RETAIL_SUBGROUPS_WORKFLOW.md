# P1 — validation subgroup diagnostics, 10/10/2026

Study `retail-subgroups-3cf671cf3152` is bound to policy
`retail-policy-bd4b8623de28`, case `lower_thresholds`, and frozen boosting/raw
model `retail-freeze-3dc86f5afe01`. It joins demographics only for the 4,499
selected validation clients. No demographic predictor is added to the model;
no model is refitted or reselected and no final holdout is rescored.

The source is historical Taiwan booked-card behavior, target
`source_default_payment_next_month`. Validation already informed model
selection. These exploratory group diagnostics are not out-of-time monitoring,
application decision outcomes, causal attribute effects or fairness/compliance
certification.

## Supported dimensions and metric definitions

SEX, EDUCATION and MARRIAGE retain original numeric source codes. Undefined
education/marriage categories are not merged or silently dropped. Age bands
are declared as 18–29, 30–39, 40–49 and 50–120; missing/invalid values remain
in a separate bucket. No current age or inferred identity is substituted.

Every dimension reconciles to the complete validation cohort and event total.
The actual source has 2 SEX groups, 7 EDUCATION groups, 4 MARRIAGE groups and
4 age bands. With declared minimum 50 records, 4 education groups and one
marriage group have insufficient descriptive support. Their counts remain
visible and metrics are unavailable, rather than false zero estimates.

Mean probability, source target rate, Brier and their calibration gap require
minimum records. AUC additionally requires at least 10 events and 10
non-events. AUC uses Mann–Whitney concordance with half credit for score ties;
one-class groups remain unavailable. Display cutoffs do not prove precision.
There are no confidence intervals, significance or multiple-comparison tests.

High-risk event capture is decline events / all source events in the group.
High-risk non-event flag rate is decline non-events / all source non-events.
Each denominator must have at least 10 observations and the group must meet
the records cutoff. Manual review remains a separate action; it is not counted
as decline. The observed target does not identify outcomes after rejection,
review or intervention.

Actual whole-validation controls:

- 4,499 clients, 995 source events; target rate 22.1160%.
- Mean probability 22.4589%; mean prediction minus target rate +0.3429
  percentage points.
- Brier 0.1323618952; AUC 0.7842100055.
- Decline flags 559 events and 447 non-events for the declared 0.10/0.30 rule;
  event capture 56.1809%, non-event flag rate 12.7568%.

These are validation diagnostics. The saved final holdout metrics remain a
separate one-time result, not a subgroup/policy tuning surface.

## Workflow and verification

Retail → choose a policy version → Subgroup calibration & policy coverage.
An existing study is bound to that exact policy and frozen model. Select the
study and one supported dimension; export includes that same scope. If no
study exists for the selected policy, the app says so rather than substituting
a different policy. Tạo subgroup study creates a new immutable study for the
chosen declared case, using all four dimensions and support cutoffs 50/10.

GET `/api/retail-subgroups` requires policy_id + freeze_id. GET
`/api/retail-subgroup` and `/api/retail-subgroup-report` require these IDs and
subgroups_id, with optional supported dimension. POST `/api/retail-subgroups`
requires an exact schema-1 plan and the local same-origin JSON client.
Exports are aggregate-only, private/no-store, without client identifiers.

The original validation demographic join is stored privately. Full replay
checks this join and every aggregate against the selected saved-score cohort.
Source/method/receipt/output digests are pinned, with hash-checked cached
serving. Independent NumPy/sklearn audit checks grouping, counts, probabilities,
Brier, tie-aware AUC, action counts and rate denominators. Audit
`retail-subgroups-audit-d3f5e79668a4.json`: **314 checks PASS**, consumed holdout
ledger unchanged. Twelve focused tests cover ties, one-class/low support,
unknown groups, age boundaries, duplicate joins, selected-ID-only SQL,
source corruption, filtered/private HTTP exports and mutation origin rules.

Complete regression: **1,077 tests PASS**, all111 test files across14 fresh
sequential batches, no failures/errors/skips/retries. Receipt:
`test-batches-e08f87732391/receipt.json`. Actual browser receipt
`retail-subgroups-browser-qa-9c07c0d9e7bb/receipt.json`: **5 checks PASS**,
including source-bound dimensions, small-group unavailable metrics, private
filtered export, desktop/390px mobile and unchanged consumed holdout ledger.
Live8770 updated and checked: `retail-subgroups-live-f4e0fb0873fc/receipt.json`
**PASS**, source-bound catalog and exact saved/report/export parity for
EDUCATION, private/no-store responses and unchanged holdout ledger.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_subgroups.py --assumptions data/private/retail-subgroups-plan-20261010.json
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_subgroups.py --verify retail-subgroups-3cf671cf3152
.\.venv\Scripts\python.exe -X utf8 scripts/audit_retail_subgroups.py --subgroups-id retail-subgroups-3cf671cf3152
.\.venv\Scripts\python.exe -X utf8 scripts/browser_retail_subgroups_qa.py
.\.venv\Scripts\python.exe -X utf8 scripts/check_retail_subgroups_live.py
```

Build creates a new version; use --verify to check an existing study. Actual
temporal monitoring, fresh intended-use population validation, protected-group
definitions/review, uncertainty analysis and interventions remain open. P1 and
the full five-workspace suite are not complete at this checkpoint.
