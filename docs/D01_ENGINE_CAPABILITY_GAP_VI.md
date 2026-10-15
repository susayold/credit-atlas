# D01 engine capability-gap audit

**Checkpoint:** 2026-10-16  
**Scope:** M01-001 in `PLAN_MODULE_01.md`, section 47.18. This is an inventory of
the pinned engine copy and the current CreditAtlas implementation; it is not a
model qualification or a release/legal approval.

## Evidence boundary

The local vendor tree is pinned to commit
`8d9994cfcb91fe871d66a4238c3f56053d71e920`. `UPSTREAM.json` lists 164 selected
files; the latest private release-readiness receipt reports zero hash
differences against that manifest. The copy excludes raw data and old derived
runs. GitHub returned 404 for the upstream repository and raw files at that
commit on 2026-10-16, so this review can inspect only the content pinned locally;
it cannot confirm the current upstream branch or a distribution license.

Evidence labels below mean:

- **Code present:** implementation exists in the pinned engine or current app.
- **Evidence present:** the described result has a saved receipt/report or a
  current scoped test. A passing synthetic fixture is engineering evidence,
  not a result on real mortgage outcomes.
- **Gate open:** the plan acceptance condition is not met. In particular,
  2012-only checks do not establish multi-vintage behavior or model validity.

## Capability map

| Capability | Pinned engine evidence | CreditAtlas evidence now | Gap / consequence |
|---|---|---|---|
| Source and canonical tables | `src/crsl/ingest.py`, `canonical.py`, `source.py`, `contracts.py`; `sql/` definitions; Release 47 header contract | 2012 source snapshot and eight-stage clean descriptive rebuild are present; 50,000 loans and 4,510,559 loan-months; source and semantic receipts are recorded | Freddie annual Clarity downloads after 2012 remain authentication-gated. A public example/layout is not an annual vintage and its loan IDs do not overlap the sample panel. M01-002/003 are verified for the supplied corpus only. |
| Labels and observability | `labels.py`, `observation.py`, `splits.py`; explicit target, maturity, gap and censoring contracts | Existing early-entry D3 target is retained; 50,000/48,066/102 source/eligible/positive counts reconcile for the supplied release; actual 2012 model study deliberately stops before fitting | Target support, label semantics and maturity must be re-qualified against additional Freddie releases before R2/R3. Do not turn unknown, immature or censored rows into negatives. M01-008/009 are verified only for 2012. |
| Portfolio profile and cohort | `portfolio.py`, `portfolio_profile.py`, `sql/marts/`; stock, cohort and loan-month aggregates | Frozen profile, count/UPB denominators, cohort findings and privacy-safe exports have actual-data acceptance | Multi-vintage composition, release revisions and between-vintage comparisons remain open. Current counts are descriptive for one supplied release. M01-010/011 are single-vintage verified. |
| Transitions, cure and episodes | `transitions.py`, `episodes.py`, `behavioral.py`; adjacency and sustained-cure code | Current-vintage adjacent matrices and episode/follow-up ledgers reconcile; transition and chart support audits cover denominators and gaps | No cross-release transition semantics or multi-vintage cure/redefault support. Code/tests establish implementation behavior, not representative cure probability. M01-012/013 remain single-vintage descriptive. |
| Observed loss | `losses.py`, `sql/loss_audit.sql`; signed component bridge | 2012 observed loss components, residual and unresolved coverage are calculated and documented | Not a severity/LGD model, expected loss or ECL. Completion coverage and selection may vary by vintage; M01-014 is descriptive only. |
| Origination baseline | `features.py`, `models/baseline.py`, `models/train.py`; strict train-fitted preprocessing and allowlist | Allowlist, exclusion and synthetic adapter tests exist; actual 2012 preparation stops before fit | No fit without the planned cohort/support/split gates. Current 2012 positive support is insufficient for the intended independent temporal evaluation. M01-015–017 gates remain open. |
| Challenger, calibration and selection | `models/challenger.py`, `calibration.py`, `evaluation.py`, `tuning.py`, `verify_assessment.py` | Same-cohort, persistence, parity and evaluation contracts are exercised with engineering fixtures; UI reports before-fit blockers | No qualified real-data challenger, calibration, model selection, final OOT evaluation or frozen serving artifact. M01-018–021 and M01-027 are unmet for a real mortgage model. |
| Macro, forecast and policy | `macro.py`, `forecast.py`, `policy/`, `monitoring.py`; as-of adapters, scenario and policy components | Public macro/HPI/NMDB context and scenario/monitor surfaces exist in separate, typed source lanes; acceptance and Excel exports cover scoped routes | Aggregate context is not joined to loans as a point-in-time predictor. Forecast backtest, validated decision strategy, full model-resource benchmark and model monitoring remain unqualified. Keep macro, scenario and strategy claims separate from observed 2012 facts. |
| Report, Excel and app adapter | `reporting/export.py`, `workbook_data.py`, report schema and workbook builders | D01 aggregate/evidence exports, user-facing filters, findings and workbooks have current acceptance; M01-028 has broad but incomplete route coverage | Continue route-by-route export, private/public boundary and unavailable-state checks. A passing route does not certify every workspace. M01-022–026 are partial or local/implemented according to the backlog. |
| Separate sources and populations | Engine contracts identify Release 47 / Freddie semantics | NSMO v7.0, Ginnie sample formats, FHFA/NMDB aggregates and HUD/CFPB context have separate source cards, code paths and evidence; NSMO is its own D02 case | Never pool NSMO/Ginnie/HMDA/HUD/NMDB rows into Freddie training by apparent field-name match. Ginnie production awaits the user-signed-in cookie path. These extensions do not fulfill the Freddie multi-vintage requirement. |

## What this audit establishes

1. The engine is a substantial reusable mortgage lifecycle codebase, not a
   ready-trained credit-risk product. Its feature catalogue explicitly calls
   the origination encoder a tested component and says it is not a fitted or
   approved real-data model.
2. CreditAtlas has reproduced the descriptive R1 foundation on the available
   2012 Freddie corpus and added review, exports, data-source views and
   engineering gates. This proves that one source/run can be profiled and
   reported; it does not prove annual-vintage compatibility.
3. Model-related code and synthetic engineering tests do not constitute
   discrimination, calibration, uncertainty or OOT evidence. Current backlog
   gates M01-015–021 and M01-027 remain open until qualified outcome data and a
   frozen temporal protocol exist.
4. The highest-value next data action for D01 is still obtaining authorized
   Freddie annual samples. The prepared Ginnie downloader can progress a
   separate case after a signed-in session cookie path is provided. Neither
   action permits source pooling.
5. R1 delivery work continues independently: finish the remaining
   M01-028 route inventory and scoped success/failure/privacy acceptance.

## M01-001 status

The capability-gap map and available-data boundary are now documented for the
verified pinned source copy, current D01 app and current backlog. M01-001 stays
**Partial** until the original upstream is inspectable again or the exact
selected-file manifest is accepted as the full source scope, and any remaining
website/repository inventory gaps are reconciled. This status does not reduce
or redefine M01-005/006: additional qualified Freddie vintages are still
required.

Evidence references: `vendor/credit_risk_strategy_lab/UPSTREAM.json`,
`docs/D01_RELEASE_READINESS_VI.md`, `docs/D01_CANONICAL_SEMANTIC_AUDIT_VI.md`,
`docs/D01_EXPORT_CONTRACT_AUDIT_VI.md`, `docs/NSMO_D02_CASE_BUILD_PLAN_VI.md`,
and the M01 table in `docs/BACKLOG_STATUS.md`.
