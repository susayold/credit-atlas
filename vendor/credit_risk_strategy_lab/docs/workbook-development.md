# B29 private development workbook

This is a real aggregate research workbook, not the public release and not proof
that the analytical B00-B35 plan is complete. The approved 15-sheet inventory is
present. ModelComparison, Calibration, Strategy and ForecastStress contain explicit
unmet gates, not invented results. Vintage contains only the available 2012 label
summary; it is not a completed multi-vintage study. Cure contains observed event
and distinct-loan counts, not a horizon-adjusted cure probability. Vintage now
also includes the verified 6/12/24-month competing-risk aggregates. Loss contains
the observed one-terminal-per-loan bridge and B18 gate, not an expected-loss model
or lender monetary bridge.

## Lineage and calculation

`python -m crsl.workbook_data --pipeline-run artifacts/private/pipeline-83667cc64126
--segmented-run artifacts/private/segmented-transitions-5f034c3464c3`
builds an aggregate payload from hash-checked Parquet. It checks common canonical
lineage, monthly metric identities, label uniqueness, outcome reconciliation and
the segmented transition mart's canonical/hash lineage.
No loan identifier or raw loan-level record is exported into the payload.

`scripts/build_workbook.mjs` authors one XLSX using the bundled artifact runtime.
It builds coverage fractions, monthly count/balance shares, count and opening-UPB
transition probabilities, and independent workbook reconciliations with formulas.
Formulas are recalculated and checked against canonical ratios. A zero denominator
and a changed numerator/denominator are exercised then restored. Gated outputs stay
textual unavailable, never fabricated numeric zero.

`scripts/verify_workbook.py <workbook-directory>` uses bundled openpyxl read-only to
compare every preview data cell with the saved XLSX cache. It scans formula errors,
sheet visibility, freeze panes, comments, names, external links, macros and private
paths. An initial exported en-dash corruption was caught; ASCII interval notation
fixed the mismatch in the builder. Do not patch exported XML to hide this issue.

The current workbook directory is
`outputs/01a08025-b938-7313-b1e6-a75f2e46bcdf/pipeline-83667cc64126-final`.
It is gitignored and outside `site/dist`. `registry.json` contains XLSX, input and
preview SHA256. `qa.json` records 4,569 preview cells across 15 sheets matching the
saved file, with zero formula errors or hidden sheets. The `03_Portfolio` sheet
includes the verified 102-row, 13-dimension origination profile with separate
count/principal shares. The `05_Transitions` sheet
includes 61 verified Relief/non-Relief/unknown segment transition cells with pair
count, distinct-loan support, missing-UPB counts and count/balance probabilities.
All sheets were rendered and
visually reviewed; clipped cure identifiers were replaced with readable labels and
proper definitions. Native Microsoft Excel recalculation is **not verified**.

## Local preview and download

Start `python -m crsl.research_server --workbook-directory <workbook-directory>`.
The server binds only 127.0.0.1:8766. It serves a fixed allowlist, not repository
directories. Workbook bytes, preview and website snapshot are frozen together after
hash / QA / pipeline checks. Unexpected Host and cross-site fetch requests are
rejected. No CORS permission or directory listing is provided. This is a local
research preview, not a production authentication or privacy certification.

The Excel Library hash route loads preview only when opened. Users can select a
sheet, search, sort and page the main table, and download the actual XLSX directly.
Filename, run and checksum are visible. Date/percentage display is formatted from
typed cached values; nulls remain unavailable. The coverage outcome table is included.

No workbook is copied into the deployable static directory. Hosting remains deferred
until a public-safe release or explicitly labeled synthetic public workbook is
validated. HTTP download/hash checks and JS syntax checks do not establish clean-
browser, keyboard, screen-reader or mobile interaction acceptance; those remain open.
