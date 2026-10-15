# CreditAtlas

SEC issuer workspaces now include a **Corporate memo** tab with structured
analyst sections, immutable server-derived filing/trend evidence and private
revision/history export. See the [financial memo guide](docs/CORPORATE_FINANCIAL_MEMO_VI.md).

The KPI analysis now appears first in Risk monitor, with individual metric
dossiers and domain investigation steps. **Xuất KPI Excel** downloads the current
filtered actuals, comparison formulas, support tables and captured review history.
See the [app and Excel guide](docs/KPI_APP_AND_EXCEL_VI.md) for calculation scope
and the outstanding data qualifications.

The Risk monitor now includes **88 source-backed KPI readouts across five domains**,
with formulas, denominators, prior-period comparisons, D3 movement decomposition,
source tables and explicit missing-data dependencies. See the
[Vietnamese data and KPI handbook](docs/KPI_ANALYSIS_GUIDE_VI.md).
Each domain also includes source-scoped data quality evidence: **22 controls**
for completeness, retained duplicates, parsing, integrity, partition coverage
and ledger reconciliation. Unavailable quality profiles remain explicit.
The [KPI analyst review workflow](docs/KPI_ANALYST_REVIEW_WORKFLOW_VI.md) captures
KPI context and verified source digests, preserves immutable evidence across
judgement revisions and supports private history/export in all five domains.
The [next analytics build plan](docs/PLAN_KPI_ANALYTICS_NEXT_VI.md) tracks
regional movement, migrations, policy economics, issuer ratios, ABS cash bridges,
Excel reporting and data/model dependencies. P4 now includes an exact-cent
regional movement bridge between the pinned February/March 2026 snapshots.

The current UI uses task workbenches for Retail, SBA, SEC, Portfolio, ABS and
Market, with direct Excel/review/case launch actions and Ctrl/CmdK task search.
Mortgage has nine workflow routes with source-backed matrix and loan drilldowns.
See the [product research and UX rebuild evidence](docs/PRODUCT_UX_RESEARCH_AND_REBUILD.md)
for scope, vendor sources, verification and the remaining suite qualification gaps.
The [Vietnamese analyst workflow guide](docs/WORKBENCH_USER_GUIDE_VI.md) covers
Excel intake/review and the five domain workflows.

Five-workspace expansion: [detailed plan](docs/PLAN_FIVE_WORKSPACES.md) and
[actual acquisition/build status](docs/FIVE_WORKSPACES_STATUS.md). The first
20-file public batch and 17-table source-native warehouse are complete;
domain adapters, additional source tracks and application/model qualification
remain in progress.

P5 now includes a direct issuer auto-ABS source package and reported servicing
adapter: World Omni 2025-A prospectus plus 20 monthly certificates, 2,980
typed reported metrics, pool/note/distribution/reserve reconciliations and an
independent raw-XLS/SQL audit. See the
[structured ABS source workflow](docs/STRUCTURED_ABS_SOURCE_WORKFLOW.md).
Selected [prospectus terms and numerical checks](docs/ABS_PROSPECTUS_TERMS_AND_NUMERICS.md)
now cover seven issued tranches, base interest/day counts, funded sequential
principal with A-2 pro-rata, OC/reserve and review trigger. Full contractual
waterfall and agreement/amendment verification remain in progress.
The [pre-acceleration waterfall workflow](docs/ABS_WATERFALL_WORKFLOW.md)
now separates due/paid, cash/reserve and tranche payments, reconciles 20
monthly reports conditionally, and supports declared maturity/terminal
scenarios. The [ABS evidence app](docs/ABS_APP_WORKFLOW.md) now exposes source
periods, due/paid cash ledgers, tranche allocations, source checks and private
period exports. Legal regime and complete obligations remain unverified.

The app now includes the five-workspace source catalog and **P1 Retail
Behavioral Risk Lab**, with verified frozen-model validation/holdout results,
reliability tables and private aggregate exports. See the
[suite app workflow](docs/SUITE_APP_AND_RETAIL_WORKFLOW.md) and
[retail research model card](docs/RETAIL_FROZEN_HOLDOUT_AND_MODEL_CARD.md).

P3 now has a dictionary-backed SBA adapter for all 2,190,504 source records,
with exact Decimal amounts, retained duplicate records, quality flags and
four descriptive marts. See the [SBA data contract](docs/SBA_BUSINESS_DATA_CONTRACT.md).
The [business app](docs/BUSINESS_APP_WORKFLOW.md) supports program/cohort/state/industry
filters, quality findings and private scoped exports. The separate
[bankruptcy ratio app](docs/BANKRUPTCY_RATIO_WORKFLOW.md) now covers 43,405
original-ARFF statements across five horizons and 64 financial variables,
preserving the CSV mirror and 2,092 documented precision differences.
Horizon/feature selection and private reports are available. Its one-year
[frozen study protocol and train-only features](docs/BANKRUPTCY_FROZEN_PROTOCOL_AND_FEATURES.md)
are prepared with duplicate groups kept together and reserved final rows
excluded from development encoding. Independent SQL transformation audit passed.
The one-year [bankruptcy development validation and model freeze](docs/BANKRUPTCY_VALIDATION_AND_MODEL_FREEZE.md)
now includes fixed-model fitting, separate calibration, paired group uncertainty
and a frozen boosting/Platt champion. Its 591-row reserved final was evaluated
once with a consumed access ledger, saved-score verification and group
uncertainty; see the [final research model card](docs/BANKRUPTCY_FINAL_MODEL_CARD.md).
The [model evidence app](docs/BANKRUPTCY_MODEL_APP_WORKFLOW.md) now separates
validation and final results, uncertainty, cohorts and private aggregate export.
The [SEC issuer financials app](docs/SEC_ISSUER_FINANCIALS_WORKFLOW.md) adds
105,441 exact source facts, 13,374 filings and 67 filing-specific annual research
statements for AAPL/MSFT/F/GM, with units/period evidence and undefined/conflicting
ratios kept unavailable. Finding/review workflows, raw filing/custom-tag/debt
parsing, issuer memos and production qualification remain in progress.

P4 also has a [typed exposure inventory](docs/EXPOSURE_IMPORT_WORKFLOW.md):
9,698 actual March 2026 Freddie sample observations, 141 zero balances and
USD 915,208,989.12 reported UPB. CLI import, currency-specific concentration,
source verification, API/UI and exact private exports are available. Actual
PD/LGD/EAD are absent, so EL remains unavailable; an explicitly declared
factorized research-assumption engine is tested separately. Independent
Fraction/SQL audit passes 66 checks. The [observation movement bridge](docs/EXPOSURE_MOVEMENT_WORKFLOW.md)
adds February–March 2026 source reconciliation, ordered amount/bucket changes,
explicit entries/exits/currency migrations, residuals and private exports.
Independent original-CSV/Fraction bridge audit passes 500 checks and actual
inventory/bridge browser acceptance passes eight.
The [declared scenario workbench](docs/EXPOSURE_SCENARIO_WORKFLOW.md) adds
versioned baseline/shock assumptions, explicit CURRENT eligibility/exclusions,
PD odds/LGD/EAD sensitivity, disclosed LGD clipping and ordered EL attribution.
Its illustrative parameters are uncalibrated; source EL stays unavailable.
Independent original-CSV Decimal(90) audit passes 2,755 checks; UI/private
exports retain the assumption version and authoritative exact rational values.
The [declared cash-shortfall ECL/staging workbench](docs/EXPOSURE_ECL_WORKFLOW.md)
adds monthly conditional-to-marginal default probabilities, explicit snapshot
SICR/default policies, full contractual/recovery timing, scenario weights and
monthly effective-rate discounting. The actual UPB source is scaled by an
illustrative 36-month bullet schedule; cash/risk inputs and classifications
are unobserved assumptions. Independent original-CSV/Fraction audit passes
1,885 checks; accounting qualification and actual contract adapters remain open.
ECL, calibrated stress, ownership and obligor linkage remain in progress.

The [tail risk workbench](docs/EXPOSURE_TAIL_WORKFLOW.md) now runs reproducible
finite-position Monte Carlo with declared correlation/recovery sensitivities,
mean-loss uncertainty, empirical VaR/ES and joint-tail segment contributions.
Actual research receipt `exposure-tail-10a079f18dc9` uses 9,602 eligible
observations and 4,096 draws per case; source EL remains unavailable. The
independent CSV/Fraction/quadrature audit passed 94,393 checks. Correlation,
PD/LGD/EAD and recovery coupling are illustrative assumptions, not calibrated
portfolio predictions or qualified capital/ECL. Multi-seed convergence,
borrower linkage and calibrated dependence remain open.
The [stability and review workbench](docs/PORTFOLIO_STABILITY_AND_REVIEW.md)
adds three-seed/three-draw-count diagnostics and private source-bound review
packages with owner/expiry, version history, stale-edit conflicts and evidence
verification. A research review does not approve accounting/capital use.

P4 now has a historical FDIC panel: 42 quarters (2016Q1–2026Q2), 214,809
bank-quarter reports, custom size peers and matched-quarter asset changes.
Independent raw JSON reconciliation passed all quarters. See the
[FDIC bank panel workflow](docs/FDIC_BANK_PANEL_WORKFLOW.md) and
[bank app workflow](docs/BANK_APP_WORKFLOW.md). The P4 app supports quarter/peer
filters, institution timelines and private scoped exports;
consolidation-adjusted industry aggregates and loan-book loss workflows remain
in progress.
The [country observatory](docs/COUNTRY_OBSERVATORY_WORKFLOW.md) adds 122,892
World Bank annual observations across seven indicators (1960–2025), with
217 economies and 49 source aggregates kept apart. Same-year comparisons,
missing-aware timelines and private exports are available; sovereign PD,
vintage backtesting and calibrated macro stress relationships remain unqualified.

P5 now includes a native-date market explorer, source quality flags, private
exports and an assumed fixed-coupon bond workbench with price, duration,
convexity, DV01 and repricing shocks. Its 46,675 source observations retain
994 DGS30 documentation conflicts as raw evidence while excluding those values
from calculations and charts. See the [market and bond workflow](docs/MARKET_AND_BOND_WORKFLOW.md)
for the independent 180-scenario numerical audit, source restrictions and
remaining actual ABS/deal work. The complete software suite passes 1,003 tests;
the market browser acceptance passes 13 checks; the ABS browser acceptance
passes 12 checks, including source/export parity and 390px mobile.

P2 now also has a separate [HMDA public application data workflow](docs/HMDA_APPLICATION_WORKFLOW.md):
347,056 Maryland/home-purchase/site-built records across 2023–2025, all 99
public fields retained, exact optional numeric values and 7,477 dimension
marts. Public-row duplicates remain; application outcomes are not default
labels. The [HMDA app](docs/HMDA_APP_WORKFLOW.md) supports intersecting
year/lender/county/product/DTI filters, denominator-aware breakdowns,
missing-aware timelines and exact private aggregate exports. The
[dated lender reference overlay](docs/HMDA_REFERENCE_WORKFLOW.md) displays
same-year names with LEI, explicit unmatched/ambiguous labels, whole-year
coverage and exact labeled exports; browser acceptance passes 12 checks.
The [cohort comparison workflow](docs/HMDA_COHORT_WORKFLOW.md) adds three
explicit mortgage/application cohorts, ordered attrition and fixed-2023
composition rates. Incomplete support remains unavailable; common-support
results have their own scope. Independent raw-CSV audit passes 70 checks,
and current HMDA browser acceptance passes 17 checks, including reload/export.
County source acquisition, coverage standardization and findings/review
remain in progress.

One research application, five domain workspaces. The first implementation is
**P2 / D01 — Residential Mortgage Lifecycle & Loss Lab**.

The implementation follows chapter 47 of the consolidated credit-risk research
plan. The mortgage analytics engine is selectively vendored from the existing
`susayold/credit-risk-strategy-lab` repository, with a pinned upstream commit and
per-file digests. Raw data, row-level derived artifacts, review records and run
receipts stay in ignored private directories on `D:`.

## Initial implementation

- Rebuild the actual authorized Release 47 annual sample rather than inventing data.
- Preserve the existing early-entry, first-observed 12-month D3-before-prepayment
  target and source semantics.
- Serve portfolio, vintage, transition, episode and observed-loss evidence from
  frozen, verified runs.
- Keep model readiness and public-export eligibility separate from descriptive
  data readiness. A one-vintage sample cannot pass the research training gate.

The current status and execution evidence are in `docs/IMPLEMENTATION_STATUS.md`.
The application is for local/private research. It does not make credit approvals,
claim production/regulatory validation or present D3 event risk as accounting ECL.

## Run locally

From D:\data\Codex\credit-atlas in PowerShell:

    .\scripts\run.ps1

Open http://127.0.0.1:8770/. The server binds only to loopback. Python dependencies
must be installed in the local .venv, including editable installs of this project
and vendor/credit_risk_strategy_lab. The bundled existing private source snapshot
is local-only and excluded from Git.

For a new environment, run scripts/setup.ps1. It installs the observed dependency
lock and both editable packages, with caches/temp files on D:.

To run engine and application checks:

    .\scripts\test.ps1

To check official source access directly:

    .\.venv\Scripts\python.exe -m credit_atlas.cli source-access

For the separate NSMO D02 codebook and weighted-table audits, install the PDF
parsers with `python -m pip install -e ".[research]"`. Obtain the current FHFA
PUF and review/accept its Notice of Monitoring and Terms directly with FHFA;
keep the PUF and resulting private audit receipts outside Git. See the
[NSMO D02 plan](docs/NSMO_D02_CASE_BUILD_PLAN_VI.md) for commands, scope, and
the state/weighting limitations. The D02 page also exposes separate HUD FHA
and FHFA NMDB aggregate benchmarks with filterable Excel workbooks; they provide
portfolio context and are not pooled into NSMO or used as loan-level labels.
See the [NMDB quarterly performance source review](docs/NMDB_PERFORMANCE_CONTEXT_VI.md)
for its 2002Q1–2026Q2 coverage, source hashes and metric limitations. The separate
[wave-comparability audit](docs/NSMO_WAVE_COMPARABILITY_AUDIT_VI.md) documents
the official questionnaire inventory, SAS-coded wave coverage index, and the
six-item cross-wave candidate pilot. Questionnaire PDFs, raw PUF rows, and
exact private receipts stay outside this repository.

To download authorized annual sample URLs through HTTP:

    .\.venv\Scripts\python.exe -m credit_atlas.cli download-samples --manifest data/private/access/downloads.json --cookie-file data/private/access/clarity-cookies.txt

The private JSON manifest contains annual_samples, a list of objects with integer
year, release 47 and the actual official URL obtained from Clarity. No download
endpoint is guessed. The optional cookie file uses Netscape format, stays local,
and is never written into receipts or chat. A 401/403 means authentication is
still required. Downloads are stored in data/private/incoming with digest receipts;
schema, permitted use and multi-vintage qualification precede modeling.

The detailed implementation plan is docs/PLAN_MODULE_01.md.

To register an authorized local annual ZIP and prepare temporal study inputs,
see docs/SOURCE_AND_STUDY_WORKFLOW.md. The prepare-features command audits
train-only preprocessing and saved encoder parity without fitting risk models.
The gated assess-study command is documented in docs/DEVELOPMENT_ASSESSMENT.md.
Report filtering and schema-2 lineage
are documented in docs/EXPORT_CONTRACT.md. Data grain, denominator and
source limits are explained in docs/D01_DATA_AND_METHOD_CARD.md.

Engineering acceptance commands:

    .\.venv\Scripts\python.exe -X utf8 scripts/browser_qa.py
    .\.venv\Scripts\python.exe -X utf8 scripts/audit_private_package.py
    .\.venv\Scripts\python.exe -X utf8 scripts/benchmark_api.py

They use actual verified case data, create separate QA review databases and
write private receipts. Browser QA uses preinstalled Google Chrome with
Playwright; no source data or findings are published.

Excel intake, editable scenario workbooks and native-currency review exports:
[EXCEL_WORKFLOW.md](docs/EXCEL_WORKFLOW.md). The input template is packaged
under apps/excel/templates; no Microsoft Excel installation is required.

Retail declared decision/cost scenarios, capacity checks and immutable policy
versions: [RETAIL_POLICY_WORKFLOW.md](docs/RETAIL_POLICY_WORKFLOW.md).

Validation subgroup coverage, calibration, AUC and declared policy capture
diagnostics: [RETAIL_SUBGROUPS_WORKFLOW.md](docs/RETAIL_SUBGROUPS_WORKFLOW.md).
Studies retain source demographic codes, report small groups as unavailable,
and bind private exports to a frozen model and saved policy case.

Frozen validation global/local model inspection:
[RETAIL_EXPLANATIONS_WORKFLOW.md](docs/RETAIL_EXPLANATIONS_WORKFLOW.md).
Whole-cohort grouped permutations and exact four-group probability Shapley
explanations share the verified model bundle and a private training reference.
Complete validation-client browsing, paginated token search and whole-cohort
contribution distributions:
[RETAIL_COHORT_EXPLANATIONS_WORKFLOW.md](docs/RETAIL_COHORT_EXPLANATIONS_WORKFLOW.md).

For complete regression with fresh sequential processes on a low-memory host:
`.\.venv\Scripts\python.exe -X utf8 scripts/test_batches.py --batch-files 8`.
The runner checks complete collection against every batch JUnit count.
# MVP giao diện

Mở [CreditAtlas local](http://127.0.0.1:8770/) để xem trang chủ mới, năm domain
và Portfolio/Excel. [Hướng dẫn và bằng chứng UI](docs/MVP_UI_WORKFLOW.md).


- [Plan chi tiết 50 chức năng, đồng bộ nội dung trong app](docs/PLAN_WORKBENCH_DETAIL.md)

- [Enterprise credit monitor research — 14 hãng, source-to-feature mapping](docs/ENTERPRISE_CREDIT_MONITOR_RESEARCH.md)
- App mặc định: `http://127.0.0.1:8770/?view=monitor`; catalog: `?view=suite`.
