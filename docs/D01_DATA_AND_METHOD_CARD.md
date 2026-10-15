# D01 data and method card

Status: descriptive research checkpoint, 2026-10-08. This card explains the
implemented measures; it does not certify the entire R0–R4 release.

## Source and population

- Source: locally authorized Freddie Mac Release 47 annual sample, origination
  year 2012. Only this vintage is currently qualified in the app.
- Frozen case: d01-a24484b21a21; pipeline: pipeline-307c354f3d74.
- Pinned engine: 8d9994cfcb91fe871d66a4238c3f56053d71e920.
- Population: 50,000 loans; 4,510,559 reported loan-month observations.
- Observed reporting dates extend from January 2012 through March 2026.
  These are reporting periods for the same source vintage, not fifteen
  separate origination vintages.
- Source receipt, hashes and reproduction results remain private. This is a
  retrospective latest-release dataset; strict historical information
  availability is not established merely because records have old dates.

## Different grains and denominators

| View | Grain | Denominator / interpretation |
|---|---|---|
| Monthly portfolio | Reporting month, selected segment | Observed active stock and observed balances in that month |
| Early-entry labels | One row per source loan | Eligibility and outcome availability are reported separately |
| Vintage competing events | Eligible first-observed entry cohort | Risk set and competing exits at 6/12/24 months |
| Transition matrix | Observed adjacent month pair | Same origin state, segment and reporting year; lifetime is explicit |
| Episode counts | Confirmed event | A loan may have repeated cure/redefault events |
| Episode follow-up | Confirmation event, horizon and support status | Contiguous known nonterminal observations after actual confirmation |
| Observed loss | Source terminal event / available components | Reported signed loss and component coverage; unresolved records remain separate |

The reporting-month filter applies only to monthly portfolio evidence.
The transition-year filter applies only to yearly transition rows.
The vintage horizon does not select the episode follow-up horizon.
Loss and quality monitoring retain their whole-source scope.

## Target contract

Version: d01-early-entry-d3-before-prepay-12m-v1.

The landmark is the first observed month. Eligibility retains the pinned
early-entry rule. The outcome window is the following twelve months: t+1
through t+12. Numeric delinquency codes 03 through 99 define the D3 event,
before prepaid/matured exit. This is an observed D3 event target; it is not a
regulatory default-PD definition or a precise days-past-due measurement.

Unknown, censored and other-exit outcomes remain unavailable when the binary
target contract does not support a value. An absence of a recorded D3 event
does not itself prove a negative label. Prepaid/matured exit has the pinned
event-before-prepayment interpretation and is not pure refinancing.

Actual source label reconciliation:

| Quantity | Loans |
|---|---:|
| Source population | 50,000 |
| Eligible early-entry population | 48,066 |
| Ineligible | 1,934 |
| Binary target available | 47,984 |
| Positive | 102 |
| Negative under this target contract | 47,882 |
| Binary unavailable, including ineligible | 2,016 |

Positives comprise 89 Relief and 13 non-Relief loans. Relief segmentation is
not synonymous with the narrower HARP subset. These sample counts do not
establish a causal program effect or performance on other credit cycles.

## Transition calculation

The app reuses the pinned transitions.sql definition. For each loan, it first
finds the next observed record in the complete timeline, then admits a pair
only if the records are exactly one calendar month apart and the origin is
nonterminal. It never filters a year before computing the next observation.
Terminal destinations remain distinct from delinquency states; gaps are not
bridged.

Year attribution uses the opening month at t. A December 2020 to January 2021
pair belongs to reporting year 2020. Balances use opening UPB at t.

For each year/segment/origin:

- Count probability = destination pair count / all admitted origin pairs.
- Balance probability = destination sum of known opening UPB / all known
  opening UPB for that origin.
- Missing-balance pair count is displayed independently. Missing balances
  are not filled with zero; no usable denominator gives no balance probability.
- Distinct loan support is counted from loan identifiers at the requested
  grain. It is never obtained by adding distinct counts from smaller groups.
- Sparse means fewer than 30 distinct loans. This is a descriptive support
  flag, not statistical validation or an independent-pair confidence interval.

Actual period extension: 4,460,559 adjacent pairs, 1,091 year/segment cells
and 94 lifetime/segment cells. Reporting years are 2012–2026. Three checks pass:
year cells reconcile to lifetime cells; overall lifetime cells reconcile to
the frozen engine matrix; segmented lifetime cells reconcile to the frozen
engine segment mart. Counts and decimal balances are compared inside DuckDB
before JSON conversion. See period-transitions-20261008.json in private artifacts.

## Cure, redefault and follow-up

Sustained cure is confirmed at the third consecutive CURRENT nonterminal
month after D3. Confirmation is not backdated to the first CURRENT month.
Unknown observations and gaps break linkage. A CURRENT terminal exit is not
a cure. Redefault after confirmed sustained cure is distinct from first D3.

The frozen panel has 4,902 confirmed events, including repeated events.
Follow-up support at 6 and 12 months begins after the actual confirmation
month. Complete support requires contiguous known nonterminal observations.
Gap, unknown, terminal exit, terminal at confirmation and source end are
separate statuses. Their event counts are not cure/redefault probabilities.
Distinct loans cannot be added across event/status groups.

## Loss and missingness

Observed reported loss retains source signs, including negative values.
The implemented bridge distinguishes reported components, unresolved
coverage and residual checks. It is not an estimated LGD, expected loss or
IFRS 9/ECL result. Missing components are not zero-filled to force a bridge.

Current field availability includes 17,400 missing original DTI observations,
of which 17,399 belong to Relief loans; all 50,000 VantageScore and valuation
fields are unavailable in this qualified source. These counts identify
availability, not a verified reason for missingness. Structural explanations
need dictionary/source evidence before becoming a model assumption.

## Model boundary and future data

No qualified mortgage model has been fitted. The implemented prepare-study
command audits temporal assignments and actual class support and records
access before reading labels. Preparation is not a frozen model-selection
protocol and does not authorize final-test use for tuning.

The prepare-features command now audits the pinned origination allowlist,
fits encoder statistics only on included train loans and checks persisted
development-transform parity. Actual 2012 preparation has 43,327 train rows;
calibration/validation rows remain absent. It does not fit a risk model.
Final-test predictors are not materialized. Source split rechecking can read
test label support, with an access log written beforehand.

Required additional vintages, split support, feature qualification and an
approved frozen study protocol remain unmet. A validated comparison requires
the same target/cohort/features, train-only feature fitting, separate
calibration and later validation, then a frozen out-of-time evaluation.
The app reports these gates instead of displaying invented model scores.

Additional data acquisition resumed on 2026-10-09. No Clarity login session
is available, so additional annual samples remain unavailable. The HTTP
downloader and local importer are implemented; archive download, source
rights/schema checks and model qualification are separate steps.

On 2026-10-15, the current Freddie Mac publisher page and Release 47 public
sample/layout files were rechecked. The examples agree with 31/35 layout
positions but their origination and performance Loan Identifier sets are
disjoint, so they are parser references only. Freddie Mac states SFLLD history
is published through March 31, 2026 and requires Clarity registration/sign-in
for full, yearly and sample downloads; see the [official SFLLD page](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
and [reference audit](../PUBLIC_RELEASE_SCOPE.md#private-research-artifacts-are-not-included).

## Reproduction and review

The full foundation rerun reconciled 13 tables and four stable summaries with
zero differing rows. This verifies the descriptive foundation, not the entire
future model/UI release. Supplement exports preserve case/pipeline and method
digests; review findings preserve case/filter/reference context and revision
history.

The current analyst interpretation of the verified stock, cohort and loss
results is in [D01_ANALYST_FINDINGS_VI.md](D01_ANALYST_FINDINGS_VI.md), backed
by a hash-verified audit of the frozen report. It preserves the distinction
between D3 stock, competing-risk incidence and observed conditional loss.

Useful files: PLAN_MODULE_01.md, BACKLOG_STATUS.md, EXPORT_CONTRACT.md,
SOURCE_AND_STUDY_WORKFLOW.md and IMPLEMENTATION_STATUS.md. Run scripts/test.ps1
for the combined application and pinned engine checks. Browser and package
checks use scripts/browser_qa.py and scripts/audit_private_package.py.
