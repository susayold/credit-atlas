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

The FHFA/CFPB NSMO v7.0 source review, codebook-grounded status parser, aggregate-only audit scripts, FHFA Appendix D weighted-table checks, SAS labels/formats, sanitized 587-field dictionary/value-label crosswalk, a 319-field/46-wave structural coverage index, and a six-item candidate crosswalk are included. The acquisition/audit scripts cover the official historical questionnaire PDFs, but the PDFs and question-text receipts remain private. The actual PUF was acquired privately
after the project owner authorized the FHFA Notice of Monitoring and NMDB Terms
gate; no NSMO ZIP/CSV, identifiers, row-level extracts, cookies, or private
receipts are part of this public repository. Anyone reproducing the research
must obtain the current PUF directly from FHFA and accept its current notice and
terms themselves. The associated analysis note includes FHFA's required
disclaimer and does not imply agency endorsement.

Aggregate-only target feasibility screens for four-quarter (about 12-month)
performance snapshots are also included, with synthetic tests and a sanitized
method note. The local NSMO app includes a SHA-bound aggregate API and UI to
compare repeated quarterly landmarks with a one-landmark-per-mortgage sizing
diagnostic, filter origination vintages, and inspect quarterly censoring. It
shows no loan rows or IDs. The private receipts and all exact PUF-derived tables
stay outside Git. The note documents that the candidate protocol is not frozen
and that no target labels, PD estimates, or model outputs are part of this
release.


## Host-provided Excel builder dependency

Blank input workbooks are included. Some workbook-generation scripts call the host-provided `@oai/artifact-tool` package; the package itself is not part of this public release. See `apps/excel/README.md`.

The HUD August 2026 FHA monthly-performance snapshot is a separately attributed
public aggregate transcription from the official report's Table 1 and Table 3.
It contains no FHA loan-level records, is not merged with NSMO/Freddie, and
documents that the report PDF binary was not saved after direct retrieval
returned HTTP 403.

The D02 Excel reference workbook also includes an aggregate-only extraction of
FHFA NSMO Technical Report v7.0 Table 3 response counts by wave (mail, online
English, online Spanish). The 48 survey-wave rows are reconciled to the report's
printed totals; this table contains no respondent/loan records or mode-to-loan
linkage. Waves 47–48 are identified as outside the v7.0 PUF.
