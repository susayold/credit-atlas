# Excel assets

The blank portfolio and affordability input workbooks are public templates. Some builders in this folder and `scripts/` use the host-provided `@oai/artifact-tool` package, which is not distributed in this repository. The dependency is intentionally not copied from the local runtime. The workbooks themselves remain available for direct use in Excel, and the Python app adapters are covered by the public test suite.

The D02 data-reference workbook includes publisher-attributed public tables. To refresh its FHFA NMDB state panel, first rebuild `CreditAtlas-D02-Data-Reference.xlsx` with the host `build_d02_data_reference.mjs` workflow, then run `python scripts/add_nmdb_state_to_reference_workbook.py`. The second step appends the 79,968-row state table and definitions sheet while preserving blank/suppressed values and the other workbook tables.

The public [Toyota](templates/CreditAtlas-Toyota-Recovery-Exception-Ledger.xlsx) and [Nissan](templates/CreditAtlas-Nissan-Exception-Ledger.xlsx) exception workbooks provide formula-driven summaries, filterable period ledgers, and method/source notes. Both contain source-linked monthly aggregates only; unresolved residuals remain visible and are not interpreted as LGD or model results.
