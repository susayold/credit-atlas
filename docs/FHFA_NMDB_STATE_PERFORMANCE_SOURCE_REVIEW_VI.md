# FHFA NMDB mortgage performance by state

**Snapshot reviewed:** 2026-10-16 · **publisher release:** 2026-09-30 · **data through:** 2026Q2.

## What this source contains

FHFA publishes a state-level quarterly extract from the National Mortgage Database (NMDB). The archive contains 79,968 rows: 50 states and the District of Columbia × 98 quarters (2002Q1–2026Q2) × four mortgage-market groups × four performance series. The data are aggregates from a nationally representative 5% sample of first-lien, closed-end mortgages reported to one of three credit bureaus; they are not loan-level records. The curated table keeps publisher percentages in percentage points and preserves `suppressed` separately from blank values.

| Series | Meaning | Main use |
|---|---|---|
| `P3089DL` | Active-mortgage share 30 or 60 days past due at quarter end | State-level early delinquency trend/context |
| `P90DL` | Active-mortgage share 90, 120, 150 or 180 days past due | Serious delinquency context |
| `PFORECL` | Active-mortgage share in foreclosure, bankruptcy or deed-in-lieu | Distressed-process context |
| `PFORB` | Active mortgages reported in forbearance | Relief/forbearance context; available from 2019Q4 |

Each series is a quarter-end share among active loans, not a fixed-horizon cohort default probability. The four mortgage-market groups are separate publisher series. Do not add `All Mortgages` to its components.

## Data quality and limits

The source has 68 suppressed cells (17 in each series), blanked by the publisher for cells with fewer than three loan records. The `PFORB` series is blank before 2019Q4 (14,484 state-market-quarter cells); those blanks mean unavailable, not zero. The additional 51 blank cells are suppressed forbearance cells. All 816 state-market-series cells for 2026Q2 are present and unsuppressed.

FHFA notes that the latest two quarters are preliminary because credit-bureau data arrive with lag. It also warns that seriously past-due mortgages may be undercounted from 2006 through 2012 because some credit histories were purged. State-to-state levels reflect sample coverage and mortgage-market mix as well as borrower risk. The sample represents owner-occupied, site-built mortgages better than investor or manufactured-home loans.

Use this source to add state-level trend and portfolio context to the mortgage workspace. Do not join these values onto Freddie Mac or NSMO loans, train the D01 label from them, or describe the rates as individual borrower PD. They are also not property valuation data; use the separate FHFA HPI table for house-price index context.

## Reproduction and workbook

The acquisition script validates the official archive's headers, state scope, time fields, 51 × 98 × 4 × 4 key coverage, duplicates, suppression and value ranges before writing the public CSV and hash receipt. `scripts/add_nmdb_state_to_reference_workbook.py` appends the 79,968-row filterable `NMDB states` table and separate `NMDB state definitions` sheet to the Excel reference workbook without re-importing its other large sheets; blank cells remain empty in Excel. The local app API returns only one selected state's 1,568 rows per request.

- [FHFA NMDB source page](https://www.fhfa.gov/data/nmdb)
- [FHFA 2026Q1 dictionary and technical notes](https://www.fhfa.gov/document/d/nmdb/nmdb-aggregate-statistics-data-dictionary-technical-notes-2026q1.pdf)
- [State quarterly ZIP](https://www.fhfa.gov/document/d/nmdb/nmdb-mortgage-performance-statistics-states-quarterly.zip)
- [Curated CSV](data/nmdb-performance-state-quarterly-2026q2.csv)
- [Hash and coverage receipt](data/nmdb-performance-state-quarterly-2026q2-receipt.json)
- [Acquisition script](../scripts/acquire_nmdb_state_performance.py)
- [Workbook integration script](../scripts/add_nmdb_state_to_reference_workbook.py)

The raw archive remains in private local storage and is not included in the public repository.
