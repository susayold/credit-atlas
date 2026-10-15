# P1 — declared decision/policy workbench, 10/10/2026

## Scope and source

The workbench uses saved development-validation scores from the fixed model
`retail-freeze-3dc86f5afe01`: boosting/raw, case
`retail-case-470bdb40682f`, assessment `retail-assessment-b8b96f471254`.
The historical Taiwan UCI 350 cohort has 4,499 validation clients and 995
source next-month payment events. It is behavioral booked-card data, not
observed application approve/reject decisions. Validation was already used
for model selection; policy comparisons are exploratory development work.

The engine never trains or selects a new model, opens holdout score files,
optimizes thresholds, or changes the consumed final-test access ledger.
Upstream frozen-evidence verification may check the original split integrity;
no reserved predictors are materialized for this workbench. Final holdout
metrics remain the saved one-time evaluation, not a policy tuning surface.

## Decision rule and cost definitions

For each declared case with lower threshold L and upper threshold U:

- accept when p < L;
- manual review when L <= p < U;
- decline when p >= U.

Threshold ties stay together. Equal thresholds create an empty review band.
Empty action buckets have unavailable target rate and mean probability, not
zero estimates. Capacity is a count on this validation cohort; a breach is
flagged with overflow count. No records are dropped or silently reassigned.
This cohort capacity is not measured daily staff productivity or a live queue.

The user declares six nonnegative costs, one for each action × source outcome
(event/non-event). Units are explicitly `declared_cost_units`, not inferred
TWD cash losses. For action a, costs c(a,0) and c(a,1):

```text
Expected declared cost = sum[(1-p_i)*c(a_i,0) + p_i*c(a_i,1)]
Retrospective cost proxy = sum[c(a_i, observed_source_target_i)]
```

Expected costs depend on the saved probability and declared matrix; they do
not prove probability calibration under a new policy. Retrospective costs
are a label-weighted proxy, not actual economic losses. In particular, the
observed target does not identify what would have happened after rejecting,
reviewing or intervening on that historical client. Reviewer efficacy is not
estimated. Declaring a low review cost does not establish that review works.

Three constant-action benchmarks are always included: accept_all, review_all,
decline_all. The workbench deliberately does not choose an optimal threshold
or declare a production winner. Arithmetic uses Fraction on the shortest
decimal representation of saved float probabilities and declared decimal
costs; exports retain rational numerator/denominator and 50-digit display.
Probability estimates themselves remain finite-precision model outputs.

## Actual illustrative study

Plan: `data/private/retail-policy-plan-20261010.json`.
Study: `retail-policy-bd4b8623de28`, primary full replay verified.
Cost matrix: accept 0/10; review 1/3; decline 2/0 for non-event/event.
Capacity: 600. These are illustrative assumptions, not recommended costs.

| Case | L / U | Accept | Review | Decline | Review overflow | Expected cost | Retrospective proxy |
|---|---|---:|---:|---:|---:|---:|---:|
| lower_thresholds | 0.10 / 0.30 | 1,216 | 2,277 | 1,006 | 1,677 | 4,808.640601 | 4,643 |
| middle_thresholds | 0.20 / 0.50 | 2,904 | 1,053 | 542 | 453 | 5,282.018299 | 5,055 |
| higher_thresholds | 0.25 / 0.65 | 3,245 | 892 | 362 | 292 | 5,790.675939 | 5,554 |

All three cases exceed the assumed capacity. Their differing cost proxies do
not justify overriding that breach, approving a policy, or inferring realized
savings. The independent saved-score/Fraction audit
`retail-policy-audit-05ddcb458e25.json` passed 184 checks and confirmed the
actual consumed holdout ledger digest was unchanged.

## App workflow and contracts

Open Retail and scroll to Decision & policy scenarios. Choose a saved policy
version, edit the two thresholds, capacity and six costs, then Tính thử policy.
A preview is explicitly unsaved. Editing fields invalidates eligibility to
save until recomputation. Lưu policy version creates a distinct immutable
study bound to the fixed model; it never replaces an earlier study or model.
Xuất policy đã lưu exports that saved version, not unfinished form edits.
The `retail_policy_id` URL state restores the chosen version on reload. An
unavailable explicit policy has no fallback to a different study/model.

GET `/api/retail-policies?freeze_id=...` returns source-scoped studies.
GET `/api/retail-policy` and `/api/retail-policy-report` require exact
policy_id + freeze_id. Preview additionally requires lower_threshold,
upper_threshold, review_capacity (empty means unavailable), and each action's
`_event`/`_non_event` cost. POST `/api/retail-policies` accepts the complete
schema-1 assumption plan and requires the local same-origin JSON client.
Reports are private/no-store and aggregate-only, with no client identifiers.

Plans require one to eight unique named cases, ordered [0,1] decimal-text
thresholds, all six decimal-text costs, explicit private visibility and false
public release approval. No final-test/model-selection filter is accepted.
Receipt verification hashes source/outputs/methods, verifies the upstream
freeze and replays every aggregate from selected saved validation scores.
Preview results use the same bound source with fresh explicit assumptions.
Serving performs full replay on first access, then hashes the complete freeze,
comparison, assessment, features, canonical case, acquisition files and methods
before cached reads. Metadata alone is insufficient; a changed file with
restored size/mtime is rejected. Cached scores remain private; preview uses
these verified fixed probabilities and recomputes only declared policy costs.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_policy.py --assumptions data/private/retail-policy-plan-20261010.json
.\.venv\Scripts\python.exe -X utf8 scripts/build_retail_policy.py --verify retail-policy-bd4b8623de28
.\.venv\Scripts\python.exe -X utf8 scripts/audit_retail_policy.py --policy-id retail-policy-bd4b8623de28
.\.venv\Scripts\python.exe -X utf8 scripts/browser_retail_policy_qa.py
```

Do not rerun the build command merely to verify; it creates a new version.
Use --verify for saved studies. Twenty focused tests cover rule boundaries,
ties, empty buckets, exact costs, capacity, strict input bounds, source changes,
semantic report corruption, independent cost faults, version saves and HTTP
origin/export contracts and cached evidence corruption with restored metadata.

## Remaining P1 work

Actual underwriting datasets and rights, affordability/income evidence,
economic cost/pricing calibration, collections/intervention outcomes,
subgroup/monitoring/explainability review and production governance remain
open. This checkpoint implements a research policy tool in the existing suite;
it does not complete P1 or the five workspaces/50 capabilities.


Actual browser: `retail-policy-browser-qa-ee755fd4f0a0`, 9 checks PASS. The
explicit invalid-threshold request correctly returns HTTP400; its known console
resource error is separate from unexpected JavaScript/console errors. Saved QA
version `retail-policy-3e0a14a7b744` is an illustrative test of the save workflow,
not an approved company policy. Initial exploratory QA version
`retail-policy-97dedccc2c46` is also retained as an immutable illustrative study.
Live parity/mobile receipt: `retail-policy-live-b7738c5da1d2`, PASS, cached reports
2.588/2.576 seconds. Full regression: 1,065 PASS, all 109 files in 14 sequential
fresh batches, no skips/failures/retries; receipt `test-batches-388f12b7a161`.
The final mobile CSS repair was additionally verified in the live browser.

For low-memory complete regression runs:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/test_batches.py --batch-files 8
```

This runner first collects all application/upstream nodes, runs every collected
file sequentially and reconciles JUnit counts against collection. It does not
change model/engine code or silently retry failures.
