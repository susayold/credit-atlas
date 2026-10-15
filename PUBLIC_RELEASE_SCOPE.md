# Public release scope

This folder is a public-source release of the CreditAtlas software and technical documentation. It preserves application code, source-level tests, and explicitly attributed public-source metadata or aggregate reference files while excluding private research payloads.

## Private research artifacts are not included

The following are deliberately absent: private `data/`, `artifacts/`, and `outputs/`; local SQLite databases; Parquet/CSV/XLSX datasets derived from private borrower-level data; screenshots/review records; environment folders; `workspace.local.json`; and source-access cookies or credentials. Several local datasets contain borrower-level or otherwise restricted records; source permissions do not automatically permit republication. Do not add them to Git. The root `.gitignore` blocks private workspace paths. Small public-source tables under `docs/data/` and their attributed reference workbooks may be included when they contain no private records and their source/use limits are documented.

Internal markdown notes were retained as technical history, but links to omitted local evidence were redirected here. Values and findings in those notes are not a substitute for the source artifacts, and this public repository does not claim that excluded data is available to reproduce them.

## Vendored engine

`vendor/credit_risk_strategy_lab/` contains the selected source files pinned to commit `8d9994cfcb91fe871d66a4238c3f56053d71e920`. Its private datasets, derived runs, and caches are omitted. The upstream source was a user-owned private repository. No separate open-source license is asserted by this public copy; inspect the upstream notices before reuse.

## Data acquisition

Users must obtain source data directly from the publisher, review current terms, keep credentials local, and register data through the documented workflow. Do not use this repository to bypass authentication or data-use restrictions.


## Public test scope

The public test command runs source-level and synthetic integration tests. A small explicit set of tests whose fixture contracts require the omitted local borrower sources or private evidence receipts is skipped when those local inputs are absent; the node IDs and reason are recorded in `tests/public_private_data_skiplist.json`. The public test runner does not download or reconstruct those payloads.

The Ginnie Mae LoanPerf source review and aggregate-only local ZIP auditor are
included as software/documentation. The production loan-level payload is not
included; the user must first accept the publisher's current Terms of Use and
acquire the data privately.

The FHFA/CFPB NSMO v7.0 source review, codebook-grounded status parser, aggregate-only audit scripts, FHFA Appendix D weighted-table checks, SAS labels/formats, sanitized 587-field dictionary/value-label crosswalk, a 587-row derived predictor timing/use-boundary inventory, a 319-field routing-review crosswalk, a seven-field question-reference reconciliation, a 319-field/46-wave structural coverage index, and a six-item candidate crosswalk are included. The predictor inventory is not an approved feature allowlist; no feature is approved. The routing crosswalk retains original omitted references, shows the derived question-number reconciliation, and flags legacy gateways; it does not claim to resolve full wave/mode paths. The acquisition/audit scripts cover the official historical questionnaire PDFs, but the PDFs and question-text receipts remain private. The actual PUF was acquired privately
after the project owner authorized the FHFA Notice of Monitoring and NMDB Terms
gate; no NSMO ZIP/CSV, identifiers, row-level extracts, cookies, or private
receipts are part of this public repository. Anyone reproducing the research
must obtain the current PUF directly from FHFA and accept its current notice and
terms themselves. The associated analysis note includes FHFA's required
disclaimer and does not imply agency endorsement.

An aggregate-only NSMO C-state horizon-sensitivity table (2/4/8 quarterly
snapshots) is included with the research docs and the filterable NSMO Excel
reference workbook. It contains only unweighted support/censor counts, not loan
rows or identifiers. Its source-hash-bound receipt and the underlying PUF remain
private; this table is feasibility evidence, not event rates, PD or a frozen
target.

Aggregate-only target feasibility screens for four-quarter (about 12-month)
performance snapshots are also included, with synthetic tests and a sanitized
method note. The local NSMO app includes SHA-bound aggregate APIs and UI to
compare repeated quarterly landmarks with one-landmark sizing and one-time
dynamic risk-set diagnostics, filter origination vintages and entry states, and
inspect quarterly censoring and 6/12/24-month horizon sensitivity. It shows no
loan rows or IDs. Private receipts and PUF-derived loan-level tables stay
outside Git. The note documents that the candidate protocol is not frozen
and that no target labels, PD estimates, or model outputs are part of this
release.


## Host-provided Excel builder dependency

Blank input workbooks are included. Some workbook-generation scripts call the host-provided `@oai/artifact-tool` package; the package itself is not part of this public release. See `apps/excel/README.md`.

The HUD August 2026 FHA performance workbook contains separately attributed
public aggregate transcriptions from Tables 1–6 of the official report: monthly
performance, portfolio subgroups, new-90+ reported reasons, foreclosure
statistics, REO recovery by geography, and REO loss components. It contains no
FHA loan-level records, is not merged with NSMO/Freddie, and documents that the
report PDF binary was not saved after direct retrieval returned HTTP 403. The
local NSMO context page renders all six source tables with separate KPI and
denominator notes. The D02 workbook includes every public CSV dataset as an
Excel Table, with source definitions and scope notes; CSV remains the app's
canonical input format.

The D02 Excel reference workbook also includes aggregate-only extractions of
FHFA NSMO Technical Report v7.0 Tables 3–6: response counts by mail/online mode,
usable-response dispositions, and origination-year scope totals. They reconcile
to printed report totals and contain no respondent/loan records, response-mode
linkage, or disposition-to-loan linkage. Waves 47–48 are identified as outside
the v7.0 PUF.

The same reference workbook includes FHFA's public quarterly state All-Transactions
HPI from 1975Q1 through 2026Q2 with an attributed source receipt. It is aggregate
geographic context, not a property-level valuation or model-ready point-in-time
predictor.

The D02 Excel reference workbook also includes FHFA NMDB quarterly performance
aggregates by state and mortgage market for 2002Q1–2026Q2 (79,968 curated rows).
It is a separate aggregate benchmark, not loan-level performance data; small
cells remain suppressed and pre-2019Q4 forbearance values remain blank. The
source review documents the active-loan denominator, preliminary latest
quarters, and limits on model or cross-source use.

Ginnie Mae's public MBS Single-Family Loan Payment History layout review and
aggregate-only TXT/single-member-ZIP auditor are included. The official layout/sample files and
sample-derived audit receipt stay in private D: storage; no identifiers or
production payment-history rows are included. The parser accepts the local
pipe-delimited source format and emits only aggregate status/history counts,
totals checks, and file hash metadata. Production acquisition remains behind
the user's authenticated Ginnie session and current Terms of Use.
