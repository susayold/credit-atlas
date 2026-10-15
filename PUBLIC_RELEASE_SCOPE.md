# Public release scope

This folder is a public-source release of the CreditAtlas software and technical documentation. It preserves the full application code and source-level tests while excluding private research payloads.

## Private research artifacts are not included

The following are deliberately absent: all `data/`, `artifacts/`, `outputs/`, local SQLite databases, generated Parquet/CSV/XLSX datasets, screenshots/review records, environment folders, `workspace.local.json`, and source-access cookies or credentials. Several local datasets contain borrower-level or otherwise restricted records; source permissions do not automatically permit republication. Do not add them to Git. The root `.gitignore` blocks these paths.

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

The FHFA/CFPB NSMO v7.0 source review, codebook-grounded status parser, aggregate-only audit scripts, FHFA Appendix D weighted-table checks, SAS labels/formats, and sanitized 587-field dictionary/value-label crosswalk are included. The actual PUF was acquired privately
after the project owner authorized the FHFA Notice of Monitoring and NMDB Terms
gate; no NSMO ZIP/CSV, identifiers, row-level extracts, cookies, or private
receipts are part of this public repository. Anyone reproducing the research
must obtain the current PUF directly from FHFA and accept its current notice and
terms themselves. The associated analysis note includes FHFA's required
disclaimer and does not imply agency endorsement.


## Host-provided Excel builder dependency

Blank input workbooks are included. Some workbook-generation scripts call the host-provided `@oai/artifact-tool` package; the package itself is not part of this public release. See `apps/excel/README.md`.
